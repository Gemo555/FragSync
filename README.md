# fps-kill-sync-montage

A command-line MVP for FPS creators who want to sync short CS2 / Valorant style kill clips to music beats. This is not a general AI video editor. The first goal is a runnable local demo: detect or load music beats, find candidate impact moments in pre-trimmed clips, align those events to beats, and render a simple horizontal montage with FFmpeg.

## MVP Scope

- Input one music file (`mp3`, `wav`, or any format FFmpeg/librosa can read).
- Input a folder of already-trimmed short kill clips (`mp4`, `mov`, `mkv`, `avi`).
- Prefer manually provided beat times when available.
- Otherwise use librosa to detect beats, onsets, and energy peaks.
- Detect candidate clip events from audio peaks and frame differences.
- Align the strongest event in each clip to a music beat.
- Export a 1080p, 60fps MP4 montage.
- Optionally export a timeline JSON, run dry-run planning, or render from a saved timeline.

## Not Doing Yet

- No web UI, accounts, cloud storage, database, or deployment.
- No long-video highlight mining.
- No full OCR or kill-feed understanding yet.
- No advanced velocity ramping, zoom, shake, freeze-frame, or template system yet.
- No game-specific CS2 / Valorant HUD tuning yet.

## Install

Python 3.10+ is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .[dev]
```

For a minimal install without editable mode:

```bash
python -m pip install -r requirements.txt
```

## FFmpeg

Rendering requires FFmpeg and FFprobe on your `PATH`.

- Windows: install from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or `winget install Gyan.FFmpeg`.
- macOS: `brew install ffmpeg`.
- Linux: `sudo apt install ffmpeg`.

If FFmpeg is missing, dry-run and timeline export still work, but MP4 rendering will fail with a clear message.

## Input Files

Place files like this:

```text
data/
  music/
    song.mp3
  clips/
    clip_001.mp4
    clip_002.mp4
  output/
```

Large media files under `data/music`, `data/clips`, and `data/output` are ignored by git.

## Run Demo

Local editor UI:

```bash
python -m src.app --open
```

Then open `http://127.0.0.1:8787` if the browser does not open automatically. The UI can:

- scan `data/music` and `data/clips`;
- analyze music beats or use manually typed beat times;
- detect initial kill points from sudden audio intensity changes, with visual frame-diff signals as a secondary cue;
- edit each clip's beat, kill time, source start, and source end;
- realign clip durations so kill points land as close as possible to the selected music beat;
- render and preview `data/output/montage_ui.mp4`.

```bash
python -m src.main ^
  --music data/music/song.mp3 ^
  --clips data/clips ^
  --output data/output/montage.mp4
```

Optional parameters:

```bash
python -m src.main ^
  --music data/music/song.mp3 ^
  --clips data/clips ^
  --output data/output/montage.mp4 ^
  --manual-beats examples/manual_beats.json ^
  --style clean_sync ^
  --max-clips 8 ^
  --resolution 1920x1080 ^
  --fps 60 ^
  --export-timeline data/output/timeline.json
```

Dry-run without rendering:

```bash
python -m src.main ^
  --music data/music/song.mp3 ^
  --clips data/clips ^
  --output data/output/montage.mp4 ^
  --manual-beats examples/manual_beats.json ^
  --dry-run ^
  --export-timeline data/output/timeline.json
```

Render from a saved timeline:

```bash
python -m src.main ^
  --timeline examples/sample_timeline.json ^
  --output data/output/montage.mp4
```

Quick dry-run helper after adding `data/music/song.mp3` and clips:

```bash
python scripts/demo.py
```

## Manual Beats

Manual beats override automatic beat detection. Example:

```json
{
  "beats": [0.8, 1.6, 2.4, 3.2, 4.0, 4.8],
  "labels": {
    "3.2": "drop",
    "4.8": "heavy_hit"
  }
}
```

Save this as `examples/manual_beats.json` or any path and pass it with `--manual-beats`.

## Output

The renderer cuts each selected clip around the chosen event, normalizes size/fps, concatenates the temporary clips, adds the music track, and writes an MP4 to `--output`. Temporary files are placed under `data/output/tmp` by default and removed after successful rendering.

## Roadmap

- Phase 0: manual demo and demand validation.
- Phase 1: command-line prototype with beat/event/timeline/render loop.
- Phase 2: interactive web MVP.
- Phase 3: CS2 / Valorant-specific detection.
- Phase 4: style templates for clean sync, slow impact, and aggressive edits.
- Phase 5: long-video highlight detection.
