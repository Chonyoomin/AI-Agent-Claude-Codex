# Claude Code Task

## Phase
Fix Phase C4 - Run Mode Selector

## Objective
Add a plain-English desktop run-mode selector that lets a non-technical
operator choose among the already-shipped runtime approval modes without
exposing internal jargon or creating a second UI-only settings plane.

## Context
Fix Phase C1 defines the guided desktop section order:
Project, PRD, Run Mode, Run, Progress. Fix Phase C2 delivered the Project
folder surface and C3 delivered the PRD picker, state mapping, and bounded
preview. Read docs/desktop-first-run-setup-contract.md, inspect the actual
repository state, and follow the shipped Phase 5A approval-mode contract and
Phase 10Q run-profile behavior. Do not rely on prior chat context.

## Required work
- add the visible default Run Mode section after PRD and before Run
- present plain-English choices such as Guided, Review Each Phase, and More
  Autonomous, with one-sentence explanations
- map each choice to the existing shipped runtime mode/profile values
- preserve canonical artifact ownership and existing approval gates
- make the selected mode observable through the existing canonical runtime
  configuration/state path rather than a UI-only settings file
- define clear initial, selected, and unavailable/refused states
- preserve cancellation and invalid-selection behavior without changing runtime
  semantics
- keep raw approval-mode names, CLI commands, canonical paths, and raw state
  vocabulary behind the existing Advanced surface
- add focused tests for section order, option copy, mapping, persistence/source
  of truth, refusal behavior, and no-automation invariants
- update README.md and .agent-loop/claude-summary.md with the shipped behavior
  and validation performed

## Constraints
- Follow CLAUDE.md.
- Do not modify AGENTS.md or CLAUDE.md.
- Do not invent new approval semantics or widen autonomy.
- Do not add Start/Stop controls, run-console behavior, automatic execution,
  or progress rendering; those belong to C5-C8.
- Do not create a UI-only settings file, preference cache, recent-mode list,
  hidden session state, background watcher, or second orchestration plane.
- Selecting a mode must not auto-start, attach, bootstrap, advance, or dispatch
  the agent.
- Preserve explicit operator gestures, shipped polling/audit cadence, and
  existing human approval gates.
- Do not add Git automation, network endpoints, or unrelated refactors.

## Required output
After implementation, write .agent-loop/claude-summary.md using the required
Claude Implementation Summary format and include the validation you ran.

