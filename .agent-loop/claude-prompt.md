# Claude Code Task

## Phase
Phase 10U - MCP Action Guardrails And Per-Tool Approval Policies

## Objective
Implement Phase 10U for the agent loop. This slice should add the mutation
boundaries, refusal behavior, auditing, per-tool allow-lists, and approval
prompts required before any non-read-only MCP-assisted runtime action is
allowed through the desktop app.

## Context
Implement the MCP Action Guardrails And Per-Tool Approval Policies slice for
the agent loop. This slice should add the mutation boundaries, refusal
behavior, auditing, per-tool allow-lists, and approval prompts required before
any non-read-only MCP-assisted runtime action is allowed through the desktop
app.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10U as active
- `.agent-loop/phase-plan.md` records Phase 10T as closed history and contains
  a `## Phase 10U - MCP Action Guardrails And Per-Tool Approval Policies`
  section with concrete objective, done criteria, and exclusions
- add the mutation boundaries, refusal behavior, auditing, per-tool allow-
  lists, and approval prompts required before any non-read-only MCP-assisted
  runtime action is allowed through the desktop app
- follow the shipped Phase 10O MCP integration contract, Phase 10S MCP server
  selection UX contract, and the Phase 10T read-only assistance surface,
  preserving the canonical-artifact-first model while introducing bounded
  mutation guardrails
- preserve approval gating, evidence review, external-workspace boundaries,
  desktop/UI boundaries, and the Phase 10I library-callable cap instead of
  introducing hidden automation, silent mutation, or a parallel state store
- add focused validation proving the mutation-capable MCP action guardrails are
  bounded, auditable, and do not widen into RAG runtime, packaging, or
  controlled-concurrency work
- `README.md` reflects that Phase 10U is active and that MCP action guardrails
  and per-tool approval policies are now the implementation focus

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
- no broad MCP runtime expansion beyond the bounded mutation-capable guardrails
  defined for this slice, and no tool-execution path that bypasses the
  approved approval and audit policies
- no RAG, GitHub, policy-pack, packaging, system-tray, or controlled-
  concurrency runtime work
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no claim that fully autonomous PRD-to-product execution is already solved
- no rewrite of current shipped behavior just to make future MCP or autonomy
  work easier
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format.
