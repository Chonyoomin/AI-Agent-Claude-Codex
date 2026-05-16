# Agentic AI Coding Loop

Agentic AI Coding Loop is a local orchestration project for running a controlled build-review-fix workflow between Codex and Claude Code.

Codex acts as the planner, reviewer, validator, and fix-prompt generator. Claude Code acts as the implementation agent. A local orchestrator manages prompts, artifacts, validation logs, and loop state. A human must approve the result before any commit.

## Goal

Reduce manual copy/paste between Codex and Claude Code while keeping the workflow auditable, scoped, and safe.

## MVP

The first version focuses on a small local loop:

- read a human-authored `TASK.md`
- generate a focused Claude implementation prompt
- let Claude implement the requested phase
- capture Claude's structured summary
- capture `git diff` and `git status`
- run validation commands and save logs
- let Codex review the prompt, summary, diff, and logs
- generate a fix prompt if needed
- stop for human approval before commit

## Workflow

1. Human writes or updates `TASK.md`.
2. Codex selects the next phase and writes `.agent-loop/claude-prompt.md`.
3. Claude Code implements the phase and writes `.agent-loop/claude-summary.md`.
4. The orchestrator captures diff, status, and validation logs.
5. Codex writes `.agent-loop/codex-review.md` with one verdict:
   - `APPROVED_FOR_HUMAN_REVIEW`
   - `NEEDS_FIXES`
   - `FAILED_REQUIRES_HUMAN`
6. If fixes are required, Codex writes `.agent-loop/fix-prompt.md`.
7. Claude applies targeted fixes.
8. The loop repeats until approval, escalation, or max cycles reached.
9. The system stops for human approval before commit.

## Repository Files

Top-level project files:

- `README.md`: public project overview
- `AGENTS.md`: operating rules, review standards, and artifact formats
- `CLAUDE.md`: Claude Code implementation contract
- `ROADMAP.md`: phased delivery plan
- `TASK.md`: current task definition

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
- no final commit without human approval

## Current Status

This repository currently defines the operating contract, prompt formats, review formats, and safety rules for the loop. The orchestrator implementation is still to be built.
