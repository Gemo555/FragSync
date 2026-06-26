# Technical Plan

## 1. Audio Analysis Layer

Input: music file and optional manual beat JSON.

Current MVP:

- `load_manual_beats` reads user-provided timestamps.
- `detect_beats` uses librosa for beats, onsets, and energy peaks.
- Manual beats always take priority over automatic detection.

Later improvements:

- Better downbeat/drop classification.
- Section detection for intro, buildup, drop, and outro.
- Beat strength scoring so heavy kills prefer heavy beats.

## 2. Game Event Detection Layer

Input: short FPS clips.

Current MVP:

- Extract audio with FFmpeg.
- Detect audio peaks as likely gunshot/impact moments.
- Sample frames with OpenCV.
- Compute adjacent frame differences as visual impact signals.
- Merge nearby audio and visual signals into candidate events.

Future extension points:

- HUD-region change detection.
- OCR for kill feed.
- Crosshair acceleration and weapon-flash detection.
- Game-specific CS2 / Valorant presets.

## 3. Editing Strategy Layer

Input: beat timestamps and per-clip candidate events.

Current MVP:

- Pick the highest-score event per clip.
- Pair clips and beats in order.
- Cut from `event_time - pre_event_time` to `event_time + post_event_time`.
- Store style intent through `speed` and `effects`.

Later improvements:

- Clip reordering based on event confidence and beat strength.
- Slow-motion and speed-ramp segments.
- Multi-kill handling.
- Style templates.

## 4. Render Export Layer

Input: `MontageTimeline`.

Current MVP:

- FFmpeg cuts normalized temporary clips.
- Concatenates segments.
- Adds the selected music track.
- Exports MP4 at the configured resolution and fps.

Later improvements:

- Real variable-speed rendering.
- Effects such as zoom, shake, freeze, flash, and motion blur.
- Optional preview files and render diagnostics.

