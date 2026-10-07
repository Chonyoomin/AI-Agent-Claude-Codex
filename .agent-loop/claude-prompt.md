# Claude Code Task

## Phase
Fix Phase C5 - Start / Stop Agent Control Surface

## Objective
Add one clear primary desktop control that starts the workflow when all
prerequisites are satisfied and changes to a Stop Agent or pause surface while
the workflow is active. Keep all existing runtime gates and canonical
artifact ownership intact.

## Context
Fix Phase C1 defines the guided desktop order:
Project, PRD, Run Mode, Run, Progress. Fix Phase C2 delivered the Project
surface, C3 delivered PRD intake, and C4 delivered the plain-English Run Mode
selector with canonical approval-mode persistence. Read
docs/desktop-first-run-setup-contract.md and inspect the actual repository state
before editing. Do not rely on prior chat context.

## Required work
- add one primary visible Start Agent control in the Run section after Run Mode
- enable it only when the existing Project, PRD, and Run Mode prerequisites are
  satisfied
- provide plain-English disabled-state guidance identifying the missing
  prerequisite
- route start through the existing canonical runtime/library owner; do not
  duplicate orchestration or create a second controller
- when the workflow is active, change the primary control to Stop Agent or a
  clearly labeled pause/stop surface
- route stop through an existing safe halt/stop owner and preserve canonical
  loop-state evidence
- define bounded plain-English states for unavailable, ready, starting,
  active, stopping, and refused/blocked
- preserve the C1 section order and keep raw runtime vocabulary behind Advanced
- add focused tests for prerequisite gating, start dispatch, active-control
  switching, stop dispatch, refusal behavior, audit output, and no-background
  automation invariants
- update README.md and .agent-loop/claude-summary.md with the shipped behavior
  and validation performed

## Constraints
- Follow CLAUDE.md.
- Do not modify AGENTS.md or CLAUDE.md.
- Do not invent approval semantics or widen autonomy.
- Do not add a progress console, automatic continuation, token polling, or
  background watcher; those belong to C6-C8 and existing cadence contracts.
- Do not create a UI-only settings/state file, recent-action cache, or second
  orchestration plane.
- Start and stop must be explicit operator gestures.
- Do not bypass human approval, strict-mode, review, token, or recovery gates.
- Preserve existing canonical state and audit ownership.
- Do not add Git automation, network endpoints, or unrelated refactors.

## Required output
After implementation, write .agent-loop/claude-summary.md using the required
Claude Implementation Summary format and include the validation you ran.

