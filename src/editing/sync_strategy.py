from __future__ import annotations

from pathlib import Path
from typing import Any

from src.editing.timeline import MontageClip, MontageTimeline


def align_events_to_beats(
    events_by_clip: dict[str, list[dict[str, Any]]],
    beats: list[float],
    music_path: str,
    style: str = "clean_sync",
    resolution: str = "1920x1080",
    fps: int = 60,
    pre_event_time: float = 0.45,
    post_event_time: float = 0.35,
) -> MontageTimeline:
    """Build a simple montage timeline by pairing each top event with one beat."""
    if not beats:
        raise ValueError("Cannot align clips: no beats were provided or detected.")

    clips: list[MontageClip] = []
    clip_items = list(events_by_clip.items())
    pair_count = min(len(clip_items), len(beats))

    for index in range(pair_count):
        clip_path, events = clip_items[index]
        best_event = _choose_best_event(events)
        event_time = float(best_event["time"])
        source_start = max(0.0, event_time - pre_event_time)
        source_end = max(source_start + 0.1, event_time + post_event_time)
        speed = 1.0
        effects: list[str] = []

        if style == "slow_impact":
            # TODO: Implement real velocity ramping in renderer. For now the
            # timeline records intent so the strategy can be tested end to end.
            speed = 0.85
            effects.append("marked_slow_impact")
        elif style != "clean_sync":
            effects.append(f"style:{style}")

        clips.append(MontageClip(
            clip_path=str(Path(clip_path)),
            source_start=round(source_start, 3),
            source_end=round(source_end, 3),
            event_time=round(event_time, 3),
            target_beat=round(float(beats[index]), 3),
            speed=speed,
            effects=effects,
            event_score=float(best_event.get("score", 0.0)),
            event_type=str(best_event.get("event_type", "unknown")),
        ))

    return MontageTimeline(
        music_path=str(music_path),
        clips=clips,
        export_resolution=resolution,
        export_fps=fps,
        style=style,
    )


def _choose_best_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {"time": 0.0, "score": 0.0, "event_type": "fallback_start", "signals": {}}
    return max(events, key=lambda item: float(item.get("score", 0.0)))

