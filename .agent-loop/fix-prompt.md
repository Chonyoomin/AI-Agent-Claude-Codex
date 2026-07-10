# Claude Code Fix Task

## Phase
Fix Phase B2 - Desktop Bootstrap Form And Validation

## Objective
Resolve the remaining repo-alignment and stale-copy issues in the current Fix
Phase B2 slice so the documentation, consistency harness, and desktop bootstrap
dialog all reflect the same active-phase and validator contract.

## Context
The current B2 implementation correctly adds the bootstrap-form classifier and
validation behavior, but the latest Codex review found two residual issues:

1. README still presents `Phase 10AE` as the active implementation focus even
   though the canonical task artifacts now mark `Fix Phase B2` as active, and
   the test update works around that contradiction by allowing two different
   active-phase anchors in the consistency harness
2. the active bootstrap-dialog comment/title still contain B1-era wording,
   including "presence contract only" and `Fix Phase B1`, which no longer match
   the shipped B2 validator behavior

Treat `.agent-loop/codex-review.md` as the source of truth for this fix cycle.

## Required fixes
- update README so the active-phase/status text reflects `Fix Phase B2` rather
  than `Phase 10AE`, and make the desktop bootstrap form/validation slice the
  current documented implementation focus
- realign `tests/test_documentation_consistency.py` so it enforces one
  canonical active-phase story instead of tolerating the README/task-artifact
  mismatch through split anchors
- update the active bootstrap-dialog code-path copy so it reflects B2 rather
  than B1:
  - remove the stale "presence contract only" wording
  - update B1 labels/comments/titles that are now inaccurate in the active B2
    path
- keep the fix narrowly scoped to these findings and directly related tests

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not reintroduce direct desktop-side dispatch to
  `attach_external_target(...)`.
- Do not weaken the shipped `partial_target` / `malformed_target` refusal
  behavior.
- Preserve the canonical-artifact-first model and avoid a second desktop-only
  state plane.

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
