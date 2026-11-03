#!/usr/bin/env python3
"""Closed-loop check: measure the rendered edit with the SAME analyzer as the reference and diff the styles.

  verify.py OUTPUT.edl.json REF_PROFILE.json [--out verify.md]

Reports technical integrity (frames, gaps, size, fps, loudness) and a style diff table:
pacing (ASD, median, shot-length spread, block pattern), cut-sync verdicts, transitions mix, camera-motion mix,
look (levels, contrast, saturation, white balance, split-toning, vignette, grain), overlay placement.
Rows outside tolerance are marked so you know what to change. Also writes a mid-shot sheet of the output.
"""
import argparse, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, probe, loudness, frames_at, labelled_sheet, sync_test, extract_wav
import analyze_reference as AR


def pct(a, q): return float(np.percentile(a, q)) if len(a) else 0.0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("edl"); ap.add_argument("profile"); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    edl, ref = load_json(a.edl), load_json(a.profile)
    out = edl["output"]; fps = edl["fps"]; info = probe(out)
    work = os.path.splitext(out)[0] + "_verify"; os.makedirs(work, exist_ok=True)
    feat = AR.frame_features(out, os.path.join(work, "frames_cache.npz")); n = len(feat["L"])
    cuts, pos = [], 0
    for s in edl["shots"][:-1]:
        pos += s["n"]; cuts.append(pos)
    shots = AR.shot_stats(feat, cuts, n, fps, info["width"])
    tail = n - sum(s["n"] for s in edl["shots"])
    if tail > 0: shots = AR.shot_stats(feat, cuts + [n - tail], n, fps, info["width"])
    blocks, _ = AR.blocks_from_shots(shots, n / fps)
    keep = feat["L"] > 3
    g_out = {k: float(np.mean(feat[k][keep])) for k in ref["grade"]}
    # one sample per distinct source clip: reused static footage must not read as an overlay
    seen, mids, pos = set(), [], 0
    for sh in edl["shots"]:
        if sh["clip"] not in seen: seen.add(sh["clip"]); mids.append(pos + sh["n"] // 2)
        pos += sh["n"]
    ov_out, _ = AR.persistent_overlays(feat, fps, n, cuts, mids=mids)

    rd = np.array([s["dur"] for s in ref["shots"] if s["motion"] != "black"])
    od = np.array([s["dur"] for s in shots if s["motion"] != "black"])
    rows = []
    def row(name, r, o, tol=None, rel=False, fmt="{:.3f}"):
        status = ""
        if tol is not None and isinstance(r, (int, float)) and isinstance(o, (int, float)):
            diff = abs(o - r) / (abs(r) + 1e-9) if rel else abs(o - r)
            status = "ok" if diff <= tol else "**CHECK**"
        f = lambda v: fmt.format(v) if isinstance(v, (int, float)) else str(v)
        rows.append(f"| {name} | {f(r)} | {f(o)} | {status} |")
    ri, oi = ref["info"], info
    row("aspect (w/h)", ri["width"] / ri["height"], oi["width"] / oi["height"], 0.01)
    row("fps", ri["fps"], oi["fps"], 0.5, fmt="{:.2f}")
    row("duration s", ri["duration"], oi["duration"], fmt="{:.2f}")
    row("shots", len(rd), len(od), fmt="{:.0f}")
    row("ASD mean s", rd.mean(), od.mean(), 0.25, rel=True)
    row("ASD median s", np.median(rd), np.median(od), 0.25, rel=True)
    row("shot p10 / p90 s", f"{pct(rd, 10):.2f}/{pct(rd, 90):.2f}", f"{pct(od, 10):.2f}/{pct(od, 90):.2f}")
    row("hold share of runtime", sum(x for x in rd if x >= ref["hold_threshold"]) / rd.sum(),
        sum(x for x in od if x >= ref["hold_threshold"]) / max(od.sum(), 1e-6), 0.12)
    row("block pattern", " ".join(b["kind"][0] for b in ref["blocks"]), " ".join(b["kind"][0] for b in blocks))
    tr_ref = {}
    for c in ref["cuts"]: tr_ref[c.get("transition", "hard")] = tr_ref.get(c.get("transition", "hard"), 0) + 1
    tr_out = {}
    for s in edl["shots"][1:]:
        k = (s.get("trans") or {}).get("type", "cut"); tr_out[k] = tr_out.get(k, 0) + 1
    row("transitions", tr_ref, tr_out)
    mref, mout = {}, {}
    for s in ref["shots"]: mref[s["motion"]] = mref.get(s["motion"], 0) + 1
    for s in shots: mout[s["motion"]] = mout.get(s["motion"], 0) + 1
    row("camera motion mix", mref, mout)
    G = ref["grade"]
    for k, tol, label in [("L1", 3, "black point L"), ("L50", 5, "median L"), ("L99", 4, "white point L"), ("Lstd", 4, "contrast (L std)"),
                          ("sat", 0.04, "saturation"), ("a", 2, "tint a (+magenta)"), ("b", 2.5, "temp b (+warm)"),
                          ("sh_b", 3, "shadow b"), ("hi_b", 3, "highlight b"), ("vign", 0.06, "vignette ratio"), ("noise", 1.0, "grain")]:
        row(label, G[k], g_out[k], tol)
    rov = "; ".join(f"y{o['y0']}-{o['y1']} x{o['x0']}-{o['x1']}" for o in ref.get("overlays", [])) or "none"
    oov = "; ".join(f"y{o['y0']}-{o['y1']} x{o['x0']}-{o['x1']}" for o in ov_out) or ("none" if len(mids) >= 5 else f"n/a (only {len(mids)} distinct clips)")
    row("persistent overlays", rov, oov)
    ra = ref.get("audio") or {}
    lufs, peak = loudness(out) if info["has_audio"] else (None, None)
    row("loudness LUFS", ra.get("lufs"), lufs, 1.5, fmt="{:.1f}")
    if info["has_audio"]:
        import librosa
        wav = extract_wav(out); y, sr = librosa.load(wav, sr=22050); os.remove(wav)
        _, b = librosa.beat.beat_track(y=y, sr=sr); bt = librosa.frames_to_time(b, sr=sr)
        st = sync_test([c / fps for c in cuts], bt, n / fps)
        rv = (ra.get("cut_sync") or {}).get("beats") or {}
        row("cuts vs beats", f"{rv.get('verdict')} (p={rv.get('p_value')})", f"{st['verdict']} (p={st['p_value']})" if st else "n/a")
    mids = [(s["start"] + s["end"]) / 2 for s in shots]
    sheet = labelled_sheet(frames_at(out, mids, 128), [f"{i + 1}" for i in range(len(mids))], os.path.join(work, "shots.png"), cols=16)
    chk = edl.get("check", {})
    md = [f"# Verify: {os.path.basename(out)}",
          f"integrity: frames {chk.get('frames')}/{chk.get('expected')}, gaps {chk.get('gaps')}, {oi['width']}x{oi['height']} {oi['fps']}fps, "
          f"audio {oi['has_audio']}, true peak {peak} dBFS",
          "\n| metric | reference | output | |\n|---|---|---|---|", *rows,
          f"\nmid-shot sheet: {sheet}",
          "Tolerances are starting points: a deliberate creative change (different length, no caption) is fine to leave as CHECK."]
    text = "\n".join(md)
    with open(a.out or os.path.join(work, "verify.md"), "w") as f: f.write(text)
    print(text)


if __name__ == "__main__":
    main()
