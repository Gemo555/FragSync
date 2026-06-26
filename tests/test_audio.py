from pathlib import Path

from src.audio.beat_detector import load_manual_beats


def test_load_manual_beats(tmp_path: Path) -> None:
    path = tmp_path / "beats.json"
    path.write_text('{"beats": [2.4, "0.8", 1.6], "labels": {"2.4": "drop"}}', encoding="utf-8")

    data = load_manual_beats(path)

    assert data["beats"] == [0.8, 1.6, 2.4]
    assert data["labels"]["2.4"] == "drop"

