# AGENTS.md

## Purpose

This repository builds a local agentic coding orchestration loop that coordinates:

- Codex as planner, reviewer, validator, and fix-prompt generator
- Claude Code as implementation agent
- a local orchestrator as loop controller
- a human as final approver before any commit

The project goal is to reduce manual copy/paste between Codex and Claude Code while preserving clear control, objective evidence, and human oversight.

## Current Scope

Build the smallest local MVP that proves the loop works end to end.

The MVP must support:

- a user-authored `TASK.md`
- Codex-generated implementation prompts for Claude Code
- Claude Code implementation against that prompt
- a structured Claude implementation summary
- captured `git diff` and `git status`
- captured validation outputs for test, lint, typecheck, and build
- Codex review using prompt, summary, diff, and logs
- Codex-generated fix prompts when needed
- repeated fix cycles with a hard maximum
- human approval before any commit

## Explicit Non-Goals

Do not build these in the first version unless a human explicitly reprioritizes the project:

- MCP integration
- VS Code extension support
- autonomous commit or push behavior
- multi-repo orchestration
- cloud-hosted orchestration
- broad plugin ecosystems
- speculative architecture for future features that are not required by the MVP

## Operating Model

The intended loop is:

1. Human writes or updates `TASK.md`.
2. Codex reads repository instructions and task context.
3. Codex selects the next phase and writes a focused Claude implementation prompt.
4. Claude Code performs implementation work only within the requested phase.
5. Claude Code writes a structured summary of what changed.
6. The orchestrator captures objective evidence:
   - `git diff`
   - `git status`
   - test output
   - lint output
   - typecheck output
   - build output
7. Codex reviews the prompt, summary, diff, and logs.
8. Codex decides one of:
   - approved
   - fix required
   - human intervention required
9. If fixes are required, Codex writes a focused repair prompt for Claude Code.
10. The loop repeats until approval, max cycles reached, or human intervention required.
11. The system stops and waits for human approval before any commit.

## Source Of Truth

Use evidence in this order of authority:

1. repository files and current task documents
2. actual `git diff` and `git status`
3. validation logs produced by the orchestrator
4. Claude Code summary text
5. planning notes or assumptions

If summary text conflicts with the diff or logs, trust the diff and logs.

## Review Standard

Codex review must be evidence-based, not impression-based.

Every review should answer:

- Did Claude implement the requested scope and only that scope?
- Does the diff match the claimed summary?
- Do validation logs show pass, fail, or not run?
- Were safety and repository rules followed?
- Is the result acceptable for human approval, or is another fix cycle required?

Codex should classify findings with clear severity:

- `blocker`: unsafe, incorrect, unreviewable, or outside scope
- `major`: meaningful bug, regression risk, missing validation, or weak repair needed
- `minor`: quality issue that does not block the phase
- `note`: observation or follow-up idea

## Safety Constraints

The loop must preserve human control.

Required safety rules:

- never auto-commit
- never auto-push
- never bypass human approval before commit
- never hide failing validation output
- never treat Claude summary text as sufficient evidence on its own
- never silently expand scope beyond the active phase
- never rewrite unrelated files just because they are nearby
- never mark work approved if required validation was skipped without explicitly recording that gap

## Change Control

The orchestrator and both agents must operate on a narrow, phase-based scope.

Rules:

- prefer small phases over large autonomous changes
- require each Claude prompt to define allowed work and exclusions
- record active phase and cycle count in `.agent-loop/loop-state.json`
- stop when the maximum fix-cycle count is reached
- escalate to human review when repeated repair prompts do not converge

## Required Repository Files

The repository should maintain these top-level files:

- `AGENTS.md`: system operating rules and review policy
- `CLAUDE.md`: Claude Code implementation contract
- `ROADMAP.md`: phased delivery plan
- `TASK.md`: current human-authored task or objective

The local controller should write transient loop artifacts under:

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

## Expected Loop Artifacts

Each loop iteration should leave enough evidence for a human to reconstruct what happened.

Minimum expectations:

- prompt sent to Claude
- Claude's change summary
- raw diff or patch
- raw git status
- raw validation logs
- Codex review decision
- next fix prompt if review fails
- current cycle number and terminal state

## MVP Implementation Priorities

Build in this order unless `TASK.md` says otherwise:

1. task loading and phase selection
2. Claude prompt generation
3. Claude summary capture
4. diff and status capture
5. validation command execution and log capture
6. Codex review output and decision model
7. repair prompt generation
8. cycle limit and human stop gate

Avoid designing for advanced future capabilities before these are working.

## Approval Rules

Work is ready for human approval only if all of the following are true:

- the requested phase scope is complete
- no blocker findings remain
- validation status is explicitly recorded
- any skipped validation is clearly disclosed with reason
- the diff is understandable and attributable to the active phase
- Codex has issued an `approved` review outcome

Even then, the system must stop and wait for a human before commit.

## Collaboration Rules For Agents

Codex responsibilities:

- choose the next small phase
- generate precise prompts for Claude Code
- compare claims against diff and logs
- generate repair prompts when necessary
- stop the loop when approval or escalation criteria are met

Claude Code responsibilities:

- implement only the requested phase
- avoid speculative refactors
- provide a structured summary of actual changes
- report validation or execution limitations honestly
- wait for the next prompt when a fix cycle is required

The orchestrator responsibilities:

- persist artifacts reliably
- run validation commands
- capture raw evidence without interpretation
- hand the same evidence back to Codex for review
- require human approval before any commit action

## Documentation Style

Project instructions should be:

- concrete rather than aspirational
- phase-oriented rather than architecture-heavy
- explicit about stop conditions
- explicit about evidence requirements
- minimal where possible and strict where needed

If there is a conflict between convenience and auditability, prefer auditability.
