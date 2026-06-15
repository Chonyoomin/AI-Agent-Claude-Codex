# Claude Code Task

## Phase
Phase 7B - Artifact Inspection And Review Workflow

## Objective
Implement the VS Code artifact-inspection and review workflow layer for the agent loop. This slice should make Codex review artifacts, fix prompts, active task/phase artifacts, and evidence logs easy to open and inspect from VS Code, while preserving the current CLI-first runtime contract and avoiding any change to the orchestrator's ownership, halt, approval, or artifact-truth rules.

## Context
Implement the VS Code artifact-inspection and review workflow layer for the
agent loop. This slice should make Codex review artifacts, fix prompts, active
task/phase artifacts, and evidence logs easy to open and inspect from VS Code
while keeping repo artifacts as the source of truth, preserving halt and
approval behavior, and avoiding any IDE-owned replacement for the shipped
orchestrator.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 7 / 7B as active
- `.agent-loop/phase-plan.md` records Phase 7A as closed history and contains a
  `## Phase 7B - Artifact Inspection And Review Workflow` section with concrete
  objective, done criteria, and exclusions
- the VS Code integration exposes an inspection workflow that makes
  `.agent-loop/codex-review.md`, `.agent-loop/fix-prompt.md`,
  `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and the shipped
  evidence logs easy to open and inspect from the editor
- any new VS Code entrypoints preserve canonical repo-artifact truth by opening
  or delegating to existing repo artifacts and shipped commands rather than
  synthesizing alternate state
- the VS Code inspection layer preserves the shipped halt/refusal vocabulary,
  approval-mode behavior, checkpoint/continuation behavior, and artifact
  ownership boundaries by remaining a thin operator convenience layer over the
  existing workflow
- the repository remains fully usable without VS Code, and the inspection
  workflow does not become a VS Code-only control plane
- focused validation covers artifact-path mapping, command mapping where
  applicable, and proof that the inspection layer does not widen runtime or
  ownership scope
- `README.md` reflects that Phase 7B is active and that artifact inspection and
  review workflow ergonomics are now the implementation focus

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
- no artifact dashboard or reset/recovery UX beyond the narrow
  artifact-inspection layer for this slice
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
