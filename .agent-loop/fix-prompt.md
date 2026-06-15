# Claude Code Fix Task

## Objective
Fix the remaining Phase 8A documentation mismatches so the new architecture/usage docs describe the shipped strict-mode and checkpoint behavior accurately rather than overstating what the runtime currently does.

## Context
Codex reviewed the current Phase 8A implementation from repo state. The new docs exist, the focused documentation-consistency suite passes, and the full test suite passes. Two contract-level doc mismatches remain:

1. `docs/architecture.md` says strict mode "adds four human checkpoints inside each cycle" and also says "Token-exhaustion (Phase 6F) and Phase 5C strict-mode gates write checkpoints". Both claims are inaccurate relative to the shipped contracts and runtime:
   - the shipped Phase 5C contract defines three strict-mode human checkpoints (`pre_claude_prompt`, `pre_fix_prompt`, `pre_codex_review`), with two halt-status flavors for the `pre_codex_review` gate so resume can route correctly
   - the current runtime writes checkpoint artifacts for token-exhaustion continuation; strict-mode halts are resumed by persisted halt status and state, not by strict-gate checkpoint writes

2. `docs/usage.md` says "Every halt persists a status that points at a specific recovery command", but that is not true for all shipped halts. `halted_failed_requires_human` and `halted_max_cycles_reached` currently point at a manual recovery path plus a fresh Codex-owned activation prompt, not a direct CLI command. The current wording over-promises command-driven recovery where the shipped system intentionally requires human/Codex intervention.

## Required fixes
- Correct the strict-mode wording in `docs/architecture.md` so it matches the shipped Phase 5C contract and README language.
- Correct the checkpoint wording in `docs/architecture.md` so it does not claim the strict-mode gates write checkpoints when the shipped runtime does not do that.
- Correct the halt-recovery wording in `docs/usage.md` so it describes a specific recovery path rather than promising a direct recovery command for every halt.
- Add or update focused documentation tests so these exact mismatches fail closed on regression.
- Update `README.md` if needed so any touched explanatory text stays aligned with the corrected documentation wording.
- Update `.agent-loop/claude-summary.md` so it accurately describes the final fix and the exact validation commands run.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 8A scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not broaden into new runtime, checkpoint, or strict-mode behavior.
- Preserve the shipped contracts and describe only behavior that already exists in the repo.
- Prefer the smallest safe documentation/test fix that makes the docs truthful relative to the current runtime.

## Required output
After implementing the fix, update `.agent-loop/claude-summary.md` with the required summary format and include the exact validation commands you ran.
