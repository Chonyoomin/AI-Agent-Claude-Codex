# Claude Code Task

## Phase
Phase 7C - Status, Reset, And Recovery UX

## Objective
Implement the VS Code status, reset, and recovery UX layer for the agent loop. This slice should add clear operator-facing run/status/reset ergonomics in VS Code, while preserving the current CLI-first runtime contract and avoiding any change to the orchestrator's ownership, halt, approval, artifact-truth, or recovery semantics.

## Context
Implement the VS Code status, reset, and recovery UX layer for the agent loop.
This slice should add clear operator-facing run/status/reset ergonomics in VS
Code while keeping repo artifacts as the source of truth, preserving halt and
approval behavior, and avoiding any IDE-owned replacement for the shipped
orchestrator.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 7 / 7C as active
- `.agent-loop/phase-plan.md` records Phase 7B as closed history and contains a
  `## Phase 7C - Status, Reset, And Recovery UX` section with concrete
  objective, done criteria, and exclusions
- the VS Code integration exposes clear status, reset, and recovery ergonomics
  for the shipped agent-loop workflow without becoming a parallel source of
  truth
- any new VS Code entrypoints preserve canonical repo-artifact truth by
  delegating to existing repo artifacts and shipped commands rather than
  synthesizing alternate state or bypassing recovery rules
- the VS Code status/reset/recovery layer preserves the shipped halt/refusal
  vocabulary, approval-mode behavior, checkpoint/continuation behavior, and
  artifact ownership boundaries by remaining a thin operator convenience layer
  over the existing workflow
- the repository remains fully usable without VS Code, and the status/reset/
  recovery workflow does not become a VS Code-only control plane
- focused validation covers command mapping, artifact mapping where applicable,
  and proof that the status/reset/recovery layer does not widen runtime or
  ownership scope
- `README.md` reflects that Phase 7C is active and that VS Code status/reset/
  recovery ergonomics are now the implementation focus

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
- no artifact dashboard beyond the narrow status/reset/recovery layer for this
  slice
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
