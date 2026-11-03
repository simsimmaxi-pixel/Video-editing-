# Reference profile: ref.mp4
576x1024 (portrait) 30.0 fps, 20.00s, hevc, HDR=False, audio=True

## Pacing
14 shots | ASD mean 1.429s median 1.400s min 0.733 max 2.367 | hold threshold 3.23s
frames per shot: 70 37 44 44 29 29 40 36 51 50 53 24 71 22

| block | time | frac | shots | ASD |
|---|---|---|---|---|
| burst | 0.00-19.27 | 0.00-0.96 | 13 | 1.482 |
| black | 19.27-20.00 | 0.96-1.00 | 1 | 0.733 |

transitions: {'hard': 12, 'gradual': 1}   unconfirmed cuts: 0
camera motion per shot: {'drift': 5, 'static': 3, 'move': 4, 'whip': 1, 'black': 1}

## Look
luma p1/p50/p99 2.6/39.4/90.6 (0-100) | contrast(std) 23.0 | sat 0.236 | a +2.31 b +3.59 (b>0 warm) | shadows a/b +3.1/-2.0 | highlights a/b -0.7/+6.3 | vignette ratio 0.96 | grain 2.33 | bars {'top_bottom_frac': 0.0, 'side_frac': 0.0}
persistent overlays (fractions of frame): x 0.306-0.688 y 0.479-0.514 (h 0.035, cov 0.42)

## Audio
117.45 BPM (beat 0.5108s), downbeats via librosa beats, bar phase 2 by bass energy (estimate), LUFS -17.5 peak -2.0, fade in True / out False, centroid 2493 Hz, flatness 0.0389
sections at: [3.88]
rms/0.5s: 0.00 0.03 0.04 0.09 0.08 0.11 0.04 0.07 0.05 0.11 0.05 0.07 0.05 0.11 0.05 0.06 0.04 0.12 0.04 0.06 0.10 0.11 0.05 0.06 0.05 0.12 0.04 0.07 0.04 0.12 0.04 0.07 0.05 0.12 0.05 0.07 0.07 0.08 0.04 0.07
speech: not checked (faster-whisper not installed)

cut sync tests (vs uniformly random cut placement):
- beats: mean offset 108.7 ms vs chance 126.7 ms, p=0.1845 -> not synced (1/13 within 1 frame)
- downbeats: mean offset 556.8 ms vs chance 505.1 ms, p=0.736 -> not synced (0/13 within 1 frame)
- onsets: mean offset 91.3 ms vs chance 81.2 ms, p=0.7455 -> not synced (3/13 within 1 frame)

## Shots
| # | start | dur | motion | luma | sat | b |
|---|---|---|---|---|---|---|
| 1 | 0.00 | 2.33 | drift | 47.2 | 0.252 | +2.1 |
| 2 | 2.33 | 1.23 | static | 47.3 | 0.26 | +7.9 |
| 3 | 3.57 | 1.47 | static | 43.9 | 0.277 | +2.4 |
| 4 | 5.03 | 1.47 | move | 47.8 | 0.235 | +4.5 |
| 5 | 6.50 | 0.97 | drift | 35.5 | 0.332 | +8.4 |
| 6 | 7.47 | 0.97 | drift | 32.8 | 0.243 | +0.7 |
| 7 | 8.43 | 1.33 | move | 33.4 | 0.271 | +7.3 |
| 8 | 9.77 | 1.20 | drift | 46.7 | 0.238 | +2.3 |
| 9 | 10.97 | 1.70 | static | 43.8 | 0.184 | +0.2 |
| 10 | 12.67 | 1.67 | move | 44.4 | 0.201 | +3.0 |
| 11 | 14.33 | 1.77 | move | 44.8 | 0.228 | +4.7 |
| 12 | 16.10 | 0.80 | whip | 45.7 | 0.192 | +1.2 |
| 13 | 16.90 | 2.37 | drift | 30.7 | 0.207 | +3.8 |
| 14 | 19.27 | 0.73 | black | 0.4 | 0.0 | +0.0 |