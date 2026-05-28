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

The instruction contract, prompt formats, review formats, task and phase ownership rules, and safety model are in place. Phase 1 (Manual File-Based Loop), Phase 2A (Evidence Collection Contract), Phase 2B (`scripts/run_checks.sh`), Phase 3 (Scripted Orchestrator MVP, delivered as sub-phases 3A through 3E), Phase 4A (Planning Contract), Phase 4B (Planner Initial Slice; the `plan` subcommand), and Phase 4C (Planner Activation Writes; the `activate` subcommand) are all complete; the historical sub-phase record is preserved in `.agent-loop/phase-plan.md`. The project is currently in **Phase 4D - Planner-Orchestrator Integration**: integrating the standalone planner into the orchestrator's post-approval handoff while keeping activation separate and human-approved. The optional planner adapter remains deferred.

The operator flow across Phase 4B + Phase 4C is:

1. Run `python scripts/agent_loop.py plan` to generate `.agent-loop/proposed-phase.md`. The planner enforces every Phase 4A refusal condition (unresolved `NEEDS_FIXES`, `FAILED_REQUIRES_HUMAN`, any `halted_*` status, orchestrator-in-flight statuses, `cycle_count >= max_cycles` on `NEEDS_FIXES`, stale evidence, unreadable evidence headers, prior approved proposal carrying `APPROVED_FOR_ACTIVATION`, malformed `loop-state.json`) and the bounded-scope rules (max 10 files, max 1 contract revision, testable Definition-of-done bullet, no vague Objective language, cycle-size estimate <= 3 without justification, no `active-in-flight` / `pending` dependency, no label collision against historical sub-phases, no `APPROVED_FOR_ACTIVATION` token authored by the planner itself, `## Exclusions` enumerating later 4x / 5+ sub-phases). The planner writes only `.agent-loop/proposed-phase.md` and a `note:`-style line in `.agent-loop/planner.log`.
2. A human reviews the proposal and, if accepted, appends a `## Approval` section to `.agent-loop/proposed-phase.md`. The approval section must contain the literal `APPROVED_FOR_ACTIVATION` token on its own line within the section AND must reference the proposal's `## Label` text. Token forgery (extra words on the line, alternate capitalization, surrounding characters) and stale-label approvals are refused at activation time.
3. Run `python scripts/agent_loop.py activate` to consume the approved proposal. The activator parses the proposal, verifies the approval requirements exactly, refuses cleanly on every failure mode (missing `## Approval` section, malformed token, label mismatch, missing/unreadable proposal, missing/malformed `loop-state.json`, empty required-proposal-section bodies), and on success performs ONLY the Phase 4A activation writes: rewriting `TASK.md`'s `## Active Phase` / `## Active Sub-Phase` / `## Phase Status` / `## Active Task` / `## Phase Outcome Required Now` / `## Next-Phase Gate` / `## Out Of Scope For Current Phase` (preserving `## Human Objective` and `## Project Intent` verbatim); rewriting `.agent-loop/current-task.md` and `.agent-loop/current-phase.md`; updating `.agent-loop/phase-plan.md`'s `## Active Phase` line, closing the previously-active sub-phase's `### Status` opening line as a transition note, and APPENDING a new sub-phase section that mirrors the activated proposal; resetting `.agent-loop/loop-state.json` to `status = awaiting_claude_implementation`, `cycle_count = 0`, `last_verdict = null`, `last_verdict_phase = null` with `phase` / `sub_phase` / `task` set from the approved proposal and `max_cycles` / `contract_version` / `claude_version` / `codex_version` / `orchestrator_version` preserved per the Phase 3A write-ownership rules; and appending a `note:`-style approval-source line (file path, mtime, literal approval line) to `.agent-loop/planner.log`. The activator exits 0 on success and 2 on any refusal; refusals never partially write any activation file.
4. Phase 4D is the next slice after this flow: planner generation and activation remain standalone subcommands, but the orchestrator will now be extended to refresh the proposal after terminal approvals without auto-activating it.

Focused tests live in:
- `tests/test_planner.py` covering the Phase 4A refusal paths, bounded-scope validation, and proposal-generation success path
- `tests/test_planner_activation.py` covering the activation success path, approval-signal refusals, required-input refusals, and activation rollback behavior
- Phase 4D will add focused integration coverage for the post-approval planner hook and its no-activation-write boundary

Deferred to later 4x sub-phases: optional planner adapter (Phase 4E or later). Deferred to later phases generally: approval modes (Phase 5), optional context and tool layer (Phase 6), editor integration (Phase 7), documentation and project polish (Phase 8). The active Phase 4D slice is the first one that intentionally changes the Phase 3 orchestrator surface after planning/activation by adding the post-approval planner hook, while keeping approval and activation as separate human-controlled steps.
