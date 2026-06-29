# Claude Code Task

## Phase
Phase 10S - MCP Server Selection UX Contract

## Objective
Implement Phase 10S for the agent loop. This slice should define the MCP server selection UX contract for the desktop app so operators can understand which MCP servers exist, what each server is allowed to do, which permission class or capability category it belongs to, what safety boundaries apply, and what explicit approvals are required before any MCP enablement becomes user-facing.

## Context
Implement the MCP Server Selection UX Contract slice for the agent loop. This
slice should define how the desktop app presents available MCP servers,
capability categories, permission classes, safety copy, approval requirements,
and deferred-runtime boundaries so operators can understand the future MCP
surface without the repo falsely implying that MCP runtime execution already
ships.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10S as active
- `.agent-loop/phase-plan.md` records Phase 10R as closed history and contains
  a `## Phase 10S - MCP Server Selection UX Contract` section with concrete
  objective, done criteria, and exclusions
- add a concrete MCP server selection UX contract, ideally in a dedicated docs
  artifact, that defines how the desktop app should present available MCP
  servers, permission classes, read-only versus deferred-mutating capability
  labels, per-server safety copy, and operator approval requirements before
  MCP enablement becomes user-facing
- ensure the contract preserves the shipped evidence-review model, approval
  gating, external-workspace boundaries, desktop/UI boundaries, and canonical-
  artifact-first model instead of allowing MCP selections to imply runtime
  behavior that does not yet ship
- distinguish user-visible MCP selection metadata from still-deferred MCP
  runtime execution and mutation-capable tool paths, and define what later
  phases must add before any enablement can become operational
- add focused validation or review coverage proving the new MCP selection UX
  contract matches the actual repo state and does not claim that MCP runtime
  integration already ships
- `README.md` reflects that Phase 10S is active and that the MCP server
  selection UX contract is now the implementation focus

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
- no actual MCP runtime integration, no tool-execution path, and no networked
  tool orchestration in this slice
- no mutation-capable MCP actions, no MCP-driven writes to canonical
  artifacts, and no bypass of the shipped CLI/library/runtime boundaries
- no RAG, GitHub, policy-pack, packaging, system-tray, or controlled-
  concurrency runtime work
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation
- no rewrite of current shipped behavior just to make future desktop or
  autonomy work easier
- no claim that fully autonomous PRD-to-product execution is already solved
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
