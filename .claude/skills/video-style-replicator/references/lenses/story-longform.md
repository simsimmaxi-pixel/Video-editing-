# Lens: Long-form story (YouTube, documentaries, video essays, vlogs, interviews)

Use this when the reference runs past ~2 minutes or speech carries the content. In long-form the transcript
is the timeline: cut on words, not on pictures.

## Reading the reference
- **Transcript:** `analyze_reference.py` runs faster-whisper if it's installed (`setup.sh --ml`). Without it, ask
  to install it: long-form analysis without a transcript is guesswork.
- **Structure:** mark segments from the transcript: hook, setup or roadmap, sections or chapters, recaps,
  payoff, CTA, outro. Note the time and length of each as a fraction of the runtime.
- **Hook:** what happens in the first 10-30 s? Common pattern: prove the title is true in the first ~10 s, say
  why it matters in the next ~10 s, give a one-line roadmap, and skip the "welcome to my channel".
  Compare the reference against this rather than assuming it.
- **Open loops:** questions or promises raised early and paid off later. List them with their times.
- **Pacing curve:** cuts per window (in `summary.md`), plus words per second. Where does density rise (hook,
  reveals) and drop (explanations)? How often do pattern interrupts arrive (B-roll, zoom, graphic, angle change,
  sound drop)? Advice online ranges from every 10-25 s to every 60-90 s, so measure the reference's own number.
- **A-roll / B-roll:** the share of runtime on the speaker vs cutaways (from the shot sheet: classify the sampled
  shots), the typical B-roll length, and whether B-roll is literal (shows what's said) or tonal.
- **Talking-head grammar:** jump cuts on pauses (cuts synced to word ends), punch-in alternation (zoom 1.0 ↔
  1.1-1.2 between jump cuts hides the jump), J/L cuts between speakers, room tone continuity.

## Recreating
1. **Paper edit first.** Transcribe the user's footage (faster-whisper word timestamps), then choose and order
   lines by text, exactly as an editor's paper edit. Reading text costs far less than looking at frames, so
   use images only to choose B-roll and check framing.
2. Build blocks per segment with `time_base="timeline"`. A-roll shots come straight from word times
   (`t = word.start - 0.05`, `n = round((end - start + 0.1) * fps)`), with `native_audio=dict(all=True)`.
3. Remove dead air: cut pauses longer than the reference's typical gap (measure the gaps between words in its
   transcript). Keep the breaths that carry emphasis.
4. Hide jump cuts with punch-in alternation (`zoom=1.12`, anchored on the face) or B-roll over the cut. Use
   `audio_offset` for J/L cuts.
5. B-roll over continuous speech: give the B-roll shot `audio_from=(aroll_clip, t)`, where t is where the
   A-roll's sound continues (the previous A-roll shot's t plus its length). The picture changes and the voice
   carries on uninterrupted (library C06).
6. Music sits as a bed about 10-15 dB under speech (ducking), changes between chapters, and drops out for emphasis.
7. Chapters and recaps: a title card or lower third per chapter, if the reference has them (graphics lens).

## Efficiency for long material
- Ingest everything (digits are cheap), but view contact sheets only for B-roll candidates.
- For a 20-minute reference, the analyzer samples the shot sheets (the first 60 s in full, then 96 tiles total).
  Read the transcript and pacing curve before any image.
