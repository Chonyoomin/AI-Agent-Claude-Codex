# Claude Code Fix Task

## Objective
Fix only the current Claude-owned Phase 10AA review issue found by Codex.

## Context
The latest Phase 10AA implementation was reviewed by Codex and received the
verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/phase-plan.md`
- `scripts/agent_loop.py`
- `tests/test_desktop_memory_vault.py`
- `README.md`
- `TASK.md`

## Required fixes
- Fix the Phase 10AA scope mismatch. The active phase contract promises the
  first bounded human-facing memory-vault export surface with optional
  human-readable memory views such as decision summaries and architecture
  snapshots, but the shipped implementation currently refuses to read durable-
  memory or canonical-artifact content and only renders metadata/freshness plus
  advisory framing.
- Align the implementation and the contract in one direction. Either:
  1. Add a bounded human-readable export body within the approved Phase 10AA
     safety boundary so the shipped UI/CLI can actually surface readable
     decision-summary / architecture-snapshot / durable-memory export content
     while preserving canonical-source precedence and non-mutation rules.
  2. Or keep the slice metadata-only, but then narrow the Phase 10AA contract,
     README text, prompt framing, and tests so they no longer claim readable
     memory views/export bodies ship in this phase.
- Add focused regression coverage for the chosen direction. The tests should
  fail if the shipped Phase 10AA behavior drifts away from what the task,
  phase-plan, and README claim.
- Keep the fix inside the approved Phase 10AA boundaries. Do not add hidden
  persistent state, background watchers, network transport, packaging, or
  controlled concurrency work.

## Constraints
- Fix only the listed issue.
- Do not redesign later phases such as 10AB+.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit `.agent-loop/loop-state.json` or
  `.agent-loop/orchestrator.log` by hand.
- Do not widen the Phase 10I three-control library-callable cap.
- Preserve the memory-vault surface as a bounded, canonical-artifact-first
  contract slice.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
