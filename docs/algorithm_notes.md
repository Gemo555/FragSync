# Algorithm Notes

## Beat Detection

Manual beats are best for the MVP because creators often know the drop and heavy hits. Automatic detection uses librosa as a fallback and returns beats, onsets, energy peaks, and tempo.

TODO: Add beat strength and downbeat labels. A kill should prefer a strong beat, not just the next beat.

## Event Detection

The first event detector is intentionally simple:

- audio onset strength approximates gunshots and impact sounds;
- frame differences approximate flashes, camera movement, and sudden action;
- nearby audio and visual events are merged into a higher-confidence impact event.

TODO: Add FPS-specific signals: kill-feed OCR, HUD region change, weapon flash masks, hit markers, and crosshair acceleration.

## Sync Strategy

The current strategy uses one selected event per clip and pairs clips to beats in order. The rendered cut starts shortly before the event and ends shortly after it so the impact lands near the target beat.

TODO: Reorder clips by confidence and pair high-confidence events with high-strength beats.

