from src.app import parse_range_header


def test_parse_range_header_open_ended() -> None:
    assert parse_range_header("bytes=10-", 100) == (10, 99)


def test_parse_range_header_suffix() -> None:
    assert parse_range_header("bytes=-25", 100) == (75, 99)


def test_parse_range_header_clamps_end() -> None:
    assert parse_range_header("bytes=90-200", 100) == (90, 99)

