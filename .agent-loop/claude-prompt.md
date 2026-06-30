# Claude Code Task

## Phase
Phase 10V - RAG Source Selection Contract And Desktop UX

## Objective
Implement Phase 10V for the agent loop. This slice should define how repo-local
docs, PRDs, notes, standards, and other knowledge sources can be selected from
the desktop app, how provenance and freshness are exposed to the operator, and
how advisory-only retrieval remains distinct from canonical artifacts.

## Context
Implement the RAG Source Selection Contract And Desktop UX slice for the agent
loop. This slice should define how repo-local docs, PRDs, notes, standards, and
other knowledge sources can be selected from the desktop app, how provenance
and freshness are exposed to the operator, and how advisory-only retrieval
remains distinct from canonical artifacts.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10V as active
- `.agent-loop/phase-plan.md` records Phase 10U as closed history and contains
  a `## Phase 10V - RAG Source Selection Contract And Desktop UX` section with
  concrete objective, done criteria, and exclusions
- add a concrete RAG source-selection contract and desktop UX definition
  covering repo-local docs, PRDs, notes, standards, and other bounded
  knowledge sources
- define how provenance, freshness, and advisory-only retrieval labeling are
  exposed to the operator without turning RAG output into canonical project
  state
- preserve approval gating, evidence review, external-workspace boundaries,
  desktop/UI boundaries, MCP boundaries, and the Phase 10I library-callable cap
  instead of introducing hidden automation, silent mutation, or a parallel
  state store
- add focused validation proving the RAG source-selection contract surface is
  bounded, auditable, and does not widen into RAG indexing/runtime retrieval
  execution, packaging, or controlled-concurrency work
- `README.md` reflects that Phase 10V is active and that RAG source selection
  contract and desktop UX are now the implementation focus

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
- no actual RAG index builder, retrieval runtime, embedding pipeline,
  background watcher, or knowledge-ingestion execution path
- no GitHub, policy-pack, packaging, system-tray, or controlled-concurrency
  runtime work
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no rewrite of current shipped behavior just to make future MCP or autonomy
  work easier
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
