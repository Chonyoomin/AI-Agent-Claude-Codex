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

Phase 10N - Desktop App Action Bridge Initial Slice

## Phase Status

Phase 10M is complete and approved to advance. Phase 10N is now active as the next mainline slice focused on adding bounded desktop actions for attach, inspect, run, and resume flows without violating the desktop shell safety boundaries.

## Active Task

Implement Phase 10N for the agent loop. This slice should add the first bounded desktop action bridge for attach, inspect, run, and resume flows by delegating only to shipped CLI and library surfaces with explicit refusal handling, audit visibility, and no hidden automation or silent mutation path.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10N as active
- `.agent-loop/phase-plan.md` records Phase 10M as closed history and contains a `## Phase 10N - Desktop App Action Bridge Initial Slice` section with concrete objective, done criteria, and exclusions
- the repository adds bounded desktop-side action affordances for attach, inspect, run, and resume flows while preserving the shipped CLI/library surfaces as the source of execution truth
- desktop actions remain explicit, operator-visible, and fail-closed: no hidden background automation, no silent mutating subprocess dispatch, no widened library-callable control surface beyond what the approved phase allows
- the action bridge preserves audit visibility, approval semantics, controller-vs-target ownership boundaries, and the canonical-artifact-first model established by Phases 10L and 10M
- focused validation proves the action bridge is bounded, routes only through approved shipped surfaces, and does not widen into packaging, multi-target sessions, concurrency runtime, MCP, RAG, GitHub, or other later Phase 10 work

## Next-Phase Gate

Do not widen the desktop app beyond the bounded action bridge until:

- Phase 10N receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the bounded desktop action bridge
- any packaging, multi-target behavior, or later controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any unbounded or silent desktop action dispatch beyond the approved Phase 10N bridge surface
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch beyond the shipped attach/bootstrap/runtime surfaces, concurrent Codex/Claude overlap execution, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 packaging, concurrency runtime, MCP, RAG, GitHub, or policy-pack work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the desktop action-bridge surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
