# Pitfalls (each one happened; the scripts already handle them)

Read this before writing custom ffmpeg or OpenCV code outside the bundled scripts.

| Symptom | Cause | Fix (where handled) |
|---|---|---|
| `Invalid duration for option ss: .500` | bc/printf dropped the leading zero | always format times as `%.3f` (`common.fmt_t`) |
| Joined video has fewer frames than planned, small timestamp gaps | concat **demuxer** drops frames at B-frame mp4 segment boundaries | concat **filter** + `setpts=N/(fps*TB)` per segment and after joining (engine) |
| Overlay shows only on the first frame | a still image input is one frame long | `-loop 1 -framerate <fps>` on the image, plus `overlay=...:shortest=1` (engine) |
| Overlay frame count off by a few | the looped image defaulted to 25 fps | give `-framerate` the output fps (engine) |
| Portrait iPhone clip comes out sideways or squashed | rotation stored in side data, stream is landscape | ffmpeg autorotates on decode; `common.probe` reports rotated w/h |
| Mixed 30/60/59.94 fps sources | different time bases | `fps=<out>` in every segment chain (engine) |
| No `drawtext` filter / emoji render as boxes | ffmpeg built without libfreetype; drawtext has no colour emoji | render text as PNG (`caption.py`) |
| Colours flat on some iPhone clips | HDR (HLG) source, no `zscale` to tone-map | check `library.md` HDR flag; export SDR or accept + grade-match |
| Default scene detection misses fast cuts | ~6-frame shots fall under default thresholds | multi-threshold voting + visual review of uncertain cuts (analyze_reference) |
| Too many cuts in handheld holds | camera motion triggers low thresholds | the same review step; keep only real cuts in `cuts_final.json` |
| `xargs: command line cannot be assembled` | long paths with spaces | Python thread pools instead of xargs (ingest) |
| `ModuleNotFoundError` for a sibling script | `python -I` drops the script dir from sys.path | scripts insert their own dir into sys.path |
| `int64 is not JSON serializable` | numpy scalars | `common.dump_json` |
| Haar cascade missing in opencv-headless | build-dependent | don't rely on it; use the visual check or mediapipe if installed |
| librosa can't read AAC/HE-AAC | audioread backend | decode to wav with ffmpeg first (`common.extract_wav`) |
| Loudness lands 1-2 LU under target | single-pass loudnorm on short programmes | measure + residual gain + limiter (engine `fix_loudness`) |
| Song "ends" late in detection | reverb/decay tail counted as music | end = last time RMS > 25% of the median (analyze_music) |
| Beat grid one beat off | librosa bar phase is a guess | use beat-exact drops, or beat_this downbeats |
| Shake QC flags every quick handheld cut | one threshold for all shots | strict only for holds (≥1 s); bursts only flag extreme shake (engine checks) |
| Caption sits across a face | fixed overlay position, moving subjects | reframe the shot: `zoom` with `anchor="top"`, not by moving the caption |
| Text shot unreadable | burst-length shot carrying a sign or title | `text=<chars>` on the shot; the engine enforces about 0.6 s + 0.05 s/char |
| Transcript of a music-only video says "Outro Music" / "Thanks for watching!", or shows song lyrics as dialogue | Whisper hallucinates on music and transcribes sung vocals with low confidence | drop segments with no_speech_prob > 0.4 or avg_logprob < -1.0; language prob < 0.5 = no speech (analyze_reference) |
| `_ARRAY_API not found` warnings, torch ops on arrays fail | torch 2.2 (last Intel-Mac build) vs NumPy 2 | setup.sh pins numpy<2 + opencv-headless<4.11 when torch < 2.3 |
| beat_this import: `unsupported operand type(s) for \|` | needs Python >= 3.10 | setup.sh skips it on 3.9; downbeats fall back to an estimate |
| Reference "ends on a 4 s hold" / has a corner "overlay" | TikTok/Reels end card and watermark | treat the end card and watermark as platform artifacts: exclude them from block structure and overlays |
