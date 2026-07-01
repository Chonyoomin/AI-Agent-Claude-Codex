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

Phase 10X - Autonomous Run Console And Completion Ledger

## Phase Status

Phase 10W is complete and approved to advance. Phase 10X is now active as the next mainline slice focused on surfacing an auditable autonomous run console and completion ledger in the desktop app.

## Active Task

Implement Phase 10X for the agent loop. This slice should add the first desktop autonomous run console and completion ledger so PRD-to-completion mode exposes the active step, pending work, blocked or deferred work, fix-cycle state, and completion progress without introducing a hidden second control plane.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10X as active
- `.agent-loop/phase-plan.md` records Phase 10W as closed history and contains a `## Phase 10X - Autonomous Run Console And Completion Ledger` section with concrete objective, done criteria, and exclusions
- the repository adds the first desktop-facing autonomous run console and completion-ledger surface for the shipped PRD-to-completion workflow
- the implementation defines how the active step, pending steps, blocked or deferred work, fix-cycle state, and completion progress are surfaced from canonical artifacts without creating a hidden second source of truth
- the implementation preserves approval gating, evidence review, external-workspace boundaries, desktop/UI boundaries, MCP/RAG boundaries, and the Phase 10I library-callable cap instead of introducing hidden automation, silent mutation, or a parallel state store
- focused validation proves the run-console path is bounded, auditable, and desktop-visible without widening into capacity auto-resume, concurrency, packaging, or hidden orchestration
- `README.md` reflects that Phase 10X is active and that the autonomous run console / completion ledger are now the implementation focus

## Next-Phase Gate

Do not widen the autonomous-run console beyond a bounded desktop visibility slice until:

- Phase 10X receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the first autonomous run console / completion ledger slice
- any capacity auto-resume, packaging, policy-pack, model-selection, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any capacity auto-resume, token-refresh detection, or retry/backoff automation beyond passive visibility
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any concurrent Codex/Claude overlap execution, model-policy extensibility work, or hidden orchestration added under the banner of the run console
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 capacity recovery, model selection, packaging, policy-pack, or concurrency work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the run-console surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
