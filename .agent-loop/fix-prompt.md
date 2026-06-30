# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10U review issues found by Codex.

## Context
The latest Phase 10U implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_mcp_action_guardrails.py`
- `tests/test_desktop_app.py`
- `README.md`
- `docs/mcp-integration-contract.md`
- `docs/mcp-server-selection-ux-contract.md`
- `TASK.md`
- `.agent-loop/phase-plan.md`

## Required fixes
- Fix the Phase 10U policy-contract mismatch where the registry advertises more
  than one approval-policy mode (`per_action_explicit_approval` and
  `per_session_explicit_approval`), but the actual approval-state computation
  does not branch on `spec["approval_policy"]`. Right now every action is gated
  through the same `operator_per_action_acknowledgement` semantics and the same
  per-action requirement text, so the shipped implementation does not actually
  model a distinct per-session approval policy for
  `github_trigger_workflow`. The approval-policy enum is therefore mostly
  descriptive text instead of executable contract logic.
- Keep the fix inside the approved Phase 10U boundaries. This is still a
  contract-only slice: do not add actual mutation dispatch, no networked MCP
  transport, no audit-log writer, no subprocess dispatch, no hidden persisted
  preference or policy-pack store, and no widening of the Phase 10I
  library-callable cap.
- Update the focused tests so they prove the approval-policy distinction is real
  in the shipped contract surface instead of only checking that the enum values
  exist. Add coverage that would fail if `per_session_explicit_approval` and
  `per_action_explicit_approval` collapse back into identical behavior.
- Update `README.md` as needed so the Phase 10U description matches the shipped
  implementation after the fix.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10V or beyond.
- Do not introduce actual mutation-capable MCP runtime behavior, actual
  networked MCP fetch, new CLI/library surfaces outside the approved Phase 10U
  scope, or any hidden persisted control plane.
- Do not silently mutate in-flight `loop-state.json` approval state or other
  canonical controller fields outside approved canonical write paths.
- Do not add subprocess spawning, shell execution, network IO, or canonical
  artifact writes beyond the shipped bounded desktop/runtime contracts.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log`
  by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10U objective and the shipped Phase 10O / 10S /
  10T / 10I boundary rules.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
