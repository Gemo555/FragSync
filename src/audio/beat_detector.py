from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manual_beats(json_path: str | Path) -> dict[str, Any]:
    """Load manually authored beat timestamps from a small JSON file."""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Manual beats file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manual beats file is not valid JSON: {path}") from exc

    beats = data.get("beats")
    if not isinstance(beats, list) or not beats:
        raise ValueError("Manual beats JSON must contain a non-empty 'beats' list.")

    clean_beats: list[float] = []
    for item in beats:
        try:
            value = float(item)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Beat value must be numeric, got {item!r}") from exc
        if value < 0:
            raise ValueError(f"Beat values must be >= 0, got {value}")
        clean_beats.append(value)

    labels = data.get("labels", {})
    if labels is None:
        labels = {}
    if not isinstance(labels, dict):
        raise ValueError("Manual beats 'labels' must be an object when provided.")

    return {"beats": sorted(clean_beats), "labels": labels}


def detect_beats(audio_path: str | Path) -> dict[str, Any]:
    """Detect beat, onset, and energy-peak timestamps with librosa."""
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    try:
        import librosa
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "Automatic beat detection requires librosa and numpy. "
            "Install dependencies with: python -m pip install -e .[dev]"
        ) from exc

    try:
        y, sr = librosa.load(str(path), sr=None, mono=True)
        if y.size == 0:
            raise ValueError("audio file loaded but contains no samples")

        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=False)
        rms = librosa.feature.rms(y=y)[0]

        if rms.size:
            threshold = float(np.mean(rms) + np.std(rms))
            peak_frames = np.where(rms >= threshold)[0]
        else:
            peak_frames = np.array([], dtype=int)

        return {
            "beats": _round_times(librosa.frames_to_time(beat_frames, sr=sr)),
            "onsets": _round_times(librosa.frames_to_time(onset_frames, sr=sr)),
            "energy_peaks": _round_times(librosa.frames_to_time(peak_frames, sr=sr)),
            "tempo": float(np.asarray(tempo).reshape(-1)[0]) if np.size(tempo) else 0.0,
        }
    except Exception as exc:
        raise RuntimeError(
            f"Could not analyze audio file '{path}'. Check that the file is readable "
            "and that FFmpeg/libsndfile support its format."
        ) from exc


def _round_times(values: Any) -> list[float]:
    return [round(float(value), 3) for value in values]

