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

Phase 10L - Controlled Concurrent Operation Contract

## Phase Status

Phase 10K is complete. Phase 10L is now active as the next mainline slice focused on defining the overlap rules and safety boundaries required before any concurrent Codex/Claude work is allowed.

## Active Task

Define Phase 10L for the agent loop. This slice should specify the overlap rules, ownership boundaries, stale-artifact detection, review/fix invalidation rules, and recovery behavior required before any concurrent Codex/Claude work is allowed.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10L as active
- `.agent-loop/phase-plan.md` records Phase 10K as closed history and contains a `## Phase 10L - Controlled Concurrent Operation Contract` section with concrete objective, done criteria, and exclusions
- the repository gains a documentation-first contract defining when concurrent Codex/Claude work is allowed, refused, invalidated, or requires recovery
- the contract defines overlap rules, ownership boundaries, stale-artifact detection, review/fix invalidation rules, and recovery behavior without permitting concurrent runtime execution yet
- the contract preserves the existing CLI-first workflow, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target ownership boundaries, and the Phase 4C activator + `APPROVED_FOR_ACTIVATION` gate
- focused validation proves the concurrency contract is bounded, internally consistent with Phase 10G through 10K, and does not widen into runtime overlap execution, MCP, or autonomy work

## Next-Phase Gate

Do not allow concurrent Codex/Claude work until:

- Phase 10L receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the controlled-concurrency contract
- any runtime overlap detection or concurrent-work execution is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- overlap detection runtime or concurrent execution beyond the contract itself
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch, concurrent Codex/Claude overlap execution, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 concurrency runtime, MCP, RAG, GitHub, or policy-pack work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the concurrency contract surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
