#!/usr/bin/env python3
"""Forensic analysis of a reference video -> profile.json + summary.md + review sheets.

Usage:
  analyze_reference.py REF.mp4 OUTDIR                 # full pass (cuts are provisional)
  analyze_reference.py REF.mp4 OUTDIR --cuts final.json  # re-run shot-level stats on adjudicated cuts (fast, cached)

Pass 1 writes sheets/cuts_review.png: every cut that fewer than 3 of 4 detector configs agreed on,
as before|after frame pairs labelled with the cut index. Look at it once, then write
OUTDIR/cuts_final.json = {"cuts": [seconds, ...]} (keep real cuts, drop whips/motion) and re-run with --cuts.
"""
import argparse, os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (probe, dump_json, load_json, extract_wav, loudness, frames_at, labelled_sheet, sync_test, fmt_t)

AW = 160  # analysis width (px); enough for stats, cheap to decode


# ---------------------------------------------------------------- per-frame features (cached)
def frame_features(path, cache):
    if os.path.exists(cache):
        return dict(np.load(cache))
    cap = cv2.VideoCapture(path); prev = None; rows = []; grays = []
    est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1; step = max(1, est // 3000)  # edge maps: <=3000 samples
    while True:
        ok, f = cap.read()
        if not ok: break
        h, w = f.shape[:2]; f = cv2.resize(f, (AW, int(h * AW / w)))
        lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(np.float32)
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        L = lab[..., 0] * 100 / 255
        sharp = cv2.Laplacian(g, cv2.CV_32F).var()
        noise = float(np.median(np.abs(g - cv2.GaussianBlur(g, (5, 5), 0))))
        hh, ww = g.shape; ch, cw = hh // 4, ww // 4
        center = g[ch:-ch, cw:-cw].mean(); corners = np.mean([g[:ch, :cw].mean(), g[:ch, -cw:].mean(), g[-ch:, :cw].mean(), g[-ch:, -cw:].mean()])
        if prev is None: dx = dy = diff = 0.0
        else:
            (dx, dy), _ = cv2.phaseCorrelate(prev, g); diff = float(np.abs(g - prev).mean())
        shadows, highs = L < 25, L > 75
        rows.append([L.mean(), np.percentile(L, 1), np.percentile(L, 50), np.percentile(L, 99), L.std(),
                     hsv[..., 1].mean() / 255, lab[..., 1].mean() - 128, lab[..., 2].mean() - 128,
                     (lab[..., 1][shadows].mean() - 128) if shadows.any() else 0, (lab[..., 2][shadows].mean() - 128) if shadows.any() else 0,
                     (lab[..., 1][highs].mean() - 128) if highs.any() else 0, (lab[..., 2][highs].mean() - 128) if highs.any() else 0,
                     sharp, noise, corners / max(center, 1), diff, dx, dy])
        prev = g
        if len(rows) % step == 1 or step == 1: grays.append(cv2.Canny(f, 80, 160) > 0)
    cap.release()
    a = np.array(rows, np.float32)
    keys = ["L", "L1", "L50", "L99", "Lstd", "sat", "a", "b", "sh_a", "sh_b", "hi_a", "hi_b", "sharp", "noise", "vign", "diff", "dx", "dy"]
    feat = {k: a[:, i] for i, k in enumerate(keys)}
    feat["edges"] = np.packbits(np.array(grays, bool), axis=0) if grays else np.zeros(1, np.uint8)
    feat["edge_shape"] = np.array(np.array(grays).shape); feat["edge_step"] = np.array(step)
    np.savez_compressed(cache, **feat)
    return feat


# ---------------------------------------------------------------- cuts
def detect_cuts(path, fps):
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector, AdaptiveDetector
    min_len = max(3, int(round(fps * 0.1)))
    configs = [("content@12", ContentDetector(threshold=12, min_scene_len=min_len)),
               ("content@18", ContentDetector(threshold=18, min_scene_len=min_len)),
               ("content@27", ContentDetector(threshold=27, min_scene_len=min_len)),
               ("adaptive", AdaptiveDetector(min_scene_len=min_len))]
    lists = []
    for _, det in configs:
        v = open_video(path); sm = SceneManager(); sm.add_detector(det); sm.detect_scenes(v, show_progress=False)
        lists.append([s[0].get_frames() for s in sm.get_scene_list()][1:])
    allc = sorted(c for l in lists for c in l); clusters = []
    for c in allc:
        if clusters and c - clusters[-1][-1] <= 2: clusters[-1].append(c)
        else: clusters.append([c])
    cuts = []
    for cl in clusters:
        fr = int(round(np.median(cl)))
        votes = sum(1 for l in lists if any(abs(x - fr) <= 2 for x in l))
        cuts.append(dict(frame=fr, t=round(fr / fps, 3), votes=votes))
    return cuts


def classify_transition(feat, fr, fps):
    """Label the join at frame `fr`: hard | flash | dip | gradual | whip."""
    L, diff, sharp = feat["L"], feat["diff"], feat["sharp"]
    n = len(L); w = max(2, int(round(fps * 0.07)))  # narrow: burst shots can be 5-6 frames long
    a, b = max(1, fr - w), min(n - 1, fr + w)
    if a >= b: return "hard"
    neigh = np.r_[L[max(0, a - w):a], L[b:b + w]]
    base = float(np.median(neigh)) if len(neigh) else float(L[fr])
    if L[a:b].max() > base + 35: return "flash"
    if L[a:b].min() < 8 and base > 25: return "dip"
    seg = diff[a:b + 1]
    if seg.sum() > 0 and seg.max() / seg.sum() < 0.35 and np.median(seg) > 3 * np.median(diff): return "gradual"
    s_in = np.median(sharp[max(0, fr - 3 * w):max(1, fr - w)]) if fr - w > 0 else sharp[fr]
    if sharp[max(0, fr - w):fr + w].min() < 0.35 * max(s_in, 1e-3): return "whip"
    return "hard"


# ---------------------------------------------------------------- shots
def shot_stats(feat, cuts_f, nframes, fps, width):
    bounds = [0] + list(cuts_f) + [nframes]; shots = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        if b - a < 1: continue
        sl = slice(a + (1 if b - a > 2 else 0), b)
        dx, dy = feat["dx"][sl], feat["dy"][sl]
        k = np.ones(5) / 5 if len(dx) >= 5 else np.ones(1)
        sx, sy = np.convolve(dx, k, "same"), np.convolve(dy, k, "same")
        speed = float(np.hypot(sx, sy).mean() / AW * 100)       # % of width per frame
        jitter = float(np.hypot(dx - sx, dy - sy).mean() / AW * 100)
        peak = float(np.hypot(dx, dy).max() / AW * 100) if len(dx) else 0
        luma = float(feat["L"][sl].mean())
        motion = ("black" if luma < 3 else "static" if speed < 0.15 and jitter < 0.25 else "whip" if peak > 12 else
                  "handheld" if jitter >= 0.5 else "move" if speed >= 0.4 else "drift")
        shots.append(dict(i=len(shots) + 1, start=round(a / fps, 3), end=round(b / fps, 3), frames=b - a,
                          dur=round((b - a) / fps, 3), luma=round(float(feat["L"][sl].mean()), 1),
                          contrast=round(float(feat["Lstd"][sl].mean()), 1), sat=round(float(feat["sat"][sl].mean()), 3),
                          a=round(float(feat["a"][sl].mean()), 2), b=round(float(feat["b"][sl].mean()), 2),
                          motion=motion, speed=round(speed, 2), jitter=round(jitter, 2)))
    return shots


def blocks_from_shots(shots, total):
    d = np.array([s["dur"] for s in shots]); med = float(np.median([s["dur"] for s in shots if s["motion"] != "black"] or d))
    hold_thr = max(1.0, 2.2 * med)
    labels = ["black" if s["motion"] == "black" else "hold" if x >= hold_thr else "burst" for s, x in zip(shots, d)]
    blocks = []
    for s, lab in zip(shots, labels):
        if blocks and blocks[-1]["kind"] == lab: blocks[-1]["shots"].append(s)
        else: blocks.append(dict(kind=lab, shots=[s]))
    out = []
    for bl in blocks:
        st, en = bl["shots"][0]["start"], bl["shots"][-1]["end"]
        durs = [s["dur"] for s in bl["shots"]]
        out.append(dict(kind=bl["kind"], start=st, end=en, frac=[round(st / total, 3), round(en / total, 3)],
                        n=len(durs), asd=round(float(np.mean(durs)), 3), frames=[s["frames"] for s in bl["shots"]]))
    return out, hold_thr


# ---------------------------------------------------------------- overlays / framing
def persistent_overlays(feat, fps, nframes, cuts_f, mids=None):
    shape = tuple(feat["edge_shape"]) if "edge_shape" in feat else None
    if not shape or len(shape) != 3 or shape[0] < 5: return [], None
    edges = np.unpackbits(feat["edges"], axis=0)[:shape[0]].reshape(shape).astype(bool)
    if mids is None:
        bounds = [0] + list(cuts_f) + [nframes]
        mids = [(bounds[i] + bounds[i + 1]) // 2 for i in range(len(bounds) - 1)]
    step = int(feat.get("edge_step", 1))
    mids = [min(shape[0] - 1, m // step) for m in mids]
    # one sample per *distinct shot*: static content inside a long shot must not look like an overlay
    if len(mids) < 5: return [], None
    pers = edges[mids].mean(0)
    mask = (pers >= 0.6).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask)
    H, W = mask.shape; out = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < 12 or w * h > 0.5 * W * H: continue
        out.append(dict(x0=round(x / W, 3), y0=round(y / H, 3), x1=round((x + w) / W, 3), y1=round((y + h) / H, 3),
                        cy=round((y + h / 2) / H, 3), h_frac=round(h / H, 3), coverage=round(float(pers[lab == i].mean()), 2)))
    return sorted(out, key=lambda o: o["y0"]), pers


def detect_bars(path, n=12):
    cap = cv2.VideoCapture(path); tot = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1; tops = []; sides = []
    for k in np.linspace(0.05, 0.95, n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(k * tot)); ok, f = cap.read()
        if not ok: continue
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); H, W = g.shape
        rows = g.mean(1) < 12; cols = g.mean(0) < 12
        t = np.argmax(~rows) if (~rows).any() else 0; bt = np.argmax(~rows[::-1]) if (~rows).any() else 0
        l = np.argmax(~cols) if (~cols).any() else 0; r = np.argmax(~cols[::-1]) if (~cols).any() else 0
        tops.append((t + bt) / 2 / H); sides.append((l + r) / 2 / W)
    cap.release()
    return dict(top_bottom_frac=round(float(np.median(tops)), 3) if tops else 0, side_frac=round(float(np.median(sides)), 3) if sides else 0)


# ---------------------------------------------------------------- audio
def audio_analysis(path, info, cut_times):
    import librosa
    wav = extract_wav(path); y, sr = librosa.load(wav, sr=22050, mono=True); os.remove(wav)
    dur = len(y) / sr
    if dur < 1 or float(np.abs(y).max()) < 1e-4:
        return dict(present=False)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr); bt = librosa.frames_to_time(beats, sr=sr)
    oenv = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, units="time")
    downbeats, db_src = estimate_downbeats(y, sr, bt, path)
    rms = librosa.feature.rms(y=y, hop_length=sr // 2)[0]
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)); fr = librosa.fft_frequencies(sr=sr)
    flat = float(librosa.feature.spectral_flatness(S=S).mean()); cent = float(librosa.feature.spectral_centroid(S=S, sr=sr).mean())
    # sections via agglomerative clustering on beat-synchronous chroma+mfcc
    sections = []
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr); mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        X = np.vstack([librosa.util.normalize(chroma), librosa.util.normalize(mfcc)])
        Xs = librosa.util.sync(X, beats) if len(beats) > 8 else X
        k = int(np.clip(round(dur / 8), 2, 12))
        bnd = librosa.segment.agglomerative(Xs, k)
        times = librosa.frames_to_time(beats[np.clip(bnd, 0, len(beats) - 1)], sr=sr) if len(beats) > 8 else librosa.frames_to_time(bnd, sr=sr)
        sections = sorted(set(round(float(t), 2) for t in times if t > 0.5))
    except Exception as e:
        sections = []
    lufs, peak = loudness(path)
    # fades: compare first/last 1.5 s RMS slope
    def ramp(seg):
        if len(seg) < 4: return 0.0
        return float(np.polyfit(np.arange(len(seg)), seg, 1)[0] / (seg.mean() + 1e-6))
    r10 = librosa.feature.rms(y=y, hop_length=sr // 10)[0]
    fade_in = ramp(r10[:15]) > 0.08; fade_out = ramp(r10[-15:]) < -0.08
    out = dict(present=True, duration=round(dur, 3), bpm=round(float(np.atleast_1d(tempo)[0]), 2),
               beat_period=round(float(np.median(np.diff(bt))), 4) if len(bt) > 2 else None,
               beats=[round(float(t), 3) for t in bt], downbeats=[round(float(t), 3) for t in downbeats], downbeat_source=db_src,
               onsets=[round(float(t), 3) for t in onsets], rms_halfsec=[round(float(x), 3) for x in rms],
               sections=sections, lufs=lufs, true_peak=peak, spectral_flatness=round(flat, 4), centroid_hz=round(cent),
               fade_in=bool(fade_in), fade_out=bool(fade_out), speech=transcribe(path))
    sync = {}
    for name, grid in [("beats", bt), ("downbeats", downbeats), ("onsets", onsets), ("sections", sections)]:
        if len(grid) > 2:
            sync[name] = sync_test(cut_times, grid, info["duration"])
    if out["speech"] and out["speech"].get("words"):
        ends = [w["end"] for w in out["speech"]["words"]]
        sync["word_ends"] = sync_test(cut_times, ends, info["duration"])
    out["cut_sync"] = sync
    return out


def estimate_downbeats(y, sr, bt, path):
    try:  # Beat This! (optional, accurate)
        from beat_this.inference import File2Beats
        b, d = File2Beats(checkpoint_path="final0", device="cpu", dbn=False)(path)
        return np.asarray(d), "beat_this"
    except Exception:
        pass
    if len(bt) < 8:
        return np.asarray(bt[::4]), "librosa/4"
    import librosa
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)); fr = librosa.fft_frequencies(sr=sr)
    low = S[fr < 150].sum(0); tt = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=512)
    def at(t): return low[min(len(low) - 1, np.searchsorted(tt, t))]
    scores = [np.mean([at(t) for t in bt[p::4]]) for p in range(4)]
    p = int(np.argmax(scores))
    return np.asarray(bt[p::4]), f"librosa beats, bar phase {p} by bass energy (estimate)"


def transcribe(path):
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return None
    try:
        m = WhisperModel("small", device="cpu", compute_type="int8")
        segs, info = m.transcribe(path, word_timestamps=True, vad_filter=True)
        words, text, dropped = [], [], []
        for s in segs:
            # Whisper invents text over music ("Outro Music", "Thanks for watching!"); its own confidence
            # gives it away: real speech has no_speech_prob < ~0.3 and avg_logprob > ~-0.7.
            if s.no_speech_prob > 0.4 or s.avg_logprob < -1.0:
                dropped.append(s.text.strip()); continue
            text.append(s.text)
            for w in (s.words or []):
                words.append(dict(w=w.word, start=round(w.start, 2), end=round(w.end, 2)))
        if not words: return dict(language=info.language, words=[], text="", hallucination_suspect=" ".join(dropped)[:80])
        wps = len(words) / max(1e-3, words[-1]["end"] - words[0]["start"])
        if len(words) < 5 or info.language_probability < 0.5:
            return dict(language=info.language, words=[], text="",
                        hallucination_suspect=" ".join(text + dropped).strip()[:80])
        return dict(language=info.language, text=" ".join(text).strip(), words=words, words_per_sec=round(wps, 2))
    except Exception as e:
        return dict(error=str(e)[:200])


# ---------------------------------------------------------------- sheets
def make_sheets(path, outdir, shots, cuts, fps):
    sd = os.path.join(outdir, "sheets"); os.makedirs(sd, exist_ok=True)
    # Long references: every shot of the first 60 s (the hook) + an even sample of the rest, max 96 tiles.
    pick = shots if len(shots) <= 96 else (
        [s for s in shots if s["start"] < 60] +
        [shots[int(k)] for k in np.linspace(0, len(shots) - 1, 96 - sum(1 for s in shots if s["start"] < 60))
         if shots[int(k)]["start"] >= 60])[:96]
    imgs = frames_at(path, [(s["start"] + s["end"]) / 2 for s in pick], 160)
    pages = []
    for p in range(0, len(pick), 48):
        out = os.path.join(sd, f"shots_{p // 48 + 1}.png")
        labelled_sheet(imgs[p:p + 48], [f"{s['i']} {s['start']:.0f}s {s['dur']:.1f}" for s in pick[p:p + 48]], out, cols=12)
        pages.append(out)
    unsure = [c for c in cuts if c["votes"] < 3]
    review = None
    if unsure:
        ims, labs = [], []
        for k, c in enumerate(unsure):
            b, a = frames_at(path, [c["t"] - 1.5 / fps, c["t"] + 1.5 / fps], 120)
            ims += [b, a]; labs += [f"#{k} {c['t']:.2f} v{c['votes']}", "after"]
        review = os.path.join(sd, "cuts_review.png")
        labelled_sheet(ims, labs, review, cols=16, max_width=1800)
    return pages, review


# ---------------------------------------------------------------- main
def summarize(p):
    L = []
    i = p["info"]
    L.append(f"# Reference profile: {os.path.basename(i['path'])}")
    L.append(f"{i['width']}x{i['height']} ({i.get('orientation')}) {i['fps']} fps, {i['duration']:.2f}s, {i.get('codec')}, HDR={i.get('hdr')}, audio={i['has_audio']}")
    s = p["shots"]; d = np.array([x["dur"] for x in s])
    L.append(f"\n## Pacing\n{len(s)} shots | ASD mean {d.mean():.3f}s median {np.median(d):.3f}s min {d.min():.3f} max {d.max():.3f} | hold threshold {p['hold_threshold']:.2f}s")
    if len(s) <= 120: L.append("frames per shot: " + " ".join(str(x["frames"]) for x in s))
    dur_all = i["duration"]
    if dur_all > 120:  # long-form: pacing over time is the signal (retention editing)
        win = 30 if dur_all <= 900 else 60
        words = ((p.get("audio") or {}).get("speech") or {}).get("words") or []
        curve = []
        for w0 in np.arange(0, dur_all, win):
            nc = sum(1 for c in p["cuts"] if w0 <= c["t"] < w0 + win)
            nw = sum(1 for w in words if w0 <= w["start"] < w0 + win)
            curve.append(f"{int(w0 // 60)}:{int(w0 % 60):02d} {nc}c" + (f"/{nw}w" if words else ""))
        L.append(f"pacing per {win}s window (cuts{'/words' if words else ''}): " + " | ".join(curve))
    L.append("\n| block | time | frac | shots | ASD |\n|---|---|---|---|---|")
    for b in p["blocks"]:
        L.append(f"| {b['kind']} | {b['start']:.2f}-{b['end']:.2f} | {b['frac'][0]:.2f}-{b['frac'][1]:.2f} | {b['n']} | {b['asd']:.3f} |")
    tt = {}
    for c in p["cuts"]: tt[c["transition"]] = tt.get(c["transition"], 0) + 1
    L.append(f"\ntransitions: {tt}   unconfirmed cuts: {sum(1 for c in p['cuts'] if c['votes'] < 3 and not p.get('cuts_final'))}")
    mc = {}
    for x in s: mc[x["motion"]] = mc.get(x["motion"], 0) + 1
    L.append(f"camera motion per shot: {mc}")
    g = p["grade"]
    L.append(f"\n## Look\nluma p1/p50/p99 {g['L1']:.1f}/{g['L50']:.1f}/{g['L99']:.1f} (0-100) | contrast(std) {g['Lstd']:.1f} | sat {g['sat']:.3f} | "
             f"a {g['a']:+.2f} b {g['b']:+.2f} (b>0 warm) | shadows a/b {g['sh_a']:+.1f}/{g['sh_b']:+.1f} | highlights a/b {g['hi_a']:+.1f}/{g['hi_b']:+.1f} | "
             f"vignette ratio {g['vign']:.2f} | grain {g['noise']:.2f} | bars {p['bars']}")
    if p["overlays"]:
        L.append("persistent overlays (fractions of frame): " + "; ".join(
            f"x {o['x0']}-{o['x1']} y {o['y0']}-{o['y1']} (h {o['h_frac']}, cov {o['coverage']})" for o in p["overlays"]))
    a = p.get("audio") or {}
    if a.get("present"):
        L.append(f"\n## Audio\n{a['bpm']} BPM (beat {a['beat_period']}s), downbeats via {a['downbeat_source']}, LUFS {a['lufs']} peak {a['true_peak']}, "
                 f"fade in {a['fade_in']} / out {a['fade_out']}, centroid {a['centroid_hz']} Hz, flatness {a['spectral_flatness']}")
        L.append(f"sections at: {a['sections']}")
        L.append("rms/0.5s: " + " ".join(f"{x:.2f}" for x in a["rms_halfsec"]))
        if a.get("speech") and a["speech"].get("words"):
            sp = a["speech"]; L.append(f"speech: {sp['language']}, {len(sp['words'])} words, {sp['words_per_sec']} w/s: \"{sp['text'][:400]}\"")
        elif a.get("speech") is None:
            L.append("speech: not checked (faster-whisper not installed)")
        elif a["speech"].get("hallucination_suspect") is not None:
            L.append(f"speech: no dialogue. Whisper's low-confidence text: \"{a['speech']['hallucination_suspect']}\" "
                     "(= sung lyrics if it reads like lyrics, else a music-only hallucination)")
        L.append("\ncut sync tests (vs uniformly random cut placement):")
        for k, v in (a.get("cut_sync") or {}).items():
            if v: L.append(f"- {k}: mean offset {v['mean_offset_ms']} ms vs chance {v['chance_ms']} ms, p={v['p_value']} -> {v['verdict']} ({v['within_1_frame']}/{v['n']} within 1 frame)")
    else:
        L.append("\n## Audio\nnone / silent")
    L.append("\n## Shots\n| # | start | dur | motion | luma | sat | b |\n|---|---|---|---|---|---|---|")
    for x in s[:80]:
        L.append(f"| {x['i']} | {x['start']:.2f} | {x['dur']:.2f} | {x['motion']} | {x['luma']} | {x['sat']} | {x['b']:+.1f} |")
    if len(s) > 80: L.append(f"... {len(s) - 80} more shots in profile.json")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("outdir")
    ap.add_argument("--cuts", help="JSON {cuts:[seconds]} after adjudication"); ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
    info = probe(a.ref); fps = info["fps"] or 30
    feat = frame_features(a.ref, os.path.join(a.outdir, "frames_cache.npz")); nframes = len(feat["L"])
    cuts_cache = os.path.join(a.outdir, "cuts_detected.json")
    if os.path.exists(cuts_cache): detected = load_json(cuts_cache)
    else: detected = detect_cuts(a.ref, fps); dump_json(detected, cuts_cache)
    if a.cuts:
        final = load_json(a.cuts)["cuts"]
        cuts = [dict(frame=int(round(t * fps)), t=round(t, 3), votes=9) for t in sorted(final)]
    else:
        cuts = [c for c in detected if c["votes"] >= 2]
    for c in cuts: c["transition"] = classify_transition(feat, c["frame"], fps)
    cut_f = [c["frame"] for c in cuts]
    shots = shot_stats(feat, cut_f, nframes, fps, info["width"])
    blocks, hold_thr = blocks_from_shots(shots, nframes / fps)
    keep = feat["L"] > 3  # ignore pure-black frames for the look
    grade = {k: float(np.mean(feat[k][keep])) for k in ["L1", "L50", "L99", "Lstd", "sat", "a", "b", "sh_a", "sh_b", "hi_a", "hi_b", "noise", "vign"]}
    overlays, _ = persistent_overlays(feat, fps, nframes, cut_f)
    prof = dict(info=info, cuts=cuts, cuts_final=bool(a.cuts), shots=shots, blocks=blocks, hold_threshold=hold_thr,
                grade=grade, overlays=overlays, bars=detect_bars(a.ref))
    if info["has_audio"] and not a.no_audio:
        ct = [c["t"] for c in cuts]
        prof["audio"] = audio_analysis(a.ref, info, ct)
    pages, review = make_sheets(a.ref, a.outdir, shots, detected if not a.cuts else [], fps)
    prof["sheets"] = dict(shots=pages, cuts_review=review)
    dump_json(prof, os.path.join(a.outdir, "profile.json"))
    md = summarize(prof)
    with open(os.path.join(a.outdir, "summary.md"), "w") as f: f.write(md)
    print(md[:6000])
    print(f"\nsheets: {pages}" + (f"\nREVIEW uncertain cuts: {review}" if review else ""))


if __name__ == "__main__":
    main()
