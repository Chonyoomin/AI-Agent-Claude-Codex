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

- a human-provided objective with Codex-managed `TASK.md`
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

1. Human provides the project objective or updates the desired outcome.
2. Codex reads repository instructions and task context.
3. Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` to reflect the active phase.
4. Codex writes a focused Claude implementation prompt for only the active phase.
5. Claude Code performs implementation work only within the requested phase.
6. Claude Code writes a structured summary of what changed.
7. The orchestrator captures objective evidence:
   - `git diff`
   - `git status`
   - test output
   - lint output
   - typecheck output
   - build output
8. Codex reviews the prompt, summary, diff, and logs.
9. Codex decides one of:
   - `APPROVED_FOR_HUMAN_REVIEW`
   - `NEEDS_FIXES`
   - `FAILED_REQUIRES_HUMAN`
10. If fixes are required, Codex writes a focused repair prompt for Claude Code.
11. The loop repeats within the same phase until `APPROVED_FOR_HUMAN_REVIEW`, max cycles reached, or `FAILED_REQUIRES_HUMAN`.
12. When a phase reaches `APPROVED_FOR_HUMAN_REVIEW`, the system stops and waits for human approval to start the next phase.
13. The system never commits without separate human approval.

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

When acting as the review and validation agent, Codex must review these inputs when available:

- `AGENTS.md`
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/claude-summary.md`
- `.agent-loop/git-diff.patch`
- `.agent-loop/git-status.log`
- `.agent-loop/test-output.log`
- `.agent-loop/lint-output.log`
- `.agent-loop/typecheck-output.log`
- `.agent-loop/build-output.log`

The git diff and validation logs are the source of truth.

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

## Required Review Verdict

Each Codex review must return exactly one final verdict.

Allowed verdicts:

```text
APPROVED_FOR_HUMAN_REVIEW
NEEDS_FIXES
FAILED_REQUIRES_HUMAN
```

Verdict rules:

- `APPROVED_FOR_HUMAN_REVIEW`: use only when the requested phase is complete, the diff matches the claimed work, no blocking issue remains, and validation status is explicitly recorded
- `NEEDS_FIXES`: use when the phase is reviewable but there are correctable implementation, scope, or validation issues that should be sent back to Claude Code
- `FAILED_REQUIRES_HUMAN`: use when the work is unsafe, ambiguous, non-converging, materially out of scope, or cannot be responsibly resolved through another automated fix cycle

Codex must return exactly one of those strings as the terminal review outcome. Do not invent synonyms such as `approved`, `rejected`, or `human intervention required`.

## Required Codex Review Format

Codex review output should be written to `.agent-loop/codex-review.md`.

Use the exact format below unless a human explicitly changes the project standard:

```md
# Codex Review

## Verdict
APPROVED_FOR_HUMAN_REVIEW | NEEDS_FIXES | FAILED_REQUIRES_HUMAN

## Review summary
[brief explanation of the review result]

## Claude summary accuracy
Accurate | Partially accurate | Inaccurate

## Scope control
In scope | Minor scope drift | Major scope drift

## Validation result
Passed | Failed | Not run | Inconclusive

## Issues found

### Issue 1
Severity: Low | Medium | High | Critical
Category: Bug | Test Failure | Scope Drift | Architecture Violation | Instruction Violation | Summary Mismatch | Other
File(s): [file paths]
Problem:
[clear explanation of the issue]

Evidence:
[reference the diff, Claude summary, validation logs, or instruction files]

Required fix:
[concrete fix required]

## Fix prompt for Claude
[Only include this section if verdict is NEEDS_FIXES. Write a direct repair prompt Claude Code can execute.]

## Human attention required
[Only include this section if verdict is FAILED_REQUIRES_HUMAN. Explain why the loop must stop.]
```

Rules:

- return exactly one allowed verdict
- base the review on objective evidence, not Claude's claims alone
- reference evidence for every issue
- omit `## Fix prompt for Claude` unless the verdict is `NEEDS_FIXES`
- omit `## Human attention required` unless the verdict is `FAILED_REQUIRES_HUMAN`
- if no issues are found, keep `## Issues found` and write `None`

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
- require phase completion and review before the next phase begins
- record active phase and cycle count in `.agent-loop/loop-state.json`
- treat `max_cycles` as a safety threshold, not as an automatic failure by itself
- when the threshold is reached, compare the latest findings with the prior findings before allowing another automated fix cycle
- if the same issue repeats with materially the same outcome and no meaningful progress, escalate to human review
- if the issue set has materially changed or narrowed, another cycle may proceed only with explicit human approval
- the loop must never continue indefinitely without a human decision once the threshold has been reached

## Task And Phase Ownership

Task and phase state must have clear ownership.

Rules:

- the human provides the initial project objective and any later priority changes
- Codex owns planning and phase decomposition
- Codex updates `TASK.md` to reflect the current objective, active phase, and expected outcome
- Codex updates `.agent-loop/current-task.md` and `.agent-loop/current-phase.md` when selecting or advancing phases
- the orchestrator records runtime state in `.agent-loop/loop-state.json`
- Claude Code reads task and phase state but does not redefine it
- a completed phase must stop for human confirmation before Codex starts the next phase
- if a review finding concerns a Codex-owned artifact or decision, Codex must correct it directly instead of issuing a Claude fix prompt
- if a review finding concerns a Claude-owned artifact or implementation result, Codex should return it to Claude through a focused fix prompt
- the loop must not assign a fix to the wrong agent

## Implementation Ownership

Claude Code is the default and only implementation editor during an active
implementation sub-phase.

Rules:

- Claude Code is the default implementation editor for code, tests, scripts, configuration changes, and other repository edits during an active implementation sub-phase
- Codex should not directly modify implementation files by default, even for small fixes, convenience edits, or follow-up cleanup
- if Codex identifies a required implementation change, Codex should decide whether the issue should be resolved by Claude Code or by Codex
- if the issue is an implementation issue, test issue, refactor issue, script implementation issue, or other code-change issue that belongs to the active development work, Codex should normally hand it off to Claude Code rather than applying it directly
- if the issue is a planning issue, task-state issue, review issue, prompt issue, phase-management issue, agent-routing issue, governance or instruction issue, or another issue that Codex determines should not be resolved by Claude Code, Codex should resolve it directly
- Codex may directly edit any file when Codex has explicitly decided that the issue should be Codex-resolved rather than Claude-resolved
- Claude Code should not be used to fix issues that Codex has explicitly classified as Codex-resolved
- if ownership or routing is ambiguous, Codex should pause and either route the change to Claude Code or surface the ambiguity for human decision

## Runtime And Evidence Ownership

The following artifacts are owned by the orchestrator or by the scripts that
generate them and must not be fabricated by hand outside explicitly assigned
implementation work:

- `.agent-loop/loop-state.json`
- `.agent-loop/orchestrator.log`
- `.agent-loop/git-diff.patch`
- `.agent-loop/git-status.log`
- `.agent-loop/test-output.log`
- `.agent-loop/lint-output.log`
- `.agent-loop/typecheck-output.log`
- `.agent-loop/build-output.log`

Enforcement:

- Claude Code handles implementation edits by default
- Codex may edit directly when the issue has been intentionally assigned to Codex for resolution
- the orchestrator and `scripts/run_checks.sh` own their runtime and evidence outputs; neither Codex nor Claude should fabricate or hand-edit those files unless the active phase explicitly assigns that implementation work

## Required Repository Files

The repository should maintain these top-level files:

- `README.md`: public project overview and current usage expectations
- `AGENTS.md`: system operating rules and review policy
- `CLAUDE.md`: Claude Code implementation contract
- `ROADMAP.md`: phased delivery plan
- `TASK.md`: Codex-maintained task and phase record derived from the human objective

## README Maintenance

This repository should maintain a concise, public-safe `README.md`.

Rules:

- create `README.md` when a repository does not already have one and the project is intended for reuse, collaboration, or GitHub publication
- update `README.md` when changes affect project purpose, workflow, setup, file structure, validation flow, usage, or current status
- keep the README concise and accurate
- do not place secrets, tokens, internal-only notes, or local machine details in the README
- prefer updating existing README sections over letting documentation drift

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
- Codex review decision with exactly one required verdict
- Codex review written in the required review format
- next fix prompt if review fails
- current cycle number and terminal state

## Required Claude Task Format

Codex should write the implementation handoff prompt to `.agent-loop/claude-prompt.md`.

Use the exact format below unless a human explicitly changes the project standard:

```md
# Claude Code Task

## Phase
[phase name]

## Objective
[clear objective]

## Context
[relevant context from TASK.md, ROADMAP.md, AGENTS.md, CLAUDE.md, and repository state]

## Required work
- [specific required item]
- [specific required item]

## Files likely involved
- [path or area]
- [path or area]

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

## Validation expected
- [expected command, such as npm test]
- [expected command, such as npm run lint]
- [expected command, such as npm run typecheck]
- [expected command, such as npm run build]

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
```

Rules:

- keep the objective and required work specific to the active phase
- keep context concise but sufficient to execute safely
- do not omit the constraints section
- do not relax protected-file constraints unless a human explicitly changes the standard
- list expected validation commands or state that none are expected only if a human explicitly allows that

## Required Claude Fix Task Format

Codex should write the repair handoff prompt to `.agent-loop/fix-prompt.md` when the review verdict is `NEEDS_FIXES`.

Use the exact format below unless a human explicitly changes the project standard:

```md
# Claude Code Fix Task

## Objective
Fix only the issues found in `.agent-loop/codex-review.md`.

## Context
The previous implementation was reviewed by Codex and received the verdict `NEEDS_FIXES`.

Read:
- `CLAUDE.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/git-diff.patch`
- `.agent-loop/test-output.log`
- `.agent-loop/lint-output.log`
- `.agent-loop/typecheck-output.log`
- `.agent-loop/build-output.log`

## Required fixes
- [specific fix from Codex review]
- [specific fix from Codex review]

## Constraints
- Fix only the listed issues.
- Do not redesign unrelated code.
- Do not expand the product scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not delete files unless explicitly required and approved.
- Preserve the original task objective.
- Update tests if behavior changes.
- Prefer minimal, targeted changes.

## Required output
After applying fixes, update `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
```

Rules:

- only use this format for repair cycles after a `NEEDS_FIXES` verdict
- required fixes must map directly to issues listed in `.agent-loop/codex-review.md`
- do not add new product work to the fix prompt
- preserve the original task objective and scope boundaries
- keep the fix prompt specific, minimal, and executable

## Required Claude Summary Format

Claude Code must write `.agent-loop/claude-summary.md` after every implementation or fix cycle.

The summary must describe what Claude actually changed.

Rules:

- do not use vague claims
- do not claim validation passed unless validation was actually run
- do not omit risk areas
- use the exact project-standard Markdown format below unless a human explicitly changes it

Required format:

```md
# Claude Implementation Summary

## Phase
[phase name]

## Task
[task name]

## Files changed
- [file path]: [short explanation of what changed in this file]

## What was implemented
- [specific implemented behavior or change]
- [specific implemented behavior or change]

## What was not implemented
- [known excluded item]
- [known excluded item]

## Tests added or changed
- [test file or test behavior added/changed]
- [write "None" if no tests were added or changed]

## Validation run
- [command run, such as npm test, npm run lint, npm run typecheck, npm run build]
- [write "Not run" if validation was not run]

## Assumptions
- [assumption made during implementation]
- [write "None" if no assumptions were made]

## Risk areas
- [potential issue, fragile area, untested behavior, integration concern]
- [write "None identified" only if there are genuinely no known risks]
```

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
- Codex has issued an `APPROVED_FOR_HUMAN_REVIEW` review outcome

Even then, the system must stop and wait for a human before commit.

## Collaboration Rules For Agents

Codex responsibilities:

- choose the next small phase
- update `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the active phase
- generate precise prompts for Claude Code
- compare claims against diff and logs
- issue exactly one allowed review verdict per review cycle
- generate repair prompts when necessary
- stop the loop when phase approval or escalation criteria are met

Claude Code responsibilities:

- implement only the requested phase
- avoid speculative refactors
- provide a structured summary of actual changes
- report validation or execution limitations honestly
- update `README.md` when the task changes user-facing project behavior or documented usage expectations
- not redefine the active task or phase on its own
- wait for the next prompt when a fix cycle is required

The orchestrator responsibilities:

- persist artifacts reliably
- run validation commands
- capture raw evidence without interpretation
- hand the same evidence back to Codex for review
- stop between phases until the human explicitly starts the next phase
- require human approval before any commit action

## Documentation Style

Project instructions should be:

- concrete rather than aspirational
- phase-oriented rather than architecture-heavy
- explicit about stop conditions
- explicit about evidence requirements
- minimal where possible and strict where needed

If there is a conflict between convenience and auditability, prefer auditability.
