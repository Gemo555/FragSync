# Product Design

## Target Users

FPS and competitive-game creators who already collect short kill clips and want faster beat-synced montage drafts for CS2, Valorant, and similar games.

## Pain Points

- Manual beat marking and impact alignment takes too much time.
- Generic editors do not understand kill timing or FPS impact moments.
- Existing highlight tools often focus on capture, storage, or long-video clipping instead of music-synced montage assembly.
- Creators need quick drafts they can later polish, not a black-box editor that makes every stylistic choice.

## Core Flow

1. User chooses a song.
2. User optionally provides manual beat/drop timestamps.
3. User adds already-trimmed kill clips.
4. System detects likely impact events per clip.
5. System aligns the best events to beats.
6. System renders a simple montage draft.
7. User reviews the timeline and improves beats, clips, or style settings.

## Difference From Existing Tools

- CapCut: broad video editor with templates and manual controls. This project focuses narrowly on FPS kill-to-beat sync.
- Powder / Eklipse: highlight discovery and creator workflows. This MVP assumes clips are already cut and focuses on montage timing.
- Medal: capture, sharing, and clipping. This project is a local montage assembly engine.

## MVP Boundary

The MVP is command-line only. It accepts short clips, detects generic audio/visual impact signals, aligns them to music beats, and exports a horizontal MP4. It does not attempt full game understanding, cloud workflows, or polished effects.

## Future Business Models

- Creator subscription for faster rendering, templates, and game-specific detectors.
- Paid style packs for Valorant, CS2, Apex, and other communities.
- Team or agency workflow for batch montage drafts.
- Local-first free tool with paid cloud rendering as an optional upgrade.

