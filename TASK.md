# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the Codex and Claude loop carry the project forward phase by phase with review, fixes, and human gating between phases.

## Active Phase

Phase 10 - Future Product Features

## Active Sub-Phase

Phase 10W - RAG Local Index And Retrieval Controls

## Phase Status

Phase 10V is complete and approved to advance. Phase 10W is now active as the next mainline slice focused on adding the first bounded controller-local RAG index and retrieval-control runtime on top of the shipped source-selection contract.

## Active Task

Implement Phase 10W for the agent loop. This slice should add the first bounded local RAG index and retrieval-control runtime so the loop can pull only the most relevant repo-local PRD sections, docs, decisions, standards, and failure/fix patterns into a run without replacing canonical artifacts.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10W as active
- `.agent-loop/phase-plan.md` records Phase 10V as closed history and contains a `## Phase 10W - RAG Local Index And Retrieval Controls` section with concrete objective, done criteria, and exclusions
- the repository adds the first bounded local indexing/retrieval runtime for the Phase 10V source-selection surface, scoped to controller-local sources only
- the implementation defines how index freshness, retrieval scope, ranking boundaries, and excerpt provenance are exposed without letting retrieved content replace canonical artifacts on disk
- the implementation preserves approval gating, evidence review, external-workspace boundaries, desktop/UI boundaries, MCP boundaries, and the Phase 10I library-callable cap instead of introducing hidden automation, silent mutation, or a parallel state store
- focused validation proves the local index/retrieval path is bounded, auditable, controller-local, and does not widen into remote retrieval, autonomous agent overlap, or hidden background ingestion
- `README.md` reflects that Phase 10W is active and that bounded local RAG index/retrieval controls are now the implementation focus

## Next-Phase Gate

Do not widen the local RAG runtime beyond a bounded controller-local retrieval slice until:

- Phase 10W receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the first bounded local index/retrieval slice
- any remote retrieval, packaging, policy-pack, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any remote/vector database, hosted retrieval service, or network-backed index
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any concurrent Codex/Claude overlap execution, model-policy extensibility work, or hidden orchestration added under the banner of retrieval
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 packaging, remote retrieval, policy-pack, or concurrency work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the local RAG runtime surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
