from pathlib import Path

from src.editing.timeline import MontageClip, MontageTimeline


def test_timeline_roundtrip(tmp_path: Path) -> None:
    timeline = MontageTimeline(
        music_path="data/music/song.mp3",
        clips=[
            MontageClip(
                clip_path="data/clips/a.mp4",
                source_start=0.1,
                source_end=0.9,
                event_time=0.5,
                target_beat=1.0,
                event_score=0.7,
                event_type="audio_peak",
            )
        ],
    )
    path = tmp_path / "timeline.json"

    timeline.save_json(path)
    loaded = MontageTimeline.load_json(path)

    assert loaded.music_path == timeline.music_path
    assert loaded.clips[0].duration == 0.8
    assert loaded.clips[0].event_type == "audio_peak"

