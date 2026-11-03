"""Shared helpers for the video-style-replicator scripts.

Everything here exists because a naive version broke in practice:
- fmt_t: ffmpeg rejects "-ss .500" (no leading zero) -> always format with "%.3f".
- probe: rotation lives in side_data (iPhone portrait = landscape stream + rotate -90).
- dump_json: numpy scalars are not JSON serialisable.
- frames_at: labelled thumbnails, so a contact sheet maps tile -> timestamp with no arithmetic.
"""
import json, os, subprocess, sys, tempfile
import numpy as np

VIDEO_EXT = {".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".webm", ".mxf"}


def run(cmd, capture=False, check=True):
    r = subprocess.run([str(c) for c in cmd], capture_output=capture, text=True, check=False)
    if check and r.returncode != 0:
        err = (r.stderr or "")[-1500:] if capture else ""
        raise RuntimeError(f"command failed ({r.returncode}): {' '.join(map(str, cmd))[:300]}\n{err}")
    return r.stdout if capture else r


def fmt_t(t):
    return f"{max(0.0, float(t)):.3f}"


def probe(path):
    j = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path], capture=True))
    v = next((s for s in j["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in j["streams"] if s.get("codec_type") == "audio"), None)
    info = dict(path=os.path.abspath(path), duration=float(j["format"].get("duration", 0) or 0), has_audio=a is not None)
    if v is None:
        return info
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    rot = rot or int(float(v.get("tags", {}).get("rotate", 0) or 0))
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den or 0) else 0.0
    trc = v.get("color_transfer", "")
    info.update(width=w, height=h, fps=round(fps, 3), rotation=rot, codec=v.get("codec_name"),
                pix_fmt=v.get("pix_fmt"), color_transfer=trc, hdr=trc in ("arib-std-b67", "smpte2084"),
                nb_frames=int(v.get("nb_frames", 0) or 0),
                orientation="portrait" if h > w else ("landscape" if w > h else "square"))
    if a is not None:
        info.update(audio_rate=int(a.get("sample_rate", 0) or 0), audio_channels=int(a.get("channels", 0) or 0))
    return info


def ffmpeg_filters():
    out = run(["ffmpeg", "-hide_banner", "-filters"], capture=True, check=False)
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and len(parts[0]) <= 4 and "->" in line:
            names.add(parts[1])
    return names


def _np_default(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return float(o)
    if isinstance(o, np.ndarray): return o.tolist()
    if isinstance(o, (np.bool_,)): return bool(o)
    raise TypeError(type(o))


def dump_json(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=_np_default)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def digit(v, lo, hi):
    if hi <= lo:
        return "0"
    return str(int(np.clip((v - lo) / (hi - lo) * 9, 0, 9)))


def extract_wav(path, sr=22050, mono=True, start=None, dur=None):
    """Decode audio through ffmpeg (librosa's audioread path is flaky with AAC/HE-AAC)."""
    fd, wav = tempfile.mkstemp(suffix=".wav"); os.close(fd)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if start is not None: cmd += ["-ss", fmt_t(start)]
    if dur is not None: cmd += ["-t", fmt_t(dur)]
    cmd += ["-i", path, "-vn", "-ac", "1" if mono else "2", "-ar", str(sr), wav]
    run(cmd)
    return wav


def loudness(path):
    """Integrated loudness (LUFS) and true peak (dBTP) via ffmpeg ebur128."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = peak = None
    for line in out.splitlines()[-30:]:
        s = line.strip()
        if s.startswith("I:") and "LUFS" in s: lufs = float(s.split()[1])
        if s.startswith("Peak:") and "dBFS" in s: peak = float(s.split()[1])
    return lufs, peak


def frames_at(video, times, height=160):
    """Grab frames (as PIL images) at the given times using OpenCV seeking (fast on proxies)."""
    import cv2
    from PIL import Image
    cap = cv2.VideoCapture(video); imgs = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0, t) * 1000)
        ok, f = cap.read()
        if not ok:
            imgs.append(None); continue
        h, w = f.shape[:2]
        f = cv2.resize(f, (max(1, int(w * height / h)), height))
        imgs.append(Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)))
    cap.release()
    return imgs


def labelled_sheet(images, labels, out, cols=10, max_width=1600):
    """Tile images with a small label burned into each tile's corner. Returns the output path."""
    from PIL import Image, ImageDraw
    imgs = [im for im in images if im is not None]
    if not imgs:
        return None
    th = imgs[0].height; tw = max(im.width for im in imgs)
    cols = max(1, min(cols, max_width // tw, len(images)))
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i, (im, lab) in enumerate(zip(images, labels)):
        x, y = (i % cols) * tw, (i // cols) * th
        if im is not None:
            sheet.paste(im, (x + (tw - im.width) // 2, y))
        if lab:
            d.rectangle([x, y, x + 7 * len(lab) + 4, y + 13], fill=(0, 0, 0))
            d.text((x + 2, y + 1), lab, fill=(255, 255, 0))
    sheet.save(out)
    return out


def sync_test(events, grid, duration, n_shuffle=2000, seed=0):
    """Are `events` (e.g. cut times) closer to `grid` (beats, downbeats, word ends...) than chance?
    Compares mean |offset to nearest grid point| with uniformly random event placement."""
    events = np.asarray([e for e in events if 0 < e < duration], float)
    grid = np.sort(np.asarray(grid, float))
    if len(events) < 3 or len(grid) < 2:
        return None
    def mean_off(ev):
        idx = np.clip(np.searchsorted(grid, ev), 1, len(grid) - 1)
        return np.minimum(np.abs(ev - grid[idx - 1]), np.abs(ev - grid[idx])).mean()
    obs = mean_off(events)
    rng = np.random.default_rng(seed)
    lo, hi = grid[0], min(grid[-1], duration)
    sims = np.array([mean_off(rng.uniform(lo, hi, len(events))) for _ in range(n_shuffle)])
    p = float((sims <= obs).mean())
    idx = np.clip(np.searchsorted(grid, events), 1, len(grid) - 1)
    near = np.minimum(np.abs(events - grid[idx - 1]), np.abs(events - grid[idx]))
    return dict(mean_offset_ms=round(obs * 1000, 1), chance_ms=round(float(sims.mean()) * 1000, 1),
                p_value=round(p, 4), within_1_frame=int((near < 0.034).sum()), n=len(events),
                verdict="SYNCED" if p < 0.01 else ("weak" if p < 0.1 else "not synced"))


def venv_python():
    return sys.executable


def camera_key(m):
    """Camera signature: footage from one camera shares noise, sharpness and stabilisation characteristics."""
    return f"{m.get('codec')}_{m.get('width')}x{m.get('height')}_{round(m.get('fps') or 0)}"


def group_stats(scan, mp, min_secs=20):
    """Per-camera scales for the per-second scan. One library-wide scale breaks on mixed cameras (a soft,
    grainy cinema camera reads 'blurry and shaky' next to a phone), so each clip is scored against its own
    camera group, falling back to the whole library when a group has fewer than `min_secs` seconds."""
    def pool(clips, k):
        return np.array([s[k] for c in clips for s in scan.get(c, [])] or [0.0])
    groups = {}
    for c in scan:
        if c in mp: groups.setdefault(camera_key(mp[c]), []).append(c)
    allc = [c for c in scan if c in mp]
    out = {}
    for key, clips in groups.items():
        src = clips if sum(len(scan[c]) for c in clips) >= min_secs else allc
        S, J, M = pool(src, "sharp"), pool(src, "shake"), pool(src, "motion")
        st = dict(group=key, S=(np.percentile(S, 5), np.percentile(S, 95)), J=(np.percentile(J, 5), np.percentile(J, 95)),
                  M=(np.percentile(M, 5), np.percentile(M, 95)), j_hold=np.percentile(J, 85), j_burst=np.percentile(J, 95),
                  s_lo=np.percentile(S, 5), s_thr=np.percentile(S, 10), m_thr=np.percentile(M, 30))
        for c in clips: out[c] = st
    return out
