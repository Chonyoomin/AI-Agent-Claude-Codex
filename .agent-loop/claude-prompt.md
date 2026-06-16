# Claude Code Task

## Phase
Phase 9B - PRD Intake And Decomposition

## Objective
Implement the PRD Intake And Decomposition slice for the agent loop. This slice should accept a structured PRD or looser product brief, normalize it into a canonical autonomous-run intake surface, and decompose it into bounded internal phases, tasks, risks, and acceptance criteria while preserving the existing planner, activation, approval, and artifact-truth boundaries.

## Context
Implement the PRD Intake And Decomposition slice for the agent loop. This slice
should accept a structured PRD or looser product brief, normalize it into a
canonical autonomous-run intake surface, and decompose it into bounded
internal phases, tasks, risks, and acceptance criteria while preserving the
existing planner, activation, approval, and artifact-truth boundaries.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 9 / 9B as active
- `.agent-loop/phase-plan.md` records Phase 9A as closed history and contains a
  `## Phase 9B - PRD Intake And Decomposition` section with concrete
  objective, done criteria, and exclusions
- the repository ships a canonical PRD-intake and decomposition surface that
  accepts both structured PRDs and looser product briefs without requiring
  prior chat context
- the intake/decomposition layer emits bounded internal phases, tasks, risks,
  and acceptance criteria that fit the shipped phase/task model rather than
  inventing a parallel control plane
- valid decomposition output remains auditable from repo artifacts and preserves
  the shipped CLI-first workflow, planner/activation boundaries, approval
  semantics, halt/refusal vocabulary, checkpoint/resume behavior, and
  repo-artifact source-of-truth model
- malformed or underspecified PRD input is refused cleanly rather than
  producing vague or unbounded decomposition output
- focused validation covers valid input normalization, bounded decomposition
  output, and refusal behavior on malformed or underspecified intake
- `README.md` reflects that Phase 9B is active and that PRD intake /
  decomposition are now the implementation focus

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no orchestrator-driven prompt handoff, autonomous review/fix execution,
  automatic next-phase activation, long-run completion heuristics,
  capacity-halt re-probe, or final acceptance automation (Phases 9C-9G)
- no replacement of the shipped Phase 4 planner / activator boundary with an
  unreviewable parallel control plane
- no regression of the shipped Phase 5 review, strict, bounded autonomous,
  reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer behavior
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no MCP support, external UI, or concurrent-agent operation in this slice
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
