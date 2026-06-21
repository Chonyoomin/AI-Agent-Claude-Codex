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

Phase 10A - External Workspace Controller Contract

## Phase Status

Phase 9G (Final Human Acceptance And Polish Gate) is closed after Codex review approval and human progression. Phase 10A is now active as the first planning slice under Phase 10. This sub-phase should define how the controller repo can safely target an external workspace or repository, with explicit controller-vs-target ownership boundaries and refusal rules, before any external bootstrap, UI, or concurrent-agent implementation is attempted.

## Active Task

Define the External Workspace Controller Contract for the agent loop. This slice should specify how the controller repo can target a different workspace or repository safely, what remains controller-owned versus target-owned, where `.agent-loop` artifacts live, how attach/bootstrap and refusal behavior must work, and which later Phase 10 slices implement those behaviors.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10A as active
- `.agent-loop/phase-plan.md` records Phase 9G as closed history and contains a `## Phase 10A - External Workspace Controller Contract` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository defines, in concrete contract form, how a controller repo may safely target an external workspace or repository without collapsing controller-owned and target-owned responsibilities
- the contract explicitly defines controller-owned versus target-owned artifacts, path boundaries, attach/bootstrap expectations, refusal behavior, and approval gates before any Phase 10B implementation work begins
- the contract preserves the shipped artifact/source-of-truth boundary: canonical repo artifacts remain authoritative, and any future external-workspace metadata or UI surfaces remain advisory unless explicitly promoted by contract
- the contract preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- focused validation proves the new contract is concrete, internally consistent, ASCII-safe, and reflected accurately in the repo planning/docs surfaces
- `README.md` reflects that Phase 10A is active and that the external-workspace controller contract is now the implementation focus

## Next-Phase Gate

Do not begin external-workspace implementation after Phase 10A until:

- this Phase 10A slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the controller-vs-target contract as concrete enough for implementation
- Codex updates the canonical phase/task artifacts to activate the next Phase 10 sub-phase rather than treating roadmap bullets as implementation authority on their own

## Out Of Scope For Current Phase

- any external workspace bootstrap, attach flow, or target selection runtime (Phase 10B)
- any external UI, dashboard, or run-control implementation (Phase 10C and later)
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
