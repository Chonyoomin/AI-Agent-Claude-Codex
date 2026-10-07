# Claude Code Task

## Phase
Fix Phase C6 - Plain-English Run Console

## Objective
Add a plain-English desktop Run Console that lets a non-technical operator
understand where the agent is, what it just did, what it is waiting for, and
what to do next without opening repository files or reading terminal output.

## Context
Fix Phase C1 defines the guided desktop section order:
Project, PRD, Run Mode, Run, Progress. Fix Phase C2 delivered the Project
surface, C3 delivered PRD intake, C4 delivered the Run Mode selector, and C5
delivered the single prerequisite-gated Start/Stop control. Read
docs/desktop-first-run-setup-contract.md and inspect the actual repository state
before editing. Reuse the shipped canonical mirrors, status summaries, audit
evidence, and existing desktop refresh cadence. Do not rely on prior chat
context.

## Required work
- add a visible Progress/Run Console section after Run
- show the current phase and sub-phase in plain English
- show the current task or objective in plain English
- show the current run status with a bounded plain-English state
- show the latest meaningful activity and the next expected step
- show clear waiting, blocked, approval-required, or recovery guidance
- prefer canonical loop-state and shipped dashboard/status helpers as the source
  of truth; label computed interpretations as advisory
- keep technical detail available only through the existing Advanced surface
- refresh only through the shipped desktop polling cadence; do not add a new
  watcher, timer, thread, progress cache, or event-log store
- add focused tests for canonical mirror mapping, plain-English state mapping,
  stale/missing artifact behavior, section order, redaction, and no-mutation
  invariants
- update README.md and .agent-loop/claude-summary.md with the shipped behavior
  and validation performed

## Constraints
- Follow CLAUDE.md.
- Do not modify AGENTS.md or CLAUDE.md.
- Do not add Start/Stop behavior, review actions, approval actions, automatic
  continuation, token polling, or phase advancement; those belong to C5,
  C7-C8, or later runtime slices.
- Do not create a hidden progress store, UI-only JSON/database/cache, pending
  transitions queue, or alternate orchestrator.
- Do not write canonical artifacts from the console.
- Do not auto-fill operator identity or infer missing state from OS/browser
  state.
- Preserve existing approval, strict-mode, recovery, and human-gate semantics.
- Do not add Git automation, network endpoints, or unrelated refactors.

## Required output
After implementation, write .agent-loop/claude-summary.md using the required
Claude Implementation Summary format and include the validation you ran.

