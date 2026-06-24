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

Phase 10G - Minimal External UI Contract

## Phase Status

Phase 10F (External Target Validation And Refusal Hardening) is closed after Codex review approval and human progression. Phase 10G is now active as the next planning/contract slice under Phase 10. This sub-phase should define the first external operator UI surface, its advisory-vs-canonical boundaries, and how it may interact with the shipped CLI-first workflow without yet implementing a UI runtime or broadening into a new control plane.

## Active Task

Define the Minimal External UI Contract for the agent loop. This slice should specify the first external operator UI surface for external-workspace mode: which canonical artifacts it may read, which actions remain CLI-only, how advisory UI state must defer to repo artifacts on disk, and what safety/approval boundaries must remain intact before any UI runtime is implemented.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10G as active
- `.agent-loop/phase-plan.md` records Phase 10F as closed history and contains a `## Phase 10G - Minimal External UI Contract` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository gains a documentation-first contract for the first external operator UI surface instead of jumping directly to implementation
- the contract defines which canonical controller-side and target-side artifacts a minimal external UI may read, and which UI-visible values are advisory mirrors rather than sources of truth
- the contract preserves the shipped CLI-first workflow by explicitly stating which actions remain CLI-only and must not be silently triggered from a UI surface
- the contract preserves the shipped artifact/source-of-truth boundary: repo artifacts on disk remain authoritative over any UI cache, session state, or rendered status summary
- the contract preserves the shipped approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target ownership boundaries, and the Phase 4C activator + `APPROVED_FOR_ACTIVATION` activation gate
- focused validation proves the new UI contract is bounded, internally consistent with the approved external-workspace slices, and reflected accurately in planning/docs surfaces
- `README.md` reflects that Phase 10G is active and that the minimal external UI contract is now the planning focus

## Next-Phase Gate

Do not begin external UI implementation or broader control-plane expansion after Phase 10G until:

- this Phase 10G slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the minimal external UI contract as concrete enough to build the first external UI implementation slice on
- Codex updates the canonical phase/task artifacts to activate the next Phase 10 sub-phase rather than treating roadmap bullets as implementation authority on their own

## Out Of Scope For Current Phase

- any external UI runtime, dashboard, or run-control implementation beyond the documentation-first contract for the minimal surface (Phase 10H and later)
- any target-side cycle dispatch, autonomous multi-target orchestration, or external control plane that can mutate canonical artifacts outside the shipped CLI surfaces
- any concurrent Codex/Claude execution implementation, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation, or that replaces canonical prompt/review/checkpoint artifacts with transient runtime-only state
- any rewrite of current shipped behavior just to make future external-workspace support easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing future Phase 10 implementation work into this planning slice
- MCP support, external UI, concurrent-agent operation, or implementation of end-to-end fully autonomous PRD-to-product execution (future phases)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite to the repository beyond focused retry/re-probe coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
