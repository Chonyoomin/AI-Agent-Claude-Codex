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

## Current Status

The instruction contract, prompt formats, review formats, task and phase ownership rules, and safety model are in place. Phase 1 (Manual File-Based Loop) closed with `APPROVED_FOR_HUMAN_REVIEW`. The project is currently in **Phase 2A - Evidence Collection Contract**, a planning sub-phase that defines how the future `scripts/run_checks.sh` (Phase 2B) must behave.

The full Evidence Collection Contract - command discovery, state vocabulary, log file format, and script-side safety constraints - lives in `.agent-loop/phase-plan.md` under `## Phase 2A - Evidence Collection Contract`. No script has been implemented yet; Phase 2A is documentation only.
