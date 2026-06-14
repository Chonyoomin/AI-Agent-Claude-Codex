# Claude Code Task

## Phase
<<<<<<< Updated upstream
Phase 6N - Experimental LangGraph Runtime Mirror

## Objective
Implement the first experimental LangGraph runtime mirror for Phase 6. This slice should add an opt-in framework-backed execution path that mirrors the shipped local orchestrator's state-machine behavior, halt/refusal vocabulary, checkpoint and continuation handling, durable-memory boundaries, audit signals, and approval-mode semantics while keeping the current local runtime as the default and preserving canonical repo-artifact precedence over any framework-managed state.

## Context
Phase 6N is the first implementation slice that exercises the shipped Phase 6M runtime-adapter contract in code. The repo already has the default local orchestrator and the durable-memory, checkpoint, continuation, optional-context, and repeated-failure surfaces through 6L, plus the 6M adapter contract that defines how an alternate runtime must behave. This phase should add a narrow experimental LangGraph-backed mirror path that is explicitly opt-in, subordinate to the existing artifact contract, and safe to compare against the local runtime. The default local path must remain unchanged when no alternate-runtime selection is made.

## Required work
- Add a narrow opt-in alternate-runtime selection surface in `scripts/agent_loop.py` for an experimental LangGraph-backed runtime mirror while preserving the existing local runtime as the default.
- Implement the experimental LangGraph mirror only to the extent needed to exercise the 6M adapter contract: canonical repo artifacts remain authoritative, and the mirror must refuse fail-closed on contradiction with framework-managed state.
- Mirror the shipped halt/refusal vocabulary, approval-mode behavior, checkpoint/continuation handling, durable-memory boundaries, and audit-note expectations closely enough to evaluate the mirror against the default runtime.
- Ensure the experimental path is explicitly non-default and evaluation-oriented; Phase 6N must not promote the LangGraph runtime to the repo default.
- Add focused tests covering runtime selection, default-runtime preservation, representative halt/refusal mirroring, checkpoint/continuation compatibility, and canonical-precedence preservation for the experimental mirror.
- Update `README.md` so it accurately describes Phase 6N as the active implementation slice and explains the narrow LangGraph-mirror scope at a high level.

## Files likely involved
- `scripts/agent_loop.py`
- `tests/`
- `.agent-loop/phase-plan.md`
- `README.md`
- `TASK.md`
- `.agent-loop/current-task.md`
- `.agent-loop/current-phase.md`
=======
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
>>>>>>> Stashed changes

## Constraints
- Follow `CLAUDE.md`.
- Stay within the current task scope.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Do not rewrite unrelated files.
- Do not delete files unless explicitly instructed.
- Prefer small, testable, reversible changes.
- Add or update tests when behavior changes.
- Keep this slice narrow: implement only the opt-in LangGraph runtime mirror needed to exercise the 6M adapter contract.
- Do not broaden into LangChain support-layer work, CrewAI evaluation, or broader multi-framework orchestration.
- Do not change the default local runtime behavior when no explicit alternate-runtime selection is provided.
- Do not widen autonomy or change the shipped `review`, `strict`, or `autonomous` semantics.
- Preserve canonical repo-artifact precedence over any framework-managed state.

<<<<<<< Updated upstream
## Validation expected
- Run the focused tests you add or update for the experimental mirror.
- Run `python -m pytest tests -q`.
- If you add new Python code paths in `scripts/agent_loop.py`, ensure they still compile cleanly.
=======
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
>>>>>>> Stashed changes

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required Claude Implementation Summary format.
