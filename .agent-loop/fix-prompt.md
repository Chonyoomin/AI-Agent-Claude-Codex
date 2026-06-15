# Claude Code Fix Task

## Objective
Fix the remaining Phase 8B documentation drift so the README's approval-mode
and halt-recovery descriptions match the shipped strict-mode behavior exactly.

## Context
Codex reviewed the current Phase 8B implementation from repo state. The three
new playbooks are internally consistent, `tests/test_documentation_consistency.py`
passes, and the full test suite passes. One Claude-owned documentation defect
remains in the touched explanatory docs:

1. `README.md` still says autonomous mode bypasses "four Phase 5C strict-mode
   human gates" and still describes `docs/halt-and-recovery.md` as covering
   "the four Phase 5C strict-mode gates". That wording is inaccurate relative
   to the shipped runtime:
   - the shipped Phase 5C contract defines three strict-mode gates:
     `pre_claude_prompt`, `pre_fix_prompt`, and `pre_codex_review`
   - `pre_codex_review` has two halt-status flavors
     (`halted_awaiting_human_pre_codex_review_normal` and
     `halted_awaiting_human_pre_codex_review_fix`) so resume can route
     correctly
   - the current README wording reintroduces the same "four gates" confusion
     Phase 8A already corrected elsewhere

The remaining related drift in `.agent-loop/phase-plan.md` is Codex-owned and
is NOT part of this Claude fix task.

## Required fixes
- Correct the Phase 5D paragraph in `README.md` so it describes autonomous mode
  as bypassing the three strict-mode gates, with `pre_codex_review` having two
  halt-status flavors rather than being counted as a fourth gate.
- Correct the Phase 8B paragraph in `README.md` so the halt-and-recovery
  playbook description no longer says "four Phase 5C strict-mode gates" and
  instead uses wording aligned with the shipped strict-mode contract.
- Add or update focused documentation-consistency coverage so this exact README
  drift fails closed on regression. The current suite protects
  `docs/architecture.md` and the Phase 8B playbooks, but it does not currently
  fail if README reintroduces the incorrect "four strict gates" wording.
- Update `.agent-loop/claude-summary.md` so it accurately describes the final
  fix and the exact validation commands run.

## Constraints
- Follow `CLAUDE.md`.
- Stay within Phase 8B scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not edit Codex-owned planning artifacts such as `.agent-loop/phase-plan.md`,
  `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, or
  `.agent-loop/codex-review.md`.
- Do not broaden into new runtime, approval-mode, halt, or checkpoint behavior.
- Preserve the shipped contracts and describe only behavior that already exists
  in the repo.
- Prefer the smallest safe documentation/test fix that makes the README truthful
  relative to the current runtime.

## Required output
After implementing the fix, update `.agent-loop/claude-summary.md` with the
required summary format and include the exact validation commands you ran.
