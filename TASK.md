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

Phase 10B - External Target Attach Record Contract

## Phase Status

Phase 10A (External Workspace Controller Contract) is closed after Codex review approval and human progression. Phase 10B is now active as the next planning slice under Phase 10. This sub-phase should define the controller-owned attach-record contract for future external-workspace mode, including schema, canonicalized-path metadata, audit requirements, and refusal-sensitive fields, before any attach/detach runtime ships.

## Active Task

Define the External Target Attach Record Contract for the agent loop. This slice should specify the controller-owned attach-record schema, what target-selection metadata it must persist, how canonicalized target paths and controller identity are represented, what audit/refusal fields are required, and how later Phase 10 attach/detach runtime slices depend on that record.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10B as active
- `.agent-loop/phase-plan.md` records Phase 10A as closed history and contains a `## Phase 10B - External Target Attach Record Contract` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository defines, in concrete contract form, the controller-owned attach-record schema for external-workspace mode rather than leaving attach metadata implicit in UI/runtime state
- the contract explicitly defines required attach-record fields such as canonicalized target path, controller identity, signal/version marker, operator/audit fields, mode-selection metadata, stale-attach detection inputs, and refusal-sensitive invariants before any Phase 10D attach runtime work begins
- the contract preserves the shipped artifact/source-of-truth boundary: the attach record remains controller-owned, target-side canonical artifacts remain target-owned, and future UI/runtime surfaces remain advisory unless explicitly promoted by contract
- the contract preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- focused validation proves the attach-record contract is concrete, internally consistent, ASCII-safe, and reflected accurately in the repo planning/docs surfaces
- `README.md` reflects that Phase 10B is active and that the attach-record contract is now the implementation focus

## Next-Phase Gate

Do not begin attach/detach runtime implementation after Phase 10B until:

- this Phase 10B slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the attach-record contract as concrete enough for implementation
- Codex updates the canonical phase/task artifacts to activate the next Phase 10 sub-phase rather than treating roadmap bullets as implementation authority on their own

## Out Of Scope For Current Phase

- any attach/detach runtime implementation or target-selection runtime behavior (Phase 10D)
- any bootstrap contract/runtime work beyond what is strictly necessary to define attach-record dependencies (Phase 10C and 10E)
- any external UI, dashboard, or run-control implementation (Phase 10G and later)
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
