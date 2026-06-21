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

Phase 9 - Fully Autonomous PRD-To-Product Mode

## Active Sub-Phase

Phase 9G - Final Human Acceptance And Polish Gate

## Phase Status

Phase 9F (Capacity-Halt Reprobe And Automatic Resume) is closed after Codex review approval and human progression. Phase 9G is now active as the final implementation slice under the approved Phase 9 contract. This sub-phase should require an explicit final human review, polish, and acceptance gate before a fully autonomous PRD-to-product run is treated as complete, while preserving the shipped planner, activation, artifact-truth, and hard-stop boundaries.

## Active Task

Implement the Final Human Acceptance And Polish Gate slice for the agent loop. This slice should require an explicit final human review, polish, and acceptance step before a fully autonomous PRD-to-product run is treated as complete, using canonical repo artifacts and preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 9 / 9G as active
- `.agent-loop/phase-plan.md` records Phase 9F as closed history and contains a `## Phase 9G - Final Human Acceptance And Polish Gate` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository ships a bounded final human acceptance / polish gate for the fully autonomous Phase 9 runtime that extends the shipped Phase 9B/9C/9D/9E/9F surfaces
- the runtime detects the final acceptance boundary from canonical artifacts and refuses to treat the run as complete until explicit human acceptance is recorded
- the new surface preserves the shipped artifact/source-of-truth boundary: canonical prompt, summary, review, fix, checkpoint, retry-state, loop-state, and final-acceptance artifacts remain authoritative; advisory descriptors remain routing/timing artifacts only
- the new surface preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- focused validation proves final-acceptance gating behavior, refusal behavior, and hard-stop preservation from repo artifacts and logs
- `README.md` reflects that Phase 9G is active and that the final human acceptance / polish gate is now the implementation focus

## Next-Phase Gate

Do not treat the fully autonomous Phase 9 run as complete after Phase 9G until:

- this Phase 9G slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly performs the final review / polish / acceptance step
- Codex updates the canonical phase/task artifacts to reflect the accepted terminal state rather than silently declaring completion from runtime-only signals

## Out Of Scope For Current Phase

- auto-accepting product completion or silently skipping the explicit final human gate
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation, or that replaces canonical prompt/review/checkpoint artifacts with transient runtime-only state
- any new intake, runtime-adapter, LangChain, VS Code, MCP, or external-UI feature work unrelated to the narrow final human acceptance / polish gate slice
- any product-completion logic that bypasses explicit human signoff
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing future roadmap work beyond the final human gate into this slice
- MCP support, external UI, concurrent-agent operation, or implementation of end-to-end fully autonomous PRD-to-product execution (future phases)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite to the repository beyond focused retry/re-probe coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
