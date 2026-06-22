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

Phase 10E - External Workspace Bootstrap Runtime Initial Slice

## Phase Status

Phase 10D (External Workspace Attach/Detach Runtime Initial Slice) is closed after Codex review approval and human progression. Phase 10E is now active as the next implementation slice under Phase 10. This sub-phase should implement the explicit bootstrap runtime for empty external targets under the approved Phase 10C contract, while preserving the shipped controller-vs-target ownership boundary and without yet adding target-side cycle dispatch or external UI control.

## Active Task

Implement the External Workspace Bootstrap Runtime Initial Slice for the agent loop. This slice should add the explicit bootstrap path for `empty_target` external workspaces under the approved Phase 10C contract, write only the allowed target-side canonical artifact set atomically, update the controller-owned attach record's bootstrap-state fields consistently, and refuse partial or malformed target states without widening into target-side cycle dispatch or external UI behavior.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10E as active
- `.agent-loop/phase-plan.md` records Phase 10D as closed history and contains a `## Phase 10E - External Workspace Bootstrap Runtime Initial Slice` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository implements the explicit bootstrap runtime path for `empty_target` external workspaces under the approved Phase 10C contract instead of leaving bootstrap documentation-only
- the runtime writes exactly the five allowed target-side canonical bootstrap artifacts atomically or rolls back fully on failure, and never bootstraps by copying controller canonical artifacts
- the runtime updates the controller-owned `.agent-loop/external-target.json` attach record's `bootstrap_state` extension fields consistently with the approved Phase 10C schema, including bootstrap signal/version, artifacts written, initial loop-state status, and bootstrap audit line handling
- the runtime enforces the approved no-opt-in / partial-target / malformed-target / missing-input / operator-identity / atomicity refusal paths without widening the planner/activation boundary
- the runtime preserves the shipped artifact/source-of-truth boundary: controller-owned attach metadata remains controller-owned, target-side canonical artifacts remain target-owned, bootstrap does not silently activate a phase, and target-side first activation still requires the shipped Phase 4C activator plus `APPROVED_FOR_ACTIVATION`
- the runtime preserves the shipped CLI-first workflow, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- focused validation proves the bootstrap runtime is bounded, consistent with the approved contracts, and reflected accurately in the repo planning/docs/runtime surfaces
- `README.md` reflects that Phase 10E is active and that the bootstrap runtime slice is now the implementation focus

## Next-Phase Gate

Do not begin target-side cycle dispatch or external UI/runtime expansion after Phase 10E until:

- this Phase 10E slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the bootstrap runtime as concrete enough to build the next external-workspace slices on
- Codex updates the canonical phase/task artifacts to activate the next Phase 10 sub-phase rather than treating roadmap bullets as implementation authority on their own

## Out Of Scope For Current Phase

- any target-side cycle dispatch implementation beyond the bounded bootstrap hooks required to leave a target at `awaiting_first_activation` (Phase 10F)
- any attach/detach contract rewrite or broader external UI, dashboard, or run-control implementation (Phase 10G and later)
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
