# Claude Code Task

## Phase
Phase 10O - MCP Integration Contract And Safe Tool Boundary

## Objective
Implement Phase 10O for the agent loop. This slice should define how MCP server support, scoped tool categories, browser/app inspection hooks, and policy rules may assist planning, implementation, and review without bypassing evidence review, approval gates, or ownership boundaries.

## Context
Implement the MCP Integration Contract And Safe Tool Boundary slice for the
agent loop. This slice should define how MCP server support, scoped tool
categories, browser/app inspection hooks, and policy rules may assist
planning, implementation, and review without bypassing evidence review,
approval gates, or ownership boundaries.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10O as active
- `.agent-loop/phase-plan.md` records Phase 10N as closed history and contains
  a `## Phase 10O - MCP Integration Contract And Safe Tool Boundary` section with
  concrete objective, done criteria, and exclusions
- the repository adds a concrete MCP integration contract, ideally in a
  dedicated docs artifact, that defines safe tool categories, ownership
  boundaries, refusal rules, audit expectations, and source-of-truth
  preservation before any MCP runtime path ships
- the contract preserves the shipped evidence-review model, approval gating,
  external-workspace boundaries, desktop/UI boundaries, and the
  canonical-artifact-first model instead of allowing MCP tools to bypass them
- the contract distinguishes read-only assistance from still-deferred
  mutation-capable MCP actions and defines what later phases must add before
  any non-read-only MCP-assisted runtime behavior is allowed
- focused validation or review coverage proves the new MCP contract/docs match
  the actual repo state and do not claim that MCP runtime integration already
  ships
- `README.md` reflects that Phase 10O is active and that the MCP integration
  contract is now the implementation focus

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
  shipped Phase 4 planner / activation separation, or that replaces canonical
  prompt/review/checkpoint artifacts with transient runtime-only state
- no rewrite of current shipped behavior just to make future MCP or autonomy
  work easier
- no regression of the shipped Phase 5 review, strict, bounded autonomous,
  reconciliation, or prompt-bootstrap behavior
- no regression of the shipped Phase 6 memory, checkpoint, continuation,
  runtime-adapter, or LangChain support-layer behavior
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no Git automation

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
