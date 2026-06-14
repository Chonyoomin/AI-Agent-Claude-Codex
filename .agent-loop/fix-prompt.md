# Claude Code Fix Task

## Objective
<<<<<<< Updated upstream
Fix the remaining Phase 6N persisted-config recovery bug so malformed `.agent-loop/runtime-config.json` artifacts are handled fail-closed instead of crashing the operator-facing clear path.

## Context
Codex re-reviewed the post-fix 6N implementation. The main contract gaps are closed: the runtime seam is wired into `run` / `resume` / `auto-continue`, the persisted default-off runtime config exists, and the focused plus full suites pass. One Claude-owned bug remains in the new recovery path.

If `.agent-loop/runtime-config.json` exists as a directory instead of a regular file, `clear_runtime_config(repo_root)` currently calls `Path.unlink()` unconditionally and raises an uncaught `PermissionError` / `IsADirectoryError`. `cmd_set_runtime_config(args)` only catches `HaltError`, so `python scripts/agent_loop.py set-runtime-config --clear` can crash exactly when the persisted config is malformed and the operator is trying to recover from it.

## Required fixes
- Make clearing the persisted runtime config fail-closed for malformed on-disk artifact shapes, especially the "path exists but is a directory" case.
- Keep the operator-facing recovery path usable: `set-runtime-config --clear` should not crash on malformed persisted config artifacts.
- Route the malformed-clear path through the existing halt vocabulary and `_halt` behavior rather than through an uncaught filesystem exception.
- Add focused tests covering at least:
- `clear_runtime_config(...)` on a directory at `.agent-loop/runtime-config.json`
- `cmd_set_runtime_config --clear` on that malformed artifact shape
- any updated success-path expectations if you change the helper contract
- Update `.agent-loop/claude-summary.md` to describe the final post-fix behavior and validation commands exactly.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 6N scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not weaken the existing runtime selection, precedence, or default-local behavior.
- Prefer the smallest safe fix.
=======
No active Claude fix task. Phase 6O is approved in the current repo state.

## Context
The latest Codex re-review found no remaining Claude-owned issues for Phase 6O. The LangChain support layer remains optional, read-only, and subordinate to the shipped runtime surfaces, and the remaining `read_loop_state` validation gap is now fixed so malformed canonical state refuses through the shipped validator path.

## Required fixes
- None.

## Constraints
- Do not make changes from this file alone.
- Wait for a new Codex `NEEDS_FIXES` verdict before implementing another fix cycle.
>>>>>>> Stashed changes

## Required output
No output required until a future Codex review generates a new active fix task.
