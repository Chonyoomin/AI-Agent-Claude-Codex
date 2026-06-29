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

Phase 10T - MCP Read-Only Assistance In Desktop App

## Phase Status

Phase 10S is complete and approved to advance. Phase 10T is now active as the next mainline slice focused on implementing the first user-selectable MCP read-only assistance surfaces in the desktop app without mutating canonical artifacts or bypassing evidence review.

## Active Task

Implement Phase 10T for the agent loop. This slice should add the first user-selectable MCP read-only assistance surfaces in the desktop app so operators can enable approved context-gathering tools from the desktop app without mutating canonical artifacts or bypassing evidence review.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10T as active
- `.agent-loop/phase-plan.md` records Phase 10S as closed history and contains a `## Phase 10T - MCP Read-Only Assistance In Desktop App` section with concrete objective, done criteria, and exclusions
- the repository adds the first user-selectable MCP read-only assistance surfaces so operators can enable approved context-gathering tools from the desktop app without mutating canonical artifacts or bypassing evidence review
- the implementation follows the shipped Phase 10O MCP integration contract and Phase 10S MCP server selection UX contract, preserving the read-only versus deferred-mutating boundary and the canonical-artifact-first model
- the implementation preserves approval gating, evidence review, external-workspace boundaries, desktop/UI boundaries, and the Phase 10I library-callable cap instead of introducing hidden automation or a parallel state store
- focused validation proves the first MCP read-only assistance surface is bounded, auditable, and does not widen into mutation-capable MCP actions, RAG runtime, packaging, or controlled-concurrency work
- `README.md` reflects that Phase 10T is active and that MCP read-only assistance in the desktop app is now the implementation focus

## Next-Phase Gate

Do not widen the desktop app beyond MCP read-only assistance until:

- Phase 10T receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the MCP read-only assistance slice
- any mutation-capable MCP actions, RAG runtime, policy-pack, packaging, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any mutation-capable MCP action, tool execution path outside the approved read-only categories, or networked tool orchestration beyond the approved Phase 10T surface
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch beyond the shipped attach/bootstrap/runtime surfaces, concurrent Codex/Claude overlap execution, mutation-capable MCP runtime, RAG layer, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 mutation-capable MCP, RAG, policy-pack, packaging, or concurrency work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the MCP read-only assistance surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
