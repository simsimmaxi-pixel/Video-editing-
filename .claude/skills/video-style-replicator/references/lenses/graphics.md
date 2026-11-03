# Lens: Graphics (text, captions, overlays)

Read this only if the reference actually has on-screen text or graphics. Adding text the reference doesn't have,
or that the user didn't ask for, is a common way to make a recreation feel wrong.

## Inventory
- **Persistent overlays:** `summary.md` lists the bounding boxes (as fractions of the frame) of anything that stays
  on screen across shots: location tags, logos, watermarks. Decide which are style (a caption) and which are
  platform artifacts (a TikTok watermark, a @handle). Never replicate the artifacts.
- **Changing text:** hooks, subtitles, lower thirds, chapter cards, CTAs. Find them on the shot sheet. For an exact
  position, grab the cleanest frame (black frames and end cards are ideal) and measure it the way the
  analyzer does.
- For each kind, record: content pattern, position (centre x/y as fractions), cap height as a fraction of
  frame height, font class (geometric sans, condensed bold, serif, handwritten), colour, stroke/shadow/box,
  timing (persistent, per-shot, word-by-word), and animation (static, pop, typewriter, slide).

## Recreating
- Static or per-shot text: `caption.py OUT.png --text ... --cx --cy --px --weight --stroke --shadow --box`,
  then add it to the edit's `overlays=[dict(png, start, end)]`. It renders PNGs because many ffmpeg builds lack
  `drawtext`, and drawtext can't render colour emoji. The script prints the bbox; compare it with the reference's.
- Word-by-word subtitles: transcribe with faster-whisper, render one PNG per word or phrase, and add one overlay
  per [start, end]. This is library X04, not built as a single command yet, so script it per project.
- Animated titles, kinetic type, end cards, logo stings: use the hyperframes skill (or logo-reveal-launch for
  brand stings), render a transparent or keyed clip, and bring it in as footage or an overlay.

## Placement rules
- **Safe zones:** platform UI covers parts of the frame. On vertical feeds, keep text out of roughly the bottom
  20% and right 15% (caption, buttons) and the top ~8%. On YouTube, avoid the bottom-right during end screens.
- **Faces:** text shouldn't cross eyes or mouths. Reframe the shot (a `zoom` with `anchor="top"` pushes faces
  down) rather than moving text the reference keeps fixed.
- **Read time:** at least about 0.6 s + 0.05 s per character. Mark the shot's `text=<chars>` and the engine warns.
