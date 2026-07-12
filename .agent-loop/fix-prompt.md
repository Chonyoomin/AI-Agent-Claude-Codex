# Claude Code Fix Task

## Phase
Fix Phase B2 - Desktop Bootstrap Form And Validation

## Objective
Resolve the last stale-copy issue in the active Fix Phase B2 desktop bootstrap
dialog so the shipped code path no longer contains a leftover B1 phase label.

## Context
The latest Codex review found one residual issue after the B2 documentation and
dialog-copy fix:

1. the comment above the bootstrap dialog's `guidance_output = tk.Text(...)`
   widget still says `Fix Phase B1 fix cycle` even though the active dialog
   path is now described elsewhere as Fix Phase B2

Treat `.agent-loop/codex-review.md` as the source of truth for this fix cycle.

## Required fixes
- update the stale comment above the active bootstrap dialog guidance Text
  widget so it reflects the current Fix Phase B2 slice
- keep the fix narrowly scoped to this local stale-copy cleanup

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not reintroduce direct desktop-side dispatch to
  `attach_external_target(...)`.
- Preserve the current B2 validation behavior and the UX-only no-dispatch
  boundary.

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
