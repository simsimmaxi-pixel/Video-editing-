#!/usr/bin/env bash
# One-time environment setup. Creates a persistent venv and reports what this machine's ffmpeg can do.
#   bash setup.sh            # core (required): numpy, opencv, librosa, scenedetect, pillow
#   bash setup.sh --ml       # + optional upgrades: Demucs (vocal stem), Beat This! (downbeats),
#                            #   faster-whisper (speech/word timing), open_clip (semantic footage tags)
# Prints the python path to use as $VSR_PY.
set -euo pipefail
VENV="${VSR_VENV:-$HOME/.cache/video-style-replicator/venv}"
command -v ffmpeg >/dev/null || { echo "ffmpeg not found: install it first (macOS: brew install ffmpeg)"; exit 1; }
PY="$(command -v python3.11 || command -v python3.12 || command -v python3.10 || command -v python3)"
if [ ! -x "$VENV/bin/python" ]; then "$PY" -m venv "$VENV"; fi
"$VENV/bin/python" -m pip install -q --upgrade pip >/dev/null 2>&1 || true
"$VENV/bin/python" -m pip install -q numpy opencv-python-headless librosa scenedetect pillow
if [ "${1:-}" = "--ml" ]; then
  # torch wheels: Intel Macs top out at torch 2.2.x; pip resolves the right one automatically.
  "$VENV/bin/python" -m pip install -q torch torchaudio || echo "WARN: torch install failed; ML extras unavailable"
  "$VENV/bin/python" -m pip install -q demucs || echo "WARN: demucs unavailable"
  if "$VENV/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    "$VENV/bin/python" -m pip install -q "git+https://github.com/CPJKU/beat_this.git" || echo "WARN: beat_this unavailable"
  else
    echo "NOTE: beat_this needs Python >= 3.10 (this venv: $("$VENV/bin/python" -V)); downbeats fall back to an estimate."
    echo "      To enable: install python3.11, delete $VENV, re-run with --ml."
  fi
  "$VENV/bin/python" -m pip install -q faster-whisper || echo "WARN: faster-whisper unavailable"
  "$VENV/bin/python" -m pip install -q open_clip_torch || echo "WARN: open_clip unavailable"
  # torch <= 2.2 (the last Intel-Mac build) is compiled against NumPy 1.x: keep NumPy/OpenCV on 1.x-compatible versions.
  if "$VENV/bin/python" -c 'import torch,sys; v=tuple(map(int,torch.__version__.split(".")[:2])); sys.exit(0 if v < (2,3) else 1)' 2>/dev/null; then
    "$VENV/bin/python" -m pip install -q "numpy<2" "opencv-python-headless<4.11"
  fi
fi
echo "--- capabilities"
"$VENV/bin/python" - <<'EOF'
import importlib
for m in ["cv2", "librosa", "scenedetect", "PIL", "demucs", "beat_this", "faster_whisper", "open_clip"]:
    try: importlib.import_module(m); print(f"  {m:15s} yes")
    except Exception: print(f"  {m:15s} no")
EOF
FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null)"
for f in drawtext lut3d xfade loudnorm sidechaincompress zscale tonemap vidstabtransform; do
  if echo "$FILTERS" | grep -qE "^ [A-Z.|]+ $f "; then echo "  ffmpeg:$f yes"; else echo "  ffmpeg:$f no"; fi
done
echo "VSR_PY=$VENV/bin/python"
