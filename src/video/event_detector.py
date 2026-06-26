from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from src.utils.ffmpeg_utils import FFmpegError, run_ffmpeg


def detect_candidate_events(video_path: str | Path, sample_fps: float = 8.0) -> list[dict[str, Any]]:
    """Detect likely kill/impact moments from audio peaks and frame changes.

    TODO: Replace or augment these generic signals with game-aware detectors:
    HUD region diffs, kill-feed OCR, weapon flash masks, and crosshair motion.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    frame_events = _detect_frame_diff_events(path, sample_fps=sample_fps)
    audio_events = _detect_audio_peak_events(path)
    merged = _merge_events(audio_events, frame_events)

    if not merged:
        merged = [{"time": 0.0, "score": 0.1, "event_type": "fallback_start", "signals": {}}]

    return sorted(merged, key=lambda item: item["score"], reverse=True)


def _detect_audio_peak_events(video_path: Path) -> list[dict[str, Any]]:
    try:
        import librosa
        import numpy as np
    except ImportError:
        return []

    with tempfile.TemporaryDirectory(prefix="fps_sync_audio_") as tmp:
        wav_path = Path(tmp) / "audio.wav"
        try:
            run_ffmpeg([
                "-y",
                "-i", str(video_path),
                "-vn",
                "-ac", "1",
                "-ar", "22050",
                str(wav_path),
            ])
        except FFmpegError:
            return []

        if not wav_path.exists() or wav_path.stat().st_size == 0:
            return []

        try:
            y, sr = librosa.load(str(wav_path), sr=None, mono=True)
            if y.size == 0:
                return []
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            if onset_env.size == 0:
                return []
            threshold = float(np.mean(onset_env) + np.std(onset_env))
            candidate_frames = np.where(onset_env >= threshold)[0]
            times = librosa.frames_to_time(candidate_frames, sr=sr)
            strengths = onset_env[candidate_frames]
            max_strength = float(np.max(strengths)) if strengths.size else 1.0
        except Exception:
            return []

    events = []
    for time_value, strength in zip(times, strengths):
        normalized = float(strength) / max(max_strength, 1e-6)
        events.append({
            "time": round(float(time_value), 3),
            "score": round(0.55 + 0.45 * normalized, 3),
            "event_type": "audio_peak",
            "signals": {"audio_peak": round(normalized, 3)},
        })
    return _dedupe_nearby(events, min_gap=0.18)


def _detect_frame_diff_events(video_path: Path, sample_fps: float) -> list[dict[str, Any]]:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Frame-difference event detection requires OpenCV. "
            "Install dependencies with: python -m pip install -e .[dev]"
        ) from exc

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV could not read video file: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, int(round(source_fps / max(sample_fps, 1.0))))
    frame_index = 0
    previous_gray = None
    diffs: list[tuple[float, float]] = []

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index % step != 0:
            frame_index += 1
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 90))
        if previous_gray is not None:
            diff = float(np.mean(cv2.absdiff(gray, previous_gray)) / 255.0)
            diffs.append((frame_index / source_fps, diff))
        previous_gray = gray
        frame_index += 1

    cap.release()
    if not diffs:
        return []

    values = [value for _, value in diffs]
    threshold = sum(values) / len(values) + _std(values)
    max_value = max(values) or 1.0
    events = []
    for time_value, diff in diffs:
        if diff >= threshold:
            normalized = diff / max_value
            events.append({
                "time": round(time_value, 3),
                "score": round(0.35 + 0.5 * normalized, 3),
                "event_type": "frame_diff",
                "signals": {"frame_diff": round(normalized, 3)},
            })
    return _dedupe_nearby(events, min_gap=0.2)


def _merge_events(audio_events: list[dict[str, Any]], frame_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    used_frame_indexes: set[int] = set()

    for audio_event in audio_events:
        best_index = None
        best_distance = 0.16
        for index, frame_event in enumerate(frame_events):
            if index in used_frame_indexes:
                continue
            distance = abs(audio_event["time"] - frame_event["time"])
            if distance <= best_distance:
                best_distance = distance
                best_index = index

        if best_index is None:
            merged.append(audio_event)
            continue

        frame_event = frame_events[best_index]
        used_frame_indexes.add(best_index)
        signals = {**audio_event.get("signals", {}), **frame_event.get("signals", {})}
        score = min(1.0, audio_event["score"] * 0.7 + frame_event["score"] * 0.5)
        merged.append({
            "time": round((audio_event["time"] + frame_event["time"]) / 2, 3),
            "score": round(score, 3),
            "event_type": "audio_visual_impact",
            "signals": signals,
        })

    for index, frame_event in enumerate(frame_events):
        if index not in used_frame_indexes:
            merged.append(frame_event)

    return _dedupe_nearby(merged, min_gap=0.12)


def _dedupe_nearby(events: list[dict[str, Any]], min_gap: float) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for event in sorted(events, key=lambda item: item["score"], reverse=True):
        if all(abs(event["time"] - kept["time"]) >= min_gap for kept in selected):
            selected.append(event)
    return sorted(selected, key=lambda item: item["time"])


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5

