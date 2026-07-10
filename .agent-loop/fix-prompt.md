# Claude Code Fix Task

## Phase
Fix Phase B1 - Desktop Bootstrap UX Contract

## Objective
Resolve the review findings in the new desktop bootstrap UX work without
weakening the shipped external-target identity/audit boundaries or silently
changing the intended scope of the B1 slice.

## Context
The latest Codex review returned `NEEDS_FIXES` for two issues in the current
desktop bootstrap implementation:

1. the full-target attach path still auto-fills `attached_by` with the synthetic
   `desktop-ui-operator` default, which violates the explicit operator-identity
   boundary for controller-owned attach metadata
2. the implementation currently performs direct bootstrap attach dispatch from
   the Tk callback even though the active B1 prompt was scoped as a desktop
   bootstrap UX-contract slice

Treat the review findings as the source of truth for this fix cycle.

## Required fixes
- remove the synthetic `PRIMARY_DESKTOP_ATTACHED_BY_DEFAULT` identity path from
  the existing-project attach flow and require an explicit operator-supplied
  identity before any attach record is written from the desktop app
- update the desktop UI and any related helpers/tests so attach-existing-project
  and bootstrap-new-project both preserve the no-auto-fill operator-identity
  boundary
- resolve the B1 scope mismatch one way or the other:
  - either narrow the implementation back to a pure UX-contract/guidance slice
    that does not perform direct bootstrap mutation, or
  - if direct bootstrap dispatch is intentionally retained, align the prompt-
    facing behavior, code comments, and tests so the slice is no longer
    inaccurately presented as UX-contract-only
- keep the fix narrowly scoped to these findings and directly related tests

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not introduce hidden defaults for any `--*-by` identity field.
- Do not weaken the shipped Phase 10C / 10D / 10E refusal behavior.
- Preserve the canonical-artifact-first model and avoid a second desktop-only
  state plane.

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
