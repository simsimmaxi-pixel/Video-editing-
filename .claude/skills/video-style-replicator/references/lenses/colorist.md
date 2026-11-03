# Lens: Colourist

Job: name the look in numbers, make mismatched sources agree with each other, then move them toward the reference.

## Reading the look (summary.md → "Look")
| Stat | Meaning | Typical signatures |
|---|---|---|
| L1 (black point, 0-100) | > 6 = lifted / matte blacks | filmic or faded looks lift blacks; phone video sits near 0-2 |
| L99 (white point) | < 90 = rolled-off highlights | filmic roll-off; phone HDR clips near 97-100 |
| Lstd (contrast) | spread of luminance | bleach bypass / punchy > 28; flat/log-ish < 18 |
| sat | mean HSV saturation | vivid social 0.3-0.4; muted/desaturated < 0.2; B&W ≈ 0 |
| a, b (Lab means) | tint (+a magenta) / temperature (+b warm) | warm vintage b > 8; cool/clinical b < 0 |
| shadows vs highlights a/b | split toning | teal-orange = shadows b < 0, highlights b > 0 (spread > 10) |
| vignette ratio | corners / centre luminance | < 0.85 = visible vignette |
| grain | high-frequency noise | well above the footage's own = added grain |
| bars | letterbox fraction | 2.39:1 inside 16:9 → bars about 0.12 each |

Per-shot luma/sat/b also shows whether the grade varies by scene (e.g. warm interiors vs cool exteriors) or is
one global look. "No grade, natural phone look" is a valid finding, and then you only normalise sources.

## Matching
1. **Normalise sources first.** Mixed cameras (phone vs DJI vs action cam) look like different films.
   `grade.py match --group camera` builds one LUT per camera signature toward the same reference, which
   evens them out and moves them to the look in one step.
2. **Strength:** 0.6-0.9. Full strength can over-push skin tones on footage very different from the reference.
   Check `compare.png`, and in particular look at faces.
3. **Effects that aren't a colour mapping:** grain, vignette and letterboxing go in the edit's `post_vf`
   (`noise=alls=6:allf=t`, `vignette=PI/5`, a crop-and-pad for bars). One-off treatments (a B&W flashback,
   a desaturated hold) go in a shot's `vf`.
4. **Verify:** the verify.py look rows (L1/L50/L99/Lstd/sat/a/b, split tone, vignette, grain) should land within tolerance.

## Cautions
- **HDR sources** (HLG/PQ, flagged in `library.md`): convert to SDR before matching. This ffmpeg may lack
  `zscale`; if so, ask the user to export SDR, or accept a flat look and compensate with the match.
- A LUT is global per camera. A shot lit very differently (e.g. a neon club vs daylight) may need its own
  `lut` or `vf` (`eq=` / `colortemperature=`).
- Don't "fix" deliberate looks. If the reference is crushed or blown out, that is the style.
