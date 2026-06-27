# Claude Code Task

## Phase
Phase 10L - Desktop App Shell Contract

## Objective
Define Phase 10L for the agent loop. This slice should specify the desktop-app shell boundaries, controller/target selection flow, polling model, artifact-opening behavior, and the safe bridge between the desktop shell and the shipped Python orchestrator/view surfaces.

## Context
Define the Desktop App Shell Contract for the agent loop. This slice should
specify the first native desktop-app shell for the external UI, including the
desktop process boundary, controller/target selection flow, refresh/polling
rules, artifact-opening behavior, and the safe bridge to the shipped Python
orchestrator/view surfaces.

## Required work
- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`,
  and `.agent-loop/loop-state.json` identify Phase 10 / 10L as active
- `.agent-loop/phase-plan.md` records Phase 10K as closed history and contains
  a `## Phase 10L - Desktop App Shell Contract` section with concrete
  objective, done criteria, and exclusions
- the repository gains a documentation-first contract defining the first
  native desktop app as a thin local operator shell over the shipped Python
  runtime and canonical artifacts
- the contract defines the desktop toolkit/process boundary, controller-root
  selection flow, attach visibility, refresh/poll rules, artifact-opening
  behavior, and explicit refusal cases without shipping the desktop runtime
  yet
- the contract preserves the shipped CLI-first workflow, approval semantics,
  halt/refusal vocabulary, checkpoint/resume behavior, controller-vs-target
  ownership boundaries, and the Phase 4C activator +
  `APPROVED_FOR_ACTIVATION` activation gate
- focused validation proves the desktop-app contract is bounded, internally
  consistent with Phase 10G through 10K, and reflected accurately in
  planning/docs surfaces
- `README.md` reflects that Phase 10L is active and that the desktop-app
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
- no desktop runtime implementation yet (Phase 10M / 10N)
- no dashboard expansion beyond the shipped Phase 10K slice
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
