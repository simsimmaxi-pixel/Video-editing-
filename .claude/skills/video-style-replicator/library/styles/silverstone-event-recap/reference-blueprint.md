# Style Blueprint: "Northampton 🎾" Event Recap (TikTok, @ade.eventsuk)

Reference: `v24044gl0000d81kh5vog65km4kl04gg.MP4`. Everything below was measured from the file. Raw data is in `analysis/`.

## 0. Technical profile (FFprobe)
| Property | Value |
|---|---|
| Duration | 21.300 s video / 21.268 s audio |
| Resolution | 576×1024 (9:16, SAR 1:1). This is a TikTok re-download; **master at 1080×1920** |
| Frame rate | 30/1 CFR, 639 frames, progressive |
| Color | BT.709, TV range, yuv420p, H.264 High |
| Audio | AAC HE-AACv2 stereo 44.1 kHz, ~32 kbps (a TikTok "sound", platform-compressed) |

---

## STAGE 1: Style deconstruction

### 1. Pacing and transition logic
Detection: PySceneDetect ContentDetector at thresholds 12/15/18/22 plus AdaptiveDetector. Each candidate cut was then checked by eye on 15 fps frame strips. Motion inside long handheld holds caused false positives at 5.667, 8.467, 10.433, 11.133, 16.4, 19.267 and 19.667 s, and those were removed.

**Final cut list (s):** 0.567, 0.833, 1.100, 1.400, 1.900, 2.233, 2.433, 2.833, 3.200, 3.467, 3.767, 4.000, 4.267, 4.500, 4.733, 5.067, 5.933, 7.967, 9.867, 10.933, 11.700, 12.533, 12.733, 13.133, 13.467, 13.700, 13.967, 14.433, 14.767, 14.933, 15.100, 15.400, 15.733, 16.067, 18.033, 19.000, 19.433, then black at 21.200 through 21.300.

**Shot lengths (frames @30):** 17, 8, 8, 9, 15, 10, 6, 12, 11, 8, 9, 7, 8, 7, 7, 10, 26 | 61, 57, 32, 23 | 25, 6, 12, 10, 7, 8, 14, 10, 5, 5, 9, 10, 10 | 59, 29 | 13, 53 | +3 black

- **38 shots. Mean ASD 0.558 s, median 0.334 s**, range 0.166 to 2.034 s.
- The video has a **bimodal "Burst / Hold" structure**:

| Block | Time | Shots | ASD | Content |
|---|---|---|---|---|
| A: Burst 1 (hook) | 0.000–5.933 | 17 | **0.349 s (≈10.5 f)** | venue tour plus faces, ultra-rapid |
| B: Hold 1 | 5.933–11.700 | 4 | **1.442 s** | guy dancing with dessert (2.03 s), girl tasting/reaction (1.9 s), crowd, court walk |
| C: Burst 2 | 11.700–16.067 | 13 | **0.336 s** | jenga, padel, pro shop, group lineups |
| D: Hold 2 | 16.067–19.000 | 2 | **1.466 s** | rotated selfie handshake (1.97 s), high-five group |
| E: Outro | 19.000–21.200 | 2 | 1.100 s | ceiling whip (0.43 s) then a slow push on the logo wall (1.77 s), then a 3-frame hard cut to black |

- **Transition grammar:** 100% hard cuts. There are no dissolves, no digital transitions and no speed ramps. Energy comes from camera motion inside the shot (handheld walk-ins, whip-tilts to the ceiling, a selfie spin), not from edit effects. Cuts usually fall mid-gesture (cut-on-action).

### 2. Audio and rhythm matrix
- Librosa tempo **152 BPM** (beat period 395 ms; it may be a 76 BPM half-time feel), 53 beats.
- **Cuts are NOT beat-synced.** The mean |cut − nearest beat| is **107 ms**, where random placement would give ~99 ms. Only 3/37 cuts land within 1 frame of a beat. Distance to the nearest onset is 58 ms, which is also chance level given an onset density of about 5/s.
- **The sync is macro, not micro.** The RMS energy curve has a near-silent break at **~10.5 s** (RMS 0.029 vs a 0.15 to 0.27 baseline). Burst 2 starts at 11.7 s, right after the music re-enters. The holds sit on groove sections.
- **Layer hierarchy:** a single music bed (trending sound) at 100%. No voiceover, subtitles or SFX layer was detected, and the location-sound mix is absent or buried. *Caveat: the "no VO" finding comes from the absence of subtitles plus the spectral profile (centroid 3.45 kHz, flatness 0.059). It was not confirmed with Whisper.*

### 3. Visual layout and graphic anchors
- **Capture:** handheld phone with no gimbal, mostly the **0.5× ultra-wide** lens (barrel distortion on the ceiling ring lights). The camera sits low at chest height and tilts up, so the ceiling, ring lights and court cages read as "venue scale".
- **Framing:** subjects are **center-framed**, medium to full body, often walking toward the lens or reacting to it directly. Selfie shots are frequent. In one deliberate **~90–120° dutch/rotated selfie** (16.07–18.03 s), the frame rotation is the "transition energy".
- **Grade:** no grade. Native phone HDR, **mean luma 134/255, mean saturation 75/255 (~29%)**, mixed warm tungsten wood with cool LED blue courts. Do not stylize.
- **Text anchor (the only graphic):** `Northampton 🎾`
  - Bounding box (measured on the end black frame): **x 29.5%–70.5%, y 48.2%–51.6%**. Horizontally centered, vertical center at **49.9%**.
  - Height ≈ **3.4% of frame** including the emoji, which is ~65 px on 1920 (font size ≈ 50–54 px).
  - White TikTok "Classic" sans with a soft drop shadow, no background box.
  - **Persistent from 0.000 to the end, including the black end frame.**
- The bouncing TikTok logo/@handle is a platform download watermark. **Do not replicate it.**

### 4. Narrative flow and retention hooks
- **First 3 s:** frame 0 opens *mid-action* (Jenga pull, 17 f), so there is no establishing ramp. Then 9 cuts in ~2.8 s (≈0.3 s each) give a dense "you missed this" sampler: venue logo, faces, courts, lounge. The caption answers *where* immediately, and the 🎾 answers *what*.
- **Content rotation inside bursts:** **Venue → Person → Activity → Person → Venue…** No two consecutive shots share the same category in a burst, except deliberate "walk-in" pairs.
- **Holds are reserved for human payoff moments:** a dance, a food-tasting facial reaction, a rotated selfie, high-fives. Each lasts 1.5–2.0 s (≈4–5 beats).
- **Bookend loop:** the logo wall appears at ~1.4 s (selfie in front of it) and again as the final 1.77 s hold, followed by a 3-frame black tail. That makes a clean loop seam for TikTok autoplay.

---

## Mathematical cutting rules (replication spec)
```
FPS = 30; TOTAL = 21.2 s (+3 black frames)   # scale proportionally if the music differs
BLOCKS = [
 ("A_burst", 0.00, 0.28), ("B_hold", 0.28, 0.55), ("C_burst", 0.55, 0.76),
 ("D_hold", 0.76, 0.90), ("E_outro", 0.90, 1.00)]   # fractions of TOTAL
BURST shot length: frames ~ U{6..12}, mean 10, ≤ 2 shots of 5f per burst, first shot of video = 15–18 f
HOLD  shot length: 45–61 f for the hero moment, 23–32 f for the secondary
OUTRO: 1 whip/ceiling tilt 12–14 f, then the venue-logo hold 50–55 f, then 3 f black
CUT PLACEMENT: free (do NOT quantize to the beat); cut on subject motion peak
MACRO SYNC: start of C_burst = first downbeat after the music's breakdown/re-entry (±0.5 s)
ROTATION in bursts: cycle categories [venue, person, activity]; never 3 of one category in a row
TEXT: single location string + emoji, centered, cy=50%, h≈3.4% frame, white + shadow, 0 → end
GRADE: none; normalize exposure only
AUDIO: music only, 0 dB bed, hard-out with the black tail
```

---

## PROMPT FOR CLAUDE 3.5 SONNET EXECUTION
> Note: Claude 3.5 Sonnet is retired. Paste this into **Claude Sonnet 5.5** (`claude-sonnet-5-5`); it works as written.

```
ROLE: You are an edit-assembly engine. A style blueprint has already been designed. Do NOT
re-analyze or reinterpret style. Your job is deterministic, line-by-line data crunching:
turn my raw asset inventory into a finished timeline file that obeys the rules below exactly.

=== STYLE PROFILE (fixed, do not modify) ===
Format: 1080x1920, 30 fps CFR, BT.709, H.264 + AAC 44.1 kHz stereo.
Total runtime: 21.2 s + 3 frames black (= 639 frames). If the music track is a different length,
scale block boundaries proportionally, but keep the per-shot frame ranges.

Block map (fraction of total -> 21.2 s values):
  A_burst  0.00-0.28 (0.000-5.933)   ~17 shots, 6-12 f each (mean 10); FIRST shot 15-18 f and must
                                      start mid-action (motion already happening on frame 0)
  B_hold   0.28-0.55 (5.933-11.700)  4 shots: hero 55-61 f, hero 55-59 f, support 30-32 f, support 23-25 f
  C_burst  0.55-0.76 (11.700-16.067) ~13 shots, 5-14 f (mean 10)
  D_hold   0.76-0.90 (16.067-19.000) 2 shots: 57-59 f (prefer a tilted/rotated selfie), 28-30 f
  E_outro  0.90-1.00 (19.000-21.200) whip/ceiling tilt 12-14 f, then venue logo/sign hold 50-55 f,
                                      then 3 f pure black

Cut rules:
- Hard cuts only. No dissolves, wipes, zooms or speed ramps.
- Do NOT snap cuts to beats. Instead, place each cut at the motion peak inside the chosen source
  range (use motion/scene scores if provided; otherwise centre the range on the clip's action).
- MACRO SYNC: if beat/energy markers are provided, move the A->B and B->C boundaries so that C_burst
  starts on the first downbeat after the largest RMS dip (breakdown) in the track, within +/-0.5 s.
  Absorb the difference in B_hold's support shots.
- Bursts rotate categories venue -> person -> activity; never 3 of the same category in a row and
  never reuse the same source clip twice in one burst.
- Holds = human payoff moments only (reaction to camera, dance, tasting, high-five).
- The E_outro logo shot should be the same venue/sign seen in the first ~2 s (loop bookend).

Graphics:
- One text overlay for the full duration, including the black tail: "<LOCATION> <EMOJI>".
- White, TikTok-Classic-like sans (use "Proxima Nova Semibold" or fallback "Montserrat SemiBold"),
  size 52 px @1920 h, drop shadow 0 2px 4px rgba(0,0,0,0.5), no box.
- Horizontally centred; vertical centre at y = 960 px (50%).
- FFmpeg drawtext cannot render colour emoji, so render the emoji as a 60x60 PNG overlay placed right
  after the text with an 8 px gap, or burn the whole caption as one pre-rendered PNG.
- No watermark, no subtitles, no other graphics.

Colour/audio:
- No creative grade. Scale/crop each clip to fill 1080x1920 (centre crop; never letterbox).
- Audio = music track only at 0 dB with clip audio muted, hard out at 21.2 s (no fade).

=== YOUR TASK ===
1. Parse my ASSET INVENTORY (below): clip list with paths, durations, optional category tags,
   optional motion/scene scores, optional Whisper transcripts, music track path, beat markers,
   RMS curve.
2. If clips lack category tags, infer them from filename/transcript/description and print the
   inferred table first (path | category | chosen in-point | out-point | reason, max 8 words).
3. Allocate shots to blocks per the rules. Print a shot table:
   # | block | src path | src_in (s) | src_out (s) | rec_in (frame) | rec_out (frame) | len (f)
   Validate: sum of lengths = total frames; every length within its block's range; no burst
   violations. If assets are insufficient, say exactly which block is short and by how many shots;
   do not silently repeat clips.
4. Emit the final timeline in the TARGET OUTPUT PIPELINE format:
   - FFmpeg bash script (default): one trim/setpts/scale/crop chain per shot, concat, overlay
     caption PNG(s), map music, -r 30 -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k.
   - Premiere: FCP7 XML (xmeml v4) sequence 1080x1920 @30, V1 clips, V2 caption graphic, A1 music.
   - Resolve: CMX3600 EDL (30 fps NDF) plus a separate note listing the caption track settings.
   Output the complete file with no ellipses or placeholders.

=== ASSET INVENTORY ===
TARGET RAW ASSETS: [PASTE: clip paths + durations + tags/transcripts/motion scores]
MUSIC TRACK + BEATS/RMS: [PASTE: path, bpm, beat array, RMS curve]
LOCATION CAPTION: [e.g. "Northampton" + 🎾]
TARGET OUTPUT PIPELINE: [FFmpeg Bash Script | Premiere XML | Resolve EDL]
```
