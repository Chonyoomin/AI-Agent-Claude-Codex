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

Phase 9E - Long-Run Continuation And Completion Heuristics

## Phase Status

Phase 9D (Autonomous Internal Review/Fix Loop) is closed after Codex review approval and human progression. Phase 9E is now active as the next implementation slice under the approved Phase 9 contract. This sub-phase should extend the autonomous runtime so it can continue across longer-running product-building sessions with bounded continuation heuristics and explicit completion detection, while preserving the shipped planner, activation, artifact-truth, and hard-stop boundaries.

## Active Task

Implement the Long-Run Continuation And Completion Heuristics slice for the agent loop. This slice should extend the shipped Phase 6 continuation primitives and the Phase 9B/9C/9D autonomous runtime so the orchestrator can continue across longer product-building runs, detect bounded “done enough” completion states from canonical artifacts, and stop or continue deterministically without silently widening autonomy, while preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 9 / 9E as active
- `.agent-loop/phase-plan.md` records Phase 9D as closed history and contains a `## Phase 9E - Long-Run Continuation And Completion Heuristics` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository ships a bounded long-run continuation layer that can extend the autonomous Phase 9 runtime across multiple continuation hops using canonical repo artifacts and the shipped Phase 6 continuation primitives
- the runtime can detect bounded completion / “done enough” terminal states from canonical artifacts and explicit review signals rather than relying on transcript-only judgment
- the new surface preserves the shipped artifact/source-of-truth boundary: canonical prompt, summary, review, fix, checkpoint, and loop-state artifacts remain authoritative; advisory descriptors remain routing/timing artifacts only
- the new surface preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- focused validation proves bounded long-run continuation behavior, completion-detection behavior, refusal behavior, and hard-stop preservation from repo artifacts and logs
- `README.md` reflects that Phase 9E is active and that long-run continuation / completion heuristics are now the implementation focus

## Next-Phase Gate

Do not start the next 9x sub-phase after Phase 9E until:

- this Phase 9E slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- capacity-halt re-probe or final acceptance automation (Phases 9F-9G)
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation, or that replaces canonical prompt/review/checkpoint artifacts with transient runtime-only state
- any new intake, runtime-adapter, LangChain, VS Code, MCP, or external-UI feature work unrelated to the narrow long-run continuation / completion slice
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 9 roadmap items into this slice
- MCP support, external UI, concurrent-agent operation, or implementation of end-to-end fully autonomous PRD-to-product execution (future phases)
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite to the repository beyond focused long-run-continuation coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
