# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10AI - Orchestration Graph And Performance View Initial Slice

## Status
Active and ready for implementation.

## Task
Implement the first bounded desktop orchestration graph and performance view so
the operator can see where the loop currently is, what just completed, what is
waiting next, and where the run is blocked or halted.

## Notes

- this is the first runtime slice for the desktop orchestration visualization
  surface inside the desktop app
- the shipped desktop app must remain canonical-artifact-first; this phase must
  not invent a hidden UI-only graph/progress state plane
- preserve the existing phase/task/loop-state ownership, approval, audit, poll-
  cadence, and canonical/advisory attribution boundaries while implementing the
  visualization surface
