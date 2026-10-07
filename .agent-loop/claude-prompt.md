# Claude Code Task

## Phase
Fix Phase C7 - Review And Approval Surface

## Objective
Add a plain-English desktop review and approval surface for approval-required pauses. The operator should understand why approval is needed and take the existing explicitly gated action from the app without manual artifact inspection, while preserving all shipped human-gate rules.

## Context
Fix Phase C1 established the desktop-first order: Project, PRD, Run Mode, Run, and Progress. Fix Phase C2 owns project selection, C3 owns PRD selection, C4 owns run-mode selection, C5 owns Start/Stop, and C6 owns the plain-English Progress console. Read TASK.md, README.md, ROADMAP.md, and the active .agent-loop artifacts before editing. Read docs/desktop-first-run-setup-contract.md and inspect the actual repository state. Do not rely on prior chat context.

Reuse the shipped canonical status, review, approval, and runtime-owner helpers. The desktop UI must remain a presentation and explicit-operator-action surface over canonical artifacts and the existing refresh cadence, not a second controller.

## Required Work

1. Add a visible approval/review section after Progress, or at the location required by the existing desktop contract, when the canonical state requires operator approval or review. When no approval is required, keep the section absent or clearly inactive without implying that work is waiting.
2. Explain in plain English what is waiting, why operator action is needed, what action is recommended, and what will happen after the action.
3. Expose explicit review and approval actions that delegate to the existing canonical runtime owners and shipped gate contracts. Do not invent a UI-only approval state or write loop state directly from a new controller.
4. Preserve operator identity and every existing acceptance or approval requirement. Never auto-fill identity, silently approve, bypass strict mode, or treat a displayed completion signal as proof of correctness.
5. Keep advanced technical details available behind an Advanced or equivalent disclosure, without making raw artifacts the default experience.
6. Add focused tests covering gate detection, plain-English copy, action routing, refusal or missing-identity behavior, strict-mode and recovery preservation, section ordering, and the no-auto-approval guarantee.
7. Update the relevant README and summary artifacts only after implementation and validation evidence is available.

## Constraints

- Do not weaken human-gate rules or add auto-approval behavior.
- Do not create a second controller, invented state store, or direct UI-only loop-state writes.
- Do not implement Fix Phase C8 completion and handoff behavior in this slice.
- Do not add Git automation, network endpoints, or unrelated redesigns.
- Use explicit operator gestures and the existing desktop polling or refresh cadence.
- Preserve the completed C2-C6 behavior and existing tests.

## Validation

Run focused desktop and documentation tests first, then the full test suite. Inspect the resulting diff and canonical artifacts. Record the implementation, validation commands, and any residual limitations in .agent-loop/claude-summary.md. Do not claim completion without evidence.

## Completion Signal

When this implementation prompt is complete, leave the repository ready for Codex review according to the repository handoff contract. Do not modify .agent-loop/codex-review.md or claim Codex approval.
