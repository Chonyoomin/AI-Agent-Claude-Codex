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

Phase 3 - Scripted Orchestrator MVP

## Active Sub-Phase

Phase 3C - Automated Fix-Cycle Handling

## Phase Status

Phase 3B (initial Orchestrator MVP slice) is complete and approved by the human to advance. Phase 3C extends `scripts/agent_loop.py` with the contract's automated fix-cycle path (fix-prompt validation, `claude_fixing` -> evidence -> review transitions, manual-handoff Claude/Codex re-invocation, threshold-policy halt), so a `NEEDS_FIXES` verdict drives a fix cycle automatically instead of parking the loop. Approval modes, Git automation, editor integration, and real subprocess-driven CLI adapters remain deferred.

## Active Task

Implement the next 3x sub-phase for Phase 3B: automated `NEEDS_FIXES` handling in `scripts/agent_loop.py`. Validate `.agent-loop/fix-prompt.md` (presence, non-empty, contract header sequence) before any fix cycle; enforce the threshold policy (`cycle_count >= max_cycles` halts with `halted_max_cycles_reached`); implement the fix-cycle control path with the contract's status transitions (`claude_fixing` -> `evidence_capture` -> `awaiting_codex_review`); reuse the manual-handoff Claude and Codex adapters (including their existing fail-closed mtime checks); rerun `bash scripts/run_checks.sh` after each Claude fix handoff; wait for an updated `codex-review.md`; parse the post-fix verdict; loop until any terminal state (approved, failed-requires-human, threshold reached, fail-closed halt, parse/schema failure, or human stop).

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 3 / 3C as active
- `.agent-loop/phase-plan.md` marks Phase 3B complete and contains a Phase 3C section
- `scripts/agent_loop.py` implements the contract's `#### Fix cycle` step order, the threshold-policy halt, and `fix-prompt.md` validation, with fail-closed behavior preserved on the manual-handoff Claude and Codex adapters
- `README.md` reflects the Phase 3C active status and documents that a `NEEDS_FIXES` verdict now drives an automated fix cycle (with manual-handoff steps still gated by the human)
- no approval modes, no real subprocess-driven Claude/Codex adapters, no Git automation, and no editor integration are introduced in this sub-phase

## Next-Phase Gate

Do not start the next 3x sub-phase (real subprocess-driven Claude/Codex adapters, approval modes, etc.) until:

- this Phase 3C slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- real subprocess-driven Claude or Codex CLI adapters (still manual-handoff only)
- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- automatic "materially changed / narrowed" cycle-extension judgment by the orchestrator (orchestrator only enforces the threshold; raising `max_cycles` is an explicit Codex/human action)
- any change to the Phase 2A Evidence Collection Contract
- any change to `scripts/run_checks.sh`
- any change to the Phase 3A Orchestrator Contract
- adding any real test/lint/typecheck/build suite to the repository (still a documentation-only project)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
