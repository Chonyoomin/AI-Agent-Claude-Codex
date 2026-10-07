# Claude Code Task

## Phase
Fix Phase C8 - Completion And Handoff Summary

## Objective
Add the end-of-run summary surface for the desktop app so the operator can understand what finished, what remains blocked, whether the next planning step is possible, and what action is recommended next. The summary must remain a faithful presentation of shipped canonical artifacts and state.

## Context
Fix Phase C1 established the desktop-first setup flow. C2 through C6 provide project, PRD, run-mode, Start/Stop, and plain-English Progress surfaces. C7 provides the Review and Approval Surface. Read TASK.md, README.md, ROADMAP.md, and all active .agent-loop artifacts before editing. Read docs/desktop-first-run-setup-contract.md and inspect the actual repository state. Do not rely on prior chat context.

Reuse the shipped completion, acceptance, planner, handoff, and runtime-owner contracts. The desktop UI is a presentation and explicit-operator-action surface over canonical artifacts; it must not become a second controller or completion ledger.

## Required Work

1. Add a visible Completion or Handoff Summary section in the established desktop section order, using plain English and the existing refresh cadence.
2. Distinguish at minimum these canonical situations: work complete and awaiting final acceptance, blocked or failed and requiring intervention, and complete/approved with the next planning step available or awaiting the operator's next phase decision.
3. For each supported situation, show what finished, what remains, the reason for any block or wait, and one recommended next action in plain English.
4. Route any explicit final acceptance or next-phase action through the existing shipped owner and identity/gate contract. Do not write loop-state directly from the new UI, auto-accept work, auto-activate a phase, or bypass Phase 9G acceptance requirements.
5. Keep raw status, verdict, paths, and command details behind the existing Advanced disclosure. Advisory interpretations must be labeled as advisory and canonical values must remain identifiable.
6. Add focused tests for canonical-state mapping, complete/blocked/awaiting-planning copy, recommendation routing, refusal and missing-identity behavior, section ordering, refresh-only behavior, no-auto-acceptance, and no-hidden-ledger guarantees.
7. Update README.md and .agent-loop/claude-summary.md with implementation and validation evidence only after the implementation is complete.

## Constraints

- Do not add new planner behavior in this slice.
- Do not create a hidden completion ledger or a second orchestration plane.
- Do not auto-accept, auto-activate, auto-approve, or silently advance phases.
- Do not add Git automation, network endpoints, or unrelated UI redesigns.
- Preserve all completed C2-C7 behavior and existing human-gate rules.
- Preserve explicit operator identity requirements and fail closed on unreadable or contradictory canonical artifacts.
- Do not modify .agent-loop/codex-review.md or claim Codex approval.

## Validation

Run focused desktop and documentation tests first, then the full test suite. Inspect the resulting diff and canonical artifacts. Record the implementation, validation commands, and residual limitations in .agent-loop/claude-summary.md. Do not claim completion without evidence.

## Completion Signal

When this implementation prompt is complete, leave the repository ready for Codex review according to the repository handoff contract. Do not modify .agent-loop/codex-review.md or fabricate a review verdict.
