# Ability library

Every technique the skill knows, labelled so it gets chosen on purpose when a blueprint calls for it. It is never
applied by default. Cite IDs in BLUEPRINT.md (e.g. "blocks: P01, cuts: C01, end: M03 + T01").

**Status:** ✅ used in an approved project (named) · 🔧 supported by the scripts, not yet proven in a project ·
📚 known technique, not built (do it by hand or extend the engine, then upgrade the status).

**Grow it:** after a user approves a project, upgrade statuses, add new moves with "use when / avoid",
and keep wording general. One project's quirks belong in its `styles/` folder, not here.

## P: Structure and pacing
| ID | Technique | Use when | Avoid | How | Status |
|---|---|---|---|---|---|
| P01 | Burst / hold alternation | montage-type references whose analyzer blocks alternate b/h | dialogue-led content | blocks with 6-12 f shots vs 45-61 f holds; fractions from the reference | ✅ Silverstone recap |
| P02 | Cold open mid-action | short-form hooks | slow, prestige tones | first shot 15-18 f, motion already happening on frame 0 | ✅ Silverstone |
| P03 | Bookend loop | looping feeds; recaps with a strong place | narrative pieces needing closure | last hold = the place or subject seen in the first ~2 s | ✅ Silverstone |
| P04 | Peak payoff hold | build sections | when the reference ends on a burst | a 1.5-2 s human-reaction hold on the loudest bars | ✅ Silverstone |
| P05 | Metronomic pacing | music videos, beat edits | human or story moments | constant shot length in beats | 🔧 (compute n from BPM) |
| P06 | Pattern interrupt cadence | long-form retention | short pieces | B-roll, punch-in, graphic or sound drop every N s (measured on the reference) | 📚 |
| P07 | Hook → roadmap → chapters | YouTube explainers | montages | segments from the transcript; see the long-form lens | 📚 |

## C: Cut placement
| ID | Technique | Use when | Avoid | How | Status |
|---|---|---|---|---|---|
| C01 | Section-locked blocks, free cuts inside | sync tests say "not synced" to beats but blocks follow the song | beat-synced references | block ends = downbeats/section times; shot lengths free | ✅ Silverstone |
| C02 | Cut on the beat grid | sync tests say SYNCED to beats or downbeats | free-cut references | n = beats × fps × 60 / BPM; block ends on downbeats | 🔧 |
| C03 | Cut on action | almost always inside blocks | — | pick in-points so the cut lands mid-gesture (strips) | ✅ Silverstone (manual) |
| C04 | Jump cuts on pauses | talking heads | music-led edits | shot boundaries from transcript word gaps | 🔧 (manual from transcript) |
| C05 | J-cut / L-cut | interviews, docs, scene transitions | montage under music | shot `audio_offset` (>0 J, <0 L) | 🔧 |
| C06 | B-roll over continuous speech | explainers, docs, vlogs | — | B-roll shot `audio_from=(aroll, t)` | 🔧 |

## T: Transitions
| ID | Technique | Use when | Avoid | How | Status |
|---|---|---|---|---|---|
| T01 | Hard cut (+ N black frames at the end) | default for social and YouTube | — | default; `tail=dict(frames=3)` | ✅ Silverstone |
| T02 | In-camera whip as a transition | reference has whips, spins, lens covers | footage without them (don't fake it badly) | choose a source moment containing the whip, 12-36 f | ✅ Silverstone (sign whip) |
| T03 | Dissolve | docs, emotional, time passing | hype edits | `trans=dict(type="xfade", kind="fade", frames=8-20)` | 🔧 |
| T04 | Dip to black/white | chapter breaks, trailers | fast montage | `trans=dict(type="dip", color="black", frames=6-16)` | 🔧 |
| T05 | Flash frame | trailer hits, music-video accents | overuse (strobing) | `trans=dict(type="flash", frames=2-4)` | 🔧 |
| T06 | Slide / wipe / zoom transitions | template-style edits that clearly use them | anything aiming at "natural" | `xfade` kinds: wipeleft, slideup, circleopen, zoomin… | 🔧 |
| T07 | Match cut | shape, motion or graphic rhymes | — | pick paired moments by eye; hard cut | 📚 |

## R: Reframing and camera
| ID | Technique | Use when | Avoid | How | Status |
|---|---|---|---|---|---|
| R01 | Face-safe punch-in under a fixed overlay | an overlay would cross a face | — | `zoom=1.2-1.3, anchor="top"` (stays ≥1080p from 4K/3K sources) | ✅ Silverstone v1 |
| R02 | Punch-in alternation | talking-head jump cuts | wide or landscape shots | alternate `zoom` 1.0 / 1.12 with a face-centred anchor | 🔧 |
| R03 | Constant speed change | slow-mo emotion, sped-up process | dialogue (audio pitch) | `speed=0.5` / `1.5` (sound muted outside 0.5-2×) | 🔧 |
| R04 | Speed ramp | music-video and travel accents | — | split into shots with stepped speeds, or extend the engine | 📚 |
| R05 | Landscape → vertical reframe | 16:9 sources in 9:16 | subjects at frame edges | `anchor=(fx, fy)` toward the subject | 🔧 |

## M: Music
| ID | Technique | Use when | Avoid | How | Status |
|---|---|---|---|---|---|
| M01 | Window chosen to fit the reference's structure | the user supplies a full song | — | `analyze_music.py --break-at` ranked windows | ✅ Silverstone |
| M02 | Anticipation hold on the drop, payoff on re-entry | songs with a break or drop | songs without one | hold over the drop bars; burst starts on the re-entry downbeat | ✅ Silverstone |
| M03 | End on the song's own ending | hard-stop or button endings | fades that run long | `music.end` = music_end; ~3-frame black tail | ✅ Silverstone v1-extended |
| M04 | Start from the top of the song | intros that open well | slow or long intros | `--from-start`; window 0 → section end | ✅ Silverstone v2 |
| M05 | Musical fade-out ending on a downbeat | no clean end point | hype pieces | `music.fade_out` 1-3 s | 🔧 |
| M06 | Duck the music under speech | any dialogue + music | — | `native_audio=dict(duck_music=True)` | 🔧 |
| M08 | Multi-song playlist with crossfades | references that change songs between sections or chapters; a user-supplied list of songs | changing songs inside a montage burst | `music=[dict(file, start, end), dict(file, start, end, crossfade=1.0)]`; `time_base="timeline"`; transition on a section boundary of both songs | 🔧 |
| M07 | Splice the song (cut out a middle section) | the target length is shorter than a good arc | — | two items of the same file in a `music` list with `crossfade` at matching downbeats | 🔧 |

## S: Sound
| ID | Technique | Use when | Avoid | How | Status |
|---|---|---|---|---|---|
| S01 | Timed SFX hit | reveals, titles, punchlines | sounding every cut | `sfx=[dict(file, at, gain_db)]` | 🔧 |
| S02 | Whoosh on a whip or transition | in-camera whips, T06 | subtle edits | S01 with the peak on the cut | 📚 |
| S03 | Riser into a drop or reveal | trailers, hype | — | S01 ending exactly at the hit | 📚 |
| S04 | Room-tone bed under jump cuts | talking heads with audible background | — | loop a room-tone clip as a second audio bed | 📚 |
| S05 | Loudness finish | always | — | engine loudnorm + measured correction (-14 LUFS, -1 dBTP default) | ✅ (engine) |

## G: Colour
| ID | Technique | Use when | Avoid | How | Status |
|---|---|---|---|---|---|
| G01 | Statistical look match (MKL + tone curve → LUT) | any reference with a measurable look | deliberately mismatched looks | `grade.py match` | 🔧 (tested on the Silverstone footage) |
| G02 | Camera normalisation | mixed phone/drone/action-cam footage | single-camera shoots | `grade.py match --group camera` | 🔧 |
| G03 | Grain / vignette | filmic references (grain/vignette stats) | clean social looks | `post_vf=["noise=alls=6:allf=t", "vignette=PI/5"]` | 🔧 |
| G04 | Per-shot treatment (B&W, desaturated flashback) | story beats | — | shot `vf=["eq=saturation=0"]` | 🔧 |
| G05 | Letterbox | cinematic references (bars > 0) | vertical social | `post_vf` crop + pad | 📚 |

## X: Text and graphics
| ID | Technique | Use when | Avoid | How | Status |
|---|---|---|---|---|---|
| X01 | Persistent location tag | reference shows one (measure the bbox) | if the user wants no text | `caption.py` (plain, shadow), `overlays` 0 → end | ✅ Silverstone v1 (removed in later versions at the user's request) |
| X02 | Bold hook headline | short-form hooks with text | — | `caption.py --weight black --stroke 5 --upper` | 🔧 |
| X03 | Boxed lower third / label | vlogs, explainers | — | `caption.py --box "#000000@0.55"` | 🔧 |
| X04 | Word-by-word subtitles | sound-off short-form, explainers | when the reference has none | whisper words → a PNG per word → timed overlays | 📚 |
| X05 | Animated titles / end cards | trailers, ads, chapter cards | — | hyperframes skill → render → overlay or footage | 📚 |
