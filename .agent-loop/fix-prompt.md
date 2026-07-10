# Claude Code Fix Task

## Phase
Fix Phase B1 - Desktop Bootstrap UX Contract

## Objective
Resolve the remaining desktop bootstrap UX issues in the current guidance-only
implementation so the surfaced bootstrap command is actually safe to copy/paste
for valid user input and the adjacent implementation comments match the shipped
contract.

## Context
The previous fix cycle correctly removed the synthetic
`desktop-ui-operator` path and narrowed the desktop back to UX-only CLI
guidance. A fresh Codex review found two residual issues:

1. the bootstrap CLI guidance helper interpolates raw free-text values into
   double-quoted arguments without escaping embedded quotes, so a valid entered
   value like `human_objective = Build "v2"` produces a broken command
2. the nearby Fix Phase B1 comment block still describes a removed
   "bootstrap-dispatch wrapper", which no longer matches the implemented
   guidance-only boundary

Treat `.agent-loop/codex-review.md` as the source of truth for this fix cycle.

## Required fixes
- make the surfaced bootstrap CLI guidance robust for operator-entered text:
  either escape embedded quotes correctly for the intended shell surface or
  fail closed with a clear validation/refusal path when a field contains
  unsupported quote characters
- add focused tests that pin the chosen contract so quote-bearing input cannot
  silently regress into broken copy/paste guidance
- correct the stale Fix Phase B1 comment text so it no longer describes a
  removed dispatch wrapper and instead reflects the current UX-only CLI
  guidance boundary
- keep the fix narrowly scoped to these findings and directly related tests

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not reintroduce direct desktop-side attach/bootstrap mutation.
- Do not introduce hidden defaults for any identity field.
- Do not weaken the shipped Phase 10C / 10D / 10E refusal behavior.
- Preserve the canonical-artifact-first model and avoid a second desktop-only
  state plane.

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
