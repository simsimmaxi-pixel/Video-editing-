# Blueprint: "Northampton !" games-night recap → recap1

**Reference:** `ref/ref.mp4`, 576×1024 (9:16) 30 fps, 20.00 s (600 f), HEVC + AAC 32 kbps. It is a TikTok re-download, so **master at 1080×1920**.
**Fidelity:** TBD (ask when footage arrives).
**Library match:** `library/styles/silverstone-event-recap` (same creator series, same venue city, same caption device).
**The big difference:** that profile is a bimodal *burst/hold* montage (ASD 0.56 s, 6-12 f bursts). This one is a
**steady medium-pace montage** (ASD 1.43 s, body shots 29-53 f) with no bursts. Don't start from P01.

Measured data: `analysis/summary.md`, `analysis/profile.json`; corrected cuts in `analysis/cuts_final.json`.

## Intent (creative director)
A "look what you missed" recap of a social games night (giant Jenga, claw machines, Connect 4, dancing, goodie
bags) that sells the *vibe* of the event to people who weren't there, for a vertical feed.
**Tone:** relaxed, communal, playful. It gives you time to see each moment rather than overwhelming you.
**What makes it work (fidelity priorities):**
1. Even, unhurried rhythm: every moment gets ~1.2-1.7 s, long enough to read what's happening.
2. People *doing* things (games, dancing), with one face-to-camera laugh as the emotional peak near the end.
3. The single persistent location caption, which answers "where" for the whole video.
**What not to copy:** the creator's identity/handle, the people's faces, the TikTok sound (not licensed to you), and
the 32 kbps platform audio softness. (No TikTok watermark is burned into this download.)

## Editing grammar (editor)
- **Pacing:** 13 picture shots + black end card. ASD mean 1.43 s / median 1.40 s. Frames per shot:
  `70 | 37 44 44 29 29 40 36 51 50 53 | 24 | 71 | black 22`.
- **Structure (fractions of runtime):**

| Part | Time | Frac | Frames | Content |
|---|---|---|---|---|
| Open hold | 0.00-2.33 | 0.00-0.12 | 70 | Jenga tower among people, slow drift (mid-activity, no establishing wide) |
| Body | 2.33-16.10 | 0.12-0.81 | 10 shots, 29-53 f (mean 41) | games/people/details rotation |
| Whip-in reaction | 16.10-16.90 | 0.81-0.85 | 24 | guy laughing at camera; entered via an in-camera whip out of the Jenga shot |
| Closing hold | 16.90-19.27 | 0.85-0.96 | 71 | wide of the crowd/venue with a photographer at work, drift |
| Black card | 19.27-20.00 | 0.96-1.00 | 22 | black + caption, music still running |

  The only "fast" pocket is shots 5-6 (29 f each: dancers → crowd at the barrier) at 0.33-0.42 of runtime. It's a
  slight lift, not a burst.
- **Cut placement:** not synced to beats (p=0.18), downbeats (p=0.74) or onsets (p=0.75). Cuts follow the content
  (C01 free cuts + C03 cut on action). **Do not snap to the beat.**
- **Transitions:** 12 hard cuts + 1 in-camera whip (Jenga → laughing guy, ~16.0-16.1 s, 2-3 blurred frames).
  T01 + T02. No digital transitions, no speed ramps, no zooms.
- **Camera:** handheld phone, mostly slow drift/move (drift 5, move 4, static 3, whip 1). Chest-height, observer
  POV (not selfie), and subjects mid-activity.
- **Rotation:** activity (Jenga, claw machine, Connect 4) ↔ people (dancers, crowd) ↔ detail (goodie bags). Claw-machine
  shots appear as a consecutive pair (shots 9-10), so pairs of the same activity are allowed. Jenga bookends the body
  (shot 1 and shot 11).
- **Opening/ending:** a cold open on an activity already in progress, the first cut at 2.33 s. It ends on the human
  peak (laugh to camera), then a calm wide, then **22 f of black with the caption still up** (much longer than
  the 3 f tail in the saved profile).

## Music (music editor)
- **Role:** the driver. A single music bed (TikTok sound), 117.5 BPM (beat 0.511 s). The RMS shows a strong accent
  every ~2.0 s (one per bar) from ~1.5 s onward.
- **Entry:** short fade-in, near-silent for the first ~0.5 s. A section change at **3.88 s (0.19 of runtime)**; the
  first body cuts sit around it (3.57 s), not on it.
- **Lock:** section level at most. Individual cuts are free.
- **Exit:** the music keeps playing under the black card and is cut hard at 20.0 s (no fade-out).
- **Level:** -17.5 LUFS, peak -2.0 dBTP (quiet for social). Deliver at -14 LUFS / -1 dBTP unless you want to match.
- **For your track:** pick a ~20 s window with no big break (`--shape sustained`), entering on or just before a
  section start. Put the open-hold → body boundary near the first section change, and end on a phrase end with the
  last ~0.7 s over black.

## Sound (sound designer)
Music only, as far as can be measured: the low spectral flatness (0.039) and centroid of 2.5 kHz fit a music bed.
No SFX hits were detected (cuts aren't onset-synced). **Speech wasn't checked** (faster-whisper isn't installed). If there's
crowd sound or voice under the music, tell me. Plan: music only, clip audio muted, -14 LUFS (S05).

## Look (colourist)
- Luma p1/p50/p99 **2.6 / 39.4 / 90.6**, contrast (std) 23.0, saturation **0.236**, a +2.3, b **+3.6** (slightly warm).
- Split: shadows b -2.0, highlights b +6.3 (mild warm highlights; under the 10-pt teal-orange threshold).
- Vignette 0.96 (none), grain 2.33 (likely compression), no bars.
- Per-shot sat 0.18-0.33 and b 0-8 vary with the lighting, so this is **natural phone footage in a dim venue, not a grade**.
- Plan: no creative grade. Normalise mixed cameras if needed (G02). Use a gentle `grade.py match` (strength ~0.6) only
  if your footage is much brighter or more saturated (the target is L50 ≈ 40, sat ≈ 0.24).

## Graphics
One persistent caption, **"Northampton !"** (location + space + "!"):
- Position: centred, x 0.306-0.688, y 0.479-0.514 → **cx 0.50, cy 0.497**, cap-box height **3.5%** of frame.
- Style: white TikTok-Classic-style sans (medium/semibold) with a **thin black outline**, no box or emoji.
- Timing: frame 0 to the end, **including the black card** (X01).
- It sits mid-frame over faces at times. The reference doesn't care, but R01 (punch-in, anchor top) is available.

## Recreation plan
- **Library techniques:** P02 (cold open, here a 70 f hold rather than 15-18 f) · C01 + C03 · T01 (22 f black tail) ·
  T02 (one in-camera whip into the peak reaction) · M01 (`--shape sustained`) · S05 · X01 (if you want the caption).
- **Shot template (600 f total, scale by fractions if the song window differs):**

| # | Role | Frames | Notes |
|---|---|---|---|
| 1 | Activity mid-action, slow drift | 66-72 | hook: something already happening |
| 2-11 | Body rotation: activity / people / detail | 29-53 each (mean ~41) | 2 shorter (~29 f) people shots near 0.35-0.42; allow one same-activity pair |
| 12 | Face-to-camera laugh/reaction, entered by a whip | 22-26 | the human peak; source moment must contain the whip |
| 13 | Calm wide of the venue/crowd | 68-72 | breathe out |
| 14 | Black + caption | ~22 | music runs under it, hard stop |

- **Footage roles to find at ingest:** 1 strong hook activity · ~10 varied activity/people/detail moments · 1 genuine laugh
  or reaction to camera (ideally with a whip into it) · 1 wide crowd/venue shot.

## Open questions for the user
1. Fidelity: near-identical rhythm, or "in the spirit of"?
2. Caption: keep a location tag ("<Your location> !"), change it, or drop it?
3. Length: ~20 s like the reference, or fit to your song?
