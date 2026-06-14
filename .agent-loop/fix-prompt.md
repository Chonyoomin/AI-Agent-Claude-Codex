# Claude Code Fix Task

## Objective
No active Claude fix task. Phase 6N is approved in the current repo state.

## Context
The latest Codex re-review found no remaining Claude-owned issues for Phase 6N. The runtime-adapter seam is wired into the real operator entry points, the persisted default-off runtime-config layer is present, and the malformed-directory recovery path for `set-runtime-config --clear` now refuses fail-closed through the standard halt path instead of crashing.

## Required fixes
- None.

## Constraints
- Do not make changes from this file alone.
- Wait for a new Codex `NEEDS_FIXES` verdict before implementing another fix cycle.

## Required output
No output required until a future Codex review generates a new active fix task.
