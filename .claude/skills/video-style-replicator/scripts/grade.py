#!/usr/bin/env python3
"""Match footage colour/tone to a reference and bake it into .cube LUTs (applied by engine.py via ffmpeg lut3d).

  grade.py match REF.mp4 MAP.json OUTDIR [--group camera|clip|all] [--strength 0.8] [--clips f01,f03]
                [--ref-profile profile.json]   # uses shot midpoints & skips black/overlay frames
  grade.py stats VIDEO                          # print look stats (same metrics as analyze_reference)

Method: Monge-Kantorovich linear (MKL) colour transfer (Pitie 2007; the 'mkl' method of the color-matcher
package) for the colour cast/saturation/contrast relationship, then a luminance quantile curve for the tone
curve (black point, gamma, roll-off). Both are global per-pixel maps, so they bake exactly into a 33^3 LUT.
--group camera builds one LUT per camera signature (codec+resolution+fps) - this also evens out
DJI vs phone vs action-cam differences. Writes compare.png: reference | before | after for a few frames.
"""
import argparse, os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, dump_json, frames_at, labelled_sheet


def sample_pixels(video, times, width=160):
    px = []
    for im in frames_at(video, times, int(width * 16 / 9)):
        if im is None: continue
        a = np.asarray(im, np.float32) / 255.0
        if a.mean() < 0.02: continue  # skip black frames
        px.append(a.reshape(-1, 3))
    return np.concatenate(px) if px else np.zeros((0, 3), np.float32)


def mkl(cs, cr):
    eps = 1e-7
    da2, ua = np.linalg.eigh(cs); da = np.diag(np.sqrt(np.clip(da2, eps, None)))
    c = da @ ua.T @ cr @ ua @ da
    dc2, uc = np.linalg.eigh(c); dc = np.diag(np.sqrt(np.clip(dc2, eps, None)))
    da_inv = np.diag(1 / np.diag(da))
    return ua @ da_inv @ uc @ dc @ uc.T @ da_inv @ ua.T


def _sat(px):
    hsv = cv2.cvtColor((np.clip(px, 0, 1).reshape(1, -1, 3) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    return float(hsv[..., 1].mean() / 255)


def luma(x):
    return x @ np.array([0.2126, 0.7152, 0.0722], np.float32)


class Transfer:
    def __init__(self, src, ref, strength=0.8):
        self.ms, self.mr = src.mean(0), ref.mean(0)
        self.T = mkl(np.cov((src - self.ms).T), np.cov((ref - self.mr).T))
        self.k = strength
        mid = self._color(src)
        qs = np.linspace(0, 100, 51)
        self.qin, self.qout = np.percentile(luma(mid), qs), np.percentile(luma(ref), qs)
        self.qin = np.maximum.accumulate(self.qin + np.arange(51) * 1e-6)
        # final chroma gain so mean saturation lands on the reference (MKL + tone can overshoot)
        self.cg = 1.0
        s_ref, s_now = _sat(ref), _sat(self._tone(src))
        if s_now > 1e-3: self.cg = float(np.clip(1 + self.k * (s_ref / s_now - 1), 0.5, 1.6))

    def _color(self, x):
        y = (x - self.ms) @ self.T + self.mr
        return x + self.k * (y - x)

    def _tone(self, x):
        y = self._color(x)
        L = luma(y); L2 = np.interp(L, self.qin, self.qout)
        return np.clip(y + self.k * (L2 - L)[:, None], 0, 1)

    def __call__(self, x):
        y = self._tone(x)
        L = luma(y)[:, None]
        return np.clip(L + getattr(self, "cg", 1.0) * (y - L), 0, 1)


def write_cube(tr, path, n=33):
    g = np.linspace(0, 1, n, dtype=np.float32)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")          # r varies fastest in .cube order
    grid = np.stack([r.ravel(), gg.ravel(), b.ravel()], 1)
    out = tr(grid)
    with open(path, "w") as f:
        f.write(f'TITLE "video-style-replicator match"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        for row in out: f.write(f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f}\n")


def look(px):
    if len(px) == 0: return {}
    lab = cv2.cvtColor((px.reshape(1, -1, 3) * 255).astype(np.uint8), cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)
    L = lab[:, 0] * 100 / 255
    hsv = cv2.cvtColor((px.reshape(1, -1, 3) * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).reshape(-1, 3)
    return dict(L1=round(float(np.percentile(L, 1)), 1), L50=round(float(np.percentile(L, 50)), 1),
                L99=round(float(np.percentile(L, 99)), 1), Lstd=round(float(L.std()), 1),
                sat=round(float(hsv[:, 1].mean() / 255), 3), a=round(float(lab[:, 1].mean() - 128), 2),
                b=round(float(lab[:, 2].mean() - 128), 2))


def cmd_match(a):
    mp = load_json(a.map)
    if a.ref_profile:
        prof = load_json(a.ref_profile)
        ref_times = [(s["start"] + s["end"]) / 2 for s in prof["shots"] if s.get("motion") != "black"]
    else:
        from common import probe
        d = probe(a.ref)["duration"]; ref_times = list(np.linspace(0.5, d - 0.5, 24))
    ref = sample_pixels(a.ref, ref_times)
    clips = [c for c in mp if (not a.clips or c in a.clips.split(","))]
    groups = {}
    for c in clips:
        m = mp[c]
        key = {"camera": f"{m.get('codec')}_{m.get('width')}x{m.get('height')}_{round(m.get('fps', 0))}", "clip": c, "all": "all"}[a.group]
        groups.setdefault(key, []).append(c)
    os.makedirs(a.outdir, exist_ok=True); assign = {}; report = [f"reference look: {look(ref)}"]
    comp_imgs, comp_labels = [], []
    for gname, members in groups.items():
        src = np.concatenate([sample_pixels(mp[c]["proxy"], np.linspace(0.5, max(0.6, mp[c]["duration"] - 0.5), 8)) for c in members])
        if len(src) == 0: continue
        tr = Transfer(src, ref, a.strength)
        cube = os.path.abspath(os.path.join(a.outdir, f"grade_{gname}.cube")); write_cube(tr, cube)
        for c in members: assign[c] = cube
        report.append(f"{gname} ({','.join(members)}): before {look(src)} -> after {look(tr(src))}")
        im = frames_at(mp[members[0]]["proxy"], [mp[members[0]]["duration"] / 2], 240)[0]
        if im is not None:
            from PIL import Image
            arr = np.asarray(im, np.float32).reshape(-1, 3) / 255
            after = Image.fromarray((tr(arr).reshape(np.asarray(im).shape) * 255).astype(np.uint8))
            comp_imgs += [im, after]; comp_labels += [f"{gname[:18]} before", "after"]
    rim = [x for x in frames_at(a.ref, ref_times[:: max(1, len(ref_times) // 3)][:3], 240) if x is not None]
    labelled_sheet(rim + comp_imgs, ["reference"] * len(rim) + comp_labels, os.path.join(a.outdir, "compare.png"), cols=8)
    dump_json(dict(assign=assign, groups=groups, strength=a.strength), os.path.join(a.outdir, "grade.json"))
    print("\n".join(report)); print(f"LUT assignment -> {os.path.join(a.outdir, 'grade.json')}; check compare.png")


def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("match"); m.add_argument("ref"); m.add_argument("map"); m.add_argument("outdir")
    m.add_argument("--group", default="camera", choices=["camera", "clip", "all"]); m.add_argument("--strength", type=float, default=0.8)
    m.add_argument("--clips", default=""); m.add_argument("--ref-profile", default=None)
    s = sub.add_parser("stats"); s.add_argument("video")
    a = ap.parse_args()
    if a.cmd == "match": cmd_match(a)
    else:
        from common import probe
        d = probe(a.video)["duration"]; print(look(sample_pixels(a.video, np.linspace(0.3, d - 0.3, 24))))


if __name__ == "__main__":
    main()
