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

Phase 10P - Desktop App Operator Setup And CLI Onboarding

## Phase Status

Phase 10O is complete and approved to advance. Phase 10P is now active as the next mainline slice focused on adding guided desktop setup for controller-root selection, target/work-folder validation, and local Claude/Codex CLI onboarding without weakening the shipped safety and artifact boundaries.

## Active Task

Implement Phase 10P for the agent loop. This slice should add the first guided desktop setup flow for selecting a controller root, validating a target/work folder, configuring local Claude/Codex CLI adapter commands, checking required local-tool availability, and surfacing fail-closed refusal messages when the environment is not ready.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10P as active
- `.agent-loop/phase-plan.md` records Phase 10O as closed history and contains a `## Phase 10P - Desktop App Operator Setup And CLI Onboarding` section with concrete objective, done criteria, and exclusions
- the repository adds the first guided desktop setup flow that lets an operator select a controller root, validate a target/work folder, and configure local Claude/Codex CLI adapter commands without manual artifact editing
- the setup flow checks for required local-tool availability and surfaces explicit, fail-closed refusal messages when the environment is missing required prerequisites or violates shipped safety boundaries
- the setup flow preserves the shipped controller-vs-target boundary, no-auto-fill identity rules, canonical-artifact-first model, and existing CLI/runtime contracts instead of introducing a hidden configuration plane
- focused validation proves the setup flow is bounded, deterministic, and does not widen into PRD intake, MCP runtime execution, RAG runtime, packaging, or controlled-concurrency work

## Next-Phase Gate

Do not widen the desktop app beyond guided setup and CLI onboarding until:

- Phase 10P receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the desktop setup and CLI onboarding slice
- any PRD intake, MCP runtime, RAG runtime, policy-pack, packaging, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any PRD intake flow, MCP runtime integration, tool execution path, or networked tool orchestration beyond the approved Phase 10P setup surface
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch beyond the shipped attach/bootstrap/runtime surfaces, concurrent Codex/Claude overlap execution, MCP runtime implementation, RAG layer, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 PRD intake, MCP runtime, RAG, policy-pack, packaging, or concurrency work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the desktop setup and onboarding surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
