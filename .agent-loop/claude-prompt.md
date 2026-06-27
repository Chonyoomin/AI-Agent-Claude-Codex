# Claude Code Task

## Phase
Phase 10N - Desktop App Action Bridge Initial Slice

## Objective
Implement Phase 10N for the agent loop. This slice should add the first bounded desktop action bridge for attach, inspect, run, and resume flows by delegating only to shipped CLI and library surfaces with explicit refusal handling, audit visibility, and no hidden automation or silent mutation path.

## Context
Implement the Desktop App Action Bridge Initial Slice for the agent loop. This
slice should add the first bounded desktop action bridge for attach, inspect,
run, and resume flows by delegating only to shipped CLI and library surfaces
with explicit refusal handling, audit visibility, and no hidden automation or
silent mutation path.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10N as active
- `.agent-loop/phase-plan.md` records Phase 10M as closed history and contains
  a `## Phase 10N - Desktop App Action Bridge Initial Slice` section with
  concrete objective, done criteria, and exclusions
- the repository adds bounded desktop-side action affordances for attach,
  inspect, run, and resume flows while preserving the shipped CLI/library
  surfaces as the source of execution truth
- desktop actions remain explicit, operator-visible, and fail-closed: no
  hidden background automation, no silent mutating subprocess dispatch, and no
  widened library-callable control surface beyond what the approved phase
  allows
- the action bridge preserves audit visibility, approval semantics,
  controller-vs-target ownership boundaries, and the canonical-artifact-first
  model established by Phases 10L and 10M
- focused validation proves the action bridge is bounded, routes only through
  approved shipped surfaces, and does not widen into packaging, multi-target
  sessions, concurrency runtime, MCP, RAG, GitHub, or other later Phase 10
  work
- `README.md` reflects that Phase 10N is active and that the desktop action
  bridge is now the implementation focus

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
- no packaging, installer, code-signing, auto-update, or system-tray work yet
- no multi-target desktop sessions or controlled-concurrency work
- no hidden background UI-side orchestration or second source of truth
- no MCP integration, RAG layer, GitHub integration, or model-policy
  extensibility work
- no automatic next-phase activation behavior that bypasses or rewrites the
  shipped Phase 4 planner / activation separation, or that replaces canonical
  prompt/review/checkpoint artifacts with transient runtime-only state
- no rewrite of current shipped behavior just to make future desktop-app,
  concurrency, or autonomy work easier
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
