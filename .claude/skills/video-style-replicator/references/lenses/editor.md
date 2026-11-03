# Lens: Editor

Job: describe the cutting so that someone else could cut new footage the same way. Most of the answers are
in `summary.md`; the rest come from one look at the shot sheet.

## Pacing
- **ASD and distribution:** mean, median, p10/p90 and frames per shot. Mean alone hides structure, because a
  0.3 s montage with a few 2 s holds has a mean of 0.5 s that matches no actual shot.
- **Blocks:** the analyzer splits runs of short shots (burst) from long ones (hold) and gives each block's position
  as a fraction of the runtime. Record the pattern (e.g. `b h b h b`) and each block's ASD.
- **Over time (long-form):** the cuts-per-window curve. Look for front-loaded density (the hook), regular
  pattern interrupts, and slow stretches that were deliberate (a story beat) rather than neglected.
- Translate it into rules: "burst shots 6-12 f (mean 10), holds 45-61 f, first shot 15-18 f". Ranges in frames
  survive a change of music, and fractions survive a change of length.

## Cut placement: what triggers a cut
Read the cut-sync tests, which compare against random placement (a small offset alone proves nothing):
- Synced to **beats/downbeats**: a music-video grammar. Cut on the grid (library C02).
- Synced to **sections only**: blocks change with the song, and cuts inside a block follow the action (C01).
- Synced to **onsets but not beats**: likely SFX hits or dialogue-driven cuts.
- Synced to **word ends / pauses**: talking-head jump cuts (C04).
- None of these: cutting on action or content. Look at the cut pairs: is it mid-gesture, on a look, or on an exit?

## Transitions
Read the transition mix (hard / whip / gradual / dip / flash). Hard cuts are the default grammar of social and
YouTube content. Note any *in-camera* transitions (whip pans, covering the lens, a spin): they belong to the
shooting, so pick footage moments that contain them (T02) rather than faking them in post.

## Shot rotation and coverage
From the shot sheet: what kinds of shots alternate (wide / medium / close-up; venue / person / action /
detail; A-roll / B-roll)? Is there a rule, like "never three of one kind in a row" or "B-roll every 8-15 s
over VO"? What earns a hold: a human reaction, a reveal, a punchline, a sign that needs reading?

## Opening and ending
- Opening: does it cold-open mid-action (P02), open on a title, or on a question? How long until the first cut?
- Ending: a bookend loop (P03), a payoff hold (P04), a fade, a hard cut to black (how many frames?), an end card?

## Camera grammar (what the shooting contributes)
The motion mix per shot (static / drift / move / handheld / whip), the lens feel (ultra-wide distortion,
telephoto compression), camera height, selfie vs observer. When choosing footage, this is matched by
selection, not by editing.

## Recreation notes
- Put block ends on the music's downbeats or section times (`time_base="song"`). Inside a block, place cuts
  where the reference does (on the grid, or free).
- Choose footage by role first, then quality (`library.md` digits), then content.
- The engine's `--dry` warns about shaky holds, too-short text shots and reused moments. Treat these as editor's
  notes, not errors.
