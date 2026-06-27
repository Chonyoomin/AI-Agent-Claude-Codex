# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10N review issue found by Codex.

## Context
The latest Phase 10N implementation was reviewed by Codex and received the verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_action_bridge.py`
- `README.md`

## Required fixes
- Fix the `attach` affordance so it matches the real shipped `attach-external-target` CLI contract.
  The current action-bridge registry renders `attach-external-target --target-root <PATH> --attached-by <NAME>`, but the actual parser requires `--target-path` and also requires `--approval-mode`. Update the affordance so the rendered command is genuinely copy-pasteable against the shipped CLI and preserves the no-auto-fill placeholder rule.
- Add or update focused tests so the action-bridge suite verifies the `attach` affordance matches the real parser contract instead of only checking placeholder presence.
- Update `README.md` only if needed to keep the 10N description accurate after the fix.

## Constraints
- Fix only the listed issue.
- Do not redesign unrelated desktop-action behavior.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log` by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10N objective.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
