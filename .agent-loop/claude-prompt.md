# Claude Code Task

## Phase
Phase 10AI - Orchestration Graph And Performance View Initial Slice

## Objective
Implement the first bounded desktop orchestration graph and performance view so
the operator can see where the loop currently is, what just completed, what is
waiting next, and where the run is blocked or halted.

## Context
`Phase 10AI` is now the active mainline slice. `Phase 10AH` defined the
contract for a bounded desktop orchestration-visualization surface: closed
visualization vocabulary, canonical-mirror-vs-advisory rules, closed node/edge/
status model, refusal boundaries, poll-cadence limits, and source-of-truth
preservation. This slice is the first runtime that materializes that contract
inside the shipped desktop app.

The implementation must stay bounded. It should give the operator a real visual
or icon-based orchestration view, but it must not widen into a second
controller, hidden state store, background watcher, autonomous progression path,
or canonical write surface.

Work against the actual repo state. Do not rely on prior chat context.

## Required work
- implement the first bounded desktop orchestration graph/performance view in
  the shipped desktop app
- surface at least the closed Phase 10AH visualization vocabulary in a runtime
  form that makes current phase/sub-phase/task, loop-state status, review/fix
  branch, blocked/halted state, and progress legible to the operator
- preserve the canonical mirror vs advisory derived-state distinction from the
  Phase 10AH contract
- preserve the shipped Phase 10L/10M polling cadence and do not introduce a
  background watcher, separate timer loop, or hidden cache/store
- keep the Phase 10I library-callable control cap intact
- add or update focused tests for the new runtime surface
- update `README.md` if the current implementation focus or shipped operator
  behavior changes

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not invent a hidden UI-only graph state store, progress cache, layout
  cache, animation-state store, or second controller.
- Do not implement automatic phase progression or downstream action dispatch
  from the graph view.
- Do not bypass canonical artifact ownership, approval gates, audit boundaries,
  or poll-cadence rules.
- Prefer small, testable, reversible changes.

## Important guardrails
- The visualization runtime is a reporting layer over shipped artifacts, not a
  control plane.
- Every displayed value must remain either a canonical mirror or advisory
  derived state.
- The desktop app must remain canonical-artifact-first and fail-closed on
  boundary violations.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- `tests/test_documentation_consistency.py`
- `README.md`
- `docs/desktop-orchestration-visualization-contract.md`

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
