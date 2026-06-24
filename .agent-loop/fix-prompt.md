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
- update `scripts/agent_loop.py` so `cmd_attach_external_target(...)` only reports "attached and bootstrapped" when bootstrap actually ran, not merely when the operator passed `--bootstrap`
- preserve the Phase 10C/10E `full_target + --bootstrap` no-op contract by reporting plain attach wording when `bootstrap_state.status == "target_canonical_set_present"` and by not pointing the operator at a nonexistent `external target: bootstrapped ...` audit note
- add focused coverage proving a `full_target + --bootstrap` attach succeeds on the no-op branch and emits non-bootstrap CLI output that matches the real audit/log behavior

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
