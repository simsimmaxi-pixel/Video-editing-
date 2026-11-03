#!/usr/bin/env python3
"""One-shot ingest of a folder of raw clips -> OUTDIR/{map.json, library.md, proxies/, sheets/, scan.json}.

  ingest_footage.py SRC_DIR OUTDIR [--workers 6] [--labels "crowd,close-up face,food,sign or text,wide venue"]

- Proxies: rotation-corrected, 10 fps, 640 px tall (landscape stays landscape). Cached: re-runs skip existing.
- Scan: per-second sharpness / shake (jitter after removing intentional camera motion) / motion / luma,
  printed as digit strings (0-9) so a whole library reads in a few hundred tokens.
- Verdict per clip + "best runs": contiguous >=2 s stretches that are steady, sharp and have something moving.
- Sheets: one labelled contact sheet per clip (tile label = seconds into the clip), up to 20 tiles.
- --labels (optional, needs open_clip_torch): zero-shot CLIP tags per second -> top moments per label,
  which lets you shortlist moments without looking at any images.
"""
import argparse, os, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import VIDEO_EXT, probe, run, dump_json, load_json, digit, frames_at, labelled_sheet, group_stats

PFPS, PH = 10, 640


def make_proxy(args):
    src, dst = args
    if os.path.exists(dst) and os.path.getsize(dst) > 0 and os.path.getmtime(dst) >= os.path.getmtime(src):
        return dst
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-an", "-vf", f"fps={PFPS},scale=-2:{PH}", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "26", "-g", str(PFPS), dst])  # GOP=1 s so seeking is cheap
    return dst


def scan_proxy(path):
    cap = cv2.VideoCapture(path); prev = None; rows = []
    while True:
        ok, f = cap.read()
        if not ok: break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        s = cv2.resize(g, (g.shape[1] // 2, g.shape[0] // 2)).astype(np.float32)
        hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
        sharp = cv2.Laplacian(g, cv2.CV_64F).var()
        if prev is None: dx = dy = diff = 0.0
        else:
            (dx, dy), _ = cv2.phaseCorrelate(prev, s); diff = float(np.abs(s - prev).mean())
        rows.append((sharp, float(g.mean()), float(hsv[..., 1].mean()), diff, dx, dy)); prev = s
    cap.release()
    if not rows: return []
    a = np.array(rows, float); k = np.ones(7) / 7
    jit = np.hypot(a[:, 4] - np.convolve(a[:, 4], k, "same"), a[:, 5] - np.convolve(a[:, 5], k, "same"))
    pan = np.hypot(np.convolve(a[:, 4], k, "same"), np.convolve(a[:, 5], k, "same"))
    secs = []
    for t in range(len(a) // PFPS):
        w = slice(t * PFPS, (t + 1) * PFPS)
        secs.append(dict(sharp=float(np.median(a[w, 0])), luma=float(a[w, 1].mean()), sat=float(a[w, 2].mean()),
                         motion=float(a[w, 3].mean()), shake=float(np.median(jit[w])), pan=float(pan[w].mean())))
    return secs


def clip_tags(proxy, labels, model_bundle):
    import torch
    model, preprocess, tok_feats = model_bundle
    from PIL import Image
    cap = cv2.VideoCapture(proxy); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); out = []
    for t in range(n // PFPS):
        cap.set(cv2.CAP_PROP_POS_FRAMES, t * PFPS + PFPS // 2); ok, f = cap.read()
        if not ok: break
        im = preprocess(Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))).unsqueeze(0)
        with torch.no_grad():
            e = model.encode_image(im); e = e / e.norm(dim=-1, keepdim=True)
            p = (100 * e @ tok_feats.T).softmax(-1)[0].numpy()
        out.append([round(float(x), 3) for x in p])
    cap.release()
    return out


def load_clip(labels):
    try:
        import torch, open_clip
    except Exception:
        print("  (open_clip not installed; skipping semantic tags)"); return None
    model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    tok = open_clip.get_tokenizer("ViT-B-32")
    with torch.no_grad():
        tf = model.encode_text(tok([f"a photo of {l}" for l in labels])); tf = tf / tf.norm(dim=-1, keepdim=True)
    return model.eval(), preprocess, tf


def best_runs(secs, jthr, sthr, mthr, min_len=2):
    steady = [s["shake"] <= jthr and s["sharp"] >= sthr for s in secs]
    good = [st and s["motion"] >= mthr for st, s in zip(steady, secs)]
    runs, st = [], None
    for i, g in enumerate(good + [False]):
        if g and st is None: st = i
        if not g and st is not None:
            if i - st >= min_len: runs.append((st, i))
            st = None
    return runs, sum(steady) / max(1, len(steady))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("outdir")
    ap.add_argument("--workers", type=int, default=6); ap.add_argument("--labels", default="")
    ap.add_argument("--tiles", type=int, default=20)
    a = ap.parse_args()
    pd, sd = os.path.join(a.outdir, "proxies"), os.path.join(a.outdir, "sheets")
    os.makedirs(pd, exist_ok=True); os.makedirs(sd, exist_ok=True)
    files = sorted(f for f in os.listdir(a.src) if os.path.splitext(f)[1].lower() in VIDEO_EXT and not f.startswith("."))
    mp = {}
    for i, f in enumerate(files):
        cid = f"f{i + 1:02d}"; info = probe(os.path.join(a.src, f))
        info["proxy"] = os.path.abspath(os.path.join(pd, f"{cid}.mp4")); info["name"] = f; mp[cid] = info
    print(f"{len(mp)} clips; building proxies with {a.workers} workers...")
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(make_proxy, [(m["path"], m["proxy"]) for m in mp.values()]))
    scan_path = os.path.join(a.outdir, "scan.json")
    scan = load_json(scan_path) if os.path.exists(scan_path) else {}
    todo = [c for c in mp if c not in scan]
    with ThreadPoolExecutor(min(a.workers, 4)) as ex:
        for c, r in zip(todo, ex.map(scan_proxy, [mp[c]["proxy"] for c in todo])): scan[c] = r
    dump_json(scan, scan_path)

    gs = group_stats(scan, mp)

    labels = [l.strip() for l in a.labels.split(",") if l.strip()]
    bundle = load_clip(labels) if labels else None
    tags = {}
    if bundle:
        tpath = os.path.join(a.outdir, "tags.json"); tags = load_json(tpath) if os.path.exists(tpath) else {}
        for c in mp:
            if c not in tags: tags[c] = clip_tags(mp[c]["proxy"], labels, bundle)
        dump_json(dict(tags, _labels=labels), tpath)

    L = ["# Footage library", "Digits are 0-9 per second, scaled **within each camera group** (codec+resolution+fps), so a soft "
         "cinema camera is not judged against a phone. S=sharpness (9 sharpest) J=shake (9 shakiest) M=motion/action L=brightness.",
         "Usable = steady and sharp for its camera; best runs = usable AND something moving, >=2 s. "
         "Very dark seconds (L=0) give unreliable shake/sharpness: judge those by eye.\n"]
    for c, m in mp.items():
        secs = scan.get(c, [])
        g = gs.get(c)
        if g is None: continue
        runs, frac = best_runs(secs, g["j_hold"], g["s_thr"], g["m_thr"])
        m["usable_frac"] = round(frac, 2); m["best_runs"] = runs
        verdict = "REJECT?" if frac < 0.25 else ("partial" if frac < 0.6 else "good")
        L.append(f"## {c} {m['name']}  {m['duration']:.1f}s {m.get('width')}x{m.get('height')} {m.get('fps')}fps "
                 f"{m.get('codec')}{' HDR' if m.get('hdr') else ''} [{gs[c]['group'] if c in gs else '?'}]{' rot' + str(m['rotation']) if m.get('rotation') else ''}  "
                 f"usable {frac:.0%} -> {verdict}")
        if secs:
            L.append(" S " + "".join(digit(s["sharp"], *g["S"]) for s in secs))
            L.append(" J " + "".join(digit(s["shake"], *g["J"]) for s in secs))
            L.append(" M " + "".join(digit(s["motion"], *g["M"]) for s in secs))
            L.append(" L " + "".join(digit(s["luma"], 30, 200) for s in secs))
        L.append(" best runs: " + (", ".join(f"{s}-{e}s" for s, e in runs) or "none"))
        if bundle and tags.get(c):
            arr = np.array(tags[c]); top = arr.argmax(1)
            L.append(" tags: " + "".join(chr(65 + int(i)) for i in top) + "   (" + ", ".join(f"{chr(65 + i)}={l}" for i, l in enumerate(labels)) + ")")
        # contact sheet with timestamps in each tile
        sheet = os.path.join(sd, f"{c}.png")
        if not os.path.exists(sheet) and m["duration"] > 0:
            n = int(min(a.tiles, max(4, m["duration"])))
            ts = [(k + 0.5) * m["duration"] / n for k in range(n)]
            h = 150 if m.get("orientation") == "landscape" else 192
            labelled_sheet(frames_at(m["proxy"], ts, h), [f"{t:.1f}s" for t in ts], sheet, cols=10, max_width=1920)
        m["sheet"] = os.path.abspath(sheet)
        L.append("")
    if bundle:
        L.append("## Top moments per label (clip@second, prob)")
        for li, lab in enumerate(labels):
            cand = [(tags[c][t][li], c, t) for c in tags if not c.startswith("_") for t in range(len(tags[c]))
                    if t < len(scan.get(c, [])) and c in gs and scan[c][t]["shake"] <= gs[c]["j_hold"]]
            cand.sort(reverse=True)
            L.append(f"- {lab}: " + ", ".join(f"{c}@{t}s ({p:.2f})" for p, c, t in cand[:8]))
    dump_json(mp, os.path.join(a.outdir, "map.json"))
    with open(os.path.join(a.outdir, "library.md"), "w") as f: f.write("\n".join(L))
    print("\n".join(L)[:8000])
    print(f"\nsheets in {sd}/ (one per clip; view only the ones you need)")


if __name__ == "__main__":
    main()
