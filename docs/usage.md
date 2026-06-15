# Usage

This document walks a new operator through the shipped agent loop from a
clean clone. It covers the prerequisites, the first cycle, the most
common operator flows, and the recovery paths. It describes only what is
implemented today; future-roadmap behavior (see `ROADMAP.md`) is not
covered here.

For the architectural model see `docs/architecture.md`. For the agent
contract see `AGENTS.md`. For the Claude-side implementation contract see
`CLAUDE.md`.

## Prerequisites

- Python 3 (the code is tested on CPython 3.14; the orchestrator uses
  only the standard library).
- `git` on `PATH` for the evidence-capture script.
- Bash for `scripts/run_checks.sh` (the evidence producer). On Windows
  Git Bash is the typical resolver.
- Optional: VS Code, for the operator-convenience tasks under
  `.vscode/tasks.json`.

No third-party Python packages are required. The `langgraph` and
`langchain` packages are explicitly NOT runtime dependencies; the Phase
6N runtime mirror and the Phase 6O support layer are pure-stdlib
structural emulations.

## Shipped CLI surface

`scripts/agent_loop.py` is the single CLI entrypoint. Every subcommand is
registered in `agent_loop.HANDLERS` (the source of truth). The shipped
subcommands fall into four groups:

- **Inspection / status (read-only):** `check-state` (load and validate
  loop-state), `status` (human-readable summary plus recovery hint),
  `inspect-artifacts` (presence / size / mtime of review, prompt,
  planning, and evidence artifacts), `validate-artifacts` (per-cycle
  artifact structural gate).
- **Cycle execution:** `run` (one normal cycle, walking automated fix
  cycles to terminal), `resume` (continue from a strict-mode or
  token-exhaustion halt), `auto-continue` (bounded token-exhaustion
  chaining).
- **Planning / activation:** `plan` (generate
  `.agent-loop/proposed-phase.md`), `activate` (consume an
  `APPROVED_FOR_ACTIVATION` proposal), `bootstrap-prompt` (synthesize
  `.agent-loop/claude-prompt.md` from canonical artifacts).
- **Configuration / advisory:** `set-runtime-config` (persist or clear
  the Phase 6N runtime selection at `.agent-loop/runtime-config.json`),
  `runtime-adapter-eval` (evaluate the local or LangGraph mirror
  adapter), `langchain-support-eval` (default off; opt-in via
  `--enable-langchain-support`), `load-optional-context` and
  `integrate-optional-context` (Phase 6J/6K declared optional context),
  `record-token-exhaustion` (Phase 6F operator entry),
  `build-continuation-context` (Phase 6H continuation prompt
  construction), `distill-phase-boundary-memory` (Phase 6I append-mostly
  durable summary/decision/failure distillation),
  `synthesize-repeated-failures` (Phase 6L flat failure-pattern
  synthesis).

Run any subcommand with `--help` for argument detail. The
`runtime-adapter-eval`, `langchain-support-eval`, and
`distill-phase-boundary-memory` paths are advisory or opt-in; they do
not drive cycle execution by default.

## Clean-clone setup

1. Clone the repository.
2. Verify the prerequisites above (`python --version`, `git --version`,
   `bash --version`).
3. Decide the operator command Claude and Codex will run when the
   orchestrator hands off:
   - `AGENT_LOOP_CLAUDE_CMD` (required to drive Claude end-to-end;
     without it the loop falls back to manual prompt handoff).
   - `AGENT_LOOP_CODEX_CMD` (required to drive Codex end-to-end; same
     manual-handoff fallback applies).
   - `AGENT_LOOP_CLAUDE_MODEL` / `AGENT_LOOP_CODEX_MODEL` (optional
     model-id overrides).
4. Decide the evidence-collection commands `scripts/run_checks.sh` runs:
   - `AGENT_LOOP_TEST_CMD`, `AGENT_LOOP_LINT_CMD`,
     `AGENT_LOOP_TYPECHECK_CMD`, `AGENT_LOOP_BUILD_CMD` (env-var
     override).
   - Or write `.agent-loop/checks.json` with a `{"test": "...", "lint":
     null, "typecheck": "...", "build": null}` shape. Unset / null keys
     report `"Not run"` per the Phase 2A Evidence Collection Contract.

Status, inspection, and read-only subcommands work without any of the
above variables set.

## First cycle

The shortest path from a clean clone to a running loop:

1. `python scripts/agent_loop.py status` shows the active phase and the
   recovery hint for the current loop-state. Use this as your default
   "where am I?" command.
2. If `loop-state.json` reports `awaiting_claude_implementation` and the
   active prompt is in place at `.agent-loop/claude-prompt.md`, run
   `python scripts/agent_loop.py run` to drive the cycle.
3. The orchestrator dispatches Claude (subprocess if
   `AGENT_LOOP_CLAUDE_CMD` is set; otherwise prints a manual handoff
   message), then runs `bash scripts/run_checks.sh` to capture evidence,
   then dispatches Codex for review.
4. When Codex returns `APPROVED_FOR_HUMAN_REVIEW` the cycle halts at
   `phase_complete_awaiting_human_approval`, awaiting human gate before
   any next-phase activation.

Run `python scripts/agent_loop.py status` at any point to see the
current state and the suggested next CLI step.

## Common operator flows

### Drive a cycle

```
python scripts/agent_loop.py run
```

Runs one normal cycle. On `NEEDS_FIXES` the orchestrator walks automated
fix cycles up to `max_cycles`, then halts.

### Recover from a halt

Run `status` to see the recovery hint, then act:

- Strict-mode gate (`halted_awaiting_human_pre_*`): after human review,
  run `python scripts/agent_loop.py resume`.
- Token-exhaustion halt
  (`halted_awaiting_token_exhaustion_continuation`): run
  `python scripts/agent_loop.py auto-continue` for bounded chaining, or
  `python scripts/agent_loop.py resume` for a single-hop resume.
- Structural halt (`halted_input_missing`,
  `halted_contract_version_mismatch`, `halted_summary_malformed`,
  `halted_review_*`, `halted_evidence_*`): inspect with
  `python scripts/agent_loop.py inspect-artifacts` and fix the
  underlying issue before retrying.
- Terminal failure (`halted_failed_requires_human`,
  `halted_max_cycles_reached`): human intervention required. The shipped
  planner refuses to propose the next phase from these states; review
  the canonical artifacts and a fresh Codex-owned activation prompt is
  required before another cycle can run.

### Generate the next-phase proposal

```
python scripts/agent_loop.py plan
```

Writes `.agent-loop/proposed-phase.md`. The planner enforces every
Phase 4A refusal rule; refusals exit 2 and log to
`.agent-loop/planner.log`.

### Activate an approved proposal

A human appends a `## Approval` section to
`.agent-loop/proposed-phase.md` containing the literal
`APPROVED_FOR_ACTIVATION` token on its own line and referencing the
proposal's `## Label`. Then:

```
python scripts/agent_loop.py activate
```

The activator parses the proposal, verifies the approval token, and
performs the activation writes (TASK.md, current-task.md,
current-phase.md, phase-plan.md append-only, loop-state.json reset)
plus the Phase 5F phase-start prompt bootstrap inside one
atomic-or-rollback transaction.

### Inspect artifacts

```
python scripts/agent_loop.py inspect-artifacts
```

Prints a deterministic table of the active review artifacts
(`codex-review.md`, `claude-prompt.md`, `fix-prompt.md`), the active
planning artifacts (`current-task.md`, `current-phase.md`), and the six
Phase 2A/2B evidence files. Output paths are repo-relative so a VS Code
task terminal auto-linkifies every row.

### Reset the persisted runtime selection

```
python scripts/agent_loop.py set-runtime-config --clear
```

Removes `.agent-loop/runtime-config.json` and returns the orchestrator
to the default `local` runtime. Idempotent rc=0.

## VS Code operator entrypoints

`.vscode/tasks.json` ships thin VS Code task wrappers around the shipped
CLI. Each task is a thin `type=process` wrapper invoking
`python scripts/agent_loop.py <subcommand>` from `${workspaceFolder}`.
The current task list:

- `Agent Loop: check state`
- `Agent Loop: status`
- `Agent Loop: reset runtime config`
- `Agent Loop: inspect artifacts`
- `Agent Loop: collect evidence` (the one exception: invokes
  `bash scripts/run_checks.sh` directly per the Phase 2B Evidence
  Collection Contract; the underlying script is the shipped evidence
  producer)
- `Agent Loop: validate artifacts`
- `Agent Loop: run cycle`
- `Agent Loop: resume strict-mode gate`
- `Agent Loop: auto-continue`
- `Agent Loop: plan next phase`
- `Agent Loop: activate approved phase`
- `Agent Loop: bootstrap claude prompt`

For an in-editor acceptance checklist on the inspection workflow see
`docs/vscode-artifact-inspection-checklist.md`.

## Safety boundaries

- No CLI command performs git operations beyond the read-only
  `git status` and `git diff HEAD` captured by
  `scripts/run_checks.sh`.
- Phase activation is human-gated by an explicit
  `APPROVED_FOR_ACTIVATION` token; the orchestrator refuses to
  silently advance phases.
- Every halt persists a status that points at a specific recovery
  command (see `status` for the per-halt hint).
- The orchestrator never modifies `AGENTS.md` or `CLAUDE.md`.

## Where the shipped behavior ends and roadmap begins

Phase 9 (Fully Autonomous PRD-To-Product Mode) and Phase 10 (Future
Product Features) in `ROADMAP.md` describe long-horizon goals not
implemented today. Read those sections as forward-looking, not as
current product behavior. The shipped behavior is everything documented
in `docs/architecture.md` and reachable through the CLI surface listed
above.
