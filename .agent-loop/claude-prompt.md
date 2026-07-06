# Claude Code Task

## Phase
Phase 10AE - Framework Evaluation Beyond The Native Loop

## Objective
Implement Phase 10AE for the agent loop. This slice should evaluate framework
options beyond the native loop and define a bounded comparison surface for
CrewAI, LangGraph, LangChain, or similar delegated-role runtimes without
rewriting the shipped Codex/Claude ownership model.

## Context
Implement the Framework Evaluation Beyond The Native Loop slice for the agent
loop. This is the next mainline step after the shipped Phase 10AD bounded
concurrent-work slice. The goal is to evaluate whether framework layers such as
CrewAI, LangGraph, and LangChain add value beyond the shipped native
Codex/Claude loop now that the desktop surface, MCP/RAG controls, durable
memory, and controlled-concurrency model are stable enough to compare against.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AE as active
- `.agent-loop/phase-plan.md` records Phase 10AD as closed history and
  contains a `## Phase 10AE - Framework Evaluation Beyond The Native Loop`
  section with concrete objective, done criteria, and exclusions
- implement a bounded framework-evaluation surface that compares the shipped
  native loop against CrewAI, LangGraph, LangChain, or similar delegated-role
  frameworks using explicit criteria rather than vague preference
- make clear where a framework could help, where it would conflict with shipped
  ownership, approval, review, desktop, and canonical-artifact boundaries, and
  what remains native-loop-only
- preserve approval gating, evidence review, external-workspace boundaries,
  run-profile semantics, desktop/UI boundaries, loop-state source-of-truth
  rules, and the canonical-artifact-first model
- add focused validation proving the framework-evaluation surface is explicit,
  auditable, bounded, and does not silently change shipped runtime behavior
- `README.md` reflects that Phase 10AE is active and that framework evaluation
  beyond the native loop is now the implementation focus

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
- no full framework migration, silent runtime swap, hidden background
  orchestration, or delegated-worker runtime added under the banner of
  evaluation
- no framework-backed path that bypasses the shipped ownership, approval,
  review, overlap-safety, or canonical-artifact boundaries
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no packaging work, hidden orchestration, or live delegated execution added
  under the banner of this evaluation slice
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
