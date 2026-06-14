# Claude Code Task

## Phase
Phase 7A - VS Code Task Entrypoints

## Objective
Implement the first VS Code task entrypoints for the agent loop. This slice should add `.vscode/tasks.json` commands for the common operator flows such as running the loop, collecting evidence, opening review artifacts, and other CLI-backed entrypoints, while preserving the current CLI-first runtime contract and avoiding any change to the orchestrator's ownership, halt, approval, or artifact-truth rules.

## Context
Implement `.vscode/tasks.json` entries for the common operator flows so the
project is easier to run from VS Code without changing the underlying runtime
contract. This slice should surface existing CLI commands for loop execution,
evidence collection, review-artifact access, and adjacent operator entrypoints
while keeping repo artifacts as the source of truth, preserving halt and
approval behavior, and avoiding any IDE-owned replacement for the shipped
orchestrator.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 7 / 7A as active
- `.agent-loop/phase-plan.md` records Phase 6O as closed history and contains a
  `## Phase 7A - VS Code Task Entrypoints` section with concrete objective, done
  criteria, and exclusions
- `.vscode/tasks.json` exists and exposes thin task wrappers for the common
  operator flows using the shipped CLI commands rather than reimplementing them
- the VS Code tasks preserve canonical repo-artifact truth by invoking the
  existing orchestrator and evidence-collection commands instead of replacing
  them with editor-owned behavior
- the VS Code task layer preserves the shipped halt/refusal vocabulary,
  approval-mode behavior, checkpoint/continuation behavior, and artifact
  ownership boundaries by delegating to existing commands
- the repository remains fully usable without VS Code, and every VS Code task
  corresponds to an existing documented CLI surface
- focused validation covers task definitions, command mapping, and proof that
  the task layer does not widen runtime or ownership scope
- `README.md` reflects that Phase 7A is active and that VS Code task entrypoints
  are now the implementation focus

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.

Out of scope for this phase (from `TASK.md` and `phase-plan.md`):
- no artifact dashboard, inspection workflow polish, or reset/recovery UX beyond
  the narrow task-entrypoint layer for this slice
- no replacement of the CLI-first workflow with a VS Code-only workflow
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no regression of the shipped Phase 6 memory, checkpoint, runtime-adapter, or
  LangChain support-layer behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
