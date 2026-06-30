# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10T review issues found by Codex.

## Context
The latest Phase 10T implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_mcp_assistance.py`
- `tests/test_desktop_app.py`
- `README.md`
- `docs/mcp-integration-contract.md`
- `docs/mcp-server-selection-ux-contract.md`
- `TASK.md`
- `.agent-loop/phase-plan.md`

## Required fixes
- Fix the Phase 10T runtime mismatch where the shipped MCP assistance surface
  claims to be the first user-selectable read-only MCP assistance surface, but
  the actual view builder hard-codes
  `operator_acknowledged_safety_copy=False` and
  `operator_supplied_identity=False` for every server. Right now that forces
  every non-deferred server into `disabled_by_default`, and
  `build_desktop_mcp_assistance_controls(...)` then disables every button
  because it only enables controls when
  `enablement_state == "enabled_pending_runtime"`. Update the shipped Phase 10T
  surface so at least the intended read-only MCP assistance path is genuinely
  selectable within the bounded Phase 10T contract, instead of being permanently
  disabled by hard-coded unmet requirements.
- Keep the fix inside the approved Phase 10T boundaries. Do not add mutation-
  capable MCP actions, no actual networked MCP transport, no subprocess
  dispatch, no hidden persisted preference store, and no widening of the Phase
  10I library-callable cap.
- Update the focused tests so they catch the real contract requirement instead
  of encoding the broken behavior. In particular, the suite must stop asserting
  that the shipped read-only descriptors are always `disabled_by_default` in the
  real Phase 10T surface, and it must add coverage that proves the shipped
  bounded Phase 10T UI actually exposes a selectable read-only MCP assistance
  path while still refusing deferred-mutating servers fail-closed.
- Update `README.md` as needed so the 10T description matches the shipped
  implementation after the fix.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10U or beyond.
- Do not introduce mutation-capable MCP behavior, actual networked MCP fetch,
  new CLI/library surfaces outside the approved Phase 10T scope, or any hidden
  persisted control plane.
- Do not silently mutate in-flight `loop-state.json` approval state or other
  canonical controller fields outside approved canonical write paths.
- Do not add subprocess spawning, shell execution, or canonical artifact writes
  beyond the shipped bounded desktop/runtime contracts.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log`
  by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10T objective and the shipped Phase 10O / 10S /
  10I / 10U boundary rules.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
