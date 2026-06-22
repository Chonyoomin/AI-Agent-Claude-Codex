# Claude Code Fix Task

## Objective
Fix only the issues found in `.agent-loop/codex-review.md`.

## Context
The previous implementation was reviewed by Codex and received the verdict `NEEDS_FIXES`.

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
- update `scripts/agent_loop.py` so the Phase 10D detach schema validator refuses malformed controller-owned attach records when `mode_selection.approval_mode` is outside `EXTERNAL_TARGET_APPROVAL_MODES`
- update `scripts/agent_loop.py` so the Phase 10D detach schema validator refuses malformed controller-owned attach records when `bootstrap_state.status` is outside `EXTERNAL_TARGET_BOOTSTRAP_STATUSES`
- add focused coverage in `tests/test_external_target_attach.py` proving both out-of-enumeration cases now refuse fail-closed and leave the malformed attach record on disk

## Constraints
- Fix only the listed issues.
- Do not redesign unrelated code.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not delete files unless explicitly required and approved.
- Preserve the original task objective.
- Update tests if behavior changes.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
