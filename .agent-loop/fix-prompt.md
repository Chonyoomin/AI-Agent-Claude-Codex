# Claude Code Fix Task

## Objective
Fix only the Claude-owned issues from the latest `.agent-loop/codex-review.md` for Phase 10H.

## Context
The latest Codex review for Phase 10H returned `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `docs/external-ui-contract.md`
- `scripts/agent_loop.py`
- `tests/test_external_ui_view.py`
- `.agent-loop/git-diff.patch`
- `.agent-loop/test-output.log`
- `.agent-loop/lint-output.log`
- `.agent-loop/typecheck-output.log`
- `.agent-loop/build-output.log`

## Required fixes
- Expand `_ui_cli_only_operations_card()` so the shipped 10H UI surface reflects the full Phase 10G CLI-only boundary for the relevant shipped commands instead of the current partial subset.
- Update the 10H tests so they assert the expanded CLI-only inventory and prevent future regressions.
- Refresh `docs/external-ui-contract.md` so it no longer describes 10H as unimplemented and instead distinguishes the now-shipped 10H read-only surface from later UI work still deferred to 10I+.

## Constraints
- Fix only the listed issues.
- Do not redesign unrelated code.
- Do not expand the product scope beyond the approved 10H slice.
- Preserve the read-only boundary: no UI-triggered mutation, no silent CLI dispatch, no new control plane.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not delete files unless explicitly required and approved.
- Update tests and documentation to match the shipped behavior.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
