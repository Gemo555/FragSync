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
    assert timeline.clips[0].source_start == 0.0
    assert timeline.clips[0].source_end == 1.35
    assert "alignment_error:-2.2" in timeline.clips[0].effects


def test_align_events_adjusts_clip_duration_to_place_event_on_beat() -> None:
    timeline = align_events_to_beats(
        events_by_clip={
            "clip_a.mp4": [{"time": 2.5, "score": 0.9, "event_type": "audio_peak"}],
            "clip_b.mp4": [{"time": 1.5, "score": 0.8, "event_type": "audio_peak"}],
        },
        beats=[1.0, 2.2],
        music_path="song.mp3",
        post_event_time=0.4,
    )

    first = timeline.clips[0]
    second = timeline.clips[1]

    assert first.source_start == 1.5
    assert first.source_end == 2.9
    assert first.event_time - first.source_start == first.target_beat
    assert round(first.duration + (second.event_time - second.source_start), 3) == second.target_beat

