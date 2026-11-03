---
name: video-style-replicator
description: Break down any reference video (TikTok/Reels/Shorts, YouTube long-form such as talking heads, documentaries, vlogs and video essays, trailers, music videos, ads, event recaps) into its editing grammar, music use, sound design, colour and graphics, measured with real tools, then recreate that style with the user's own footage and music as a finished render. Use this whenever someone shares a reference video and wants it analysed, or says things like "make it like this", "recreate this edit/style", "edit my clips in the style of", "same vibe as this video", "match this pacing/grade", or wants a series of videos in one consistent style from a footage dump, even if they never say "replicate". Not for pure motion-graphics pieces with no camera footage (use hyperframes or logo-reveal-launch for those).
---

# Video Style Replicator

Two jobs, done as one pipeline:
1. **Forensics:** take a reference video apart the way a team of specialists would (creative director, editor, music editor, sound designer, colourist, graphics), backing every claim with a measurement.
2. **Recreation:** rebuild that style with new footage and music, render it, measure the result with the same tools, and close the gap.

Three principles make this work. Each one came from a real project going right or wrong:
- **Measure, don't assume.** Intuition is often wrong about a style. In the first project everyone would have said "cut on the beat", but a statistical test showed the cuts were *not* beat-synced (p≈0.7). Copying the intuition would have produced a stiffer, less authentic edit.
- **Copy the grammar, not the shots.** Reduce the style to transferable rules (pacing as fractions and frame ranges, what each kind of shot is *for*, how the edit relates to the music), then let the new footage and song fill those rules. Shot-for-shot copying only works when the new footage happens to match.
- **Close the loop.** Render, re-measure, compare with the reference profile, fix. Verified output beats careful guessing.

## Setup (once per machine)

```bash
bash scripts/setup.sh          # core: numpy, opencv, librosa, scenedetect, pillow (+ reports ffmpeg capabilities)
bash scripts/setup.sh --ml             # optional: demucs (vocal stem), beat_this (true downbeats), faster-whisper (speech), open_clip (semantic footage tags)
```
It prints `VSR_PY=...`; run every script with that interpreter (`$VSR_PY -I scripts/x.py ...`). Ask before installing the `--ml` extras (about 2 GB). Every script degrades gracefully without them and says so in its output, so mention what was skipped when it matters (e.g. "speech not transcribed").

## Workflow

Make a project folder: `analysis/` (reference), `footage/` (ingest output), `music/`, `edit/`, `output/`.

### 0. Intake: ask only what you can't infer
- Reference(s), raw footage folder, music (a supplied track, the reference's own audio, or none).
- Deliverable: platform/aspect, target length, how many versions, and **fidelity**: near-identical ("recreate this") or "in the spirit of" (a looser adaptation).
- Text on screen: don't add captions or titles unless the reference depends on them or the user asks. Ask if unsure; it's cheap to add and annoying to remove.

### 1. Measure the reference
```bash
$VSR_PY -I scripts/analyze_reference.py REF.mp4 analysis/
```
This writes `summary.md` (read it), `profile.json`, and sheets. It covers specs, cuts with transition types, per-shot duration/motion/look, the burst/hold block structure, persistent overlays, letterboxing, grain/vignette, audio tempo/downbeats/sections/loudness/fades, speech (if whisper is installed), and **cut-sync tests against chance** (beats, downbeats, onsets, sections, word ends).
- Look at `sheets/cuts_review.png` once. It shows the cuts that detectors disagreed on, as before|after pairs. Keep the real cuts, drop camera whips, write `analysis/cuts_final.json` = `{"cuts":[sec,...]}` and re-run with `--cuts analysis/cuts_final.json` (fast, cached).
- Look at `sheets/shots_*.png` (one mid-frame per shot; long videos are sampled).
- Separate the style from **platform artifacts**: watermarks, app UI, re-encode softness, a creator's @handle. Don't replicate those.

### 2. Read it through the lenses that apply
Each lens is a specialist's checklist: what to look for, which numbers in `summary.md` answer it, and how to recreate it. Read only the lenses the reference calls for. Over-analysing a simple video wastes effort and pushes the recreation toward features the reference doesn't have.

| Lens | Read when | File |
|---|---|---|
| Creative director | Always: intent, audience, emotional arc, what makes it work | `references/lenses/creative-director.md` |
| Editor | Always: pacing, cut placement, transitions, shot rotation | `references/lenses/editor.md` |
| Music editor | Music drives the piece, or the user supplies a song | `references/lenses/music-editor.md` |
| Sound designer | Voice, SFX, ambience or layered audio; any dialogue-led video | `references/lenses/sound-designer.md` |
| Colourist | The look is distinctive, or the footage mixes cameras | `references/lenses/colorist.md` |
| Graphics | Text, captions, overlays, titles or end cards are present | `references/lenses/graphics.md` |
| Long-form story | Over ~2 min, or speech/VO carries the content (YouTube, docs) | `references/lenses/story-longform.md` |

`references/formats.md` has quick orientation per format (what usually matters for a vlog, a trailer, and so on). Use it as a prior to check against the measurements, never as a substitute for them.

### 3. Write the blueprint
Fill `assets/blueprint_template.md` into `BLUEPRINT.md`: the intent in a sentence, each lens's rules **as numbers** (fractions of runtime, frame ranges, dB, LUFS, colour stats), the library techniques it uses (IDs from `library/techniques.md`), and what not to copy.
- Check `library/styles/` first. If a saved profile is close, start from it and note the differences.
- If the user only asked for a breakdown, the blueprint (plus a short summary in chat) is the deliverable. If they asked for a recreation, keep going without waiting.

### 4. Prepare the materials
```bash
$VSR_PY -I scripts/ingest_footage.py FOOTAGE_DIR footage/ [--labels "crowd,close-up face,food,sign or text"]
$VSR_PY -I scripts/analyze_music.py TRACK music/ --min 20 --max 40 --break-at 0.45 [--from-start]
$VSR_PY -I scripts/grade.py match REF.mp4 footage/map.json footage/grade --ref-profile analysis/profile.json
$VSR_PY -I scripts/strips.py footage/strips.png footage/map.json f03:5:9 f12:74:86
```
- `library.md` gives every clip's per-second sharpness/shake/motion as digit strings, a usable %, best runs and a reject flag. Read it **before** any image.
- `--labels` (CLIP) tags are hints for a shortlist, not facts. Zero-shot tagging forces every frame onto the closest label you gave it, so an ice rink became "boat or water" in one test. Include broad labels ("indoor venue", "sports or activity", "other") and confirm picks on strips before building the edit.
- Multiple references are normal (a creator's style across several posts). Analyse each one, then write the blueprint from what they share. Ranges across references are the rules; one-off features are optional. View a clip's contact sheet only if the digits make it a candidate, then use `strips.py` on the few moments you are choosing between.
- `analyze_music.py` returns bars, beat-exact bass drops, sections, where the music and vocals really end, and ranked windows. Set `--break-at` from the reference's block structure, or `--shape sustained` when the reference never breathes (one burst end to end). Without either, the ranker favours windows that contain a break. Bar phase is an estimate unless `beat_this` is installed; the beat-exact drops are reliable either way.
- Grade only when the colourist lens says the look matters or the cameras disagree. Check `compare.png`.

### 5. Build the edit
Copy `assets/edit_template.py` to `edit/<name>.py`. Blocks come from the blueprint, block ends are downbeats or section times, and shots are `(clip, src_in, frames)`, with `n=None` filling the block. Use only the library techniques the blueprint calls for.
```bash
$VSR_PY -I scripts/engine.py edit/name.py --dry       # frame math + rule checks (shake, read time, reused moments)
$VSR_PY -I scripts/engine.py edit/name.py --preview   # low-res from proxies, seconds: iterate here
$VSR_PY -I scripts/engine.py edit/name.py             # full-res final (segments cached; re-renders only what changed)
```
When craft rules conflict, rank them the way Walter Murch does: emotion > story > rhythm > eye-trace > screen planarity > spatial continuity. A cut that feels right beats one that is technically tidy.

### 6. Verify, show, iterate
```bash
$VSR_PY -I scripts/verify.py output/name.edl.json analysis/profile.json
```
`verify.md` lists integrity (frames, gaps, loudness) and a reference-vs-output style table. Fix CHECK rows unless they're deliberate (a different length, no caption). Look at `shots.png` (one frame per shot) instead of scrubbing the video. Then deliver the file. User notes usually become one-line changes to the edit file followed by a preview.

### 7. Learn: grow the library
When the user approves a result:
- Add or upgrade entries in `library/techniques.md` (status ✅ plus the project name; new moves get "use when / avoid" notes).
- Save the profile to `library/styles/<short-name>/`: the condensed blueprint, the key numbers, the edit file, and the user's feedback.

Keep entries general ("hold a text-bearing shot ≥1 s"), not project trivia ("the Silverstone sign"). This is how the skill gets better without hard-coding any one style into the workflow.

## Working efficiently (tokens and time)
- Images are the expensive part. Video file size is irrelevant, because scripts process files locally and return text. Never step through frames. A first project of 18 clips, about 11 minutes, came in at about 25 images; a second video from the same footage needed 4.
- Order of evidence: numbers (`summary.md`, `library.md`, `music.md`), then semantic tags, then one contact sheet per *candidate* clip, then strips of shortlisted moments, then the output `shots.png`.
- Iterate with `--preview` (about 10× faster), render the final once, and run long renders in the background.
- A second video from the same footage reuses everything: ingest, scan, sheets you've already seen, the grade and the segment cache.

## Reference map
- `references/lenses/*.md`: the specialist checklists (above).
- `references/formats.md`: format priors (short-form, YouTube long-form, doc, vlog, trailer, music video, ad).
- `references/pitfalls.md`: ffmpeg and pipeline gotchas, and how the scripts avoid them. Read it before writing custom ffmpeg.
- `library/techniques.md`: the ability library (IDs, use-when/avoid, how, status).
- `library/styles/`: saved style profiles from past projects, with edit files.
- `assets/edit_template.py`, `assets/blueprint_template.md`.
- Scripts: `analyze_reference`, `ingest_footage`, `analyze_music`, `grade`, `caption` (text and title PNGs, only when the reference uses text), `strips`, `engine`, `verify`, `setup.sh`.
