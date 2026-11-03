#!/usr/bin/env python3
"""Render a text overlay (any style) to a transparent PNG the size of the output frame.

  caption.py OUT.png --text "Northampton 🎾" [--size 1080x1920] [--cx 0.5 --cy 0.5] [--px 52]
             [--font auto|PATH[:index]] [--weight medium|bold|regular|black] [--color white]
             [--stroke 0] [--stroke-color black] [--shadow 0,2,6,140] [--box none|#000000@0.6]
             [--box-pad 18] [--box-radius 14] [--max-width 0.8] [--align center|left|right] [--upper]

Why PNG instead of ffmpeg drawtext: many ffmpeg builds ship without drawtext (no libfreetype), drawtext
cannot draw colour emoji, and a PNG is measurable (bbox printed) so the position can be checked against
the reference profile's overlay bbox. For word-by-word captions, render one PNG per word/phrase and give
each its own [start, end] in the edit's overlays list.
"""
import argparse, glob, os, sys, unicodedata
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageColor

FONT_CANDIDATES = {  # (path, ttc index by weight) - first existing wins
    "regular": [("/System/Library/Fonts/HelveticaNeue.ttc", 0), ("/System/Library/Fonts/Helvetica.ttc", 0),
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0), ("C:/Windows/Fonts/arial.ttf", 0)],
    "medium": [("/System/Library/Fonts/HelveticaNeue.ttc", 10), ("/System/Library/Fonts/Helvetica.ttc", 1),
               ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0), ("C:/Windows/Fonts/arialbd.ttf", 0)],
    "bold": [("/System/Library/Fonts/HelveticaNeue.ttc", 1), ("/System/Library/Fonts/Helvetica.ttc", 1),
             ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0), ("C:/Windows/Fonts/arialbd.ttf", 0)],
    "black": [("/System/Library/Fonts/HelveticaNeue.ttc", 9), ("/System/Library/Fonts/Supplemental/Arial Black.ttf", 0),
              ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0), ("C:/Windows/Fonts/ariblk.ttf", 0)],
}
EMOJI_FONTS = [("/System/Library/Fonts/Apple Color Emoji.ttc", 160), ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 109),
               ("C:/Windows/Fonts/seguiemj.ttf", 109)]


def load_font(spec, weight, px):
    if spec and spec != "auto":
        path, _, idx = spec.partition(":")
        return ImageFont.truetype(path, px, index=int(idx or 0))
    for path, idx in FONT_CANDIDATES[weight]:
        if os.path.exists(path):
            return ImageFont.truetype(path, px, index=idx)
    return ImageFont.load_default()


def is_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or unicodedata.category(ch) == "So"


def emoji_img(ch, px):
    for path, native in EMOJI_FONTS:
        if os.path.exists(path):
            f = ImageFont.truetype(path, native)
            im = Image.new("RGBA", (native * 2, native * 2), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
            bb = im.getbbox()
            if bb:
                im = im.crop(bb); s = px * 0.95 / im.height
                return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return None


def runs(text):
    out = []
    for ch in text:
        if ch in "\ufe0f\u200d": continue
        kind = "e" if is_emoji(ch) else "t"
        if out and out[-1][0] == kind == "t": out[-1][1] += ch
        else: out.append([kind, ch])
    return out


def measure_line(line, font, px):
    w = 0
    for kind, s in runs(line):
        w += (font.getbbox(s)[2] if kind == "t" else int(px * 1.0)) + (0 if kind == "t" else int(px * 0.15))
    return w


def wrap(text, font, px, maxw):
    lines = []
    for para in text.split("\\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if cur and measure_line(trial, font, px) > maxw: lines.append(cur); cur = word
            else: cur = trial
        lines.append(cur)
    return lines


def color(c):
    if "@" in c:
        c, a = c.split("@"); r, g, b = ImageColor.getrgb(c)[:3]; return (r, g, b, int(float(a) * 255))
    return ImageColor.getrgb(c) + ((255,) if len(ImageColor.getrgb(c)) == 3 else ())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--text", required=True)
    ap.add_argument("--size", default="1080x1920"); ap.add_argument("--cx", type=float, default=0.5); ap.add_argument("--cy", type=float, default=0.5)
    ap.add_argument("--px", type=int, default=52); ap.add_argument("--font", default="auto"); ap.add_argument("--weight", default="medium")
    ap.add_argument("--color", default="white"); ap.add_argument("--stroke", type=int, default=0); ap.add_argument("--stroke-color", default="black")
    ap.add_argument("--shadow", default="0,2,6,140", help="dx,dy,blur,alpha or 'none'")
    ap.add_argument("--box", default="none"); ap.add_argument("--box-pad", type=int, default=18); ap.add_argument("--box-radius", type=int, default=14)
    ap.add_argument("--max-width", type=float, default=0.85); ap.add_argument("--align", default="center")
    ap.add_argument("--line-spacing", type=float, default=1.2); ap.add_argument("--upper", action="store_true")
    a = ap.parse_args()
    W, H = map(int, a.size.lower().split("x")); text = a.text.upper() if a.upper else a.text
    font = load_font(a.font, a.weight, a.px)
    lines = wrap(text, font, a.px, a.max_width * W)
    lh = int(a.px * a.line_spacing); block_h = lh * len(lines)
    widths = [measure_line(l, font, a.px) for l in lines]; bw = max(widths)
    x_c, y_top = a.cx * W, a.cy * H - block_h / 2
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    if a.box != "none":
        x0 = x_c - bw / 2 - a.box_pad
        d.rounded_rectangle([x0, y_top - a.box_pad * 0.6, x0 + bw + 2 * a.box_pad, y_top + block_h + a.box_pad * 0.6],
                            radius=a.box_radius, fill=color(a.box))
    text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); td = ImageDraw.Draw(text_layer)
    for i, (line, w) in enumerate(zip(lines, widths)):
        x = {"center": x_c - w / 2, "left": a.cx * W, "right": a.cx * W - w}[a.align]
        ym = y_top + i * lh + lh / 2
        for kind, s in runs(line):
            if kind == "t":
                td.text((x, ym), s, font=font, fill=color(a.color), anchor="lm",
                        stroke_width=a.stroke, stroke_fill=color(a.stroke_color))
                x += font.getbbox(s)[2]
            else:
                x += int(a.px * 0.15); em = emoji_img(s, a.px)
                if em: text_layer.alpha_composite(em, (int(x), int(ym - em.height / 2)))
                x += int(a.px * 1.0)
    if a.shadow != "none":
        dx, dy, blur, alpha = map(float, a.shadow.split(","))
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sh.putalpha(text_layer.getchannel("A").point(lambda v: v * alpha / 255))
        sh = sh.filter(ImageFilter.GaussianBlur(blur)); layer.alpha_composite(sh, (int(dx), int(dy)))
    layer.alpha_composite(text_layer); layer.save(a.out)
    bb = layer.getbbox()
    if bb: print(f"{a.out}: bbox x {bb[0] / W:.3f}-{bb[2] / W:.3f}  y {bb[1] / H:.3f}-{bb[3] / H:.3f}  (h {(bb[3] - bb[1]) / H:.3f} of frame)")


if __name__ == "__main__":
    main()
