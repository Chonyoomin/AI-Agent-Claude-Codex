# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10S review issues found by Codex.

## Context
The latest Phase 10S implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `tests/test_documentation_consistency.py`
- `README.md`
- `docs/mcp-server-selection-ux-contract.md`
- `docs/mcp-integration-contract.md`
- `ROADMAP.md`
- `TASK.md`
- `.agent-loop/phase-plan.md`

## Required fixes
- Fix the README active-phase mismatch. Right now the README correctly says
  Phase 10S is active in one paragraph, but a later paragraph still says
  `Phase 10R (Desktop App PRD Intake And Project Start Flow, active)`. Update
  the README so it does not claim two different active phases at once and so
  the 10R paragraph is described as a completed shipped runtime slice rather
  than the current active phase.
- Strengthen the Phase 10S documentation-consistency tests so this kind of
  stale active-phase claim cannot pass silently again. The existing tests only
  prove that `Phase 10S` and `MCP Server Selection UX Contract` appear
  somewhere in the README; they do not fail if an older paragraph still claims
  a different phase is active. Add or update focused tests that explicitly
  reject stale README active-phase claims once Phase 10S is the canonical
  active phase.
- Keep the fix bounded to README alignment and the missing regression
  coverage. Do not widen into runtime work, new contracts, or unrelated
  documentation rewrites.

## Constraints
- Fix only the listed issues.
- Do not redesign later phases such as 10T or 10U.
- Do not introduce runtime MCP behavior, new CLI/library surfaces, or any
  hidden persisted control plane.
- Do not silently mutate in-flight `loop-state.json` approval state or other
  canonical controller fields outside approved canonical write paths.
- Do not add subprocess spawning, shell execution, network IO, or canonical
  artifact writes beyond the shipped documentation/test scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log`
  by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the original Phase 10S documentation-only objective and the shipped
  Phase 10O/10T/10U routing boundaries.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
