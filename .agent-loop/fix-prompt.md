# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10M review issue found by Codex.

## Context
The latest Phase 10M implementation was reviewed by Codex and received the verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `docs/desktop-app-contract.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- `README.md`

## Required fixes
- Fix the controller-root selection contract violation in the Phase 10M desktop runtime.
  Phase 10L makes explicit operator selection of the controller root load-bearing: the shell must require the operator to choose a root before rendering any canonical artifact, and must not silently pick a default root. The shipped 10M runtime still falls back to `find_repo_root()` when `--controller-root` is omitted, and the tests currently permit that path.
  Update the 10M implementation so desktop rendering cannot proceed without an explicit controller-root selection path that satisfies the contract. Keep the fix bounded to the existing 10M runtime shape; do not widen into Phase 10N action-bridge work.
- Update the focused tests so they pin the corrected behavior and fail closed if implicit repo-root fallback returns.
- Update `README.md` only if needed to keep the 10M description accurate after the fix.

## Constraints
- Fix only the listed issue.
- Do not redesign unrelated desktop runtime behavior.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log` by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10M objective.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
