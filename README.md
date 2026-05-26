# Agentic AI Coding Loop

Agentic AI Coding Loop is a local orchestration project for running a controlled, phase-gated build-review-fix workflow between Codex and Claude Code.

Codex acts as the planner, task-state manager, reviewer, validator, and fix-prompt generator. Claude Code acts as the implementation agent for the active phase only. A local orchestrator manages prompts, artifacts, validation logs, and loop state. A human approves movement between phases and separately approves any eventual commit.

## Goal

Reduce manual copy/paste between Codex and Claude Code while keeping the workflow auditable, scoped, and safe.

## MVP

The first version focuses on a small local loop:

- read a human-provided objective
- let Codex maintain `TASK.md` and active phase state
- generate a focused Claude implementation prompt
- let Claude implement the requested phase
- capture Claude's structured summary
- capture `git diff` and `git status`
- run validation commands and save logs
- let Codex review the prompt, summary, diff, and logs
- generate a fix prompt if needed
- stop after each approved phase until the human starts the next one

## Workflow

This section describes the intended end-to-end workflow once the orchestrator (Phase 3) is built. Until then, the same loop runs by hand - see `## Running The Loop Manually (Phase 1)` below.

1. Human provides the project objective or updates the desired outcome.
2. Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the active phase.
3. Codex writes `.agent-loop/claude-prompt.md`.
4. Claude Code implements only the active phase and writes `.agent-loop/claude-summary.md`.
5. The orchestrator captures diff, status, and validation logs.
6. Codex writes `.agent-loop/codex-review.md` with one verdict:
   - `APPROVED_FOR_HUMAN_REVIEW`
   - `NEEDS_FIXES`
   - `FAILED_REQUIRES_HUMAN`
7. If fixes are required, Codex writes `.agent-loop/fix-prompt.md`.
8. Claude applies targeted fixes within the same phase.
9. The loop repeats until the phase is approved, escalated, or reaches max cycles.
10. When a phase is approved, the system stops until the human starts the next phase.
11. The system never commits without separate human approval.

## Repository Files

Top-level project files:

- `README.md`: public project overview
- `AGENTS.md`: operating rules, review standards, and artifact formats
- `CLAUDE.md`: Claude Code implementation contract
- `ROADMAP.md`: phased delivery plan
- `TASK.md`: Codex-maintained task and phase record derived from the human objective

Loop artifacts:

```text
.agent-loop/
  phase-plan.md
  current-task.md
  current-phase.md
  claude-prompt.md
  claude-summary.md
  git-diff.patch
  git-status.log
  test-output.log
  lint-output.log
  typecheck-output.log
  build-output.log
  codex-review.md
  fix-prompt.md
  loop-state.json
```

## Safety

- no auto-commit
- no auto-push
- no hidden validation failures
- no trusting summary text over actual diffs and logs
- no phase advancement without human approval
- no final commit without human approval

## Running The Loop Manually (Phase 1)

While the orchestrator is not yet built, the loop runs by hand against the artifact formats defined in `AGENTS.md`. One full manual cycle:

1. Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the active phase.
2. Codex writes the implementation prompt to `.agent-loop/claude-prompt.md` using the required Claude task format.
3. A human pastes that prompt into Claude Code.
4. Claude Code implements only the active phase and writes `.agent-loop/claude-summary.md` using the required Claude implementation summary format.
5. A human captures evidence into `.agent-loop/`:
   - `git diff > .agent-loop/git-diff.patch`
   - `git status > .agent-loop/git-status.log`
   - test, lint, typecheck, and build output to `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log` (or record "Not run" explicitly).
6. A human pastes the prompt, summary, diff, and logs into Codex.
7. Codex writes `.agent-loop/codex-review.md` with exactly one verdict: `APPROVED_FOR_HUMAN_REVIEW`, `NEEDS_FIXES`, or `FAILED_REQUIRES_HUMAN`.
8. If the verdict is `NEEDS_FIXES`, Codex writes `.agent-loop/fix-prompt.md` and the cycle repeats from step 3 within `max_cycles`.
9. The cycle stops for human approval before any commit, and again before the next phase begins.

`.agent-loop/loop-state.json` records the active phase, task, cycle count, max cycles, and last verdict by hand.

## Current Status

The instruction contract, prompt formats, review formats, task and phase ownership rules, and safety model are in place. Phase 1 (Manual File-Based Loop), Phase 2A (Evidence Collection Contract), Phase 2B (`scripts/run_checks.sh`), Phase 3 (Scripted Orchestrator MVP, delivered as sub-phases 3A through 3E), and Phase 4A (Planning Contract) are all complete; the historical sub-phase record is preserved in `.agent-loop/phase-plan.md`. The project is currently in **Phase 4B - Planner Initial Slice (Proposal Generation)**: implementing the first working slice of the automatic phase planner against the Phase 4A contract. The slice covers proposal generation only; planner-driven activation writes are explicitly deferred to a later 4x sub-phase.

The Phase 4B planner is invoked via the new `python scripts/agent_loop.py plan` subcommand. On invocation the planner:

- loads the planner inputs the Phase 4A contract enumerates (`TASK.md`, `.agent-loop/phase-plan.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/loop-state.json`, `.agent-loop/claude-summary.md`, `.agent-loop/codex-review.md`, the six evidence files, and `ROADMAP.md`) as read-only
- applies every Phase 4A refusal condition: unresolved `NEEDS_FIXES`, `FAILED_REQUIRES_HUMAN`, any `halted_*` status, orchestrator-in-flight statuses (`claude_implementing`, `claude_fixing`, `evidence_capture`, `awaiting_codex_review`), `cycle_count >= max_cycles` on `NEEDS_FIXES`, stale evidence (`captured_at` older than the latest `claude-summary.md` or `codex-review.md` mtime), unreadable evidence headers, a previously-approved `proposed-phase.md` carrying the `APPROVED_FOR_ACTIVATION` token, and unreadable / malformed `loop-state.json`
- when allowed, generates a structurally valid `.agent-loop/proposed-phase.md` (title + nine required sections in order) and validates it against the bounded-scope rules (max 10 files, max 1 contract revision, at least one testable Definition-of-done bullet, no vague language, cycle-size estimate <= 3 without justification, no dependency in `active-in-flight` / `pending` status, no label collision against historical sub-phases, no `APPROVED_FOR_ACTIVATION` token authored by the planner itself)
- appends a single timestamped `note:` / `refused:` line to `.agent-loop/planner.log` (best-effort) describing the outcome
- exits 0 on success and 2 on any refusal; the proposal file is never partially written on a refusal path

Activation writes (modifying `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json` on the basis of an approved proposal) are NOT implemented in this sub-phase; the planner only writes its two planner-owned artifacts (`.agent-loop/proposed-phase.md` and `.agent-loop/planner.log`).

Focused tests live in `tests/test_planner.py` and cover the major refusal paths, the bounded-scope self-validation, and one full proposal-generation success path. Run them with `python tests/test_planner.py`.

Deferred to later 4x sub-phases: planner activation writes (the activation step described above), planner-orchestrator integration, optional planner adapter. Deferred to later phases generally: approval modes (Phase 5), optional context and tool layer (Phase 6), editor integration (Phase 7), documentation and project polish (Phase 8). The Phase 3 orchestrator surface (`scripts/agent_loop.py` normal cycle / fix cycle / adapters, `scripts/run_checks.sh`) is unchanged by Phase 4B beyond the addition of planner functions and the `plan` subcommand.
