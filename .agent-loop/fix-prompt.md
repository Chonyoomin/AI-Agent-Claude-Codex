# Claude Code Fix Task

## Objective
Fix only the remaining Claude-owned Phase 10I review issue found by Codex.

## Context
The latest Phase 10I fix cycle was reviewed by Codex and still received the verdict `NEEDS_FIXES` because one README inconsistency remains.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/git-diff.patch`
- `.agent-loop/test-output.log`
- `.agent-loop/lint-output.log`
- `.agent-loop/typecheck-output.log`
- `.agent-loop/build-output.log`

## Required fixes
- Fix the remaining README inconsistency in `README.md`.
  The runtime and tests now correctly show that the Phase 10I `invoke-external-control` surface does NOT append an `[orchestrator] ...` line to `.agent-loop/orchestrator.log` and does NOT route refusals through `_halt(...)` / `halted_input_missing`. However, the active Phase 10I paragraph in `README.md` still describes that old behavior.
- Rewrite only the stale Phase 10I paragraph so it matches the shipped runtime exactly.
  The updated paragraph should reflect that:
  - `invoke-external-control --control <ID>` delegates only the allowed read-only library-call controls
  - success is surfaced through `[external-ui] ...` stdout lines, not canonical audit-log writes
  - refusal is surfaced through `[external-ui] REFUSED: ...` on stderr with non-zero exit, not via `_halt(...)`
  - neither success nor refusal mutates `.agent-loop/orchestrator.log` or `.agent-loop/loop-state.json`
- Keep the edit narrow.
  Do not rewrite unrelated README sections, and do not make any runtime/code/test changes unless a tiny wording-alignment test absolutely requires it.

## Constraints
- Fix only the listed issues.
- Do not redesign unrelated code.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log` by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original task objective.
- Update tests only if documentation wording assertions require it.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
