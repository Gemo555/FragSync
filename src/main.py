from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from src.audio.beat_detector import detect_beats, load_manual_beats
from src.editing.renderer import render_timeline
from src.editing.sync_strategy import align_events_to_beats
from src.editing.timeline import MontageTimeline
from src.video.clip_loader import scan_clips
from src.video.event_detector import detect_candidate_events


def main() -> int:
    args = parse_args()
    config = load_config(args.config)

    if args.timeline:
        timeline = MontageTimeline.load_json(args.timeline)
        if args.output:
            render_timeline(timeline, args.output, keep_tmp=args.keep_tmp)
        else:
            print(json.dumps(timeline.to_dict(), indent=2))
        return 0

    if not args.music or not args.clips:
        raise SystemExit("--music and --clips are required unless --timeline is used.")

    style = args.style or config["editing"]["style"]
    max_clips = args.max_clips if args.max_clips is not None else config["editing"]["max_clips"]
    resolution = args.resolution or config["export"]["resolution"]
    fps = args.fps or config["export"]["fps"]

    print("[audio] loading beats")
    if args.manual_beats:
        beat_data = load_manual_beats(args.manual_beats)
        print(f"[audio] loaded {len(beat_data['beats'])} manual beats")
    else:
        beat_data = detect_beats(args.music)
        print(f"[audio] detected {len(beat_data['beats'])} beats, tempo={beat_data.get('tempo', 0):.1f}")

    beats = beat_data["beats"]
    clips = scan_clips(args.clips, max_clips=max_clips)
    if not clips:
        raise SystemExit(f"No supported video clips found in: {args.clips}")
    print(f"[video] found {len(clips)} clips")

    events_by_clip: dict[str, list[dict[str, Any]]] = {}
    for clip_path in clips:
        print(f"[video] detecting events in {clip_path}")
        events = detect_candidate_events(clip_path, sample_fps=config["video"]["sample_fps"])
        events_by_clip[str(clip_path)] = events
        if events:
            best = max(events, key=lambda item: item.get("score", 0.0))
            print(f"[video] best event {best['time']:.3f}s score={best['score']:.3f} type={best['event_type']}")

    timeline = align_events_to_beats(
        events_by_clip=events_by_clip,
        beats=beats,
        music_path=args.music,
        style=style,
        resolution=resolution,
        fps=fps,
        pre_event_time=config["editing"]["pre_event_time"],
        post_event_time=config["editing"]["post_event_time"],
    )

    print_report(timeline)

    if args.export_timeline:
        timeline.save_json(args.export_timeline)
        print(f"[timeline] saved to {args.export_timeline}")

    if args.dry_run:
        print("[done] dry-run complete; video render skipped")
        return 0

    if not args.output:
        raise SystemExit("--output is required unless --dry-run is used.")

    render_timeline(timeline, args.output, keep_tmp=args.keep_tmp)
    print(f"[done] rendered {args.output}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync FPS kill clips to music beats.")
    parser.add_argument("--music", help="Path to the music file.")
    parser.add_argument("--clips", help="Folder containing short kill clips.")
    parser.add_argument("--output", help="Output montage MP4 path.")
    parser.add_argument("--manual-beats", help="JSON file with manual beat timestamps.")
    parser.add_argument("--style", default=None, help="Editing style, e.g. clean_sync or slow_impact.")
    parser.add_argument("--max-clips", type=int, default=None, help="Maximum number of clips to use.")
    parser.add_argument("--resolution", default=None, help="Export resolution, e.g. 1920x1080.")
    parser.add_argument("--fps", type=int, default=None, help="Export frame rate.")
    parser.add_argument("--config", default="configs/default.yaml", help="YAML config path.")
    parser.add_argument("--dry-run", action="store_true", help="Build timeline and report without rendering.")
    parser.add_argument("--export-timeline", help="Write generated timeline JSON to this path.")
    parser.add_argument("--timeline", help="Render or print an existing timeline JSON.")
    parser.add_argument("--keep-tmp", action="store_true", help="Keep renderer temporary files.")
    return parser.parse_args()


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def print_report(timeline: MontageTimeline) -> None:
    print("[timeline] selected clips")
    for index, clip in enumerate(timeline.clips, start=1):
        print(
            f"  {index:02d}. beat={clip.target_beat:.3f}s "
            f"event={clip.event_time:.3f}s score={clip.event_score:.3f} "
            f"type={clip.event_type} clip={clip.clip_path}"
        )


if __name__ == "__main__":
    raise SystemExit(main())

