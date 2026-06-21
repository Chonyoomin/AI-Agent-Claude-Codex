# Claude Code Fix Task

## Phase
Phase 9 - Fully Autonomous PRD-To-Product Mode (sub-phase: Phase 9F - Capacity-Halt Reprobe And Automatic Resume)

## Objective
Align the remaining Phase 9F README documentation with the shipped per-side adapter-invocation behavior so the operator-facing docs no longer describe the superseded single-flag long-run forwarding model.

## Context
Codex re-reviewed the current Phase 9F repo state and found one remaining artifact mismatch:

1. The runtime and tests now correctly implement per-side adapter invocation control for capacity-resume dispatch (`invoke_claude_adapter` and `invoke_codex_adapter`), and the Phase 9E long-run pre-hop path now forwards both flags into `reprobe_capacity_and_resume(...)`. However, the active Phase 9F README section still contains stale prose from the older implementation. It still says the Phase 9E long-run loop dispatches `reprobe_capacity_and_resume(..., invoke_adapter=invoke_claude_adapter)` and that the second `capacity reprobe: resumed ...` audit line records a single `invoke_adapter` flag. That is no longer true in the shipped code: the long-run path forwards both per-side flags, and the audit line now records `invoke_claude_adapter=...` plus `invoke_codex_adapter=...`. This is now the only remaining mismatch blocking a clean approve-for-transition verdict.

## Required fixes
- update the Phase 9F README section so it matches the shipped runtime exactly:
  - Phase 9E long-run forwarding uses both `invoke_claude_adapter` and `invoke_codex_adapter`
  - the standalone `run-capacity-reprobe` CLI still uses the back-compat global `--no-invoke-adapter` toggle
  - the `capacity reprobe: resumed ...` audit line now records the per-side effective flags, not a single `invoke_adapter` field
- preserve the existing documented behavior that is still correct:
  - Claude-side resume dispatches through the Claude prompt-handoff path
  - Codex-side resume dispatches through `make_codex_adapter().wait_for_review(...)`
  - per-side dry-run suppression remains supported in the long-run path
- do not widen scope beyond the narrow README / summary artifact alignment issue
- add or rerun focused validation sufficient to prove the documentation now matches the shipped repo state

## Constraints
- follow `CLAUDE.md`
- stay within Phase 9F scope
- do not modify `AGENTS.md` or `CLAUDE.md`
- prefer the smallest safe documentation change that removes the stale single-flag wording

## Required output
After applying the fix, update `.agent-loop/claude-summary.md` in the required Claude Implementation Summary format and include the new validation results.
