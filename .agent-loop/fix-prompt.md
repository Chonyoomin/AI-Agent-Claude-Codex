# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10O review issue found by Codex.

## Context
The latest Phase 10O implementation was reviewed by Codex and still has one
remaining Claude-owned issue after the Codex-owned routing fix was applied
directly.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `docs/mcp-integration-contract.md`
- `README.md`
- `ROADMAP.md`
- `tests/test_documentation_consistency.py`

## Required fixes
- Add focused documentation-consistency coverage that fails closed when the
  shipped Phase 10O MCP contract and README routing drift from the roadmap's
  actual successor phases for MCP runtime work.
- The test coverage should specifically protect the current canonical routing:
  the roadmap now places first MCP read-only runtime work at `Phase 10T` and
  mutation-capable MCP action work at `Phase 10U+`, so the tests should catch
  any future regression back to the stale `10P` / `10Q` routing or any other
  mismatch between the 10O docs and `ROADMAP.md`.
- Keep the change narrowly scoped to the missing guardrail. Do not rewrite the
  10O contract substance, the roadmap structure, or unrelated documentation.

## Constraints
- Fix only the listed issue.
- Do not redesign the Phase 10 roadmap.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or `.agent-loop/orchestrator.log`
  by hand.
- Do not delete files unless explicitly required and approved.
- Preserve the current desktop-product roadmap direction.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
