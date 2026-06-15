# Claude Code Fix Task

## Objective
Correct the remaining Phase 7C recovery-hint contract mismatch so the new human-facing hints point at real shipped recovery paths instead of suggesting planner/activation flows that the current runtime and planning contracts explicitly refuse from those halted states.

## Context
Codex re-reviewed the current Phase 7C fix from repo state. The original gap is fixed: the previously-unmapped shipped statuses now have explicit `STATUS_RECOVERY_HINTS`, the focused status tests were broadened, and both the focused and full test suites pass.

One remaining issue was introduced in the new hint text for terminal halt states:

- `halted_failed_requires_human` currently tells the operator to "manually advance or re-activate the phase via `python scripts/agent_loop.py activate` once the proposal is approved"
- `halted_max_cycles_reached` currently tells the operator to "re-activate or supersede the phase via the shipped planner/activate flow"

Those instructions do not match the shipped contracts. The planner explicitly refuses when `last_verdict == FAILED_REQUIRES_HUMAN`, when `status` is any `halted_*`, and when `cycle_count >= max_cycles` on `NEEDS_FIXES`. So the current Phase 7C hint text points at a path the system itself will reject rather than at the real human-intervention path.

## Required fixes
- Update the Phase 7C recovery hints for `halted_failed_requires_human` and `halted_max_cycles_reached` so they describe the real shipped recovery path and do not direct the operator to `plan` / `activate` as the immediate next step when those flows are contractually blocked.
- Keep the hints CLI-first and contract-accurate: they may point at inspection artifacts, explicit human intervention, Codex-owned state changes, or other already-shipped recovery surfaces, but must not invent a recovery path that the current runtime refuses.
- Add or update focused tests so this specific semantic mismatch is guarded. The tests should fail if these halt statuses regress to suggesting blocked planner/activation recovery as the direct next step.
- Update `README.md` if needed so the Phase 7C description stays aligned with the corrected halt-recovery guidance.
- Update `.agent-loop/claude-summary.md` so it accurately describes the final fix and the exact validation commands run.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 7C scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not broaden into new runtime behavior, new reset commands, new planner behavior, or later Phase 7 UI/dashboard work.
- Preserve the existing halt/refusal vocabulary, planner refusal rules, approval semantics, and CLI-first contract.
- Prefer the smallest safe fix that makes the hints truthful relative to the shipped runtime and planning behavior.

## Required output
After implementing the fix, update `.agent-loop/claude-summary.md` with the required summary format and include the exact validation commands you ran.
