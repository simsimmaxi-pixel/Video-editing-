#!/usr/bin/env python3
"""Map a music track's structure and propose edit windows -> OUTDIR/music.json + music.md

  analyze_music.py TRACK OUTDIR [--min 20 --max 40] [--break-at 0.45] [--from-start] [--vocals demucs|auto|off]

Gives: tempo, beats, downbeats (Beat This! if installed, else a bass-energy bar-phase estimate),
per-bar low/mid/high energy, breaks (bass drop-outs / energy dips), section boundaries, where the
music actually ends (hard stop vs fade) and where vocals end (Demucs stem if installed; otherwise a
low-confidence spectral estimate), plus ranked windows that start/end on downbeats.

--break-at: where (as a fraction of the edit) the reference had its breather/hold (from the reference
profile's block structure). Windows with a break near that point score higher.
--shape sustained: the reference never breathes (one burst end to end): favour windows with high, steady
energy and penalise breaks inside them. A drop-in at the very start (an intro ending on bar 1) is rewarded:
it gives a cold open on a hit.
"""
import argparse, os, sys, shutil, subprocess, tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump_json, extract_wav, loudness


def downbeats_for(path, y, sr, bt):
    try:
        from beat_this.inference import File2Beats
        b, d = File2Beats(checkpoint_path="final0", device="cpu", dbn=False)(path)
        return np.asarray(b), np.asarray(d), "beat_this"
    except Exception:
        pass
    import librosa
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)); fr = librosa.fft_frequencies(sr=sr)
    low = S[fr < 150].sum(0); tt = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=512)
    at = lambda t: low[min(len(low) - 1, np.searchsorted(tt, t))]
    p = int(np.argmax([np.mean([at(t) for t in bt[p::4]]) for p in range(4)])) if len(bt) >= 8 else 0
    return bt, bt[p::4], f"estimate (librosa beats, bar phase {p} chosen by bass energy) - verify by ear/eye if critical"


def vocal_activity(path, y, sr, mode):
    """Returns (per-frame vocal energy array, frame times, source)."""
    import librosa
    if mode in ("demucs", "auto") and shutil.which(sys.executable):
        try:
            import demucs  # noqa
            tmp = tempfile.mkdtemp()
            subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", tmp, path],
                           check=True, capture_output=True)
            stem = next(os.path.join(r, f) for r, _, fs in os.walk(tmp) for f in fs if f.startswith("vocals"))
            v, _ = librosa.load(stem, sr=sr, mono=True); shutil.rmtree(tmp, ignore_errors=True)
            e = librosa.feature.rms(y=v, hop_length=512)[0]
            return e, librosa.frames_to_time(np.arange(len(e)), sr=sr, hop_length=512), "demucs"
        except Exception as ex:
            if mode == "demucs": print("demucs failed:", ex)
    if mode == "off": return None, None, "off"
    S, _ = librosa.magphase(librosa.stft(y, n_fft=2048, hop_length=512))
    F = np.minimum(S, librosa.decompose.nn_filter(S, aggregate=np.median, metric="cosine",
                                                  width=int(librosa.time_to_frames(2, sr=sr))))
    V = librosa.util.softmask(S - F, 10 * F, power=2) * S
    fr = librosa.fft_frequencies(sr=sr); band = (fr > 200) & (fr < 4000)
    e = V[band].sum(0)
    return e, librosa.frames_to_time(np.arange(len(e)), sr=sr, hop_length=512), "repet (low confidence)"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("track"); ap.add_argument("outdir")
    ap.add_argument("--min", type=float, default=15); ap.add_argument("--max", type=float, default=45)
    ap.add_argument("--break-at", type=float, default=None); ap.add_argument("--from-start", action="store_true")
    ap.add_argument("--vocals", default="auto", choices=["auto", "demucs", "off"])
    ap.add_argument("--shape", default="auto", choices=["auto", "sustained", "break"])
    a = ap.parse_args(); os.makedirs(a.outdir, exist_ok=True)
    import librosa
    wav = extract_wav(a.track); y, sr = librosa.load(wav, sr=22050, mono=True); os.remove(wav)
    dur = len(y) / sr
    tempo, bfr = librosa.beat.beat_track(y=y, sr=sr); bt = librosa.frames_to_time(bfr, sr=sr)
    bt, db, dsrc = downbeats_for(a.track, y, sr, bt)
    # where sound really ends
    r10 = librosa.feature.rms(y=y, hop_length=sr // 10)[0]; t10 = np.arange(len(r10)) / 10
    med = np.median(r10[r10 > 1e-4]) if (r10 > 1e-4).any() else 1.0
    content = r10 > 0.25 * med                      # "music is playing" (ignores reverb/decay tails)
    music_end = float(t10[np.where(content)[0][-1]] + 0.1) if content.any() else dur
    pre = r10[(t10 >= music_end - 4) & (t10 < music_end - 3)]; last = r10[(t10 >= music_end - 1) & (t10 < music_end)]
    end_kind = "fade" if len(pre) and len(last) and last.mean() < 0.5 * pre.mean() else "hard stop"
    # bars
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)); fr = librosa.fft_frequencies(sr=sr)
    tt = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=512)
    low, mid, hi = S[fr < 150].sum(0), S[(fr >= 150) & (fr < 4000)].sum(0), S[fr >= 4000].sum(0)
    ve, vt, vsrc = vocal_activity(a.track, y, sr, a.vocals)
    db = np.asarray([d for d in db if d < music_end])
    bars = []
    for i in range(len(db)):
        s0, s1 = db[i], db[i + 1] if i + 1 < len(db) else min(music_end, db[i] + np.median(np.diff(db)))
        m = (tt >= s0) & (tt < s1)
        if not m.any(): continue
        bar = dict(i=i, t=round(float(s0), 3), low=float(low[m].mean()), mid=float(mid[m].mean()), hi=float(hi[m].mean()))
        if ve is not None:
            vm = (vt >= s0) & (vt < s1); bar["vocal"] = float(ve[vm].mean()) if vm.any() else 0.0
        bars.append(bar)
    if not bars:
        print("no bars found"); return
    for k in ("low", "mid", "hi", "vocal"):
        if k in bars[0]:
            med = np.median([b[k] for b in bars]) or 1
            for b in bars: b[k] = round(b[k] / med, 2)  # relative to the track's median bar
    for b in bars:
        b["energy"] = round((b["low"] + b["mid"] + b["hi"]) / 3, 2)
        b["break"] = b["low"] < 0.6 or b["energy"] < 0.7
    # beat-resolution drops: runs of >=2 beats where the bass falls below 55% of its median.
    # Exact even when the bar phase estimate is a beat off - use these to place "break" edits.
    bl = np.array([low[(tt >= bt[i]) & (tt < bt[i + 1])].mean() if ((tt >= bt[i]) & (tt < bt[i + 1])).any() else 0
                   for i in range(len(bt) - 1)])
    drops, i = [], 0
    while i < len(bl):
        if bl[i] < 0.55 * np.median(bl) and bt[i] < music_end:
            j = i
            while j + 1 < len(bl) and bl[j + 1] < 0.55 * np.median(bl): j += 1
            if j - i + 1 >= 2: drops.append(dict(start=round(float(bt[i]), 3), end=round(float(bt[j + 1]), 3), beats=j - i + 1))
            i = j + 1
        else: i += 1
    vocal_end = None
    if ve is not None:
        thr = 0.35 if vsrc == "demucs" else 0.6
        voc = [b for b in bars if b.get("vocal", 0) >= thr]
        vocal_end = voc[-1]["t"] + (np.median(np.diff(db)) if len(db) > 1 else 2) if voc else None
    # sections: novelty on beat-synced features, snapped to downbeats
    sections = []
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr); mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        X = librosa.util.sync(np.vstack([librosa.util.normalize(chroma), librosa.util.normalize(mfcc)]), bfr)
        bnd = librosa.segment.agglomerative(X, int(np.clip(round(music_end / 12), 3, 14)))
        st = librosa.frames_to_time(bfr[np.clip(bnd, 0, len(bfr) - 1)], sr=sr)
        sections = sorted({round(float(min(db, key=lambda d: abs(d - s))), 3) for s in st if 0.5 < s < music_end - 1})
    except Exception:
        pass
    # candidate windows (start/end on downbeats; end may also be the music end / vocal end)
    starts = [0.0] if a.from_start else sorted({0.0, *[b["t"] for b in bars]})
    ends = sorted({*[b["t"] for b in bars], round(music_end, 3)})
    def bar_at(t): return min(bars, key=lambda b: abs(b["t"] - t))
    cands = []
    for s in starts:
        for e in ends:
            L = e - s
            if not (a.min <= L <= a.max): continue
            inside = [b for b in bars if s <= b["t"] < e]
            score, why = 0.0, []
            brk = [b for b in inside if b["break"]] + [dict(t=d["start"]) for d in drops if s <= d["start"] < e]
            if a.shape == "sustained":
                en = [b["energy"] for b in inside]
                if en:
                    score += 2 * min(1.2, float(np.mean(en))) - 2 * float(np.std(en))
                    why.append(f"energy {np.mean(en):.2f}±{np.std(en):.2f}")
                late = [b for b in brk if (b["t"] - s) > 0.1 * L]
                if late: score -= 1.5 * len(late); why.append(f"{len(late)} break(s) inside")
                prev = [b for b in bars if b["t"] < s][-1:] 
                if prev and prev[0]["energy"] < 0.75 and inside and inside[0]["energy"] >= 0.95:
                    score += 1.5; why.append("starts on the drop-in")
            elif a.break_at is not None and brk:
                pos = min(abs((b["t"] - s) / L - a.break_at) for b in brk)
                if pos < 0.12: score += 3 - 10 * pos; why.append(f"break near {a.break_at:.0%}")
            elif brk and a.break_at is None and a.shape != "sustained":
                score += 1; why.append("has a break")
            if s == 0.0: score += 1; why.append("song start")
            if any(abs(s - x) < 0.3 for x in sections): score += 1; why.append("starts on section")
            if abs(e - music_end) < 0.3: score += 2; why.append(f"ends at music end ({end_kind})")
            elif vocal_end and abs(e - vocal_end) < 1.0: score += 1.5; why.append("ends at vocal end")
            elif any(abs(e - x) < 0.3 for x in sections): score += 1; why.append("ends on section")
            last = [b for b in inside if b["t"] >= e - 4]
            if last and np.mean([b["energy"] for b in last]) >= 1.0: score += 0.5; why.append("strong ending energy")
            cands.append(dict(start=round(s, 3), end=round(e, 3), length=round(L, 2), score=round(score, 2), why=why))
    cands.sort(key=lambda c: (-c["score"], c["length"]))
    lufs, peak = loudness(a.track)
    res = dict(track=os.path.abspath(a.track), duration=round(dur, 3), music_end=round(music_end, 3), end_kind=end_kind,
               vocal_end=round(vocal_end, 3) if vocal_end else None, vocal_source=vsrc,
               bpm=round(float(np.atleast_1d(tempo)[0]), 2), beat_period=round(float(np.median(np.diff(bt))), 4),
               beats=[round(float(x), 3) for x in bt], downbeats=[round(float(x), 3) for x in db], downbeat_source=dsrc,
               bars=bars, drops=drops, sections=sections, lufs=lufs, true_peak=peak, windows=cands[:12])
    dump_json(res, os.path.join(a.outdir, "music.json"))
    L = [f"# Music: {os.path.basename(a.track)}",
         f"{res['bpm']} BPM (beat {res['beat_period']}s, bar ~{4 * res['beat_period']:.3f}s), downbeats: {dsrc}",
         f"file {dur:.2f}s | music ends {music_end:.2f}s ({end_kind}) | vocals end ~{res['vocal_end']} ({vsrc}) | {lufs} LUFS, peak {peak} dBFS",
         f"sections (snapped to downbeats): {sections}",
         "bass drops (beat-exact): " + (", ".join(f"{d['start']:.2f}-{d['end']:.2f} ({d['beats']} beats)" for d in drops) or "none"),
         "\n| bar | t | low | mid | hi | energy | vocal | break |\n|---|---|---|---|---|---|---|---|"]
    for b in bars:
        L.append(f"| {b['i']} | {b['t']:.2f} | {b['low']} | {b['mid']} | {b['hi']} | {b['energy']} | {b.get('vocal', '-')} | {'BREAK' if b['break'] else ''} |")
    L.append("\n## Best windows\n| start | end | length | score | why |\n|---|---|---|---|---|")
    for c in cands[:12]:
        L.append(f"| {c['start']:.3f} | {c['end']:.3f} | {c['length']} | {c['score']} | {', '.join(c['why'])} |")
    md = "\n".join(L)
    with open(os.path.join(a.outdir, "music.md"), "w") as f: f.write(md)
    print(md)


if __name__ == "__main__":
    main()
