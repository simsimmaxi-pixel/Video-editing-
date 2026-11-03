#!/usr/bin/env python3
"""Deterministic edit renderer. An edit is a Python file defining EDIT (see assets/edit_template.py).

  engine.py my_edit.py --preview     # ~10x faster, low-res from proxies: use for every iteration
  engine.py my_edit.py               # full-res final from the original files
  engine.py my_edit.py --dry         # resolve + rule checks only

Timeline model: blocks of shots. Each block ends at an absolute time (song seconds when
time_base="song", i.e. a downbeat from analyze_music; or timeline seconds). A shot with n=None fills
its block. music may be a list of items (a playlist with crossfades); see music_items(). Frame math is exact and asserted, so cuts land on the intended frames.

Shot = (clip, src_in, frames) or dict(clip, t, n, zoom=1, anchor="center"|"top"|"bottom"|"left"|"right"|(fx,fy),
       speed=1, hflip=False, lut=None|"off"|path, trans=None|{"type":"xfade","kind":"fade|wipeleft|slideup|...",
       "frames":8}|{"type":"dip","color":"black","frames":6}|{"type":"flash","frames":3}, audio=False|gain_db,
       text=0 (characters on screen -> enforces read time), qc=True, note="",
       vf=[...] extra ffmpeg filters for this shot (e.g. "eq=saturation=0", "vignette=PI/5"),
       audio_from=(clip, t): play sound from another clip/time under this picture (B-roll over A-roll speech),
       audio_offset=0.0 seconds: >0 = J-cut (this shot's sound starts that much before its picture),
                                  <0 = L-cut (previous shot's sound runs on that much into this shot))
Edit-level post_vf=[...] filters applied to the whole programme after overlays (grain, letterbox, vignette).

Lessons baked in: concat *filter* not demuxer (demuxer drops frames at B-frame boundaries); setpts=N/(fps*TB)
on every segment; looping overlays need -loop 1 -framerate fps; output is verified for frame count and gaps.
"""
import argparse, hashlib, importlib.util, json, os, shutil, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import run, fmt_t, load_json, dump_json, probe

def music_items(e):
    """music may be one dict or a list (a playlist). Each item: file, start, end (song seconds), and optionally
    at (timeline seconds; default = right after the previous item), crossfade (s of overlap with the previous
    item), fade_in, fade_out, gain_db. Returns items with resolved `at`/fades."""
    m = e.get("music")
    if not m: return []
    items = [dict(x) for x in (m if isinstance(m, list) else [m])]
    t = 0.0
    for i, x in enumerate(items):
        xf = float(x.get("crossfade", 0) if i else 0)
        x.setdefault("at", max(0.0, t - xf))
        if xf:
            x["fade_in"] = max(float(x.get("fade_in", 0) or 0), xf)
            items[i - 1]["fade_out"] = max(float(items[i - 1].get("fade_out", 0.03) or 0), xf)
        t = x["at"] + x["end"] - x["start"]
    return items


def loud_target(e):
    if "loudnorm" in e: return e["loudnorm"]
    it = music_items(e)
    return it[0].get("loudnorm", -14) if it else -14


DEFAULTS = dict(fps=30, size="1080x1920", time_base="song", music=None, native_audio=None, grade=None,
                overlays=[], sfx=[], tail=None, post_vf=[], crf=18, preset="slow", workers=3)


# ------------------------------------------------------------------ edit loading / resolving
def load_edit(path):
    spec = importlib.util.spec_from_file_location("edit_mod", path); mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    e = dict(DEFAULTS); e.update(mod.EDIT); e["_path"] = os.path.abspath(path)
    e.setdefault("name", os.path.splitext(os.path.basename(path))[0])
    e.setdefault("out_dir", os.path.join(os.path.dirname(os.path.abspath(path)), "output"))
    e["W"], e["H"] = map(int, e["size"].lower().split("x"))
    return e


def norm_shot(s):
    if isinstance(s, dict): d = dict(s)
    else: d = dict(clip=s[0], t=s[1], n=s[2])
    d.setdefault("zoom", 1.0); d.setdefault("anchor", "center"); d.setdefault("speed", 1.0); d.setdefault("hflip", False)
    d.setdefault("lut", None); d.setdefault("trans", None); d.setdefault("audio", False); d.setdefault("text", 0); d.setdefault("qc", True)
    d.setdefault("vf", []); d.setdefault("audio_offset", 0.0); d.setdefault("audio_from", None)
    if d["audio_from"] and d["audio"] is False: d["audio"] = True
    return d


def resolve(e):
    fps = e["fps"]; mi = music_items(e)
    off = mi[0]["start"] - mi[0]["at"] if (e["time_base"] == "song" and mi) else 0.0  # song time of timeline 0
    shots, pos = [], 0
    for bname, end_t, items in e["blocks"]:
        end = int(round((end_t - off) * fps))
        items = [norm_shot(x) for x in items]
        fixed = sum(x["n"] for x in items if x["n"] is not None); nfill = sum(1 for x in items if x["n"] is None)
        if nfill > 1: raise ValueError(f"block {bname}: only one fill shot (n=None) allowed")
        for x in items:
            if x["n"] is None: x["n"] = end - pos - fixed
            x["block"] = bname; shots.append(x)
        pos = end
        got = sum(x["n"] for x in shots)
        if got != end: raise ValueError(f"block {bname}: shots sum to frame {got}, block ends at {end} (fixed shots too long?)")
        bad = [x for x in items if x["n"] < 2]
        if bad: raise ValueError(f"block {bname}: shot shorter than 2 frames: {bad[0]['clip']}@{bad[0]['t']}")
    # dips: previous shot fades out over half the frames
    for i, x in enumerate(shots):
        x["fade_out"] = None
        nx = shots[i + 1]["trans"] if i + 1 < len(shots) else None
        if nx and nx.get("type") == "dip": x["fade_out"] = (max(1, nx.get("frames", 6) // 2), nx.get("color", "black"))
    return shots, pos


def checks(e, shots, srcs):
    fps = e["fps"]; warn = []
    scan_p = os.path.join(os.path.dirname(e["_sources_path"]), "scan.json")
    scan = load_json(scan_p) if os.path.exists(scan_p) else None
    if scan:
        from common import group_stats
        gs = group_stats(scan, srcs)
    used = []
    for x in shots:
        m = srcs.get(x["clip"])
        if m is None: warn.append(f"unknown clip {x['clip']}"); continue
        need = x["t"] + x["n"] / fps * x["speed"]
        if need > m["duration"] + 0.05: warn.append(f"{x['clip']}@{x['t']}: needs {need:.2f}s but clip is {m['duration']:.2f}s")
        if x["n"] < 4 and not x["trans"]: warn.append(f"{x['clip']}@{x['t']}: {x['n']} frames is subliminal - intended?")
        if x["text"]:
            chars = x["text"] if isinstance(x["text"], int) else 12
            need_f = int(fps * (0.6 + 0.05 * chars))
            if x["n"] < need_f: warn.append(f"{x['clip']}@{x['t']}: shows text but only {x['n']}f; readable needs ~{need_f}f")
        for (c, a, b) in used:
            if c == x["clip"] and a < x["t"] + x["n"] / fps and x["t"] < b:
                warn.append(f"{x['clip']}@{x['t']}: overlaps a moment already used ({a:.2f}-{b:.2f})"); break
        used.append((x["clip"], x["t"], x["t"] + x["n"] / fps))
        if scan and x["qc"] and x["clip"] in scan:
            secs = scan[x["clip"]][int(x["t"]): int(x["t"] + x["n"] / fps) + 1]
            if secs:
                j = float(np.median([s["shake"] for s in secs])); sh = min(s["sharp"] for s in secs)
                g = gs.get(x["clip"])
                if g is None: continue
                lim, s_lo = (g["j_hold"] if x["n"] >= fps else g["j_burst"]), g["s_lo"]
                if j > lim: warn.append(f"QC {x['block']} {x['clip']}@{x['t']} ({x['n']}f): shaky for a {'hold' if x['n'] >= fps else 'burst shot'} (set qc=False if intended)")
                if sh < s_lo: warn.append(f"QC {x['block']} {x['clip']}@{x['t']}: soft/blurred")
    return warn


# ------------------------------------------------------------------ segments
def crop_expr(anchor, W, H):
    if isinstance(anchor, (list, tuple)): fx, fy = anchor
    else: fx, fy = {"center": (0.5, 0.5), "top": (0.5, 0), "bottom": (0.5, 1), "left": (0, 0.5), "right": (1, 0.5)}[anchor]
    return f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})*{fy}"


def lut_for(e, x):
    if x["lut"] == "off": return None
    if x["lut"]: return x["lut"]
    g = e.get("grade") or {}
    assign = g.get("assign") or (load_json(g["luts"])["assign"] if g.get("luts") else {})
    return assign.get(x["clip"], g.get("default"))


def seg_job(e, x, src, preview, cache):
    fps, W, H = e["fps"], e["W"], e["H"]
    if preview: W, H = (W // 3) // 2 * 2, (H // 3) // 2 * 2
    lead = x["trans"]["frames"] if x["trans"] and x["trans"].get("type") == "xfade" else 0
    total = x["n"] + lead
    start = max(0.0, x["t"] - lead / fps * x["speed"])
    vf = []
    if x["speed"] != 1: vf.append(f"setpts=(PTS-STARTPTS)/{x['speed']}")
    z = x["zoom"]
    vf += [f"fps={fps}", f"scale={int(W * z) // 2 * 2}:{int(H * z) // 2 * 2}:force_original_aspect_ratio=increase", crop_expr(x["anchor"], W, H)]
    if x["hflip"]: vf.append("hflip")
    lut = lut_for(e, x)
    if lut: vf.append(f"lut3d=file='{lut}':interp=tetrahedral")
    vf += list(x["vf"])
    tr = x["trans"] or {}
    if tr.get("type") == "dip": vf.append(f"fade=t=in:st=0:d={max(1, tr.get('frames', 6) // 2) / fps:.4f}:color={tr.get('color', 'black')}")
    if tr.get("type") == "flash": vf.append(f"fade=t=in:st=0:d={tr.get('frames', 3) / fps:.4f}:color={tr.get('color', 'white')}")
    if x["fade_out"]:
        k, col = x["fade_out"]; vf.append(f"fade=t=out:st={(total - k) / fps:.4f}:d={k / fps:.4f}:color={col}")
    vf += [f"setpts=N/({fps}*TB)", "setsar=1", "format=yuv420p"]
    lut_sig = os.path.getmtime(lut) if lut and os.path.exists(lut) else None  # re-render when a LUT is re-matched
    key = hashlib.md5(json.dumps([src, os.path.getmtime(src), start, total, vf, preview, lut_sig]).encode()).hexdigest()[:16]
    out = os.path.join(cache, f"{x['clip']}_{key}.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", fmt_t(start), "-t", fmt_t(total / fps * x["speed"] + 1.0), "-i", src,
           "-an", "-vf", ",".join(vf), "-frames:v", str(total), "-c:v", "libx264",
           "-preset", "ultrafast" if preview else "fast", "-crf", "30" if preview else "16", "-r", str(fps), out]
    return out, cmd, total


def audio_job(e, x, src_info, cache, a_next=0.0):
    """Sound window for shot x = [t - a_x, t + n/fps - a_next]; offsets shift sound across the picture cut
    (J/L cuts) while every window still sums to the programme length."""
    fps = e["fps"]; a0 = float(x["audio_offset"]); d = x["n"] / fps + a0 - float(a_next)
    if d <= 0: raise ValueError(f"{x['clip']}@{x['t']}: audio offsets leave no sound window")
    t_src = x["audio_from"][1] if x["audio_from"] else x["t"]
    t0 = max(0.0, t_src - a0)
    gain = 0.0 if x["audio"] is True else float(x["audio"] or 0)
    key = hashlib.md5(json.dumps([src_info["path"], t0, d, x["speed"], x["audio"], fps]).encode()).hexdigest()[:16]
    out = os.path.join(cache, f"a_{x['clip']}_{key}.wav")
    if x["audio"] is not False and src_info.get("has_audio") and 0.5 <= x["speed"] <= 2:
        af = ([f"atempo={x['speed']}"] if x["speed"] != 1 else []) + [f"volume={gain}dB", f"apad=whole_dur={d:.4f}"]
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", fmt_t(t0), "-t", fmt_t(d * x["speed"] + 0.5), "-i", src_info["path"],
               "-vn", "-af", ",".join(af), "-ac", "2", "-ar", "48000", "-t", fmt_t(d), out]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", fmt_t(d), out]
    return out, cmd


# ------------------------------------------------------------------ render
def render(e, preview=False, dry=False):
    fps = e["fps"]
    e["_sources_path"] = os.path.abspath(e["sources"]); srcs = load_json(e["sources"])
    shots, total = resolve(e)
    tail = e.get("tail") or {}; tail_n = int(tail.get("frames", 0))
    dur = (total + tail_n) / fps
    print(f"{e['name']}: {len(shots)} shots, {total}+{tail_n} frames = {dur:.3f}s @ {fps} fps {'(PREVIEW)' if preview else ''}")
    for w in checks(e, shots, srcs): print("  WARN", w)
    os.makedirs(e["out_dir"], exist_ok=True)
    tsv = os.path.join(e["out_dir"], f"{e['name']}_shotlist.tsv"); pos = 0
    with open(tsv, "w") as f:
        f.write("#\tblock\tclip\tfile\tsrc_in\tframes\trec_in_s\ttrans\tnote\n")
        for i, x in enumerate(shots):
            f.write(f"{i + 1}\t{x['block']}\t{x['clip']}\t{os.path.basename(srcs[x['clip']]['path'])}\t{x['t']}\t{x['n']}\t"
                    f"{pos / fps:.3f}\t{(x['trans'] or {}).get('type', 'cut')}\t{x.get('note', '')}\n"); pos += x["n"]
    if dry: return None
    cache = os.path.join(e["out_dir"], "cache_preview" if preview else "cache"); os.makedirs(cache, exist_ok=True)
    jobs = [seg_job(e, x, srcs[x["clip"]]["proxy" if preview else "path"], preview, cache) for x in shots]
    def go(j):
        out, cmd, _ = j
        if not os.path.exists(out): run(cmd)
        return out
    with ThreadPoolExecutor(e["workers"]) as ex: segs = list(ex.map(go, jobs))
    W, H = (e["W"] // 3) // 2 * 2 if preview else e["W"], (e["H"] // 3) // 2 * 2 if preview else e["H"]
    if tail_n:
        tp = os.path.join(cache, f"tail_{tail.get('color', 'black')}_{tail_n}_{W}x{H}_{fps}.mp4")
        if not os.path.exists(tp):
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={tail.get('color', 'black')}:s={W}x{H}:r={fps}",
                 "-frames:v", str(tail_n), "-c:v", "libx264", "-pix_fmt", "yuv420p", tp])
    # native audio bed (one wav for the whole timeline)
    nat = None; na = e.get("native_audio")
    if na:
        if na.get("all"):
            for x in shots:
                if x["audio"] is False: x["audio"] = True
        if any(x["audio"] is not False for x in shots):
            ajobs = [audio_job(e, x, srcs[x["audio_from"][0] if x["audio_from"] else x["clip"]], cache, shots[i + 1]["audio_offset"] if i + 1 < len(shots) else 0.0)
                     for i, x in enumerate(shots)]
            for out, cmd in ajobs:
                if not os.path.exists(out): run(cmd)
            nat = os.path.join(cache, f"native_{hashlib.md5(''.join(o for o, _ in ajobs).encode()).hexdigest()[:12]}.wav")
            lst = os.path.join(cache, "alist.txt")
            with open(lst, "w") as f: f.writelines(f"file '{o}'\n" for o, _ in ajobs)
            run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", nat])  # PCM: exact
    # ---- filter graph
    ins, g = [], []
    for s in segs: ins += ["-i", s]
    groups, cur = [], []
    for i, x in enumerate(shots):
        if x["trans"] and x["trans"].get("type") == "xfade" and cur: groups.append(cur); cur = []
        cur.append(i)
    groups.append(cur)
    if tail_n: ins += ["-i", tp]; tail_idx = len(segs)
    acc, acc_frames = None, 0
    for gi, grp in enumerate(groups):
        labels = "".join(f"[{i}:v]" for i in grp)
        if gi == len(groups) - 1 and tail_n: labels += f"[{tail_idx}:v]"
        nin = len(grp) + (1 if gi == len(groups) - 1 and tail_n else 0)
        g.append(f"{labels}concat=n={nin}:v=1:a=0,setpts=N/({fps}*TB)[g{gi}]" if nin > 1 else f"{labels}setpts=N/({fps}*TB)[g{gi}]")
        gframes = sum(shots[i]["n"] for i in grp) + (tail_n if gi == len(groups) - 1 else 0)
        if acc is None: acc, acc_frames = f"[g{gi}]", gframes; continue
        tr = shots[grp[0]]["trans"]; k = tr.get("frames", 8)
        g.append(f"{acc}[g{gi}]xfade=transition={tr.get('kind', 'fade')}:duration={k / fps:.4f}:offset={(acc_frames - k) / fps:.4f}[x{gi}]")
        acc, acc_frames = f"[x{gi}]", acc_frames + gframes
    g.append(f"{acc}setpts=N/({fps}*TB)[v0]"); vlab = "[v0]"; n_in = len(ins) // 2
    for k, ov in enumerate(e.get("overlays") or []):
        ins += ["-loop", "1", "-framerate", str(fps), "-i", ov["png"]]
        scale = f"scale={W}:{H}," if preview else ""
        g.append(f"[{n_in}:v]{scale}format=rgba[ovs{k}]")
        en = f":enable='between(t,{ov.get('start', 0)},{ov['end'] if ov.get('end') is not None else dur + 1})'"
        g.append(f"{vlab}[ovs{k}]overlay=0:0:shortest=1{en}[v{k + 1}]"); vlab = f"[v{k + 1}]"; n_in += 1
    if e.get("post_vf"):
        g.append(f"{vlab}{','.join(e['post_vf'])}[vpost]"); vlab = "[vpost]"
    g.append(f"{vlab}format=yuv420p[vout]")
    amix = []
    m = music_items(e)
    if m:
        labs = []
        for k, it in enumerate(m):
            ins += ["-ss", fmt_t(it["start"]), "-t", fmt_t(it["end"] - it["start"]), "-i", it["file"]]
            af = [f"volume={it.get('gain_db', 0)}dB"]
            if it.get("fade_in"): af.append(f"afade=t=in:st=0:d={it['fade_in']}")
            fo = it.get("fade_out", 0.03)
            if fo: af.append(f"afade=t=out:st={max(0, it['end'] - it['start'] - fo):.3f}:d={fo}")
            ms = int(round(it["at"] * 1000))
            if ms: af.append(f"adelay={ms}|{ms}")
            g.append(f"[{n_in}:a]{','.join(af)},aresample=48000[mu{k}]"); n_in += 1; labs.append(f"[mu{k}]")
        g.append(f"{''.join(labs)}amix=inputs={len(labs)}:duration=longest:dropout_transition=0:normalize=0[mus]"
                 if len(labs) > 1 else f"{labs[0]}anull[mus]")
        amix.append("[mus]")
    if nat:
        ins += ["-i", nat]; g.append(f"[{n_in}:a]volume={na.get('gain_db', 0)}dB,aresample=48000[nat0]"); n_in += 1
        if m and na.get("duck_music", True):
            g.append("[nat0]asplit=2[nat][natsc]")
            g.append(f"[mus][natsc]sidechaincompress=threshold={na.get('duck_threshold', 0.03)}:ratio={na.get('duck_ratio', 8)}:attack=15:release=350[musd]")
            amix[amix.index("[mus]")] = "[musd]"; amix.append("[nat]")
        else: amix.append("[nat0]")
    for k, s in enumerate(e.get("sfx") or []):
        ins += ["-i", s["file"]]; ms = int(s["at"] * 1000)
        g.append(f"[{n_in}:a]adelay={ms}|{ms},volume={s.get('gain_db', 0)}dB,aresample=48000[sfx{k}]"); n_in += 1; amix.append(f"[sfx{k}]")
    has_audio = bool(amix)
    if has_audio:
        mix = f"{''.join(amix)}amix=inputs={len(amix)}:duration=longest:dropout_transition=0:normalize=0" if len(amix) > 1 else f"{amix[0]}anull"
        ln = loud_target(e)
        if ln is not None: mix += f",loudnorm=I={ln}:TP=-1.0:LRA=11"
        g.append(f"{mix},aresample=48000,apad[aout]")
    final = os.path.join(e["out_dir"], f"{e['name']}{'_preview' if preview else ''}.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(g), "-map", "[vout]"]
    if has_audio: cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast" if preview else e["preset"], "-crf", "28" if preview else str(e["crf"]),
            "-pix_fmt", "yuv420p", "-r", str(fps), "-t", fmt_t(dur), "-movflags", "+faststart", final]
    with open(os.path.join(cache, "last_ffmpeg_cmd.txt"), "w") as f: f.write(" ".join(map(str, cmd)))
    run(cmd)
    ln = loud_target(e) if has_audio else None
    if ln is not None and not preview:
        fix_loudness(final, ln)
    rep = verify_basic(final, total + tail_n, fps)
    dump_json(dict(name=e["name"], output=final, preview=preview, fps=fps, size=[W, H], frames=total + tail_n, duration=dur,
                   music=m, time_base=e["time_base"], shots=[{k: v for k, v in x.items() if k != "fade_out"} for x in shots],
                   overlays=e.get("overlays"), check=rep), os.path.join(e["out_dir"], f"{e['name']}{'_preview' if preview else ''}.edl.json"))
    print(f"-> {final}\n   {rep}")
    return final


def fix_loudness(path, target, tol=0.7):
    """Single-pass loudnorm undershoots on short edits; measure and apply the residual gain (+ -1 dBTP limiter)."""
    from common import loudness
    lufs, _ = loudness(path)
    if lufs is None or abs(lufs - target) <= tol: return
    tmp = path + ".loud.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", path, "-c:v", "copy", "-af",
         f"volume={target - lufs:.2f}dB,alimiter=limit=0.89:level=false", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", tmp])
    os.replace(tmp, path)
    print(f"   loudness {lufs:.1f} -> target {target} LUFS (gain {target - lufs:+.1f} dB)")


def verify_basic(path, expect, fps):
    info = probe(path)
    pts = run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "frame=pts_time", "-of", "csv=p=0", path], capture=True)
    t = np.array([float(x.strip(",")) for x in pts.split() if x.strip(", ") and x.strip(", ") != "N/A"])
    gaps = int((np.diff(t) > 1.5 / fps).sum()) if len(t) > 1 else 0
    ok = len(t) == expect and gaps == 0
    return dict(ok=bool(ok), frames=len(t), expected=expect, gaps=gaps, duration=info["duration"], audio=info["has_audio"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("edit"); ap.add_argument("--preview", action="store_true")
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--workers", type=int)
    a = ap.parse_args(); e = load_edit(a.edit)
    if a.workers: e["workers"] = a.workers
    render(e, preview=a.preview, dry=a.dry)


if __name__ == "__main__":
    main()
