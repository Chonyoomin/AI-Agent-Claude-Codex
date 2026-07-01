# Claude Code Task

## Phase
Phase 10W - RAG Local Index And Retrieval Controls

## Objective
Implement Phase 10W for the agent loop. This slice should add the first bounded
local RAG index and retrieval-control runtime so the loop can pull only the
most relevant repo-local PRD sections, docs, decisions, standards, and
failure/fix patterns into a run without replacing canonical artifacts.

## Context
Implement the RAG Local Index And Retrieval Controls slice for the agent loop.
This slice should add the first bounded local indexing and retrieval-control
runtime on top of the shipped Phase 10V source-selection contract, while
keeping retrieved content advisory and preserving canonical artifacts as the
source of truth.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10W as active
- `.agent-loop/phase-plan.md` records Phase 10V as closed history and contains
  a `## Phase 10W - RAG Local Index And Retrieval Controls` section with
  concrete objective, done criteria, and exclusions
- add the first bounded local indexing/retrieval runtime for the Phase 10V
  source-selection surface, scoped to controller-local sources only
- define how index freshness, retrieval scope, ranking boundaries, and excerpt
  provenance are exposed without letting retrieved content replace canonical
  artifacts on disk
- preserve approval gating, evidence review, external-workspace boundaries,
  desktop/UI boundaries, MCP boundaries, and the Phase 10I library-callable cap
  instead of introducing hidden automation, silent mutation, or a parallel
  state store
- add focused validation proving the local index/retrieval path is bounded,
  auditable, controller-local, and does not widen into remote retrieval,
  autonomous agent overlap, or hidden background ingestion
- `README.md` reflects that Phase 10W is active and that bounded local RAG
  index/retrieval controls are now the implementation focus

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
- no remote/vector database, hosted retrieval service, or network-backed index
- no GitHub, policy-pack, packaging, system-tray, or controlled-concurrency
  runtime work
- no hidden daemon, crawler, or watcher farm outside the shipped Python runtime
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
