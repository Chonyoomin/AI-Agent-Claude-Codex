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

Phase 9D - Autonomous Internal Review/Fix Loop

## Phase Status

Phase 9C (Orchestrator-Driven Prompt Handoff) is closed after Codex review approval and human progression. Phase 9D is now active as the next implementation slice under the approved Phase 9 contract. This sub-phase should let the orchestrator autonomously run the internal Codex review plus Claude fix loop across bounded cycles while preserving the shipped planner, activation, artifact-truth, and hard-stop boundaries.

## Active Task

Implement the Autonomous Internal Review/Fix Loop slice for the agent loop. This slice should let the orchestrator consume the Phase 9B/9C handoff artifacts, trigger Codex review automatically, route findings by owner, regenerate `.agent-loop/fix-prompt.md` when Claude-owned fixes are required, and continue bounded internal review/fix cycles without manual routing between agents, while preserving the shipped planner/activation boundary, artifact source-of-truth model, and hard-stop behavior.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 9 / 9D as active
- `.agent-loop/phase-plan.md` records Phase 9C as closed history and contains a `## Phase 9D - Autonomous Internal Review/Fix Loop` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository ships a bounded autonomous internal review/fix loop that can, from canonical repo artifacts, run Codex review after Claude completion, classify findings by owner, and continue Claude fix cycles without manual prompt passing
- the loop preserves the shipped artifact/source-of-truth boundary: canonical prompt, summary, review, and fix artifacts remain on disk; `.agent-loop/claude-done.json` and `.agent-loop/prompt-handoff.json` remain routing/timing artifacts rather than substitutes for review evidence
- the runtime makes Codex-owned versus Claude-owned routing explicit and deterministic, including automatic `.agent-loop/fix-prompt.md` refresh only when Claude-owned fixes are required
- the new surface preserves the shipped CLI-first workflow, planner/activation boundaries, approval semantics, halt/refusal vocabulary, checkpoint/resume behavior, cycle thresholds, and repo-artifact source-of-truth model
- focused validation proves bounded autonomous review/fix continuation, refusal behavior, and hard-stop preservation from repo artifacts and logs
- `README.md` reflects that Phase 9D is active and that autonomous internal review/fix continuation is now the implementation focus

## Next-Phase Gate

Do not start the next 9x sub-phase after Phase 9D until:

- this Phase 9D slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- automatic next-phase activation, long-run completion heuristics, capacity-halt re-probe, or final acceptance automation (Phases 9E-9G)
- any autonomous review/fix behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation, or that replaces canonical prompt/review artifacts with transient runtime-only state
- any new intake, memory, runtime-adapter, LangChain, VS Code, MCP, or external-UI feature work unrelated to the narrow autonomous internal review/fix slice
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
- adding any project-wide CI suite to the repository beyond focused autonomous-loop coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
