# Claude Code Task

## Phase
Fix Phase C3 - PRD Intake UX

## Objective
Implement the guided desktop PRD intake step: let a non-technical operator
choose a PRD file, show clear missing/invalid/ready states, and preview the
selected PRD in a bounded plain-English setup surface.

## Context
Fix Phase C1 established the first-run contract and Fix Phase C2 delivered
the Project folder-picker/classification surface. Read
docs/desktop-first-run-setup-contract.md and inspect the actual repository
state before editing. Do not rely on prior chat context.

## Required work
- add an OS-native PRD file-picker action to the default desktop setup flow
- reuse the shipped PRD intake validation/helpers and canonical artifact
  boundaries; do not duplicate PRD parsing or invent a second intake runtime
- surface plain-English states for:
  no PRD selected, project selected but PRD missing, invalid/empty PRD,
  and PRD ready
- show a bounded preview that identifies the selected PRD without dumping the
  entire file into the default surface
- provide actionable copy for missing, invalid, and ready states
- preserve the C1 section order: Project, PRD, Run Mode, Run, Progress
- keep raw CLI names, canonical paths, parser/refusal tokens, and full raw PRD
  contents behind the existing Advanced surface
- add focused tests for picker wiring, validation mapping, bounded preview,
  refusal behavior, and source-of-truth invariants
- update README.md and .agent-loop/claude-summary.md with the shipped behavior
  and validation performed

## Constraints
- Follow CLAUDE.md.
- Do not modify AGENTS.md or CLAUDE.md.
- Do not add run-mode selection, Start/Stop controls, run-console behavior,
  automatic execution, or PRD decomposition redesign; those belong to C4-C8.
- Do not persist a hidden PRD cache, staging file, recent-file list, or
  UI-only settings/state plane.
- Selecting a PRD must not auto-start, attach, bootstrap, or advance the agent.
- Preserve explicit operator gestures and shipped polling/audit cadence.
- Do not add Git automation, background watchers, or network endpoints.

## Required output
After implementation, write .agent-loop/claude-summary.md using the required
Claude Implementation Summary format and include the validation you ran.