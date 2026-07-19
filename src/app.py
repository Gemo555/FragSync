from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from src.audio.beat_detector import detect_beats, load_manual_beats
from src.editing.renderer import render_timeline
from src.editing.sync_strategy import align_events_to_beats
from src.editing.timeline import MontageTimeline
from src.video.clip_loader import scan_clips
from src.video.event_detector import detect_candidate_events

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "src" / "web"
DATA_ROOT = ROOT / "data"
OUTPUT_ROOT = DATA_ROOT / "output"
DEFAULT_CONFIG = ROOT / "configs" / "default.yaml"


class AppState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.timeline: MontageTimeline | None = None
        self.events_by_clip: dict[str, list[dict[str, Any]]] = {}
        self.last_output: Path | None = None


STATE = AppState()


class MontageRequestHandler(BaseHTTPRequestHandler):
    server_version = "FragSyncUI/0.1"

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_static(WEB_ROOT / "index.html", include_body=False)
        elif parsed.path.startswith("/static/"):
            self._send_static(WEB_ROOT / parsed.path.removeprefix("/static/"), include_body=False)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Route not found")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_static(WEB_ROOT / "index.html")
        elif parsed.path.startswith("/static/"):
            self._send_static(WEB_ROOT / parsed.path.removeprefix("/static/"))
        elif parsed.path == "/api/media":
            self._handle_media(parsed.query)
        elif parsed.path == "/api/state":
            self._send_json(current_state())
        elif parsed.path == "/api/media-list":
            self._send_json(media_list())
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Route not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/analyze":
                self._send_json(handle_analyze(payload))
            elif parsed.path == "/api/update-timeline":
                self._send_json(handle_update_timeline(payload))
            elif parsed.path == "/api/render":
                self._send_json(handle_render(payload))
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Route not found")
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {format % args}")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_static(self, path: Path, include_body: bool = True) -> None:
        resolved = path.resolve()
        if not is_relative_to(resolved, WEB_ROOT.resolve()) or not resolved.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
            return
        content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
        raw = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if include_body:
            self.wfile.write(raw)

    def _handle_media(self, query: str) -> None:
        params = parse_qs(query)
        raw_path = params.get("path", [""])[0]
        if not raw_path:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing media path")
            return
        try:
            media_path = resolve_media_path(unquote(raw_path))
        except ValueError as exc:
            self.send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        self._send_media_file(media_path)

    def _send_media_file(self, media_path: Path) -> None:
        content_type = mimetypes.guess_type(media_path.name)[0] or "application/octet-stream"
        file_size = media_path.stat().st_size
        if file_size == 0:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", "0")
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            return
        range_header = self.headers.get("Range")
        if not range_header:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            start, end = 0, file_size - 1
        else:
            start, end = parse_range_header(range_header, file_size)
            self.send_response(HTTPStatus.PARTIAL_CONTENT)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(end - start + 1))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.end_headers()

        with media_path.open("rb") as handle:
            handle.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)


def handle_analyze(payload: dict[str, Any]) -> dict[str, Any]:
    config = load_config()
    music_path = resolve_existing_path(payload.get("musicPath") or DATA_ROOT / "music" / "song.mp3")
    clips_dir = resolve_existing_path(payload.get("clipsDir") or DATA_ROOT / "clips")
    max_clips = int(payload.get("maxClips") or config["editing"]["max_clips"])
    style = str(payload.get("style") or config["editing"]["style"])
    resolution = str(payload.get("resolution") or config["export"]["resolution"])
    fps = int(payload.get("fps") or config["export"]["fps"])
    pre_event_time = float(payload.get("preEventTime") or config["editing"]["pre_event_time"])
    post_event_time = float(payload.get("postEventTime") or config["editing"]["post_event_time"])

    manual_beats = payload.get("manualBeats")
    manual_beats_path = payload.get("manualBeatsPath")
    if isinstance(manual_beats, list) and manual_beats:
        beats = sorted(float(value) for value in manual_beats)
        beat_source = "manual_ui"
    elif manual_beats_path:
        beat_data = load_manual_beats(resolve_existing_path(manual_beats_path))
        beats = beat_data["beats"]
        beat_source = "manual_json"
    else:
        beat_data = detect_beats(music_path)
        beats = beat_data["beats"]
        beat_source = "auto_audio"

    clips = scan_clips(clips_dir, max_clips=max_clips)
    if not clips:
        raise ValueError(f"No supported clips found in {clips_dir}")

    events_by_clip: dict[str, list[dict[str, Any]]] = {}
    for clip_path in clips:
        events_by_clip[str(clip_path)] = detect_candidate_events(
            clip_path,
            sample_fps=float(config["video"]["sample_fps"]),
        )

    timeline = align_events_to_beats(
        events_by_clip=events_by_clip,
        beats=beats,
        music_path=str(music_path),
        style=style,
        resolution=resolution,
        fps=fps,
        pre_event_time=pre_event_time,
        post_event_time=post_event_time,
    )

    save_current_timeline(timeline, events_by_clip)
    timeline_path = OUTPUT_ROOT / "ui_timeline.json"
    timeline.save_json(timeline_path)

    return {
        "ok": True,
        "beatSource": beat_source,
        "beats": beats,
        "eventsByClip": events_by_clip,
        "timeline": timeline.to_dict(),
        "timelinePath": str(timeline_path),
    }


def handle_update_timeline(payload: dict[str, Any]) -> dict[str, Any]:
    timeline_data = payload.get("timeline")
    if not isinstance(timeline_data, dict):
        raise ValueError("Payload must include a timeline object.")
    timeline = MontageTimeline.from_dict(timeline_data)
    timeline_path = OUTPUT_ROOT / "ui_timeline.json"
    timeline.save_json(timeline_path)
    save_current_timeline(timeline, STATE.events_by_clip)
    return {"ok": True, "timeline": timeline.to_dict(), "timelinePath": str(timeline_path)}


def handle_render(payload: dict[str, Any]) -> dict[str, Any]:
    timeline_data = payload.get("timeline")
    if isinstance(timeline_data, dict):
        timeline = MontageTimeline.from_dict(timeline_data)
    else:
        timeline = require_timeline()
    output = Path(payload.get("outputPath") or OUTPUT_ROOT / "montage_ui.mp4")
    output = resolve_output_path(output)
    rendered = render_timeline(timeline, output, keep_tmp=bool(payload.get("keepTmp", False)))
    with STATE.lock:
        STATE.timeline = timeline
        STATE.last_output = rendered
    return {
        "ok": True,
        "outputPath": str(rendered),
        "previewUrl": media_url(rendered),
        "timeline": timeline.to_dict(),
    }


def current_state() -> dict[str, Any]:
    with STATE.lock:
        timeline = STATE.timeline.to_dict() if STATE.timeline else None
        last_output = str(STATE.last_output) if STATE.last_output else None
        preview_url = media_url(STATE.last_output) if STATE.last_output else None
        events = STATE.events_by_clip
    return {
        "ok": True,
        "timeline": timeline,
        "eventsByClip": events,
        "lastOutput": last_output,
        "previewUrl": preview_url,
    }


def media_list() -> dict[str, Any]:
    music_dir = DATA_ROOT / "music"
    clips_dir = DATA_ROOT / "clips"
    music_exts = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
    music = sorted(str(path) for path in music_dir.iterdir() if path.is_file() and path.suffix.lower() in music_exts)
    clips = [str(path) for path in scan_clips(clips_dir)] if clips_dir.exists() else []
    outputs = sorted(str(path) for path in OUTPUT_ROOT.glob("*.mp4")) if OUTPUT_ROOT.exists() else []
    return {"ok": True, "music": music, "clips": clips, "outputs": outputs}


def save_current_timeline(timeline: MontageTimeline, events_by_clip: dict[str, list[dict[str, Any]]]) -> None:
    with STATE.lock:
        STATE.timeline = timeline
        STATE.events_by_clip = events_by_clip


def require_timeline() -> MontageTimeline:
    with STATE.lock:
        if STATE.timeline is None:
            raise ValueError("No timeline is loaded. Analyze clips or send a timeline first.")
        return STATE.timeline


def load_config() -> dict[str, Any]:
    with DEFAULT_CONFIG.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_existing_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")
    return resolved


def resolve_output_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if not is_relative_to(resolved, ROOT.resolve()):
        raise ValueError("Output path must stay inside the project folder.")
    return resolved


def resolve_media_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    resolved = path.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"Media file does not exist: {resolved}")
    allowed_roots = [DATA_ROOT.resolve(), OUTPUT_ROOT.resolve()]
    if not any(is_relative_to(resolved, allowed_root) for allowed_root in allowed_roots):
        raise ValueError("Media preview is limited to files under data/.")
    return resolved


def media_url(path: str | Path | None) -> str | None:
    if path is None:
        return None
    return f"/api/media?path={Path(path).as_posix()}"


def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    if not range_header.startswith("bytes="):
        return 0, file_size - 1
    range_value = range_header.removeprefix("bytes=").split(",", 1)[0]
    start_text, _, end_text = range_value.partition("-")
    if start_text:
        start = int(start_text)
        end = int(end_text) if end_text else file_size - 1
    else:
        suffix_length = int(end_text)
        start = max(0, file_size - suffix_length)
        end = file_size - 1
    start = max(0, min(start, file_size - 1))
    end = max(start, min(end, file_size - 1))
    return start, end


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def run(host: str, port: int, open_browser: bool) -> None:
    server = ThreadingHTTPServer((host, port), MontageRequestHandler)
    url = f"http://{host}:{server.server_port}"
    print(f"[app] FragSync UI running at {url}")
    print("[app] Put music in data/music and clips in data/clips, then use the browser UI.")
    if open_browser:
        webbrowser.open(url)
    server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local FragSync montage editor UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--open", action="store_true", help="Open the UI in the default browser.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run(args.host, args.port, args.open)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
