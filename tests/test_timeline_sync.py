from src.editing.sync_strategy import align_events_to_beats


def test_align_events_to_beats_pairs_top_events() -> None:
    timeline = align_events_to_beats(
        events_by_clip={
            "clip_a.mp4": [
                {"time": 0.5, "score": 0.2, "event_type": "frame_diff"},
                {"time": 1.0, "score": 0.9, "event_type": "audio_peak"},
            ],
            "clip_b.mp4": [{"time": 2.0, "score": 0.6, "event_type": "audio_visual_impact"}],
        },
        beats=[3.2, 4.0, 4.8],
        music_path="song.mp3",
    )

    assert len(timeline.clips) == 2
    assert timeline.clips[0].event_time == 1.0
    assert timeline.clips[0].target_beat == 3.2
    assert timeline.clips[0].source_start == 0.55
    assert timeline.clips[0].source_end == 1.35

