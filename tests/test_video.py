from src.video.clip_loader import scan_clips


def test_scan_clips_filters_supported_extensions(tmp_path) -> None:
    (tmp_path / "a.mp4").write_text("", encoding="utf-8")
    (tmp_path / "b.mov").write_text("", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")

    clips = scan_clips(tmp_path)

    assert [clip.name for clip in clips] == ["a.mp4", "b.mov"]

