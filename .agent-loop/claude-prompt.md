# Claude Code Task

## Phase
Fix Phase C1 - First-Run Setup Contract

## Objective
Define the non-technical desktop UX contract for selecting a project folder,
loading a PRD, choosing run behavior, starting/stopping the agent, and
understanding plain-English progress without terminal knowledge.

## Context
`Fix Phase C1` is now the active remediation slice. The goal is to define the
desktop UX contract for a single local operator who dislikes terminals and
wants the shortest path to "choose a folder, load a PRD, choose run behavior,
and run". This slice is contract-first: it should define the bounded UX,
plain-English states, section layout, and advanced-detail hiding rules before
later Fix Phase C runtime slices implement the actual desktop behavior.

The implementation must stay bounded. This slice should define the product
surface clearly, but it must not widen into a second controller, hidden UI-only
state store, background watcher, alternate orchestration path, or canonical
write surface.

Work against the actual repo state. Do not rely on prior chat context.

## Required work
- define the bounded desktop UX contract for the guided single-user workflow:
  choose folder -> choose PRD -> choose run mode -> start agent -> monitor
  progress
- define the default top-level sections of the app at minimum as `Project`,
  `PRD`, `Run Mode`, `Run`, and `Progress`
- define the required plain-English states for setup, ready, running, waiting,
  blocked, approval-required, and complete
- define what technical details are hidden by default versus what appears in an
  optional advanced-details surface
- preserve the canonical-artifact-first model and explicitly refuse any second
  UI-only state plane
- add or update focused tests or documentation-consistency coverage for the new
  contract surface
- update `README.md` if the current implementation focus or shipped operator
  behavior changes

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not invent a hidden UI-only state store, progress cache, or second
  controller.
- Do not implement the runtime folder picker, PRD picker, or run console in
  this contract slice.
- Do not bypass canonical artifact ownership, approval gates, audit boundaries,
  or poll-cadence rules.
- Prefer small, testable, reversible changes.

## Important guardrails
- The desktop app must remain canonical-artifact-first and fail-closed on
  boundary violations.
- The default experience should optimize for one non-technical local operator,
  not for a developer dashboard.
- Internal CLI/runtime terms should be hidden by default and exposed only in
  advanced views where necessary.

## Likely files
- `.agent-loop/phase-plan.md`
- `ROADMAP.md`
- `README.md`
- `TASK.md`
- `.agent-loop/current-task.md`
- `.agent-loop/current-phase.md`

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
