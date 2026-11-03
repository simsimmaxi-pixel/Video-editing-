# Lens: Sound designer

Job: inventory the audio layers and say how each one is used, then rebuild only the layers the reference has.
Restraint is the rule: one source warns against sounding every cut, because it tires viewers fast.

## Layer inventory (from summary.md plus the transcript)
| Layer | Evidence | Questions |
|---|---|---|
| Dialogue / VO | speech words, words/sec, language | On-camera or VO? Continuous or broken by music moments? |
| Music | tempo, sections, LUFS | Driver or bed? (see the music-editor lens) |
| SFX hits | onsets that are **not** on the beat grid; cuts synced to onsets but not beats | Whooshes on whips, impacts on reveals or titles, pops on text, risers into drops? |
| Ambience / room tone | quiet sections that aren't silent; flatness | Natural sound kept under the music? Room tone covering jump cuts? |
| Silence | rms near 0 inside the piece | A deliberate pause for emphasis, or a gap? |

You can't listen, so infer from the measurements and say how confident you are.
- Onsets near cuts but off the beat grid usually mean hits or whooshes.
- Speech words with music energy dipping under them means ducking.
- When an inference is uncertain and changes the plan, ask the user to confirm.

## Rebuilding
- **SFX:** the engine's `sfx=[dict(file, at, gain_db)]` places hits on exact times. Source SFX from the user, a
  licensed library, or a generator (`media-use` resolves sfx/bgm when available). Use them sparingly:
  - whoosh: a whip or a fast transition, peaking on the cut;
  - impact: a reveal, title or punchline;
  - riser: ends exactly where the drop or reveal lands.
- **Dialogue-led edits:** `native_audio=dict(all=True)`. Cut points come from the transcript (word ends and
  pauses). Use J/L cuts (`audio_offset`) where a voice should lead into or trail over the next shot.
  This is standard in interviews and docs.
- **Room tone:** jump cuts on speech can click or drop the background out. A 20-80 ms audio overlap via
  `audio_offset` helps; a continuous room-tone bed under the dialogue hides it (library S04, not built).
- **Ducking:** sidechain the music under native audio (`duck_music=True`, threshold/ratio adjustable).

## Loudness and finish
- Streaming and social targets cluster around -14 LUFS integrated with true peak ≤ -1 dBTP. Sources disagree
  for short-form (-14 to -10). Default to -14 unless the reference measures louder and the user wants it to match.
- The engine runs loudnorm, then measures the result and corrects the residual (single-pass undershoots on short edits).
- Clicks: every hard audio start or stop gets a micro-fade of 10-40 ms; the engine does this for music.
