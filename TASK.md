# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated
local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and
  generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the
Codex and Claude loop carry the project forward phase by phase with review,
fixes, and human gating between phases.

## Active Phase

Phase 10 - Future Product Features

## Active Sub-Phase

Phase 10AE - Framework Evaluation Beyond The Native Loop

## Phase Status

Phase 10AD is complete and approved to advance. Phase 10AE is now active as
the next mainline slice focused on evaluating whether framework layers such as
CrewAI, LangGraph, and LangChain add value beyond the shipped native
Codex/Claude loop now that the desktop product surface, MCP/RAG controls,
durable memory, and controlled-concurrency model are stable enough to compare
against.

## Active Task

Implement Phase 10AE for the agent loop. This slice should evaluate framework
options beyond the native loop and define a bounded comparison surface for
CrewAI, LangGraph, LangChain, or similar delegated-role runtimes without
rewriting the shipped Codex/Claude ownership model.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 10 / 10AE as active
- `.agent-loop/phase-plan.md` records Phase 10AD as closed history and
  contains a
  `## Phase 10AE - Framework Evaluation Beyond The Native Loop`
  section with concrete objective, done criteria, and exclusions
- the repository adds a bounded framework-evaluation surface that compares the
  shipped native loop against CrewAI, LangGraph, LangChain, or similar
  delegated-role frameworks using explicit criteria rather than vague
  preference
- the implementation makes clear where a framework could help, where it would
  conflict with shipped ownership and approval boundaries, and what remains
  native-loop-only
- the implementation preserves approval gating, evidence review,
  external-workspace boundaries, existing run-profile semantics, desktop/UI
  boundaries, and the canonical-artifact-first model instead of introducing
  hidden automation, silent mutation, or a parallel hidden orchestrator
- focused validation proves the bounded framework-evaluation surface is
  explicit, auditable, and does not silently change shipped runtime behavior
- `README.md` reflects that Phase 10AE is active and that framework evaluation
  beyond the native loop is now the implementation focus

## Next-Phase Gate

Do not widen into framework-backed runtime integration until:

- Phase 10AE receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the framework-evaluation slice
- any actual framework integration is activated through a later dedicated phase
  instead of being folded into this comparison/evaluation slice

## Out Of Scope For Current Phase

- any full framework migration, silent runtime swap, hidden background
  orchestration, or delegated-worker runtime added under the banner of
  "evaluation"
- any framework-backed path that bypasses the shipped ownership, approval,
  review, or overlap-safety boundaries
- any automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any packaging work, hidden orchestration, or live delegated execution added
  under the banner of this evaluation slice
- any rewrite of current shipped behavior just to make future autonomy work
  easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently
  ship just to simplify the implementation
- collapsing later framework-integration, autonomous orchestration, packaging,
  or external sync work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the
  contract surface
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
