# Architecture

This document describes the shipped architecture of the Agentic AI Coding
Loop as of Phase 8A. It is intended to make the project understandable from
a clean clone without prior chat context. It describes what is implemented
today, not what the roadmap proposes for future phases.

For per-phase historical detail see `.agent-loop/phase-plan.md`. For the
agent contract and review format see `AGENTS.md`. For the Claude-side
implementation contract see `CLAUDE.md`. For the long-horizon roadmap see
`ROADMAP.md`.

## High-level model

Three actors collaborate inside a phase-gated local loop:

1. **Codex** is the planner and reviewer. Codex authors the phase plan,
   activates approved proposals, writes per-cycle review verdicts, and
   regenerates fix prompts when a cycle needs additional work.
2. **Claude Code** is the implementation agent. Claude reads the current
   prompt, implements only the active phase, and writes the structured
   per-cycle summary back to disk.
3. **The local orchestrator** (`scripts/agent_loop.py`) drives one cycle at
   a time, captures evidence (via `scripts/run_checks.sh`), validates the
   per-cycle artifact set, and persists loop state.

A human gates every phase transition. The system never auto-commits and
never auto-pushes.

## Loop lifecycle

Each cycle follows a fixed sequence (Phase 3A Orchestrator Contract):

1. Load and validate `.agent-loop/loop-state.json`.
2. Increment `cycle_count` and dispatch Claude on the active prompt
   (`.agent-loop/claude-prompt.md` or `.agent-loop/fix-prompt.md`).
3. Claude writes `.agent-loop/claude-summary.md`.
4. The orchestrator invokes `bash scripts/run_checks.sh` to capture
   evidence (Phase 2B).
5. Codex authors `.agent-loop/codex-review.md` with exactly one verdict:
   `APPROVED_FOR_HUMAN_REVIEW`, `NEEDS_FIXES`, or `FAILED_REQUIRES_HUMAN`.
6. The orchestrator branches on the verdict:
   - `APPROVED_FOR_HUMAN_REVIEW`: persists
     `phase_complete_awaiting_human_approval`; waits for human approval
     before any next-phase activation.
   - `NEEDS_FIXES`: Codex authors `.agent-loop/fix-prompt.md`; the
     orchestrator runs another fix cycle (bounded by `max_cycles`).
   - `FAILED_REQUIRES_HUMAN`: halts immediately.

The four canonical halt families plus the structural halts are documented
under "Halt vocabulary" below.

## Phase model

The phase plan in `.agent-loop/phase-plan.md` is the source of truth for
phase identity. `TASK.md` carries the human-readable active phase plus
phase outcome and next-phase gate. `.agent-loop/current-phase.md` and
`.agent-loop/current-task.md` are Codex-owned per-cycle planning artifacts.

Phase activation is a separate, human-gated step (Phase 4C): a proposal at
`.agent-loop/proposed-phase.md` must carry the literal
`APPROVED_FOR_ACTIVATION` token in a human-authored `## Approval` section
referencing the proposal's `## Label`. Only then does
`python scripts/agent_loop.py activate` consume the proposal and rewrite
the per-phase planning artifacts.

## Approval modes

The orchestrator supports three approval modes (Phase 5A Contract):

- `review` (default on activation): one cycle runs; Codex reviews; humans
  gate phase transition.
- `strict`: adds four human checkpoints inside each cycle
  (`pre_claude_prompt`, `pre_fix_prompt`, `pre_codex_review_normal`,
  `pre_codex_review_fix`). Each pause persists a `halted_awaiting_human_*`
  status; `python scripts/agent_loop.py resume` continues from the matching
  gate.
- `autonomous`: bypasses each of the four strict gates with auditable
  `autonomous mode: bypassing <gate>` notes. Every other hard stop
  (`FAILED_REQUIRES_HUMAN`, `cycle_count >= max_cycles`, structural halts,
  the `phase_complete_*` terminal) is preserved; autonomy never
  auto-progresses phases.

The active mode is recorded in `loop-state.json` under `approval_mode`.

## Halt vocabulary

`loop-state.json` records a single `status` field at any moment. The
operator-visible status values are:

- In-flight: `claude_implementing`, `claude_fixing`, `evidence_capture`,
  `awaiting_codex_review`, `awaiting_claude_implementation`.
- Terminal: `phase_complete_awaiting_human_approval` (success),
  `halted_failed_requires_human`, `halted_max_cycles_reached`.
- Strict-mode gates: `halted_awaiting_human_pre_claude_prompt`,
  `halted_awaiting_human_pre_fix_prompt`,
  `halted_awaiting_human_pre_codex_review_normal`,
  `halted_awaiting_human_pre_codex_review_fix`.
- Token-exhaustion: `halted_awaiting_token_exhaustion_continuation`.
- Operator interrupt: `halted_human_stop`.
- Structural: `halted_input_missing`, `halted_contract_version_mismatch`,
  `halted_review_malformed`, `halted_review_parse_failed`,
  `halted_summary_malformed`, `halted_evidence_incomplete`,
  `halted_evidence_script_unavailable`.

Run `python scripts/agent_loop.py status` for a one-line human-readable
recovery hint per status. The mapping is `STATUS_RECOVERY_HINTS` in
`scripts/agent_loop.py` and is the source of truth for what to do next.

## Runtime adapters

The default runtime is the shipped in-process local orchestrator
(`scripts/agent_loop.py`). One opt-in alternate runtime exists: an
experimental LangGraph mirror (Phase 6N), a pure-stdlib structural
emulation that does not depend on the `langgraph` package and runs as a
canonical-state pre-pass before delegating to the shipped writers.

Runtime selection precedence (Phase 6N): `--runtime` CLI flag > the
`AGENT_LOOP_RUNTIME` environment variable > the persisted
`.agent-loop/runtime-config.json` > default `local`. The persisted file is
managed through `python scripts/agent_loop.py set-runtime-config`
(`--runtime <id>` writes, `--clear` removes).

Canonical state always wins over framework-managed state per the Phase 6M
contract; alternate runtimes that contradict canonical artifacts refuse
fail-closed.

## Memory layer

`.agent-loop/memory/` holds append-mostly durable entries (Phase 6A-6L) in
five categories: `decision`, `failure`, `preference`, `summary`, and
`checkpoint`. Entries are JSON files with deterministic filenames keyed by
content hash plus a UTC timestamp.

Retrieval is **advisory-only** (Phase 6C): every returned entry carries an
`advisory_only = True` structural marker. Memory cannot override canonical
artifacts. The shipped phase-boundary distillation (Phase 6I) writes
`summary` + `decision` (and conditionally `failure`) entries at every
APPROVED phase boundary; the repeated-failure synthesis (Phase 6L)
distills recurring failure patterns into a flat advisory `failure` entry.

## Checkpoint layer

Token-exhaustion (Phase 6F) and Phase 5C strict-mode gates write
checkpoints under `.agent-loop/memory/checkpoint/` so the cycle can resume
without re-running prior work. `python scripts/agent_loop.py resume`
consumes the active checkpoint; `python scripts/agent_loop.py
auto-continue` chains up to four bounded token-exhaustion hops
(`AUTO_CONTINUE_MAX_HOPS = 4`).

## Optional context and LangChain support (advisory)

Two optional advisory layers exist on top of the shipped runtime:

- Phase 6J/6K: declared optional-context file loading and prompt
  integration. Bounded, in-repo, advisory-only.
- Phase 6O: a narrow opt-in LangChain support layer
  (`LangChainPromptHelper`, `LangChainRetrievalHelper`,
  `LangChainToolRegistry`) for prompt construction, retrieval, and a
  static read-only tool registry. Default off; opt-in via the
  `--enable-langchain-support` flag or `AGENT_LOOP_LANGCHAIN_SUPPORT`. Not
  a runtime owner.

Both layers preserve canonical-artifact precedence and refuse fail-closed
on any attempt to override loop-state, checkpoints, memory, evidence, or
review artifacts.

## Artifact ownership

Per CLAUDE.md the following are orchestrator/script-owned and read-only
for Claude unless the active phase explicitly implements the writer:

- `.agent-loop/loop-state.json`
- `.agent-loop/orchestrator.log`
- `.agent-loop/git-diff.patch`
- `.agent-loop/git-status.log`
- `.agent-loop/test-output.log`
- `.agent-loop/lint-output.log`
- `.agent-loop/typecheck-output.log`
- `.agent-loop/build-output.log`

Codex-owned planning surface includes `TASK.md`, `.agent-loop/current-
task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`,
`.agent-loop/claude-prompt.md`, `.agent-loop/fix-prompt.md`, and
`.agent-loop/codex-review.md`. The single Claude-owned per-cycle artifact
is `.agent-loop/claude-summary.md`. Everything else under the repository
is Claude-routed implementation surface unless explicitly reassigned.

## Safety boundaries

- No auto-commit, no auto-push, no force-push, no branch creation, no
  stash, no reset, no checkout, no tag operations. The orchestrator never
  invokes git outside read-only `git status` / `git diff HEAD` for
  evidence capture.
- Every halt is recovery-preserving: a structural refusal never clobbers
  an existing recovery point (`HaltError` plus the strict-gate halt-status
  vocabulary).
- The orchestrator log (`.agent-loop/orchestrator.log`) captures every
  state transition, every audit note (`runtime adapter:`, `langchain
  support:`, `phase-boundary distillation:`, `token exhaustion recorded:`,
  etc.), and every halt reason so the cycle history is reconstructable
  from on-disk artifacts.

## VS Code integration

The shipped VS Code integration (Phase 7A-7C) is purely an operator
convenience layer. It consists of:

- `.vscode/tasks.json` thin task wrappers around shipped CLI surfaces
  (run, resume, auto-continue, plan, activate, bootstrap-prompt, status,
  inspect-artifacts, validate-artifacts, collect evidence, reset runtime
  config).
- `.vscode/settings.json` workspace settings for file associations (the
  `.patch` diff viewer) and file nesting (review/prompt/planning/evidence
  artifact grouping).
- `docs/vscode-artifact-inspection-checklist.md` for the in-editor
  acceptance checks a headless test cannot exercise.

The repository remains fully usable without VS Code; every task maps to
an existing documented CLI surface.

## Boundary summary

Canonical repo artifacts always win over framework-managed state. The
shipped CLI surfaces in `agent_loop.HANDLERS` are the operator source of
truth; the VS Code integration is a thin wrapper. The single Claude-owned
per-cycle artifact is `.agent-loop/claude-summary.md`. Every other write
is either orchestrator-owned (loop state, evidence, logs) or Codex-owned
(planning, review).
