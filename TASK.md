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

Phase 10C - External Workspace Bootstrap Contract

## Phase Status

Phase 10B (External Target Attach Record Contract) is closed after Codex review approval and human progression. Phase 10C is now active as the next planning slice under Phase 10. This sub-phase should define the bootstrap contract for target-side `.agent-loop` initialization in external-workspace mode, including what may be bootstrapped, what must be refused, and how partial bootstrap remains fail-closed before any bootstrap or attach runtime ships.

## Active Task

Define the External Workspace Bootstrap Contract for the agent loop. This slice should specify how target-side `.agent-loop` initialization may occur in external-workspace mode, which canonical artifacts may be created or refused, what operator decisions and bootstrap states must be recorded, and how later Phase 10D/10E runtime slices depend on that bootstrap contract.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10C as active
- `.agent-loop/phase-plan.md` records Phase 10B as closed history and contains a `## Phase 10C - External Workspace Bootstrap Contract` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository defines, in concrete contract form, how target-side `.agent-loop` initialization may occur in external-workspace mode rather than leaving bootstrap behavior implicit in later runtime/UI code
- the contract explicitly defines what canonical artifact set may be bootstrapped, which partial or malformed target states must be refused, what operator opt-in or approval-sensitive inputs are required, and what bootstrap-state invariants later Phase 10D/10E runtime slices must preserve
- the contract preserves the shipped artifact/source-of-truth boundary: controller-owned attach metadata remains controller-owned, target-side canonical artifacts remain target-owned, and bootstrap does not blur those boundaries or invent advisory state as canonical truth
- the contract preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- focused validation proves the bootstrap contract is concrete, internally consistent, ASCII-safe, and reflected accurately in the repo planning/docs surfaces
- `README.md` reflects that Phase 10C is active and that the bootstrap contract is now the implementation focus

## Next-Phase Gate

Do not begin attach/detach or bootstrap runtime implementation after Phase 10C until:

- this Phase 10C slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the bootstrap contract as concrete enough for implementation
- Codex updates the canonical phase/task artifacts to activate the next Phase 10 sub-phase rather than treating roadmap bullets as implementation authority on their own

## Out Of Scope For Current Phase

- any attach/detach runtime implementation or target-selection runtime behavior (Phase 10D)
- any bootstrap runtime implementation beyond the contract/planning work for this phase (Phase 10E)
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
