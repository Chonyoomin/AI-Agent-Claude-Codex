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

Phase 10S - MCP Server Selection UX Contract

## Phase Status

Phase 10R is complete and approved to advance. Phase 10S is now active as the next mainline slice focused on defining how the desktop app should present available MCP servers, permission classes, read-only versus deferred-mutating capability labels, per-server safety copy, and operator approval requirements before MCP enablement becomes user-facing.

## Active Task

Implement Phase 10S for the agent loop. This slice should define the MCP server selection UX contract for the desktop app so operators can understand which MCP servers exist, what each server is allowed to do, which permission class or capability category it belongs to, what safety boundaries apply, and what explicit approvals are required before any MCP enablement becomes user-facing.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10S as active
- `.agent-loop/phase-plan.md` records Phase 10R as closed history and contains a `## Phase 10S - MCP Server Selection UX Contract` section with concrete objective, done criteria, and exclusions
- the repository adds a concrete contract, ideally in a dedicated docs artifact, that defines how the desktop app should present available MCP servers, permission classes, read-only versus deferred-mutating capability labels, per-server safety copy, and operator approval requirements before MCP enablement becomes user-facing
- the contract preserves the shipped evidence-review model, approval gating, external-workspace boundaries, desktop/UI boundaries, and canonical-artifact-first model instead of allowing MCP selections to imply runtime behavior that does not yet ship
- the contract distinguishes user-visible MCP selection metadata from still-deferred MCP runtime execution and mutation-capable tool paths, and states what later phases must add before any enablement can become operational
- focused validation or review coverage proves the new MCP selection UX contract matches the actual repo state and does not claim that MCP runtime integration already ships
- `README.md` reflects that Phase 10S is active and that the MCP server selection UX contract is now the implementation focus

## Next-Phase Gate

Do not widen the desktop app beyond the MCP server selection UX contract until:

- Phase 10S receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the MCP server selection UX contract slice
- any actual MCP runtime enablement, RAG runtime, policy-pack, packaging, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any actual MCP runtime integration, tool execution path, or networked tool orchestration beyond the approved Phase 10S contract surface
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch beyond the shipped attach/bootstrap/runtime surfaces, concurrent Codex/Claude overlap execution, MCP runtime implementation, RAG layer, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 MCP runtime, RAG, policy-pack, packaging, or concurrency work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the MCP selection-contract surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
