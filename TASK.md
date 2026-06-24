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

Phase 10H - Minimal External UI Read-Only Status Surface

## Phase Status

Phase 10G (Minimal External UI Contract) is closed after Codex review approval and human progression. Phase 10H is now active as the next implementation slice under Phase 10. This sub-phase should implement the first bounded read-only external UI surface that satisfies the approved 10G contract without introducing a mutating control plane, UI-side source of truth, or any bypass of the shipped CLI and approval boundaries.

## Active Task

Implement the Minimal External UI Read-Only Status Surface for the agent loop. This slice should add a thin external UI that can select an attached target, read the approved controller-side and target-side canonical artifacts, render active phase/task/status and related read-only views, and preserve the 10G advisory-vs-canonical, CLI-only, and source-of-truth boundaries without yet adding run/resume controls or any canonical-artifact writes from the UI.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10H as active
- `.agent-loop/phase-plan.md` records Phase 10G as closed history and contains a `## Phase 10H - Minimal External UI Read-Only Status Surface` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository implements the first bounded external UI runtime slice described by the approved 10G contract rather than remaining documentation-only
- the UI reads only the approved controller-side and target-side canonical artifacts, renders phase/task/status and related read-only views from those artifacts, and marks derived values as advisory rather than canonical
- the UI preserves the shipped CLI-first workflow by rendering CLI-only operations as non-executing guidance or copyable commands rather than dispatching them
- the UI preserves the shipped artifact/source-of-truth boundary: repo artifacts on disk remain authoritative over any UI cache, session state, rendered status summary, or in-memory view model
- the UI preserves the shipped approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target ownership boundaries, and the Phase 4C activator + `APPROVED_FOR_ACTIVATION` activation gate
- focused validation proves the new read-only UI surface is bounded, consistent with the approved 10G contract, and reflected accurately in planning/docs/runtime surfaces
- `README.md` reflects that Phase 10H is active and that the minimal external UI read-only status surface is now the implementation focus

## Next-Phase Gate

Do not begin mutating external UI controls or broader control-plane expansion after Phase 10H until:

- this Phase 10H slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the read-only external UI surface as concrete enough to build the first bounded control slice on
- Codex updates the canonical phase/task artifacts to activate the next Phase 10 sub-phase rather than treating roadmap bullets as implementation authority on their own

## Out Of Scope For Current Phase

- any mutating external UI control, dashboard action surface, or run/resume implementation beyond the bounded read-only viewer (Phase 10I and later)
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
