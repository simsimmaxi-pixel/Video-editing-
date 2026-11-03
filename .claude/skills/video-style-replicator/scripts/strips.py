#!/usr/bin/env python3
"""Close look at specific candidate moments: one composite image, one labelled row per range.

  strips.py OUT.png MAP.json f03:5:9 f12:74:86 f07:1:9 [--n 10] [--h 140]

Use after the contact sheets have narrowed things down, to pick exact in-points for holds and
action peaks. Each tile is labelled with its timestamp in the source clip.
"""
import argparse, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, frames_at, labelled_sheet


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("map"); ap.add_argument("ranges", nargs="+")
    ap.add_argument("--n", type=int, default=10); ap.add_argument("--h", type=int, default=140)
    a = ap.parse_args(); mp = load_json(a.map); rows = []
    for r in a.ranges:
        cid, s, e = r.split(":"); s, e = float(s), float(e)
        ts = [s + (k + 0.5) * (e - s) / a.n for k in range(a.n)]
        tmp = a.out + f".{cid}_{s}.png"
        labelled_sheet(frames_at(mp[cid]["proxy"], ts, a.h), [f"{cid} {t:.1f}" for t in ts], tmp, cols=a.n, max_width=4000)
        rows.append(Image.open(tmp)); os.remove(tmp)
    W = max(r.width for r in rows); out = Image.new("RGB", (W, sum(r.height for r in rows)))
    y = 0
    for r in rows: out.paste(r, (0, y)); y += r.height
    out.save(a.out); print(a.out)


if __name__ == "__main__":
    main()
