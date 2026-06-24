# Claude Code Fix Task

## Objective
Fix only the issues found in `.agent-loop/codex-review.md`.

## Context
The latest implementation was reviewed by Codex and received the verdict `APPROVED_FOR_HUMAN_REVIEW`.

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
- none; there are no open Claude-owned fixes from the current Codex review

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
