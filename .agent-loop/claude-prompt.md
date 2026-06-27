# Claude Code Task

## Phase
Phase 10P - Desktop App Operator Setup And CLI Onboarding

## Objective
Implement Phase 10P for the agent loop. This slice should add the first guided desktop setup flow for selecting a controller root, validating a target/work folder, configuring local Claude/Codex CLI adapter commands, checking required local-tool availability, and surfacing fail-closed refusal messages when the environment is not ready.

## Context
Implement the Desktop App Operator Setup And CLI Onboarding slice for the
agent loop. This slice should add the first guided desktop setup flow for
selecting a controller root, validating a target/work folder, configuring
local Claude/Codex CLI adapter commands, checking required local-tool
availability, and surfacing fail-closed refusal messages when the environment
is not ready.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10P as active
- `.agent-loop/phase-plan.md` records Phase 10O as closed history and contains
  a `## Phase 10P - Desktop App Operator Setup And CLI Onboarding` section with
  concrete objective, done criteria, and exclusions
- the repository adds the first guided desktop setup flow that lets an
  operator select a controller root, validate a target/work folder, and
  configure local Claude/Codex CLI adapter commands without manual artifact
  editing
- the setup flow checks for required local-tool availability and surfaces
  explicit, fail-closed refusal messages when the environment is missing
  required prerequisites or violates shipped safety boundaries
- the setup flow preserves the shipped controller-vs-target boundary,
  no-auto-fill identity rules, canonical-artifact-first model, and existing
  CLI/runtime contracts instead of introducing a hidden configuration plane
- focused validation proves the setup flow is bounded, deterministic, and does
  not widen into PRD intake, MCP runtime execution, RAG runtime, packaging, or
  controlled-concurrency work
- `README.md` reflects that Phase 10P is active and that desktop setup and CLI
  onboarding are now the implementation focus

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
- no PRD intake flow, no MCP runtime integration, no tool-execution path, and
  no networked tool orchestration in this slice
- no credential capture, no hidden background config plane, and no bypass of
  the shipped CLI/library/runtime boundaries
- no RAG, policy-pack, packaging, system-tray, or controlled-concurrency
  runtime work
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation, or that replaces canonical
  prompt/review/checkpoint artifacts with transient runtime-only state
- no rewrite of current shipped behavior just to make future desktop or
  autonomy work easier
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
