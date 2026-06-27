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

Phase 10L - Desktop App Shell Contract

## Phase Status

Phase 10K is complete. Phase 10L is now active as the next mainline slice focused on defining the first native desktop-app shell for the external UI so the system is easier to operate than through terminal-only workflows.

## Active Task

Define Phase 10L for the agent loop. This slice should specify the desktop-app shell boundaries, controller/target selection flow, polling model, artifact-opening behavior, and the safe bridge between the desktop shell and the shipped Python orchestrator/view surfaces.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10L as active
- `.agent-loop/phase-plan.md` records Phase 10K as closed history and contains a `## Phase 10L - Desktop App Shell Contract` section with concrete objective, done criteria, and exclusions
- the repository gains a documentation-first contract defining the first native desktop-app shell as a thin local operator surface over the shipped Python runtime and canonical artifacts
- the contract defines toolkit/process boundaries, controller-root selection, target attach visibility, refresh/poll behavior, artifact-opening behavior, and explicit refusal cases without shipping the desktop runtime yet
- the contract preserves the existing canonical-artifact-first model, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target ownership boundaries, and the Phase 4C activator + `APPROVED_FOR_ACTIVATION` gate
- focused validation proves the desktop-app contract is bounded, internally consistent with Phase 10G through 10K, and does not widen into hidden orchestration, concurrency runtime, MCP mutation, or autonomy work

## Next-Phase Gate

Do not ship the desktop app runtime until:

- Phase 10L receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the desktop-app shell contract
- any desktop runtime, action bridge, or later controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- desktop runtime implementation beyond the contract itself
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch beyond the shipped attach/bootstrap/runtime surfaces, concurrent Codex/Claude overlap execution, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
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
- adding any project-wide CI suite beyond focused validation for the desktop-app contract surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
