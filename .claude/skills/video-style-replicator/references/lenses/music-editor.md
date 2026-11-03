# Lens: Music editor

Job: decide what part of a song to use, where it enters, how picture and music lock together, and how it ends.
Inputs: the reference profile's audio section and `analyze_music.py` on the user's track.

## Reading the reference's music use
- **Role:** is the music the driver (montage, recap, music video), a bed under speech (vlog, YouTube), or a
  score (trailer, doc)? Speech present plus low music energy means a bed.
- **Entry:** cold from frame 0, after a hook line, under the title, or on a downbeat after silence?
- **Lock:** the cut-sync tests show whether picture locks to beats, downbeats or sections, or not at all.
  Many social edits lock only at the section level, so the energy changes line up and the individual cuts are free.
- **Arc:** match the reference's block structure to its song sections (where the break, drop and peak sit, as fractions).
- **Exit:** a hard stop on the song's own ending, a "button" (the last hit or held chord), a fade (how long?),
  a cut to silence or black, or music running under an end card.
- **Level:** integrated LUFS and true peak. Under speech, measure how far the music sits below the voice.

## Choosing and fitting the user's track
- `music.md` lists bars, beat-exact bass drops, sections, where the music actually ends (with hard stop vs fade)
  and where the vocals end, plus ranked windows. Set `--break-at` to where the reference has its breather, `--shape sustained`
  if it never breathes (it then rewards steady energy and a start on the drop-in), and `--from-start` if the song
  should start at the top.
- Start points that sound intentional: the song's top, a section start, or a downbeat right after a drop. Starting
  mid-phrase sounds like a mistake unless masked (a fade-in over 0.3-1 s, or a cold open on a hit).
- End points that sound intentional: the song's real end (a hard stop is a gift), a phrase end on a downbeat,
  or a fade timed to finish on a downbeat. Avoid cutting just before a downbeat, because the listener expects the hit.
- If the song is too long for the target, the window chooser handles it. To splice out a middle section, list the
  same file twice in `music=[...]` with a `crossfade` at matching downbeats (M07).
- **Several songs (M08):** `music` takes a list. Each item is a window of a track; `crossfade` overlaps it with the
  previous one. Change songs where the picture changes chapter or energy. Crossfade between section ends,
  1-2 s for beds, or hard-switch on a downbeat for hype edits. Use `time_base="timeline"` and put block ends on
  each song's downbeats converted to timeline time (item.at + downbeat - item.start).

## Locking picture to music
- Put block boundaries on downbeats or section times; the engine converts song seconds to exact frames.
- Map the reference's dramatic beats onto the song's features: a held anticipation shot on a drop or break,
  the action payoff on the re-entry (M02), the peak payoff hold on the loudest bars.
- If the reference cuts on the grid, take shot lengths from beat multiples (beat = 60/BPM s, so
  frames = beats × fps × 60 / BPM). Otherwise cut freely within blocks.
- Bar phase from librosa is an estimate. Beat-exact drops are reliable, so prefer them for anything critical.

## Levels and fades (engine `music=` settings)
- Music-only social: loudnorm about -14 LUFS (platforms normalise down, not up), true peak ≤ -1 dBTP.
- Under dialogue: keep music roughly 10-15 dB below the voice. Use `native_audio=dict(duck_music=True)` for
  automatic sidechain ducking, or drop `gain_db` for a constant bed. If the music has vocals, prefer an
  instrumental section under speech.
- Fades: a 0.03-0.05 s micro-fade only prevents clicks on hard starts/stops. A musical fade-out is usually 1-3 s
  and should finish on a downbeat.
