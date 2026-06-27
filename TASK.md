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

Phase 10O - MCP Integration Contract And Safe Tool Boundary

## Phase Status

Phase 10N is complete and approved to advance. Phase 10O is now active as the next mainline slice focused on defining the MCP integration contract, safe tool categories, refusal boundaries, and audit expectations before any MCP-assisted runtime path is allowed.

## Active Task

Implement Phase 10O for the agent loop. This slice should define how MCP server support, scoped tool categories, browser/app inspection hooks, and policy rules may assist planning, implementation, and review without bypassing evidence review, approval gates, or ownership boundaries.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10O as active
- `.agent-loop/phase-plan.md` records Phase 10N as closed history and contains a `## Phase 10O - MCP Integration Contract And Safe Tool Boundary` section with concrete objective, done criteria, and exclusions
- the repository adds a concrete MCP integration contract, ideally in a dedicated docs artifact, that defines safe tool categories, ownership boundaries, refusal rules, audit expectations, and source-of-truth preservation before any MCP runtime path ships
- the contract preserves the shipped evidence-review model, approval gating, external-workspace boundaries, desktop/UI boundaries, and canonical-artifact-first model instead of allowing MCP tools to bypass them
- the contract distinguishes read-only assistance from still-deferred mutation-capable MCP actions and defines what later phases must add before any non-read-only MCP-assisted runtime behavior is allowed
- focused validation or review coverage proves the new MCP contract/docs match the actual repo state and do not claim that MCP runtime integration already ships

## Next-Phase Gate

Do not widen the loop into MCP runtime execution beyond the approved contract until:

- Phase 10O receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the MCP integration contract
- any actual MCP runtime, mutation-capable tool usage, RAG, GitHub, policy-pack, packaging, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any actual MCP runtime integration, tool execution path, or networked tool orchestration beyond the approved Phase 10O contract surface
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch beyond the shipped attach/bootstrap/runtime surfaces, concurrent Codex/Claude overlap execution, MCP runtime implementation, RAG layer, GitHub integration, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 MCP runtime, RAG, GitHub, policy-pack, packaging, or concurrency work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the MCP-contract documentation surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
