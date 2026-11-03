# Edit file for scripts/engine.py. Copy to edit/<name>.py, fill in, then:
#   engine.py edit/<name>.py --dry  ->  --preview  ->  (final)
# Every option below is optional except sources and blocks. Delete what the blueprint doesn't call for.

EDIT = dict(
    name="my_video",
    sources="footage/map.json",          # from ingest_footage.py (clip ids f01, f02, ...)
    fps=30, size="1080x1920",            # 1920x1080 for YouTube, etc.
    time_base="song",                    # "song": block ends are song seconds (downbeats from music.md)
                                         # "timeline": block ends are seconds of the finished video
    music=dict(file="music/track.mp3", start=0.0, end=30.0,  # window from music.md; a list = playlist (M07/M08)
               fade_in=0, fade_out=0.04, gain_db=0, loudnorm=-14),
    # native_audio=dict(all=True, gain_db=0, duck_music=True),   # dialogue-led edits (C04-C06, M06)
    # grade=dict(luts="footage/grade/grade.json"),               # from grade.py match (G01/G02)
    # overlays=[dict(png="edit/title.png", start=0, end=None)],  # from caption.py (X01-X03)
    # sfx=[dict(file="sfx/hit.wav", at=4.09, gain_db=-6)],       # S01
    # post_vf=["noise=alls=6:allf=t", "vignette=PI/5"],          # G03
    tail=dict(frames=3, color="black"),  # T01 ending; None for no tail
    blocks=[
        # (block name, block END time, [shots])
        # shot = (clip, src_in_seconds, frames)  or a dict with options; n=None fills the block exactly
        ("A_hook", 4.249, [
            ("f03", 1.30, 17),
            ("f07", 4.00, 9),
            ("f01", 2.00, None),
        ]),
        ("B_hold", 8.313, [
            dict(clip="f12", t=4.3, n=None, zoom=1.2, anchor="top", note="payoff reaction"),
        ]),
        # Shot options: zoom, anchor ("center"|"top"|"bottom"|"left"|"right"|(fx, fy)), speed, hflip,
        #   lut ("off" | path), vf=[...], text=<chars on screen>, qc=False (skip shake check),
        #   trans=dict(type="xfade", kind="fade", frames=8) | dict(type="dip", color="black", frames=8)
        #         | dict(type="flash", frames=3),
        #   audio=True | gain_db, audio_offset=+0.4 (J-cut) / -0.4 (L-cut), audio_from=("f02", 31.5)
    ],
)
