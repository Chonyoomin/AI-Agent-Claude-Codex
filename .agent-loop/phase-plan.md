# Phase Plan

## Active Phase

Phase 8 - Documentation and Project Polish (sub-phase: Phase 8A - Architecture And Usage Docs)

## Phase 0 - Instruction Foundation

### Status

Complete and approved for human review.

### Objective

Create the foundational project instructions and initial loop artifacts that define agent roles, safety rules, review standards, required formats, and the first tracked task state.

### Definition of done

- `README.md` exists and reflects the current project accurately
- `AGENTS.md`, `CLAUDE.md`, and `ROADMAP.md` are aligned
- `TASK.md` exists and defines the active objective
- `.agent-loop/current-task.md` exists
- `.agent-loop/current-phase.md` exists
- `.agent-loop/claude-prompt.md` exists in the required format
- `.agent-loop/loop-state.json` exists with the initial phase state

### Exclusions

- no orchestrator code
- no validation scripts
- no Git automation

## Phase 1 - Manual File-Based Loop

### Status

Complete and approved by human to advance to Phase 2. Terminal verdict for the trial cycle: `APPROVED_FOR_HUMAN_REVIEW` (see `.agent-loop/codex-review.md`).

### Objective

Prove the Codex/Claude/human workflow end to end using only files and documented handoffs, before any orchestrator or evidence-collection script is built.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` record Phase 1 as the active phase
- `.agent-loop/phase-plan.md` records the Phase 1 objective, definition of done, and exclusions
- `.agent-loop/claude-prompt.md` holds the active Phase 1 prompt in the required Claude task format
- `.agent-loop/loop-state.json` reflects the Phase 1 cycle state (`phase`, `task`, `status`, `cycle_count`, `max_cycles`, `last_verdict`)
- `README.md` documents that the manual file-based loop is the current operating mode and outlines the by-hand workflow
- the repository is ready, with no additional scaffolding, to capture one full manual cycle of:
  - Codex-authored `.agent-loop/claude-prompt.md`
  - Claude-authored `.agent-loop/claude-summary.md`
  - manually captured `.agent-loop/git-diff.patch` and `.agent-loop/git-status.log`
  - manually captured `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log` (or an explicit "Not run" note where applicable)
  - Codex-authored `.agent-loop/codex-review.md` with exactly one allowed verdict
  - Codex-authored `.agent-loop/fix-prompt.md` if and only if the verdict is `NEEDS_FIXES`

### Exclusions

- no `scripts/run_checks.sh` (Phase 2)
- no `scripts/agent_loop.py` (Phase 3)
- no automated diff, status, or log capture
- no automated verdict parsing
- no approval-mode logic (Phase 5)
- no editor integration (Phase 7)
- no changes to `AGENTS.md` or `CLAUDE.md`

## Phase 2 - Evidence Collection Automation

Phase 2 is delivered in two sub-phases:

- Phase 2A - Evidence Collection Contract (planning and documentation; this sub-phase)
- Phase 2B - Implement `scripts/run_checks.sh` against the contract (deferred until 2A is approved)

## Phase 2A - Evidence Collection Contract

### Status

Complete and approved by human to advance to Phase 2B. Terminal verdict: `APPROVED_FOR_HUMAN_REVIEW`.

### Objective

Specify, before any implementation, how evidence collection must behave: where validation commands come from, how each state (passed / failed / not run / inconclusive) is recorded, and what each evidence file is expected to contain. The contract is what Phase 2B will be implemented against.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 2 / 2A as active
- `.agent-loop/phase-plan.md` contains a Phase 2A section that defines the Evidence Collection Contract below
- `README.md` notes the Phase 2A active status and points readers at the contract
- `ROADMAP.md` reflects the 2A / 2B decomposition of Phase 2
- the contract is concrete enough that Phase 2B can be implemented from it without further design decisions
- no `scripts/run_checks.sh` is created
- no fabricated `.agent-loop/git-diff.patch`, `.agent-loop/git-status.log`, or `.agent-loop/*-output.log` files are created

### Exclusions

- no implementation of `scripts/run_checks.sh` (Phase 2B)
- no orchestrator code (Phase 3)
- no validation suite added to the repository (still a documentation-only project)
- no changes to `AGENTS.md` or `CLAUDE.md`

### Evidence Collection Contract

The contract below is what Phase 2B's `scripts/run_checks.sh` must satisfy. It is also what a human running evidence capture by hand should follow so that manual output stays interchangeable with future script output.

#### Command discovery

Evidence collection runs two kinds of work: unconditional git capture, and configured validation commands.

Unconditional git capture (always runs):

- `git status` -> `.agent-loop/git-status.log`
- `git diff HEAD` (working tree vs HEAD, including unstaged and staged changes; text diffs only, binary files are summarized by Git's default behavior rather than emitted as full binary patches) -> `.agent-loop/git-diff.patch`

Configured validation commands (run only if configured):

- logical names: `test`, `lint`, `typecheck`, `build`
- each name is configured to either a single shell command string or to no value at all
- there is no auto-detection: if a name is not configured, that command is treated as `Not run: not configured`, never silently inferred from `package.json`, `pyproject.toml`, etc.

Configuration source (precedence, highest first):

1. environment variables, one per command: `AGENT_LOOP_TEST_CMD`, `AGENT_LOOP_LINT_CMD`, `AGENT_LOOP_TYPECHECK_CMD`, `AGENT_LOOP_BUILD_CMD`
2. a project-local config file at `.agent-loop/checks.json` (created by Phase 2B if needed; not part of Phase 2A) with shape:

```json
{
  "test": "pytest -q",
  "lint": null,
  "typecheck": "mypy .",
  "build": null
}
```

If both an env var and a config file value are set for the same name, the env var wins. An explicit `null` (or empty string) means "intentionally not configured" and produces a `Not run: not configured` log, not an error. A missing key in `checks.json` is treated identically to `null`.

#### State vocabulary

Every validation log records exactly one state, drawn from the same vocabulary `AGENTS.md` uses for `Validation result`:

- `Passed` - the command ran and exited 0
- `Failed` - the command ran and exited non-zero, OR the command was configured but failed to launch (binary not found, permission denied, etc.)
- `Not run` - the command was intentionally not configured for this project, OR was skipped for an explicitly recorded reason
- `Inconclusive` - the command launched but its state cannot be determined cleanly (for example, timeout reached, killed by signal, or output is structurally ambiguous)

State must never be inferred silently. The header of each log file records the state explicitly so a reviewer never has to guess.

#### Behavior on each state

- `Passed`: full stdout+stderr captured to the log; script continues to the next command; script exit code stays 0 unless another command fails.
- `Failed`: full stdout+stderr captured; script continues to the next command (never aborts on first failure - all evidence must be collected); script exit code becomes non-zero at the end.
- `Not run`: log file is still written, containing only the header (no stdout+stderr body); script continues; script exit code is not affected.
- `Inconclusive`: full captured output (truncated with an explicit marker if a length limit applies) plus the reason (`timeout`, `signal=SIGKILL`, etc.); script continues; script exit code becomes non-zero at the end.

#### Missing or failed-to-launch commands

A configured command whose binary cannot be found, cannot be executed, or fails to launch for any pre-exit reason is recorded as `Failed` with the reason captured in the header (`reason: command not found`, `reason: permission denied`, etc.) and any stderr the OS produced placed in the body. This is distinct from `Not run`, which is reserved for "no configuration was provided".

#### Log file contents

Every evidence file begins with a single-block ASCII header followed by a separator line `----` (four hyphens, on its own line), followed by the raw body.

`.agent-loop/git-status.log`:

```
# git status
captured_at: <ISO 8601 UTC timestamp>
command: git status
exit_code: 0
state: Passed
----
<raw `git status` output>
```

`.agent-loop/git-diff.patch`:

```
# git diff (working tree vs HEAD, includes unstaged and staged changes)
captured_at: <ISO 8601 UTC timestamp>
command: git diff HEAD
exit_code: 0
state: Passed
----
<raw unified diff output>
```

Each of `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log`:

```
# <logical name>
captured_at: <ISO 8601 UTC timestamp>
command: <resolved shell command string, or "(not configured)">
exit_code: <integer, or "n/a" when state is Not run or failed-to-launch>
state: Passed | Failed | Not run | Inconclusive
reason: <optional, present when state is Not run, failed-to-launch, or Inconclusive>
----
<merged stdout and stderr, or empty body when state is Not run>
```

All headers and separators use plain ASCII. No smart quotes, em-dashes, or other non-ASCII punctuation. CRLF and LF line endings are both acceptable; the script should not normalize the body's line endings.

#### Safety constraints (script-side)

The future `scripts/run_checks.sh` must, by construction:

- never commit, push, tag, branch, stash, reset, checkout, or otherwise mutate Git history or working-tree state
- never delete, rename, or move any file outside `.agent-loop/`
- never modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `TASK.md`, `README.md`, `.agent-loop/claude-prompt.md`, `.agent-loop/claude-summary.md`, `.agent-loop/codex-review.md`, `.agent-loop/fix-prompt.md`, `.agent-loop/phase-plan.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, or `.agent-loop/loop-state.json`
- only write the six evidence files listed above (overwriting them is allowed)
- never expand shell variables from configured command strings beyond what the user's shell would do; configuration values are executed verbatim
- run with a working-directory anchored at the repository root, regardless of where the user invokes it from

#### Exit code

- `0` if every command's state is `Passed` or `Not run`
- non-zero if any command's state is `Failed` or `Inconclusive`

The exit code is a fast signal; the per-log `state:` field is the source of truth for review.

## Phase 2B - Implement `scripts/run_checks.sh`

### Status

Complete and approved by human to advance to Phase 3. Terminal verdict for Phase 2: `APPROVED_FOR_HUMAN_REVIEW` (see `.agent-loop/codex-review.md`).

### Objective

Implement `scripts/run_checks.sh` against the approved Phase 2A Evidence Collection Contract. Implementation only; no contract changes.

### Definition of done

- `scripts/run_checks.sh` exists and is executable.
- The script anchors its working directory at the repository root regardless of where it is invoked from.
- Unconditional git capture: `git status` -> `.agent-loop/git-status.log`; `git diff HEAD` -> `.agent-loop/git-diff.patch`.
- Validation command discovery resolves env vars first, then `.agent-loop/checks.json`, with explicit `Not run` for unconfigured commands.
- Each of `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log` is written with the contract's header + `----` separator + body format.
- State values are drawn from the contract vocabulary (`Passed | Failed | Not run | Inconclusive`).
- Evidence collection never aborts on first failure; every evidence file is written every run.
- Configured commands that fail to launch are recorded as `Failed` (not `Not run`); unconfigured commands are recorded as `Not run` (never `Failed`).
- Script exit code is `0` iff every command's state is `Passed` or `Not run`; non-zero if any state is `Failed` or `Inconclusive`.
- Script never commits, pushes, mutates git history, deletes files, modifies protected files, or writes outside `.agent-loop/`.
- `README.md` documents how to run the script.

### Exclusions

- no changes to the Phase 2A contract
- no orchestrator code (`scripts/agent_loop.py`, Phase 3)
- no creation of `.agent-loop/checks.json` (the script must work with or without it; whether to create one is a per-project decision)
- no real test/lint/typecheck/build suite added to the repository
- no changes to `AGENTS.md` or `CLAUDE.md`

## Phase 3 - Scripted Orchestrator MVP

### Status

Closed and treated as the established prior chapter for the purposes of activating Phase 4. The Phase 3 sub-phase history (3A Orchestrator Contract; 3B initial-slice implementation; 3C automated fix-cycle handling; 3D subprocess-driven Claude/Codex adapters; 3E end-to-end MVP verification) is recorded in the sub-phase sections below and in `git log`. Phase 4 builds the planning layer on top of this established orchestrator surface.

Phase 3 was delivered in sub-phases:

- Phase 3A - Orchestrator Contract (planning and documentation)
- Phase 3B - Implement `scripts/agent_loop.py` initial slice (scaffold + normal-cycle path)
- Phase 3C - Automated Fix-Cycle Handling (`NEEDS_FIXES` verdict-loop branch + threshold-policy halt)
- Phase 3D - Subprocess-Driven Claude/Codex Adapters (with manual-handoff fallback)
- Phase 3E - End-to-End MVP Verification (real bounded `python scripts/agent_loop.py run` invocations against the actual `.agent-loop/` workflow)

## Phase 3A - Orchestrator Contract

### Status

Complete and approved by human to advance to Phase 3B. The Phase 3A Orchestrator Contract below is frozen; Phase 3B implements against it without rewriting it. The latest Codex review at `.agent-loop/codex-review.md` returned `NEEDS_FIXES` on a documentation-only summary issue; the human has reviewed the contract directly and authorized advancing.

### Objective

Specify, before any implementation, how `scripts/agent_loop.py` must behave: which files it reads, which files it is allowed to write, the order of operations in a normal cycle and in a fix cycle, how it invokes `scripts/run_checks.sh`, how it parses and acts on each allowed Codex verdict, how it updates `.agent-loop/loop-state.json`, and what stop conditions it enforces. The contract is what Phase 3B will be implemented against.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 3 / 3A as active
- `.agent-loop/phase-plan.md` records Phase 2 / 2B as complete history and contains a Phase 3A section that defines the Orchestrator Contract below
- `README.md` reflects the Phase 3A active status and points readers at the contract
- `ROADMAP.md` reflects the 3A / 3B decomposition of Phase 3
- the contract is concrete enough that Phase 3B can be implemented from it without further design decisions
- no `scripts/agent_loop.py` is created
- no protected files (`AGENTS.md`, `CLAUDE.md`) are modified

### Exclusions

- no implementation of `scripts/agent_loop.py` (Phase 3B)
- no changes to the Phase 2A Evidence Collection Contract
- no changes to `scripts/run_checks.sh`
- no fabricated evidence files
- no approval-mode behavior (Phase 5)
- no editor integration (Phase 7)
- no changes to `AGENTS.md` or `CLAUDE.md`

### Orchestrator Contract

The contract below is what Phase 3B's `scripts/agent_loop.py` must satisfy. It is also a reference for any human running the loop by hand so manual operation stays interchangeable with future orchestrator behavior.

#### Inputs the orchestrator reads (read-only)

- `TASK.md`
- `.agent-loop/current-task.md`
- `.agent-loop/current-phase.md`
- `.agent-loop/phase-plan.md`
- `.agent-loop/claude-prompt.md` (authored by Codex per implementation cycle)
- `.agent-loop/claude-summary.md` (authored by Claude per cycle)
- `.agent-loop/codex-review.md` (authored by Codex per cycle)
- `.agent-loop/fix-prompt.md` (authored by Codex per fix cycle)
- `.agent-loop/checks.json` (optional; consumed by `scripts/run_checks.sh`, not by the orchestrator directly)
- `AGENTS.md` and `CLAUDE.md` (referenced for boundary enforcement; never modified)

The orchestrator must treat these files as read-only inputs. It must never author or overwrite them.

#### Files the orchestrator is allowed to write

- `.agent-loop/loop-state.json` - status transitions, cycle counter, verdict bookkeeping (see field-ownership rules below)
- `.agent-loop/orchestrator.log` (optional) - a per-run log of orchestrator decisions; scoped to `.agent-loop/`; never used as authoritative evidence

The orchestrator must not write any other file.

#### Files the orchestrator must never write

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md` (Codex-owned planning state)
- `.agent-loop/claude-prompt.md`, `.agent-loop/fix-prompt.md`, `.agent-loop/codex-review.md` (Codex-owned per-cycle artifacts)
- `.agent-loop/claude-summary.md` (Claude-owned)
- `.agent-loop/git-status.log`, `.agent-loop/git-diff.patch`, `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log` (owned by `scripts/run_checks.sh`; only overwritten via that script)
- `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`, `.gitattributes`, `.gitignore`
- `scripts/run_checks.sh`, `scripts/agent_loop.py`, any other script

#### Normal cycle (initial implementation cycle for a sub-phase)

Preconditions:

- `.agent-loop/loop-state.json` exists; `phase` and `sub_phase` reflect the active sub-phase as set by Codex
- `status` is a ready-to-start state (`awaiting_claude_implementation` or equivalent)
- `.agent-loop/claude-prompt.md` exists, is non-empty, and is in the required Claude task format

Steps:

1. Increment `cycle_count` (see counter rules) and set `status = claude_implementing` in `loop-state.json`.
2. Invoke Claude Code with the active prompt (`.agent-loop/claude-prompt.md`).
3. Wait for Claude's handoff: `.agent-loop/claude-summary.md` updated, and its `## Phase` value matches the active phase or sub-phase.
4. Set `status = evidence_capture` in `loop-state.json`.
5. Invoke `bash scripts/run_checks.sh` from the repository root. Capture the script's exit code. A non-zero exit does NOT abort the loop - the per-log `state:` field is the source of truth for review; only a script-launch failure (binary missing, non-executable) aborts.
6. Set `status = awaiting_codex_review` in `loop-state.json`.
7. Hand the review context to Codex (the orchestrator must not author `.agent-loop/codex-review.md`).
8. Wait for `.agent-loop/codex-review.md` to be updated. Parse exactly one verdict line.
9. Branch on the verdict (see verdict handling).

#### Fix cycle

Preconditions:

- last parsed verdict was `NEEDS_FIXES`
- `.agent-loop/fix-prompt.md` exists, is non-empty, and is in the required Claude fix task format
- if `cycle_count >= max_cycles`, a human has explicitly approved continuing because the issue set materially changed or narrowed under the cycle-threshold policy

Steps:

1. Increment `cycle_count` and set `status = claude_fixing` in `loop-state.json`.
2. Invoke Claude Code with the fix prompt (`.agent-loop/fix-prompt.md`).
3. Wait for Claude's handoff: `.agent-loop/claude-summary.md` updated, and its content reflects the fix-cycle work.
4. Set `status = evidence_capture`.
5. Re-invoke `bash scripts/run_checks.sh` from the repository root.
6. Set `status = awaiting_codex_review`.
7. Wait for `.agent-loop/codex-review.md` to be updated. Parse the verdict.
8. Branch on the verdict.

#### Evidence-capture invocation

- Always invoked as `bash scripts/run_checks.sh` with the current working directory set to the repository root.
- The orchestrator must not set, unset, or rewrite the `AGENT_LOOP_TEST_CMD`, `AGENT_LOOP_LINT_CMD`, `AGENT_LOOP_TYPECHECK_CMD`, or `AGENT_LOOP_BUILD_CMD` environment variables; whatever the user's shell provides is passed through unchanged.
- The script's exit code is recorded in `orchestrator.log` (if used) but does not by itself decide the verdict; Codex reads the per-log `state:` fields.
- A script-launch failure (script missing or not executable) is a halt condition: `status = halted_evidence_script_unavailable`, stop, require human intervention.

#### Version-aware adapter layer

The orchestrator's core loop must remain stable across Claude and Codex version changes. Model invocation specifics (which CLI binary or API endpoint to call, which flags to pass, how to stream and capture output, how to detect end-of-response, how to surface tool-use vs. text-only modes) must NOT be hardcoded into the core loop. Instead:

- The orchestrator must isolate Claude invocation behind a `claude_adapter` module (suggested path `scripts/agent_loop/adapters/claude.py`).
- The orchestrator must isolate Codex invocation behind a `codex_adapter` module (suggested path `scripts/agent_loop/adapters/codex.py`).
- Each adapter exposes a stable interface to the core loop: at minimum a function that takes a prompt file path and returns a structured `ExecutionResult` (exit code, captured stdout/stderr path, model identifier actually used, wall-clock duration).
- The core loop must select adapters by version-aware configuration (a config field, an environment variable, or a CLI flag), not by hardcoded model strings.
- A new Claude or Codex CLI version that changes flags, output format, or invocation surface must be addressable by editing or adding an adapter, NOT by editing the core loop.
- Adapters must record the resolved model identifier they actually invoked (e.g., the literal `claude-opus-4-7` or `claude-sonnet-4-6` string) into the cycle's record so reviewers can tie a given cycle's evidence to a specific model version.
- The core loop must never parse model-specific output formats; that translation is the adapter's job.

This is a Phase 3B code-organization constraint. Phase 3A documents it; Phase 3B implements it.

#### Artifact schema validation (fail closed)

The orchestrator must validate the structural shape of each Codex- and Claude-authored artifact BEFORE acting on it. A malformed artifact is a halt condition; the orchestrator must never silently advance the loop, retry a malformed artifact, or guess at missing structure. All validation is fail-closed.

Required well-formed checks:

- `.agent-loop/claude-summary.md` must contain all of these top-level headers in order, each followed by a non-empty body: `# Claude Implementation Summary`, `## Phase`, `## Task`, `## Files changed`, `## What was implemented`, `## What was not implemented`, `## Tests added or changed`, `## Validation run`, `## Assumptions`, `## Risk areas`. The `## Phase` value must match the active `phase` or `sub_phase` in `loop-state.json`. On failure: `status = halted_summary_malformed`; stop; require human intervention.
- `.agent-loop/codex-review.md` must contain all of these top-level headers in order, each followed by a non-empty body: `# Codex Review`, `## Verdict`, `## Review summary`, `## Claude summary accuracy`, `## Scope control`, `## Validation result`, `## Issues found`. The `## Verdict` body must contain exactly one of `APPROVED_FOR_HUMAN_REVIEW`, `NEEDS_FIXES`, or `FAILED_REQUIRES_HUMAN`; zero, multiple, or unrecognized verdict tokens are a parse failure (`status = halted_review_parse_failed`). Any other structural defect (missing header, empty body, wrong order) is a schema failure (`status = halted_review_malformed`). Both halt cases stop the loop and require human intervention.
- `.agent-loop/fix-prompt.md` (only required when the latest verdict was `NEEDS_FIXES`) must contain all of these top-level headers in order, each followed by a non-empty body: `# Claude Code Fix Task`, `## Objective`, `## Context`, `## Required fixes`, `## Constraints`, `## Required output`. On failure: `status = halted_fix_prompt_malformed`; stop; require human intervention.
- `.agent-loop/loop-state.json` must be valid JSON; required keys (`phase`, `sub_phase`, `task`, `status`, `cycle_count`, `max_cycles`) must be present with non-null values of the documented types; `contract_version` must be readable as a string when present. On failure: `status = halted_input_missing`; stop; require human intervention.

Validation order in each cycle:

1. Before invoking Claude: validate `claude-prompt.md` (or `fix-prompt.md` on a fix cycle) and `loop-state.json`.
2. After Claude returns: validate `claude-summary.md`.
3. After `scripts/run_checks.sh` returns: confirm all six evidence files exist and each header has a `state:` field drawn from the contract vocabulary.
4. After Codex returns: validate `codex-review.md` structure first, then parse the verdict.

The orchestrator's validator must be the same shape as the documented format. If the formats in `AGENTS.md` or `CLAUDE.md` change, the validator must be updated to match (this is a contract change, not a silent tolerance).

#### Verdict handling

Allowed verdict strings (exact match; anything else is a parse failure):

- `APPROVED_FOR_HUMAN_REVIEW`
- `NEEDS_FIXES`
- `FAILED_REQUIRES_HUMAN`

Per verdict:

- `APPROVED_FOR_HUMAN_REVIEW`: set `last_verdict = APPROVED_FOR_HUMAN_REVIEW`, `last_verdict_phase = <current sub-phase or phase>`, `status = phase_complete_awaiting_human_approval`. Stop. Do not start the next phase. The next phase begins only when the human explicitly starts it and Codex updates `TASK.md`, `current-task.md`, `current-phase.md`, and `phase-plan.md`.
- `NEEDS_FIXES`: set `last_verdict = NEEDS_FIXES`. If `cycle_count >= max_cycles`, do not continue automatically. Compare the latest findings to the prior findings under the cycle-threshold policy. If the same issue repeats with materially the same outcome and no meaningful progress, set `status = halted_max_cycles_reached` and stop. If the issue set materially changed or narrowed, continue only after explicit human approval and an intentional reset/raise of the cycle limit state. Otherwise, wait for `.agent-loop/fix-prompt.md` to be updated by Codex, then enter the fix cycle.
- `FAILED_REQUIRES_HUMAN`: set `last_verdict = FAILED_REQUIRES_HUMAN`, `status = halted_failed_requires_human`. Stop. Do not retry. Require human intervention.
- parse failure (no verdict line, malformed verdict line, multiple verdict lines, unknown string): set `status = halted_review_parse_failed`. Stop. Do not retry. Require human intervention.

#### `loop-state.json` updates

The orchestrator may write only these fields:

- `status`
- `cycle_count`
- `last_verdict`
- `last_verdict_phase`
- `claude_version` (the resolved model identifier the Claude adapter actually invoked, e.g. `claude-opus-4-7`)
- `codex_version` (the resolved version identifier of the Codex adapter, e.g. `codex-cli-2026-05` or whatever the adapter reports; `null` if not yet known)
- `orchestrator_version` (the running version of `scripts/agent_loop.py` itself, e.g. a semver string or short git SHA; `null` only when no orchestrator has yet run for this state)

The orchestrator must NOT write these fields (Codex- or human-owned):

- `phase`
- `sub_phase`
- `task`
- `max_cycles`
- `contract_version` (the version identifier of the orchestrator contract this state was produced under, e.g. `phase-3a-v2`; bumped by Codex or a human whenever the contract changes; the orchestrator reads it to refuse to operate against an incompatible contract)

Version-field write rules:

- `claude_version` is written by the orchestrator at the start of each Claude invocation, using the model identifier the Claude adapter resolves and reports back. The orchestrator must not invent or hardcode this string; it comes from the adapter.
- `codex_version` is written by the orchestrator after Codex's adapter reports the version it used to produce the latest review. If the Codex adapter cannot self-report, the value is `null` and a `note` is written to `orchestrator.log`; the orchestrator must not silently fabricate one.
- `orchestrator_version` is written by the orchestrator at the start of every run.
- `contract_version` is read at startup. If the value is missing, malformed, or does not match a version the running orchestrator declares support for, the orchestrator must halt with `status = halted_contract_version_mismatch` and require human intervention. Compatibility is declared by the orchestrator binary, not inferred.

Allowed `status` vocabulary (the orchestrator uses these and only these values):

- `awaiting_claude_implementation` - waiting for the first cycle of a new sub-phase to begin
- `claude_implementing` - Claude has been invoked with `.agent-loop/claude-prompt.md`
- `claude_fixing` - Claude has been invoked with `.agent-loop/fix-prompt.md`
- `evidence_capture` - `scripts/run_checks.sh` is running
- `awaiting_codex_review` - waiting for `.agent-loop/codex-review.md` to be updated
- `phase_complete_awaiting_human_approval` - verdict was `APPROVED_FOR_HUMAN_REVIEW`; loop halted
- `halted_max_cycles_reached` - verdict was `NEEDS_FIXES` but `cycle_count >= max_cycles`
- `halted_failed_requires_human` - verdict was `FAILED_REQUIRES_HUMAN`
- `halted_review_parse_failed` - the verdict line could not be parsed cleanly (zero, multiple, or unrecognized verdict tokens)
- `halted_review_malformed` - `codex-review.md` failed structural validation (missing header, empty body, wrong order)
- `halted_summary_malformed` - `claude-summary.md` failed structural validation, OR its `## Phase` value did not match the active phase / sub-phase
- `halted_fix_prompt_malformed` - `fix-prompt.md` was required (latest verdict was `NEEDS_FIXES`) but failed structural validation
- `halted_evidence_script_unavailable` - `scripts/run_checks.sh` is missing or not executable
- `halted_evidence_incomplete` - `scripts/run_checks.sh` ran but one or more of the six evidence files is missing or lacks a `state:` field from the contract vocabulary
- `halted_input_missing` - a required input file (e.g., `claude-prompt.md`, `fix-prompt.md` when expected, or `loop-state.json` itself) is missing, empty, or malformed
- `halted_contract_version_mismatch` - `contract_version` in `loop-state.json` is missing or not supported by the running orchestrator
- `halted_human_stop` - the orchestrator received an explicit human stop signal

All other status values are reserved for future sub-phases or out-of-band human edits; the orchestrator must not invent new statuses.

#### Cycle counting

- `cycle_count` is reset to `0` by Codex when a new sub-phase is activated (Codex writes the reset value when updating `loop-state.json` for the new sub-phase).
- `cycle_count` may also be reset to `0` within the same sub-phase when a human explicitly authorizes a threshold-policy reset after review. This is a Codex-owned state correction, not an automatic orchestrator action.
- The orchestrator increments `cycle_count` at the START of each Claude invocation (both implementation and fix cycles).
- `max_cycles` is a safety threshold on Claude invocations within a single sub-phase. It is human- and Codex-owned; the orchestrator only enforces it.
- Reaching `cycle_count >= max_cycles` does NOT automatically mean the phase has failed. It means the loop must stop and require an explicit human decision before another automated fix cycle can begin.
- When the threshold is reached and the latest verdict is `NEEDS_FIXES`, Codex (or the human, in a manual review) must compare the latest findings with the prior findings:
  - if the same issue repeats with materially the same outcome and no meaningful progress, the loop halts with `status = halted_max_cycles_reached` and requires human intervention
  - if the issue set has materially changed or narrowed, another cycle may proceed only after explicit human approval and an intentional update to `max_cycles` or a new sub-phase activation
- The orchestrator must never silently continue past the threshold on its own.

#### Stop conditions

The orchestrator must stop and return control to the human in any of these cases:

- verdict is `APPROVED_FOR_HUMAN_REVIEW` (phase complete; next phase requires human start)
- verdict is `FAILED_REQUIRES_HUMAN`
- verdict line could not be parsed cleanly (`halted_review_parse_failed`)
- `codex-review.md` failed structural schema validation (`halted_review_malformed`)
- `claude-summary.md` failed structural schema validation, or its `## Phase` value did not match the active phase / sub-phase (`halted_summary_malformed`)
- `fix-prompt.md` was required and failed structural schema validation (`halted_fix_prompt_malformed`)
- `cycle_count >= max_cycles`, another cycle would be required, and a human has not explicitly approved continuing after reviewing convergence (`halted_max_cycles_reached`)
- a required input file is missing or empty when needed - `claude-prompt.md` at cycle start, `fix-prompt.md` after `NEEDS_FIXES`, `codex-review.md` after evidence capture, or `loop-state.json` itself missing/malformed (`halted_input_missing`)
- `scripts/run_checks.sh` is missing or not executable (`halted_evidence_script_unavailable`)
- `scripts/run_checks.sh` ran but one or more of the six evidence files is missing or lacks a contract-vocabulary `state:` value (`halted_evidence_incomplete`)
- `contract_version` in `loop-state.json` is missing or not supported by the running orchestrator (`halted_contract_version_mismatch`)
- the orchestrator would otherwise be required to modify a protected file
- the orchestrator receives an explicit human stop signal, e.g. SIGINT (`halted_human_stop`)

Restart from a halt state is always a human action. The orchestrator must never silently retry past a halt, accept a partial artifact, guess at missing structure, or continue automatically past the cycle threshold without an explicit human decision.

#### Prohibited actions

The orchestrator must, by construction:

- never author or modify `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, or `.agent-loop/phase-plan.md`
- never author or modify `.agent-loop/claude-prompt.md`, `.agent-loop/claude-summary.md`, `.agent-loop/codex-review.md`, or `.agent-loop/fix-prompt.md`
- never modify `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`, `.gitattributes`, or `.gitignore`
- never modify, delete, rename, or move any file outside `.agent-loop/` (invoking `scripts/run_checks.sh` is allowed; modifying it is not)
- never overwrite the six evidence files directly; those are written only by `scripts/run_checks.sh`
- never commit, push, tag, branch, merge, stash, reset, checkout, or otherwise mutate Git history or working-tree state
- never advance the loop past a halt state without explicit human intervention
- never invent verdict synonyms, retry parse failures, or treat unrecognized verdicts as approval
- never silently advance past a malformed `claude-summary.md`, `codex-review.md`, or `fix-prompt.md`; structural validation is fail-closed
- never write `phase`, `sub_phase`, `task`, `max_cycles`, or `contract_version` in `loop-state.json` (those are Codex- or human-owned)
- never invent, hardcode, or fabricate `claude_version`, `codex_version`, or `orchestrator_version` values; each must come from the adapter or the running orchestrator self-identifying
- never hardcode Claude or Codex CLI invocation specifics (binary path, flags, output parsing) into the core loop; those live in the version-aware adapter layer
- never set or unset Claude / Codex / shell credentials, API keys, or environment variables beyond what the loop documents
- never write fake or inferred evidence files

#### Failure modes worth naming

These are the realistic failure modes the orchestrator must handle gracefully (always: record state in `loop-state.json`, write to `orchestrator.log` if present, halt, return control):

- Claude exits non-zero or produces no `claude-summary.md` (`halted_summary_malformed` or `halted_input_missing`)
- Claude's `claude-summary.md` is structurally malformed or its `## Phase` does not match (`halted_summary_malformed`)
- `scripts/run_checks.sh` is missing or not executable (`halted_evidence_script_unavailable`)
- `scripts/run_checks.sh` ran but the six evidence files are incomplete or lack contract-vocabulary `state:` values (`halted_evidence_incomplete`)
- `codex-review.md` is structurally malformed (`halted_review_malformed`)
- `codex-review.md` verdict line is missing, multiple, or unrecognized (`halted_review_parse_failed`)
- `fix-prompt.md` is missing, empty, or structurally malformed after a `NEEDS_FIXES` verdict (`halted_fix_prompt_malformed` or `halted_input_missing`)
- `loop-state.json` is missing or malformed JSON (`halted_input_missing`)
- `contract_version` is missing or not supported by the running orchestrator (`halted_contract_version_mismatch`)
- the Claude adapter cannot resolve a model identifier to write into `claude_version` (treat as adapter failure; halt with `halted_input_missing` and require human intervention)
- the Codex adapter cannot resolve a version identifier (write `null` to `codex_version` and continue; do NOT halt; note in `orchestrator.log`)

## Phase 3B - Implement `scripts/agent_loop.py` (initial slice)

### Status

Complete and approved by human to advance to Phase 3C. The Phase 3B scaffold (repository-root discovery, `loop-state.json` helpers, artifact validators, normal-cycle control path, fail-closed manual-handoff adapters, normal-cycle start-state gate) is in place; Phase 3C builds the automated fix-cycle path on top of it.

### Objective

Implement the first working slice of `scripts/agent_loop.py` against the approved Phase 3A Orchestrator Contract. Scope is limited to the scaffold and the normal-cycle control path (Claude handoff via the adapter boundary, evidence capture via `scripts/run_checks.sh`, and waiting on Codex review). Fix-cycle automation, real subprocess-driven Claude/Codex adapters, approval modes, Git automation, and editor integration are explicitly deferred to later 3x sub-phases.

### Definition of done

- `scripts/agent_loop.py` exists and is runnable on a system with Python 3 and Bash.
- The script anchors its working directory at the repository root regardless of where it is invoked from (markers: `TASK.md`, `AGENTS.md`, `.agent-loop/`).
- `.agent-loop/loop-state.json` load/save helpers write only the orchestrator-writable fields (`status`, `cycle_count`, `last_verdict`, `last_verdict_phase`, `claude_version`, `codex_version`, `orchestrator_version`) and refuse to write the Codex- or human-owned fields (`phase`, `sub_phase`, `task`, `max_cycles`, `contract_version`).
- Artifact validation scaffolding covers: `.agent-loop/claude-prompt.md` presence/non-emptiness, `.agent-loop/fix-prompt.md` presence/non-emptiness/structure (when applicable), `.agent-loop/claude-summary.md` structure + `## Phase` match, `.agent-loop/codex-review.md` structure + single-verdict parse, and the six evidence files' presence + contract-vocabulary `state:` field.
- The normal-cycle control path executes the sequence the contract specifies: validate inputs -> set `status = claude_implementing` and increment `cycle_count` -> invoke the Claude adapter boundary -> validate `claude-summary.md` -> set `status = evidence_capture` -> invoke `bash scripts/run_checks.sh` -> validate evidence files -> set `status = awaiting_codex_review` -> wait for `codex-review.md` -> validate and parse verdict -> branch on verdict.
- Fail-closed halts use the contract's `halted_*` status vocabulary (`halted_input_missing`, `halted_summary_malformed`, `halted_review_malformed`, `halted_review_parse_failed`, `halted_evidence_script_unavailable`, `halted_evidence_incomplete`, `halted_contract_version_mismatch`, `halted_max_cycles_reached`, `halted_human_stop`, `halted_failed_requires_human`).
- The orchestrator never writes any file outside the allowed set (`.agent-loop/loop-state.json` and the optional `.agent-loop/orchestrator.log`); in particular, it never writes `.agent-loop/claude-prompt.md`, `.agent-loop/claude-summary.md`, `.agent-loop/codex-review.md`, `.agent-loop/fix-prompt.md`, the six evidence files, or any source/instruction file.
- Adapter boundaries are real Python classes/functions even when their current implementation is the manual-handoff stub; replacing them with subprocess-driven CLI adapters is purely a later-slice concern.
- The orchestrator records `orchestrator_version` and (when the Claude adapter resolves one) `claude_version` into `loop-state.json`.
- A `python scripts/agent_loop.py --help`-style CLI surface exists and at minimum provides:
  - `check-state` (load and validate `loop-state.json`; print a summary; non-zero exit on contract-version mismatch)
  - `validate-artifacts` (run the per-cycle artifact validators against the current `.agent-loop/` state)
  - `run` (execute one normal cycle interactively against the manual-handoff adapters)

### Exclusions

- no fix-cycle automation (deferred to a later 3x sub-phase)
- no real subprocess-driven Claude or Codex adapter (the only adapters wired up are manual-handoff stubs that pause for the human to drive the actual CLI)
- no approval modes (Phase 5)
- no editor integration (Phase 7)
- no Git automation (no commit, push, branch, stash, reset, checkout, tag)
- no changes to the Phase 2A Evidence Collection Contract
- no changes to `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract (above)
- no changes to `AGENTS.md` or `CLAUDE.md`
- no fabricated evidence files
- no `.agent-loop/checks.json` is created by this slice

## Phase 3C - Automated Fix-Cycle Handling

### Status

Complete and approved by human to advance to Phase 3D. The Phase 3C verdict-handling loop (`_handle_verdict_loop`), automated fix-cycle path (`_run_fix_cycle`), threshold-policy halt, `halted_human_stop` persistence on `KeyboardInterrupt`, and `codex_version` null-note behavior are all in place; Phase 3D replaces the manual-handoff adapter stubs with real subprocess-driven adapters while keeping the verdict loop, fix-cycle, and fail-closed validators unchanged.

### Objective

Extend `scripts/agent_loop.py` so the orchestrator handles a `NEEDS_FIXES` verdict automatically by entering the contract's fix-cycle path (with manual-handoff adapters), instead of parking the loop for human handling. The Phase 3A contract's `#### Fix cycle` section and the `NEEDS_FIXES` branch of `#### Verdict handling` are the authoritative specification; this sub-phase implements them. Threshold-policy enforcement (`cycle_count >= max_cycles` halts the loop, no auto-continue) is part of the same change. No approval modes, Git automation, editor integration, or real subprocess-driven CLI adapters are introduced.

### Definition of done

- `scripts/agent_loop.py` validates `.agent-loop/fix-prompt.md` (presence, non-empty, contract header sequence) before entering any fix cycle and halts `halted_fix_prompt_malformed` (or `halted_input_missing` for missing/empty) when the file is unusable.
- After parsing a `NEEDS_FIXES` verdict from `.agent-loop/codex-review.md`, the orchestrator records `last_verdict` / `last_verdict_phase` and either enters the fix cycle or halts `halted_max_cycles_reached`, depending on the threshold check.
- The fix-cycle control path follows the contract's `#### Fix cycle` step order: increment `cycle_count` and set `status = claude_fixing`, invoke the Claude adapter with `fix-prompt.md`, validate the resulting `claude-summary.md` (structure + `## Phase` match), set `status = evidence_capture`, invoke `bash scripts/run_checks.sh`, validate the six evidence files, set `status = awaiting_codex_review`, wait for `codex-review.md` to be updated, validate the review and parse exactly one verdict, branch on the new verdict.
- Threshold-policy enforcement: if `cycle_count >= max_cycles` and the latest verdict is `NEEDS_FIXES`, the orchestrator halts with `status = halted_max_cycles_reached` and does NOT enter another fix cycle. The contract's "materially changed / narrowed" judgment is not made automatically by the orchestrator; raising `max_cycles` or resetting `cycle_count` is an explicit Codex- or human-owned action.
- Existing fail-closed mtime behavior on the manual-handoff adapters carries over to the fix cycle unchanged: a stale `claude-summary.md` (after fix invocation) or a stale `codex-review.md` (after fix-cycle review handoff) causes a `halted_input_missing` halt.
- Multiple consecutive `NEEDS_FIXES` verdicts within a single sub-phase walk through repeated fix cycles until any one of: `APPROVED_FOR_HUMAN_REVIEW`, `FAILED_REQUIRES_HUMAN`, threshold reached, fail-closed halt, parse/schema failure, or human stop.
- `README.md` reflects the Phase 3C active status and updates the orchestrator usage notes to describe the automated fix-cycle behavior.

### Exclusions

- no approval modes (Phase 5)
- no editor integration (Phase 7)
- no Git automation (no commit, push, branch, stash, reset, checkout, tag)
- no real subprocess-driven Claude or Codex CLI adapter (still manual-handoff only)
- no changes to the Phase 2A Evidence Collection Contract
- no changes to `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract body
- no changes to `AGENTS.md` or `CLAUDE.md`
- no fabricated evidence files
- no automatic "materially changed / narrowed" cycle-extension judgment by the orchestrator (orchestrator only enforces the threshold; the policy escape valve is a human raising `max_cycles` or activating a new sub-phase)
- no replacement of the manual-handoff Codex adapter with a subprocess-driven one

## Phase 3D - Subprocess-Driven Claude/Codex Adapters

### Status

Complete and approved by human to advance to Phase 3E. The subprocess adapters, env-var selection factories, model-id resolution rules, and manual-handoff fallback are all in place; Phase 3E exercises the whole pipeline against the repository's actual `.agent-loop/` workflow and documents what really happens.

### Objective

Replace the manual-handoff Claude and Codex adapter stubs in `scripts/agent_loop.py` with real subprocess-driven adapters that launch the user's configured Claude / Codex CLI command, wait for the artifact handoff, capture exit code and wall-clock duration, and return a structured `ExecutionResult` with a resolved model identifier. The Phase 3A contract's adapter-boundary requirement (version-aware, no model-specific output parsing in the core loop) is honored unchanged; the verdict loop, fix-cycle, fail-closed validators, threshold-policy halt, `halted_human_stop` persistence, and `codex_version` null-note behavior all carry over without modification. The manual-handoff adapters remain available as the fallback when the user has not configured a subprocess command (so the documented manual workflow still works), but the subprocess adapter is the default when configured.

### Definition of done

- `scripts/agent_loop.py` defines `SubprocessClaudeAdapter` and `SubprocessCodexAdapter`. Each is a real Python class whose interface matches the existing manual-handoff adapter (the Claude adapter exposes `invoke(prompt_path, summary_path) -> ExecutionResult`; the Codex adapter exposes `wait_for_review(review_path) -> ExecutionResult`).
- Adapter selection is driven by environment variables (no hardcoded command strings, no model-specific parsing in the core loop):
  - `AGENT_LOOP_CLAUDE_CMD` selects the subprocess Claude adapter and provides the shell-style command to invoke.
  - `AGENT_LOOP_CODEX_CMD` selects the subprocess Codex adapter and provides the shell-style command to invoke.
  - `AGENT_LOOP_CLAUDE_MODEL` and `AGENT_LOOP_CODEX_MODEL` optionally provide the explicit model-identifier strings the adapters should record into `claude_version` and `codex_version`.
  - When the `*_CMD` variable is unset, the orchestrator falls back to the existing manual-handoff adapter so the documented manual workflow keeps working.
- Each subprocess adapter:
  - executes the operator-provided command via `subprocess.run(self.command, shell=True, ...)`, letting the platform shell (cmd.exe on Windows, /bin/sh on POSIX) parse the command string. This matches the standard idiom for env-var-configured tools and avoids the cross-platform quoting traps that come from pre-splitting an operator-typed command into argv (notably Windows paths with backslashes). `cwd` is set to the repository root and the prompt file content is piped to stdin (the Codex adapter passes an empty stdin because Codex review CLIs operate on the captured `.agent-loop/` artifacts).
  - waits for the subprocess to exit; captures `returncode` and wall-clock `duration` into the returned `ExecutionResult`.
  - confirms the expected output artifact (`claude-summary.md` for Claude, `codex-review.md` for Codex) exists and its mtime has advanced since the call started, preserving the existing fail-closed-on-stale-mtime behavior; a stale mtime returns `(exit_code=1, model_id=None)` so the orchestrator halts via its existing `halted_input_missing` path.
  - resolves the model identifier from `AGENT_LOOP_{CLAUDE,CODEX}_MODEL` first; for Claude, falls back to the first token of the command string extracted via `shlex.split(posix=True)` (e.g. `claude` for the command `claude --print`), so the contract's "Claude adapter cannot resolve a model identifier -> halt" branch only fires when the subprocess itself fails; for Codex, leaves the resolved model as `None` when no env var is provided, so the orchestrator's existing null-note path writes the contract-required `orchestrator.log` line instead of fabricating a version. `shlex.split` is used for this fallback only; the actual command invocation goes through `shell=True` as described above.
  - never parses model-specific output formats inside the core loop; subprocess stdout/stderr is captured for future logging but not interpreted by the orchestrator beyond the exit code.
- Subprocess failures (binary missing -> `FileNotFoundError` -> exit_code `127`; non-zero exit code; missing or stale output artifact) map cleanly onto the orchestrator's existing fail-closed halt paths.
- `ORCHESTRATOR_VERSION` bumped to `phase-3d-v0`; the running orchestrator writes that into `loop-state.json` at the start of each cycle.
- `README.md` documents the new env-var configuration and the manual-handoff fallback.

### Exclusions

- no approval modes (Phase 5)
- no editor integration (Phase 7)
- no Git automation (no commit, push, branch, stash, reset, checkout, tag)
- no changes to the Phase 2A Evidence Collection Contract
- no changes to `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract body
- no changes to `AGENTS.md` or `CLAUDE.md`
- no removal of the manual-handoff adapter classes (kept as the documented fallback)
- no parsing of Claude / Codex CLI output formats inside the core loop (the contract forbids that)
- no streaming subprocess output to a TTY (subprocess output is captured, not streamed; future sub-phases can layer streaming on top)
- no introduction of a `scripts/agent_loop/` package layout (the contract suggests it but does not require it; staying single-file keeps this slice's diff minimal)
- no concurrent invocation of multiple Claude / Codex processes from the orchestrator (single sequential subprocess per step)

## Phase 3E - End-to-End MVP Verification

### Status

Complete. Phase 3E execution + report reviewed; Phase 3 is closed.

### Objective

Execute at least one real bounded `python scripts/agent_loop.py run` against the repository's actual `.agent-loop/` workflow and observe what really happens. The goal is operational verification of the MVP: confirm that the orchestrator's load/validate/contract-check/start-state-gate/cycle-counter/adapter-invoke/fail-closed/halt-persistence/orchestrator.log pipeline behaves as the contract specifies under real OS conditions, not only inside synthetic harnesses. Fix any concrete operational bug the live run reveals, with minimal targeted changes. If no bug is revealed, do not make speculative code changes; document the residual risks honestly.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 3 / 3E as active.
- `.agent-loop/phase-plan.md` marks Phase 3D complete and contains this Phase 3E section.
- At least one real bounded orchestrator run was actually executed against the repository's `.agent-loop/` workflow. The chosen adapter path (subprocess-driven vs. manual-handoff) is explicitly recorded, along with the reason for the choice.
- `.agent-loop/claude-summary.md` truthfully describes the real run: what was set up, which adapter path ran, which validators fired, which `bash scripts/run_checks.sh` outcome was observed (if it was reached), which status transitions actually landed in `.agent-loop/loop-state.json`, what lines appeared in `.agent-loop/orchestrator.log`, and which artifact mtimes actually changed.
- Any concrete operational bug revealed by the live run is fixed with a minimal targeted change to `scripts/agent_loop.py`. If no bug is revealed, the script is unchanged.
- `README.md` is updated only if the real operator workflow observed in the live run differs from the currently documented usage.
- The final on-disk state is left coherent and reviewable: `.agent-loop/loop-state.json` either records the live-run terminal status truthfully (if that is the chosen review handoff state) or is reset to a documented `awaiting_codex_review` posture with the live-run outcome captured in `.agent-loop/claude-summary.md` + `.agent-loop/orchestrator.log`. The choice of handoff posture is explicit, not silent.

### Exclusions

- no approval modes (Phase 5)
- no editor integration (Phase 7)
- no Git automation (no commit, push, branch, stash, reset, checkout, tag)
- no recursive invocation of the locally-installed `claude` CLI (would spawn a nested Claude Code session inside the current one - unsafe and outside the operational verification scope)
- no fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- no speculative code changes to `scripts/agent_loop.py` if the live run did not reveal a concrete operational bug
- no changes to the Phase 2A Evidence Collection Contract
- no changes to `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract body
- no changes to `AGENTS.md` or `CLAUDE.md`
- no removal of the manual-handoff adapter classes or the subprocess adapter classes (both remain available)

## Phase 4 - Phase Planning Automation

Phase 4 is delivered in sub-phases:

- Phase 4A - Planning Contract (planning and documentation; complete)
- Phase 4B - Planner Initial Slice (proposal generation only; complete)
- Phase 4C - Planner Activation Writes (activation step that consumes an approved proposal; this sub-phase)
- additional 4x sub-phases (planner-orchestrator auto-integration, optional planner adapter) deferred until 4C is approved

The Phase 4 layer sits ON TOP of the Phase 3 orchestrator and is bound by it. The planner is a Codex capability that reads the project state and proposes the next phase or sub-phase; it never bypasses the orchestrator and never activates its own proposals.

## Phase 4A - Planning Contract

### Status

Complete. Phase 4A planning contract reviewed and approved for human review; Phase 4B is now active and implements the contract's proposal-generation step.

### Objective

Specify, before any planner code is written, how an automatic phase planner must behave: which files it reads, which artifacts it is allowed to write, what a valid generated phase or sub-phase proposal must contain, how bounded scope is enforced, which decisions are Codex- or human-owned, what refusal and halt conditions apply, and how the planner handles unresolved review verdicts, halted loop state, or stale evidence. The contract is what a later 4x sub-phase will be implemented against.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 4 / 4A as active
- `.agent-loop/phase-plan.md` records Phase 3 as closed history and contains this Phase 4A section that defines the Planning Contract below
- `README.md` reflects the Phase 4A active status and points readers at the contract
- `ROADMAP.md` reflects the 4A / later-4x decomposition of Phase 4 without changing overall scope
- the contract is concrete enough that a later 4x sub-phase could implement the planner from it without further design decisions
- no planner code is created
- no changes to `scripts/agent_loop.py` or `scripts/run_checks.sh`
- no changes to the Phase 2A Evidence Collection Contract or the Phase 3A Orchestrator Contract body
- no protected files (`AGENTS.md`, `CLAUDE.md`) are modified

### Exclusions

- no implementation of the automatic planner itself (deferred to a later 4x sub-phase)
- no auto-activation of any proposed phase (activation always requires explicit human approval; the planner only proposes)
- no approval-mode behavior (Phase 5)
- no editor integration (Phase 7)
- no MCP support
- no Git automation (no commit, push, branch, stash, reset, checkout, tag)
- no changes to the Phase 2A or Phase 3A contracts
- no changes to `scripts/agent_loop.py` or `scripts/run_checks.sh`
- no fabricated evidence files
- no removal or rewrite of historical phase-plan sections (Phase 0 through Phase 3E sections stay intact)

### Planning Contract

The contract below is what a later 4x sub-phase's planner implementation must satisfy. It is also a reference for any human or Codex doing planning by hand so manual operation stays interchangeable with future planner behavior.

#### Inputs the planner reads (read-only)

- `TASK.md` (the human objective, the active phase / sub-phase, the active task, and current Out-Of-Scope list)
- `.agent-loop/phase-plan.md` (the full phase history and the active phase / sub-phase definition)
- `.agent-loop/current-task.md` and `.agent-loop/current-phase.md`
- `.agent-loop/loop-state.json` (`status`, `cycle_count`, `max_cycles`, `last_verdict`, `last_verdict_phase`, `contract_version`)
- `.agent-loop/claude-prompt.md` (the active implementation prompt, if any)
- `.agent-loop/claude-summary.md` (the latest implementation summary)
- `.agent-loop/codex-review.md` (the latest review verdict and findings)
- `.agent-loop/fix-prompt.md` (the active fix prompt during a fix cycle, if any)
- `.agent-loop/git-status.log`, `.agent-loop/git-diff.patch`, `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log` (the six evidence files)
- `.agent-loop/orchestrator.log` (optional; provides the orchestrator's own running history)
- `ROADMAP.md` (the broader phase roadmap and overall product scope)
- `AGENTS.md` and `CLAUDE.md` (referenced for boundary enforcement; never modified)

The planner must treat these files as read-only inputs. It must never author or overwrite them outside the allowed-writes set below.

#### Files the planner is allowed to write

- `.agent-loop/proposed-phase.md` - a per-cycle proposal artifact authored by the planner that describes a single candidate next phase or sub-phase. Required structure is defined below. Activation of the proposal is a separate Codex- or human-owned step.
- `.agent-loop/planner.log` (optional) - a per-run log of planner decisions and refusals; scoped to `.agent-loop/`; never used as authoritative evidence.

On ACTIVATION of a proposal (only after explicit human approval, never autonomously), the planner is additionally allowed to write:

- `TASK.md` (rewrite `## Active Phase`, `## Active Sub-Phase`, `## Phase Status`, `## Active Task`, `## Phase Outcome Required Now`, `## Next-Phase Gate`, and `## Out Of Scope For Current Phase` to describe the newly activated phase; preserve `## Human Objective` and `## Project Intent` verbatim)
- `.agent-loop/current-task.md` and `.agent-loop/current-phase.md` (one-line / short rewrites for the newly activated phase)
- `.agent-loop/phase-plan.md` (update `## Active Phase` and APPEND a new sub-phase section that mirrors the just-activated proposal; never rewrite historical sections)
- `.agent-loop/loop-state.json` (reset `cycle_count = 0`, set `status = awaiting_claude_implementation`, set `phase` / `sub_phase` / `task` for the new phase, clear `last_verdict` / `last_verdict_phase`, leave `max_cycles` / `contract_version` / `claude_version` / `codex_version` / `orchestrator_version` per the orchestrator-write-ownership rules of the Phase 3A contract)

The planner must not write any other file.

#### Files the planner must never write

- `scripts/agent_loop.py`, `scripts/run_checks.sh`, any other script
- `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`
- `.gitattributes`, `.gitignore`
- `.agent-loop/claude-prompt.md` (the implementation prompt is authored by Codex per cycle; the planner is a separate Codex capability that prepares the next phase, not the next implementation prompt)
- `.agent-loop/claude-summary.md` (Claude-owned)
- `.agent-loop/codex-review.md` (Codex-owned, per-cycle review artifact, distinct from planning)
- `.agent-loop/fix-prompt.md` (Codex-owned per-cycle fix artifact)
- `.agent-loop/git-status.log`, `.agent-loop/git-diff.patch`, `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log` (owned by `scripts/run_checks.sh`)
- `.agent-loop/orchestrator.log` (owned by the orchestrator)
- any historical `## Phase X - ...` section in `.agent-loop/phase-plan.md` (history is append-only; the planner may append a new sub-phase section but never edit prior ones)
- `## Human Objective` and `## Project Intent` in `TASK.md` (human-owned)

#### What a valid generated proposal must contain

A `.agent-loop/proposed-phase.md` written by the planner must include every section below, in this order, each with a non-empty body. Missing or empty sections make the proposal invalid (see refusal conditions).

```md
# Proposed Phase

## Label
[exact label, e.g. "Phase 4B - Implement scripts/agent_loop/planner.py (initial slice)" - must follow the existing phase / sub-phase naming convention]

## Objective
[one paragraph: concrete, actionable, in the present tense. Vague language ("improve X", "refactor Y to be better", "make things faster") is forbidden.]

## Definition of done
[bulleted list of specific, testable bullets. Each bullet must describe a file-state outcome, a CLI behavior, a validator outcome, or a similar verifiable end state. "Code is cleaner" is not testable; "scripts/agent_loop.py has no function longer than 50 lines as measured by X" is testable.]

## Exclusions
[bulleted list of what is explicitly out of scope. At minimum, every later 4x / 5+ sub-phase that this proposal does NOT cover must appear here.]

## Files likely involved
[bulleted list of file paths the proposal is expected to read or write. Predicted list; the actual implementation may diverge with explanation, but the list must be specific (no "various .py files").]

## Required contract changes
[either the literal text "None" or a bulleted list naming each contract that must be revised (Phase 2A Evidence Collection Contract; Phase 3A Orchestrator Contract; Phase 4A Planning Contract; AGENTS.md format sections; CLAUDE.md required-format sections). A proposal that silently requires a contract change (i.e. the implementation can only be done by violating an existing contract) is invalid.]

## Cycle-size estimate
[a single integer in the range 1..3 indicating the recommended `max_cycles` for the proposed sub-phase. Values larger than 3 require an explicit justification paragraph and are still subject to human approval.]

## Dependencies
[bulleted list of prior sub-phases this proposal depends on, each with one of these dependency-status tokens: complete-approved | complete-superseded | active-in-flight | pending. A proposal that depends on an active-in-flight or pending phase is invalid.]

## Risk areas
[bulleted list of known risks the proposal carries (fragile area, untested behavior, integration concern). At least one risk must be listed; "None identified" is allowed only with an explicit justification sentence.]
```

#### Bounded-scope rules

The planner must enforce these scope bounds when generating a proposal. Any proposal that violates them is invalid and must be refused (see refusal conditions below).

- `## Files likely involved` lists at most 10 files. Larger proposals must be split.
- `## Required contract changes` lists at most ONE contract revision. Multi-contract revisions must be split into separate sequential sub-phases.
- `## Definition of done` contains at least one testable bullet. Pure-documentation proposals are allowed but must have at least one bullet that names a specific file-state outcome.
- The proposal must not require modifying any file in the "Files the planner must never write" list outside the proposal's own per-cycle artifact set; the orchestrator's own write-ownership rules still apply transitively.
- The proposal's `## Cycle-size estimate` is at most 3 by default. A value > 3 requires an explicit justification paragraph naming why the work cannot be split.
- The proposal must not propose silent removal of any historical phase-plan section, evidence file, contract, or Codex-owned artifact.

#### Human-approval requirements

- The planner may WRITE `.agent-loop/proposed-phase.md` and append to `.agent-loop/planner.log` autonomously. These two writes are the proposal step.
- The planner may NEVER perform the activation writes (`TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json`) without an explicit human approval signal.
- The human approval signal is one of:
  - a human-authored `## Approval` section appended to `.agent-loop/proposed-phase.md` containing the literal token `APPROVED_FOR_ACTIVATION` on its own line
  - a Codex-authored cycle that includes the proposal's label in the next Codex review and the human explicitly confirms activation out of band (the planner reads this confirmation only through the on-disk `## Approval` section above; it never infers approval from review text alone)
- The planner must never write `APPROVED_FOR_ACTIVATION` to a proposal it authored. Self-approval is forbidden.
- On activation, the planner must record the approval source (file path, mtime, and the literal approval line) into `.agent-loop/planner.log` so the activation chain is auditable.

#### Refusal / halt conditions

The planner must refuse to generate or activate a proposal in any of these cases. A refusal writes a `note:`-style line to `.agent-loop/planner.log` (if writable) explaining the refusal reason and returns control without modifying any other file.

- the current sub-phase's `last_verdict` in `.agent-loop/loop-state.json` is `NEEDS_FIXES` and the fix cycle has not yet produced a subsequent `APPROVED_FOR_HUMAN_REVIEW` verdict (the unresolved fix takes precedence over planning the next phase)
- the current sub-phase's `last_verdict` is `FAILED_REQUIRES_HUMAN` (escalation takes precedence)
- `loop-state.json` `status` is any `halted_*` value (the existing halt must be resolved by human / Codex action before planning the next phase)
- `loop-state.json` `cycle_count >= max_cycles` and `last_verdict` is `NEEDS_FIXES` without a subsequent approval (the threshold halt takes precedence)
- the evidence files' `captured_at` headers are older than the mtime of `.agent-loop/claude-summary.md` or `.agent-loop/codex-review.md` (stale evidence; the planner must recommend re-running `bash scripts/run_checks.sh` before planning)
- the proposal would violate any rule in "Bounded-scope rules" above (size limit, multi-contract revision, missing testable bullet, etc.)
- the proposal would require modifying a file in "Files the planner must never write"
- the proposal's `## Label` collides with an existing historical sub-phase label in `.agent-loop/phase-plan.md` (re-use of labels is forbidden)
- the proposal's `## Dependencies` lists any dependency with status `active-in-flight` or `pending`
- the proposal's `## Definition of done` contains a bullet whose language is vague per the bounded-scope rules
- a proposal arrives for activation without a `## Approval` section containing the literal `APPROVED_FOR_ACTIVATION` token

The planner must never silently proceed past a refusal condition, partially write activation artifacts, or guess at missing approval.

#### Handling of unresolved issues, stale evidence, and halted loop states

- Unresolved `NEEDS_FIXES`: planner refuses to plan a new phase; recommends executing the fix cycle to convergence first.
- Unresolved `FAILED_REQUIRES_HUMAN`: planner refuses; recommends human escalation.
- `halted_*` status: planner refuses; recommends the appropriate recovery per the Phase 3A contract (manual `status` reset, raising `max_cycles`, replacing the missing input, etc.).
- Stale evidence (`captured_at` older than `claude-summary.md` or `codex-review.md` mtime): planner refuses; recommends `bash scripts/run_checks.sh` before re-attempting to plan.
- `cycle_count == 0` and no prior `last_verdict`: this is a fresh start; the planner may propose the very next phase based on `TASK.md`, `ROADMAP.md`, and the latest closed historical sub-phase.

#### Failure modes worth naming

These are the realistic failure modes the planner must handle gracefully (always: write a `note:` line to `.agent-loop/planner.log` if writable, return without partial activation):

- `proposed-phase.md` already exists from a prior planner run and contains an approval token but for a different label (planner refuses to silently overwrite; recommends archiving or human resolution)
- a proposal references a contract revision that the planner cannot enumerate (refuse; require Codex / human to author the contract revision separately and re-propose against the new contract version)
- the orchestrator is currently in flight (`status` is `claude_implementing`, `claude_fixing`, `evidence_capture`, or `awaiting_codex_review`); the planner refuses because the orchestrator's view of the cycle is not yet terminal
- the human-approval signal token is malformed (whitespace, alternate capitalization, additional words on the line); planner refuses and reports the exact tokens it accepts
- the planner cannot read one of its required input files (file missing, unreadable, JSON malformed); planner refuses and reports the unreadable input

This is a Phase 4A contract-definition slice. Phase 4A documents the contract; a later 4x sub-phase implements a planner that satisfies it.

## Phase 4B - Planner Initial Slice (Proposal Generation)

### Status

Complete. Phase 4B planner initial slice reviewed and approved for human review; the `plan` subcommand, refusal checks, concrete-proposal dispatch, exclusions-enumeration validator, vague-Objective validator, `note:`-style log format, and the 29-test test suite are in place. Phase 4C is now active and implements the activation step against the same Phase 4A contract.

### Objective

Implement the first working slice of the automatic planner so that, on a single CLI invocation, the planner loads the inputs defined by the Phase 4A contract, applies every refusal and halt condition the contract names, and (when allowed) writes one structurally valid `.agent-loop/proposed-phase.md` plus an optional `.agent-loop/planner.log` decision note - without ever writing any activation file. Activation writes are deferred to a later 4x sub-phase.

### Definition of done

- `scripts/agent_loop.py` (or a small adjacent planner module) implements: planner input loading, the full Phase 4A refusal / halt check set, proposal generation, bounded-scope self-validation, optional `.agent-loop/planner.log` notes, and a `plan` CLI subcommand that wires those pieces together
- the planner writes only files in the Phase 4A "Files the planner is allowed to write" set: `.agent-loop/proposed-phase.md` and `.agent-loop/planner.log`
- the planner never writes any file in the Phase 4A "Files the planner must never write" set, including `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json`, `.agent-loop/claude-prompt.md`, `.agent-loop/claude-summary.md`, `.agent-loop/codex-review.md`, `.agent-loop/fix-prompt.md`, any evidence file, `.agent-loop/orchestrator.log`, `AGENTS.md`, `CLAUDE.md`, `ROADMAP.md`, `README.md`, or any script
- the planner refuses (without writing the proposal) when any Phase 4A refusal condition applies: unresolved `NEEDS_FIXES`, `FAILED_REQUIRES_HUMAN`, any `halted_*` status, orchestrator-in-flight statuses (`claude_implementing`, `claude_fixing`, `evidence_capture`, `awaiting_codex_review`), `cycle_count >= max_cycles` on `NEEDS_FIXES`, stale evidence (evidence `captured_at` older than `claude-summary.md` or `codex-review.md` mtime), unreadable required input, or a bounded-scope violation in its own generated proposal
- on refusal, the planner appends a `note:` line to `.agent-loop/planner.log` (best-effort) and exits non-zero without touching `.agent-loop/proposed-phase.md`
- the planner never writes the `APPROVED_FOR_ACTIVATION` token to any file it authors (self-approval is forbidden by the Phase 4A contract)
- `tests/` contains focused tests covering at least: each major refusal path, the bounded-scope self-validation, and one valid proposal-generation path
- `README.md` documents the new `python scripts/agent_loop.py plan` invocation and reflects the Phase 4B active status

### Exclusions

- no planner activation writes (`TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, `.agent-loop/loop-state.json` rewrites driven by an approved proposal) - deferred to a later 4x sub-phase
- no planner-orchestrator integration that would invoke the planner from inside `run_normal_cycle` or `_run_fix_cycle` (the planner is a standalone CLI subcommand in this slice)
- no Phase 5 approval-mode behavior
- no Phase 7 editor integration
- no MCP support
- no Git automation
- no changes to the Phase 2A Evidence Collection Contract or `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract body or to the existing `scripts/agent_loop.py` normal-cycle / fix-cycle / adapter code paths beyond adding planner functions and the `plan` CLI handler
- no changes to the Phase 4A Planning Contract body
- no changes to `AGENTS.md` or `CLAUDE.md`
- no removal or rewrite of any historical phase-plan section (Phase 0 through Phase 4A sections stay intact)
- no fabricated evidence files

## Phase 4C - Planner Activation Writes

### Status

Complete. Closed by activation of Phase 4D - Planner-Orchestrator Integration.

### Objective

Implement the activation step the Phase 4A Planning Contract authorizes: a separate `activate` CLI subcommand on `scripts/agent_loop.py` that consumes an already-generated `.agent-loop/proposed-phase.md` (typically produced by the Phase 4B `plan` subcommand), verifies the human approval signal exactly as the contract specifies, refuses every malformed-approval / label-mismatch / missing-input path, and on success performs ONLY the writes the contract authorizes on activation. Planner-orchestrator auto-integration is explicitly out of scope; the activator is invoked by the human, not by `run_normal_cycle` / `_run_fix_cycle`.

### Definition of done

- `scripts/agent_loop.py` exposes an `activate` CLI subcommand (separate from `plan`) whose exit code is 0 on a successful activation and 2 on any refusal
- the activation parser verifies the proposal carries a human-authored `## Approval` section, that the section contains the literal `APPROVED_FOR_ACTIVATION` token on its own line within that section (not whole-file substring matching), and that the section body references the proposal's `## Label` text (so a stale approval against a different label is refused)
- the activation parser refuses each Phase 4A-required failure path: missing `## Approval` section, missing-or-malformed token (wrong case, extra words on the line, leading/trailing characters), label-mismatch against `## Label`, missing or unreadable `.agent-loop/proposed-phase.md`, missing or malformed `.agent-loop/loop-state.json`, and empty required-proposal-section bodies; refusals exit 2 and append a `note:`-style line to `.agent-loop/planner.log` without modifying any other file
- on success, the activation path writes ONLY the files the Phase 4A contract authorizes on activation: `TASK.md` (preserving `## Human Objective` and `## Project Intent` verbatim and rewriting `## Active Phase` / `## Active Sub-Phase` / `## Phase Status` / `## Active Task` / `## Phase Outcome Required Now` / `## Next-Phase Gate` / `## Out Of Scope For Current Phase`), `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md` (update `## Active Phase` line and APPEND one new sub-phase section), `.agent-loop/loop-state.json` (set `phase` / `sub_phase` / `task` from the approved proposal; set `status = awaiting_claude_implementation`, `cycle_count = 0`, `last_verdict = null`, `last_verdict_phase = null`; preserve `max_cycles` / `contract_version` / `claude_version` / `codex_version` / `orchestrator_version`), and a `note:`-style approval-source line in `.agent-loop/planner.log` (file path, mtime, literal approval line)
- the planner's existing `plan`-subcommand write boundary (only `.agent-loop/proposed-phase.md` and `.agent-loop/planner.log`) is unchanged outside this explicit activation path
- `tests/test_planner_activation.py` covers the activation success path plus every refusal condition listed above and asserts the activator never writes any file outside its allowed set
- `README.md` documents the new `python scripts/agent_loop.py activate` invocation and the operator flow (`plan` -> human appends `## Approval` section -> `activate`)

### Exclusions

- no planner-orchestrator auto-integration; the activator stays a standalone CLI subcommand in this sub-phase and is not invoked from `run_normal_cycle` or `_run_fix_cycle` (deferred to Phase 4D)
- no optional planner adapter (deferred to Phase 4E or later)
- no Phase 5 approval-mode behavior beyond the literal `APPROVED_FOR_ACTIVATION` token
- no Phase 6 optional context and tool layer
- no Phase 7 editor / VS Code integration
- no Phase 8 documentation polish
- no MCP support
- no Git automation
- no changes to the Phase 2A Evidence Collection Contract or `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract body or to the existing `scripts/agent_loop.py` normal-cycle / fix-cycle / adapter code paths beyond adding activator functions and the `activate` CLI handler
- no changes to the Phase 4A Planning Contract body
- no changes to `AGENTS.md` or `CLAUDE.md`
- no removal or rewrite of any historical phase-plan section (Phase 0 through Phase 4B sections stay intact)
- no fabricated evidence files

## Phase 4D - Planner-Orchestrator Integration

### Status

Complete. Closed by activation of Phase 4E - Optional Planner Adapter.

### Objective

Integrate the standalone planner into the orchestrator's post-approval handoff so that, after a terminal `APPROVED_FOR_HUMAN_REVIEW` verdict is already persisted, `scripts/agent_loop.py` invokes the existing planner once to refresh `.agent-loop/proposed-phase.md`. The integration must not auto-activate the refreshed proposal; approval and activation remain a separate human-driven step.

### Definition of done

- `scripts/agent_loop.py` invokes the existing planner once after a terminal `APPROVED_FOR_HUMAN_REVIEW` verdict is persisted, in both the normal-cycle and fix-cycle paths where that terminal verdict can be reached
- the planner integration logs a single note to `.agent-loop/orchestrator.log` per eligible planner invocation and surfaces planner refusal outcomes without converting the already-approved orchestrator result into a halt
- the planner's write boundary remains unchanged under integration: only `.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` may be written by the planner call
- no activation-owned file is written by the integration path: `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`, and `.agent-loop/loop-state.json` remain untouched by the orchestrator's planner hook
- `tests/` contains focused coverage for a successful integration call, a planner-refusal path, and a proof that the integration never performs activation writes
- `README.md` reflects the Phase 4D active status and documents the post-approval planner refresh behavior

### Exclusions

- no planner-driven activation; the refreshed proposal still requires separate human approval plus `python scripts/agent_loop.py activate`
- no optional planner adapter (deferred to Phase 4E or later)
- no Phase 5 approval-mode behavior
- no Phase 6 optional context and tool layer
- no Phase 7 editor / VS Code integration
- no Phase 8 documentation polish
- no MCP support
- no Git automation
- no changes to the Phase 2A Evidence Collection Contract or `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract body beyond the narrow planner-hook implementation
- no changes to the Phase 4A Planning Contract body
- no changes to `AGENTS.md` or `CLAUDE.md`
- no removal or rewrite of any historical phase-plan section

## Phase 4E - Optional Planner Adapter

### Status

Complete. Closed by activation of Phase 4F - Alternate Planner Adapter Selection.

### Objective

Introduce an optional planner-adapter boundary so planner execution is no longer hard-wired to direct in-process calls. The adapter seam must cover both the `plan` command path and the orchestrator's post-approval planner refresh path while preserving the current local planner behavior by default. Activation remains a separate human-driven step.

### Definition of done

- `scripts/agent_loop.py` defines a dedicated planner-adapter seam for planner execution instead of direct hard-wired planner calls
- the default planner adapter preserves today's local planner behavior for the `plan` CLI path and the post-approval planner refresh path
- the planner's existing write boundary remains unchanged under adapterization: only `.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` may be written by planner execution
- planner refusals and unexpected planner exceptions remain surfaced with the same fail-closed behavior already required by the shipped 4B through 4D paths
- `tests/` contains focused coverage for the adapterized `plan` path, the adapterized post-approval planner path, and proof that the adapter seam does not widen planner or activation writes
- `README.md` documents the optional planner-adapter behavior and explains that activation remains separate from planning

### Exclusions

- no planner-driven activation; the refreshed proposal still requires separate human approval plus `python scripts/agent_loop.py activate`
- no Phase 5 approval-mode behavior
- no Phase 6 durable memory, token-reset continuation, checkpoint-resume logic, or continuation chaining
- no Phase 7 editor / VS Code integration
- no Phase 8 documentation polish beyond the narrow README update for planner-adapter behavior
- no MCP support
- no Git automation
- no changes to the Phase 2A Evidence Collection Contract or `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract body beyond the narrow planner-adapter seam implementation
- no changes to the Phase 4A Planning Contract body
- no changes to `AGENTS.md` or `CLAUDE.md`
- no removal or rewrite of any historical phase-plan section

## Phase 4F - Alternate Planner Adapter Selection

### Status

Complete. Closed by transition to Phase 5A - Approval Modes Contract.

### Objective

Implement adapter selection behind the Phase 4E planner-adapter seam so planner execution can use either the default in-process adapter or one alternate adapter path. The default local planner behavior must remain the fallback, and both the `plan` CLI path and the orchestrator's post-approval planner refresh path must continue to flow through the same seam. Activation remains a separate human-driven step.

### Definition of done

- `scripts/agent_loop.py` selects the planner adapter through a narrow, explicit configuration path instead of always instantiating the local adapter
- the default local planner adapter remains the fallback when no alternate adapter is configured or when alternate configuration is invalid
- exactly one alternate planner adapter path is implemented and routed through the existing Phase 4E seam
- the planner's existing write boundary remains unchanged under adapter selection: only `.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` may be written by planner execution
- planner refusals and unexpected planner exceptions remain surfaced with the same fail-closed behavior already required by the shipped 4B through 4E paths
- `tests/` contains focused coverage for adapter selection, local fallback behavior, the alternate adapter path, and proof that the selection logic does not widen planner or activation writes
- `README.md` documents how planner-adapter selection works and explains that activation remains separate from planning

### Exclusions

- no planner-driven activation; the refreshed proposal still requires separate human approval plus `python scripts/agent_loop.py activate`
- no multiple alternate planner adapters, plugin discovery, or adapter registry
- no Phase 5 approval-mode behavior
- no Phase 6 durable memory, token-reset continuation, checkpoint-resume logic, or continuation chaining
- no Phase 7 editor / VS Code integration
- no Phase 8 documentation polish beyond the narrow README update for planner-adapter selection
- no MCP support
- no Git automation
- no changes to the Phase 2A Evidence Collection Contract or `scripts/run_checks.sh`
- no changes to the Phase 3A Orchestrator Contract body beyond the narrow planner-adapter selection implementation
- no changes to the Phase 4A Planning Contract body
- no changes to `AGENTS.md` or `CLAUDE.md`
- no removal or rewrite of any historical phase-plan section

## Phase 5A - Approval Modes Contract

### Status

Complete. Closed by activation of Phase 5B - Review Mode Initial Slice.

### Objective

Define, before implementation, the contract for approval modes `strict`, `review`, and `autonomous`. The contract must specify when human approval is required, when Codex may send implementation prompts or fix prompts, when Claude completion should hand the loop back to Codex for review, how the loop pauses or continues under each mode, and what refusal / halt / escalation behavior applies when a mode would otherwise weaken the existing safety model.

### Definition of done

- `.agent-loop/phase-plan.md` contains a `## Phase 5A - Approval Modes Contract` body that defines `strict`, `review`, and `autonomous` mode semantics before any Phase 5 implementation code is written
- the contract specifies, for each mode, when the loop may send a Claude implementation prompt, when it may send a Claude fix prompt, when it must wait for a human, and when Codex review begins after Claude completion
- the contract specifies how a machine-readable Claude completion signal should participate in prompt / fix-prompt / review timing without being treated as proof of correctness
- the contract defines how approval-mode state interacts with loop-state, review verdicts, fix cycles, and phase boundaries without weakening the existing safety guarantees
- the contract names refusal / halt / escalation cases for unsafe or inconsistent mode-driven continuations
- `README.md` reflects that Phase 5A is active and that approval modes are still a contract-definition slice, not implemented runtime behavior

### Exclusions

- no implementation of approval modes in `scripts/agent_loop.py` or any other runtime file
- no changes to the Phase 2A Evidence Collection Contract
- no changes to the Phase 3A Orchestrator Contract body
- no changes to the Phase 4A Planning Contract body
- no changes to `scripts/run_checks.sh`
- no changes to `AGENTS.md` or `CLAUDE.md`
- no Phase 6 durable memory / checkpoint / continuation implementation
- no Phase 7 editor integration
- no Phase 8 documentation polish beyond the narrow README current-status update

### Approval Modes Contract

The contract below defines how future Phase 5 implementation slices must
behave. Phase 5A documents the rules; a later 5x slice implements them.

#### Modes covered

The system defines exactly three approval modes:

- `strict`
- `review`
- `autonomous`

No implementation may introduce additional mode names, aliases, or
partially-overlapping mode flags without a later contract revision.

#### Canonical goals of each mode

- `strict`: maximize human checkpoints. The loop pauses before every
  major agent-to-agent handoff and before any new Claude work starts.
- `review`: keep the existing default loop posture. Codex may issue
  implementation prompts and fix prompts, Claude may complete work and
  hand it back for review, and the human remains required before commit
  and before phase progression.
- `autonomous`: allow the loop to continue through implementation,
  evidence capture, review, and fix cycles with fewer human pauses, but
  NEVER weaken the hard safety stops already defined by the existing
  contracts.

#### Required runtime state

Any later implementation slice that adds approval-mode behavior must
represent it in runtime state explicitly.

Required fields to add to `.agent-loop/loop-state.json` in a later 5x
implementation slice:

- `approval_mode`: one of `strict`, `review`, `autonomous`
- `awaiting_human_for`: nullable string naming the current human gate,
  such as `pre_claude_prompt`, `pre_fix_prompt`,
  `phase_complete_awaiting_human_approval`, or `halt_resolution`

Required semantics for those fields in a later 5x implementation slice:

- newly initialized or newly activated Phase 5+ runtime state must
  default `approval_mode` to `review` unless the human or an explicit
  future configuration artifact selected a different allowed mode
- `awaiting_human_for` must be `null` whenever the loop is not currently
  blocked on a human gate
- changing `approval_mode` mid-cycle must be treated as a human-directed
  control action, recorded explicitly in runtime/logging artifacts, and
  must not silently resume an already-in-flight step under different
  semantics

Until a later implementation slice adds those fields, the absence of
`approval_mode` means the project remains on the pre-Phase-5 behavior.
Phase 5A itself does not modify runtime code or schema.

#### Claude completion signal

Future approval-mode implementation must treat
`.agent-loop/claude-done.json` as the machine-readable handoff signal
from Claude back to Codex/orchestrator.

Required semantics:

- it is a routing signal, not proof that work is correct
- it tells the loop that Claude believes the current implementation or
  fix prompt is complete and ready for review
- it must distinguish `implementation` completion from `fix` completion
- it must reference the source prompt path
  (`.agent-loop/claude-prompt.md` or `.agent-loop/fix-prompt.md`)
- a newly issued prompt or fix prompt must clear, replace, or supersede
  the prior `claude-done.json` so stale completion signals cannot drive
  the wrong review cycle

Minimum fields a later implementation slice must include:

- `signal_version`
- `phase`
- `sub_phase`
- `task`
- `cycle_count`
- `mode`: `implementation` or `fix`
- `source_prompt_path`
- `status`: `ready_for_codex_review`

Codex must still review `.agent-loop/claude-summary.md`, diff, and
validation evidence before issuing any verdict.

#### Prompt and review timing by mode

In every mode, Codex remains the owner of prompt authoring and review
decisions. Approval modes may change when a prompt is allowed to be sent
or when review is allowed to begin; they do NOT allow Claude to self-issue
new prompts, rewrite phase/task state, or bypass Codex review.

##### `strict`

Required pauses:

1. Before Codex sends a new implementation prompt to Claude.
2. Before Codex sends a new fix prompt to Claude.
3. After Claude signals completion and before Codex begins review.
4. Before any phase transition.
5. Before any commit or push action (independent of later Git policy).

Implications:

- Codex may prepare `.agent-loop/claude-prompt.md` or
  `.agent-loop/fix-prompt.md`, but the loop must wait for explicit human
  confirmation before Claude work begins.
- Claude completion (`claude-done.json`) is not enough to begin review;
  the loop must wait for explicit human confirmation to hand the work to
  Codex review.
- after a human allows review to begin, the existing evidence-capture
  step still runs before Codex issues any verdict
- `strict` does not bypass existing halt states or malformed-artifact
  stops; it adds pauses, not fewer safeguards.

##### `review`

Required pauses:

1. Human approval is required before phase progression.
2. Human approval is required before any commit or push action.
3. Existing halt / escalation states still stop the loop immediately.

Implications:

- Codex may send a normal implementation prompt without a separate human
  pre-approval step.
- Codex may send a fix prompt after a `NEEDS_FIXES` verdict without a
  separate human pre-approval step, subject to the existing cycle-limit
  and escalation rules.
- When Claude completion is signaled, Codex review may begin
  automatically.
- automatic review start still means: capture evidence first, then let
  Codex review the resulting artifacts
- `review` is the baseline/default mode because it matches the current
  artifact-driven loop most closely.

##### `autonomous`

Required pauses:

1. Human approval is required before phase progression.
2. Human approval is required before any commit or push action.
3. Human approval is required whenever an existing contract says the
   loop must halt or escalate.

Implications:

- Codex may send implementation prompts and fix prompts automatically.
- Claude completion may hand directly into Codex review automatically.
- Additional fix cycles may proceed automatically only while they remain
  inside the existing cycle-threshold policy and no halt or escalation
  condition is triggered.
- autonomous continuation still requires the normal evidence-capture
  step between Claude completion and Codex review
- `autonomous` may remove discretionary pauses, but it may not suppress
  or reinterpret existing hard safety stops.

#### Interaction with existing verdicts and fix cycles

Approval modes do NOT change the allowed verdict set:

- `APPROVED_FOR_HUMAN_REVIEW`
- `NEEDS_FIXES`
- `FAILED_REQUIRES_HUMAN`

Per-verdict mode interaction:

- `APPROVED_FOR_HUMAN_REVIEW`: all modes stop for human approval before
  advancing to the next phase.
- `NEEDS_FIXES`: `review` and `autonomous` may allow Codex to issue a
  fix prompt automatically, but only while the existing threshold /
  escalation rules remain satisfied. `strict` requires a human pause
  before Claude begins the fix cycle.
- `FAILED_REQUIRES_HUMAN`: all modes stop immediately. No mode may
  auto-continue past this verdict.

Approval modes do NOT change:

- prompt ownership by Codex
- the cycle-threshold policy
- halt-state behavior
- malformed-artifact fail-closed behavior
- evidence-capture requirements
- the rule that Codex review must be based on objective evidence

#### Required human gates that no mode may remove

The following gates are absolute and mode-independent:

- human approval before phase progression
- human approval before commit
- human intervention for any `FAILED_REQUIRES_HUMAN` outcome
- human intervention for unresolved `halted_*` states unless an existing
  contract explicitly allows a Codex-owned correction
- human intervention whenever the same issue repeats without meaningful
  progress and the threshold/escalation policy requires a stop

No approval mode may reinterpret those gates as optional.

#### Refusal / halt / escalation cases for approval-mode implementation

Any later 5x implementation must refuse or halt when:

- `approval_mode` is missing, null, or not one of the three allowed
  values
- mode-driven behavior would continue past an existing hard stop
  (`FAILED_REQUIRES_HUMAN`, `halted_*`, malformed-artifact stop,
  unresolved threshold escalation)
- a stale or mismatched `claude-done.json` would cause review to begin
  for the wrong prompt or wrong cycle
- the loop cannot determine whether the current Claude completion signal
  corresponds to `.agent-loop/claude-prompt.md` or
  `.agent-loop/fix-prompt.md`
- a mode attempts to treat Claude completion as sufficient evidence for
  approval without Codex review
- a mode would allow a new prompt/fix-prompt issuance while the prior
  cycle is still in flight and not yet terminal

Required handling:

- fail closed
- record the reason in runtime/logging artifacts
- do not silently fall back to a different mode
- require human resolution when the inconsistency affects safety or
  cycle ownership

#### Implementation constraints for later 5x slices

Any later implementation of approval modes must:

- preserve compatibility with the existing Phase 2A Evidence Collection
  Contract
- preserve compatibility with the existing Phase 3A Orchestrator
  Contract unless a later contract-revision slice explicitly changes it
- preserve compatibility with the existing Phase 4A Planning Contract
- treat `.agent-loop/claude-done.json` as a handoff/timing artifact
  only, never as a correctness artifact
- keep the mode logic auditable from repo artifacts rather than hidden
  in transient UI state
- document user-visible behavior changes in `README.md`

## Phase 5B - Review Mode Initial Slice

### Status

Complete. Closed by activation of Phase 5C - Strict Mode Pauses.

### Objective

Implement the initial approval-modes runtime behavior by making `review`
the explicit default mode, adding the first machine-readable
`.agent-loop/claude-done.json` handoff artifact, and preserving the
existing baseline loop behavior for prompt issuance, evidence capture,
review timing, fix cycles, and phase gating. This slice should make the
current review-driven flow explicit without implementing `strict` or
`autonomous` runtime branching yet.

### Definition of done

- `scripts/agent_loop.py` adds explicit runtime support for
  `approval_mode` and `awaiting_human_for` in the narrow `review`-mode
  path
- newly initialized or newly activated Phase 5+ runtime state defaults
  `approval_mode` to `review`
- `awaiting_human_for` is maintained consistently for the implemented
  `review` path and remains `null` whenever no human gate is active
- Claude completion produces `.agent-loop/claude-done.json` with the
  baseline contract fields and `status = ready_for_codex_review` for
  both implementation and fix completion
- new implementation-prompt or fix-prompt issuance clears, replaces, or
  supersedes stale `claude-done.json` so review cannot begin on the
  wrong cycle
- Codex review still depends on `.agent-loop/claude-summary.md`, git
  diff, and validation evidence; `claude-done.json` is treated only as a
  routing/timing signal
- the existing prompt, evidence-capture, review, fix-cycle, and
  phase-complete human-gating behavior remains unchanged in effect for
  the `review` path
- focused tests cover runtime-state defaults, `claude-done.json`
  creation, stale-signal protection, and non-regression of the existing
  review-mode loop
- `README.md` reflects that Phase 5B is active and that only the
  `review`-mode initial slice is implemented

### Exclusions

- no implementation of `strict` mode runtime pauses
- no implementation of `autonomous` mode runtime continuation behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body except the narrow
  approval-mode / `claude-done.json` implementation needed for this
  slice
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 6 durable memory / checkpoint / continuation implementation
- no Phase 7 editor integration
- no Git automation

## Phase 5C - Strict Mode Pauses

### Status

Complete. Closed by activation of Phase 5D - Autonomous Mode Initial Slice.

### Objective

Implement the `strict`-mode pause behavior defined in the Phase 5A
contract. This slice should add explicit human-gated pauses before a new
implementation prompt is dispatched, before a new fix prompt is
dispatched, and after Claude completion but before Codex review begins.
The shipped `review`-mode baseline from Phase 5B must remain intact, and
`autonomous` runtime branching remains deferred.

### Definition of done

- `scripts/agent_loop.py` implements the `strict`-mode pause behavior
  using the existing `approval_mode` runtime field
- strict mode pauses before a new implementation prompt is allowed to
  proceed, using `awaiting_human_for = "pre_claude_prompt"`
- strict mode pauses before a new fix prompt is allowed to proceed,
  using `awaiting_human_for = "pre_fix_prompt"`
- strict mode pauses after Claude completion and evidence capture but
  before Codex review begins, requiring explicit human approval before
  review starts
- the implemented strict-mode gates are represented explicitly in
  runtime/logging state and do not silently auto-resume under the wrong
  step
- `.agent-loop/claude-done.json` remains a routing/timing artifact only
  and integrates correctly with the strict pre-review human gate
- the shipped `review`-mode behavior from Phase 5B is not regressed
- focused tests cover strict-mode gate entry, strict-mode resume after
  human approval, correct `awaiting_human_for` transitions, and
  non-regression of the review path
- `README.md` reflects that Phase 5C is active and that `strict` is the
  implementation focus while `autonomous` remains deferred

### Exclusions

- no implementation of `autonomous` runtime continuation behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  strict-mode pause implementation
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 6 durable memory / checkpoint / continuation implementation
- no Phase 7 editor integration
- no Git automation

## Phase 5D - Autonomous Mode Initial Slice

### Status

Complete. Closed by activation of Phase 5E - Post-Review Artifact Reconciliation.

### Objective

Implement the first narrow `autonomous` runtime continuation behavior
defined in the Phase 5A contract. This slice should allow the loop to
continue automatically through implementation handoff, Claude
completion-to-Codex-review handoff, and bounded fix cycles where the
existing contracts already allow continuation, while preserving the
shipped `review` and `strict` behavior and without weakening any
existing hard safety stop.

### Definition of done

- `scripts/agent_loop.py` implements a narrow `autonomous` runtime path
  using the existing `approval_mode` field
- `autonomous` mode may automatically proceed through a normal
  implementation cycle and into Codex review without the strict-mode
  human pauses
- `autonomous` mode may automatically continue through bounded
  `NEEDS_FIXES` fix cycles only while `cycle_count`, `max_cycles`, and
  the existing threshold/escalation rules remain satisfied
- `autonomous` mode does not bypass evidence capture, Codex review
  ownership, malformed-artifact fail-closed behavior, or any
  `FAILED_REQUIRES_HUMAN` / `halted_*` stop
- human approval remains mandatory before phase progression and before
  any future Git action
- `.agent-loop/claude-done.json` remains a routing/timing artifact only
  and integrates correctly with the autonomous continuation path
- the shipped `review` and `strict` behavior from Phases 5B and 5C are
  not regressed
- focused tests cover autonomous normal-cycle continuation, autonomous
  bounded fix-cycle continuation, refusal on hard-stop conditions, and
  non-regression of the review and strict paths
- `README.md` reflects that Phase 5D is active and that `autonomous` is
  now the implementation focus

### Exclusions

- no broader autonomy model than the narrow initial autonomous
  continuation path for existing allowed loop steps
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  autonomous-mode continuation implementation
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 6 durable memory / checkpoint / continuation implementation
- no Phase 7 editor integration
- no Git automation

## Phase 5E - Post-Review Artifact Reconciliation

### Status

Closed after Codex review approval and human phase progression. Historical
record preserved.

### Objective

Implement post-review artifact reconciliation so Codex-owned artifact
issues are corrected automatically after review, Claude-owned issues are
synchronized into `.agent-loop/fix-prompt.md`, and the markdown/state
artifact set remains coherent before the loop proceeds. This slice should
preserve the shipped `review`, `strict`, and `autonomous` runtime
behavior while making ownership-driven follow-up more consistent and less
manual.

### Definition of done

- `scripts/agent_loop.py` implements post-review artifact reconciliation
  for supported Codex-owned artifact fixes and Claude-owned fix-prompt
  generation
- review findings are classified into Codex-owned vs Claude-owned
  follow-up using explicit ownership or deterministic fallback rules
- supported Codex-owned follow-up may directly update coherent
  markdown/state/prompt/review artifacts without touching Claude-owned
  implementation files
- Claude-owned findings regenerate `.agent-loop/fix-prompt.md` in the
  required format, derived directly from the current Codex review
- reconciliation refuses or halts when ownership is ambiguous, when a
  requested Codex-owned action is unsupported, or when the requested
  correction would overwrite Claude-owned implementation work
- the shipped `review`, `strict`, and `autonomous` runtime behavior from
  Phases 5B, 5C, and 5D are not regressed
- focused tests cover mixed-owner reviews, supported Codex-owned
  artifact auto-fixes, generated Claude fix prompts, refusal on
  unsupported/ambiguous reconciliation, and non-regression of the
  approval-mode runtime paths
- `README.md` reflects that Phase 5E is active and that post-review
  artifact reconciliation is now the implementation focus

### Exclusions

- no broader autonomy model than the current Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  post-review reconciliation implementation
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 6 durable memory / checkpoint / continuation implementation
- no Phase 7 editor integration
- no Git automation

## Phase 5F - Automatic Phase-Start Claude Prompt Bootstrap

### Status

Closed after Codex review approval and human phase progression. Historical
record preserved.

### Objective

Implement automatic phase-start Claude prompt bootstrap so Codex can
synthesize `.agent-loop/claude-prompt.md` directly from the newly active
phase/task artifacts after phase activation, while refusing if the source
artifacts are incomplete, contradictory, or unsafe to hand off.

### Definition of done

- `scripts/agent_loop.py` implements automatic phase-start Claude prompt
  generation from the canonical active phase/task artifacts
- prompt bootstrap reads the active phase/task definition from the
  canonical repo artifacts rather than depending on manually written
  prompt text
- bootstrap validates that the required source artifacts are present,
  ordered, non-empty where required, and mutually consistent before
  writing `.agent-loop/claude-prompt.md`
- bootstrap refuses or halts instead of guessing when the phase
  definition is incomplete, contradictory, stale, or otherwise unsafe to
  hand off to Claude
- the shipped Phase 5E post-review reconciliation behavior remains
  intact, including `.agent-loop/fix-prompt.md` generation from
  Claude-owned review findings on `NEEDS_FIXES`
- the shipped `review`, `strict`, and `autonomous` runtime behavior from
  Phases 5B, 5C, and 5D are not regressed
- focused tests cover successful phase-start prompt generation, refusal
  on incomplete/inconsistent source artifacts, preservation of the
  existing fix-prompt path, and non-regression of the approval-mode
  runtime paths
- `README.md` reflects that Phase 5F is active and that automatic
  phase-start Claude prompt bootstrap is now the implementation focus

### Exclusions

- no broader autonomy model than the current Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  phase-start prompt-bootstrap implementation
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 6 durable memory / checkpoint / continuation implementation
- no Phase 7 editor integration
- no Git automation

## Phase 6A - Durable Memory Contract

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Define the durable memory contract before implementation: what counts as
durable memory versus canonical task/state artifacts, how memory and
checkpoint data is categorized and stored, how selective retrieval works,
and how interruption recovery must preserve the existing safety and
approval boundaries.

### Definition of done

- `.agent-loop/phase-plan.md` contains a durable memory contract section
  that clearly separates canonical workflow/state artifacts from future
  memory artifacts
- the contract defines the intended durable memory categories for future
  implementation, including decisions, failures, preferences, summaries,
  and checkpoint/continuation state
- the contract defines checkpoint/resume behavior for interrupted Claude
  and Codex runs, including token-exhaustion handling and bounded
  continuation rules
- the contract defines selective retrieval rules so memory augments
  prompts without becoming a competing source of truth
- the contract defines refusal / halt conditions for missing, stale, or
  contradictory memory/checkpoint state
- the shipped review, strict, autonomous, reconciliation, and phase-start
  prompt behavior from Phases 5B through 5F are not regressed in effect
- `README.md` reflects that Phase 6A is active and that durable memory
  contract definition is now the implementation focus

### Exclusions

- no implementation of memory storage, checkpoint files, retrieval
  pipelines, or continuation chaining in code during this slice
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `scripts/run_checks.sh`
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

### Durable Memory Contract

The contract below defines how future Phase 6 implementation slices must
behave. Phase 6A documents the rules; later 6x slices implement them. No
runtime file, schema, or storage layout is created by this slice.

#### Scope and ownership boundaries

Durable memory is a separate, additive artifact layer. It must not
substitute for, override, or compete with the existing canonical
workflow / state artifacts.

Canonical workflow / state artifacts (Codex- or orchestrator-owned,
unchanged by Phase 6):

- `TASK.md`
- `.agent-loop/current-task.md`
- `.agent-loop/current-phase.md`
- `.agent-loop/phase-plan.md`
- `.agent-loop/claude-prompt.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/fix-prompt.md`
- `.agent-loop/claude-summary.md`
- `.agent-loop/loop-state.json`
- `.agent-loop/orchestrator.log`
- `.agent-loop/claude-done.json`
- the evidence files (`git-diff.patch`, `git-status.log`,
  `test-output.log`, `lint-output.log`, `typecheck-output.log`,
  `build-output.log`)

Future durable memory artifacts (Phase 6 implementation-owned, NOT yet
created):

- a memory directory under `.agent-loop/memory/` whose layout is
  defined by a later 6x implementation slice
- per-category memory entries within that directory
- a checkpoint / continuation state file within that directory

Required scope rules for any later 6x implementation:

- memory artifacts must live under their own directory (the canonical
  artifact set above is read-only to the memory layer)
- a missing or empty memory layer must not block any cycle that the
  canonical artifacts can already drive
- the canonical artifacts remain the single source of truth for the
  active phase / task / cycle / verdict; memory is advisory only
- memory writes are subject to the existing ownership boundaries
  (Codex-owned vs Claude-owned vs orchestrator-owned), and no memory
  write may modify any canonical artifact

#### Durable memory categories

Any later 6x implementation must categorize each memory entry as
exactly one of the following kinds:

- `decision`: a chosen approach the loop should keep applying (for
  example, "this project uses pytest, not unittest, for new suites").
  Sourced from explicit human direction or from a confirmed
  Codex/Claude resolution.
- `failure`: a known failure mode the loop should avoid repeating (for
  example, "do not bypass the strict-gate resume mode-coherence
  check"). Sourced from a refusal, halt, or correction recorded in a
  prior cycle.
- `preference`: a stylistic or workflow rule the human or Codex has
  expressed (for example, "keep claude-summary.md ASCII-only").
  Sourced from explicit human direction or from a confirmed Codex
  ruling.
- `summary`: a compact, retrieval-friendly synopsis of prior work
  (for example, the high-level outcome of a closed sub-phase).
  Sourced by post-cycle synthesis from canonical artifacts, not from
  raw prompt text.
- `checkpoint`: structured continuation state for an interrupted
  Claude or Codex run, including token-exhaustion checkpoints (see
  the dedicated subsection below).

The five category names are exhaustive for this contract. Any later
slice that needs a new category must add it via a contract revision
rather than introduce a new ad-hoc kind.

Required metadata for every memory entry (later implementation must
populate, the contract requires the field to exist):

- `category` (one of the five above)
- `phase` and `sub_phase` of the cycle that created the entry
- `cycle_count` of the cycle that created the entry
- `source_artifact_path` (which canonical artifact the entry was
  derived from, or `human` for direct human direction)
- `created_at` (ISO-8601 UTC timestamp)
- `signal_version` (versioned schema marker, same pattern as
  `.agent-loop/claude-done.json`)

Memory entries are append-mostly. A later 6x implementation may
supersede a stale entry with a fresh one, but must record the
supersession (an explicit "supersedes" reference) rather than silently
mutate existing bytes.

#### Checkpoint and resume behavior

A `checkpoint` memory entry is the only memory kind that has runtime
significance for resume. It must capture:

- the cycle context being suspended (`phase`, `sub_phase`, `task`,
  `cycle_count`, `status`, `approval_mode`, `awaiting_human_for`)
- the active prompt path (`.agent-loop/claude-prompt.md` or
  `.agent-loop/fix-prompt.md`)
- the reason for suspension (`token_exhaustion`, `human_interrupt`,
  `process_killed`, `orchestrator_restart`, or a contract-named
  Phase 5C strict-gate halt)
- a bounded continuation budget: the maximum number of further
  continuation attempts the loop may take for this checkpoint before
  escalating to human resolution

Required runtime behavior for any later 6x implementation:

- a checkpoint write must NOT mutate any canonical artifact
- on resume, the loop must verify that the checkpoint's
  (`phase`, `sub_phase`, `task`, `cycle_count`) matches the current
  `.agent-loop/loop-state.json`; on any mismatch the loop must refuse
  and require human resolution
- token-exhaustion checkpoints inherit the existing approval-mode
  vocabulary: the resumed cycle stays in the same `approval_mode`
  that wrote the checkpoint and does not silently flip to
  `autonomous` continuation
- a strict-gate halt that has its own resume path
  (`halted_awaiting_human_pre_*`) must continue to dispatch through
  the existing `run_strict_resume` flow; the checkpoint memory is
  advisory and does not replace strict-gate dispatch
- bounded continuation: the loop must count continuation attempts
  for the same checkpoint and refuse to continue past the
  checkpoint's declared budget without explicit human approval
- a stale checkpoint (one whose canonical `loop-state.json` context
  has moved on) must be refused at resume time, not silently
  consumed
- checkpoint reads happen at resume; no automatic background
  continuation may fire without an explicit resume invocation

#### Selective retrieval

Durable memory augments prompts; it does not replace canonical inputs.
Any later 6x implementation that adds retrieval into Codex- or Claude-
authored prompts must:

- treat retrieval as a read-only enrichment step that runs AFTER the
  canonical phase/task artifacts have been parsed and validated
- limit the retrieved set to entries whose metadata is relevant to
  the active `phase`, `sub_phase`, or `task`
- bound the retrieved set so a single prompt cannot be flooded with
  memory entries (a hard upper bound defined by the implementation
  slice, not unbounded)
- mark retrieved entries as advisory text in the prompt, never as
  authoritative state that overrides the canonical artifacts
- never feed memory back into a verdict, a halt status, an
  `awaiting_human_for` value, or any other field that is supposed to
  come from the canonical loop
- refuse to retrieve from any memory entry whose required metadata
  is missing or whose `signal_version` is not recognized by the
  current orchestrator

Retrieval is selective by design: the contract intentionally forbids
"all memory always" enrichment, because that would let memory drift
become a hidden source of truth.

#### Required human gates that durable memory may not bypass

The Phase 5A approval-mode gates remain the authoritative human-control
surface. Durable memory may not relax them.

Specifically, no later 6x implementation may use memory to:

- skip an `awaiting_human_for` gate that any approval mode currently
  enforces
- auto-continue past `FAILED_REQUIRES_HUMAN`, any `halted_*` status,
  or unresolved threshold escalation
- treat a checkpoint resume as equivalent to phase progression
  (phase progression still requires the existing human approval)
- treat a checkpoint resume as equivalent to commit approval (no
  Git action is in scope for any Phase 6 slice)
- broaden the shipped `autonomous` runtime path beyond its Phase 5D
  definition by silently re-enabling steps the operator had not yet
  approved

#### Refusal / halt / escalation cases

Any later 6x implementation must refuse or halt closed when any of
the following holds:

- a referenced memory entry is missing, unreadable, or empty where
  required metadata is expected
- a checkpoint's `phase` / `sub_phase` / `task` / `cycle_count`
  disagrees with the current `.agent-loop/loop-state.json`
- a checkpoint's `approval_mode` disagrees with the current
  `.agent-loop/loop-state.json` `approval_mode` and the cycle is in
  flight
- a checkpoint declares a continuation budget that has already been
  exhausted by prior resume attempts
- a memory entry's `signal_version` is not recognized
- a memory entry claims a category outside the five exhaustive
  categories defined above
- retrieval would inject memory text into a prompt for a phase or
  sub-phase that does not match the entry's metadata
- a memory write attempts to modify any canonical workflow / state
  artifact
- a checkpoint resume is attempted under an `approval_mode` that the
  checkpoint did not record

Required handling on any of the above:

- fail closed (no partial application of the memory entry, no
  partial resume)
- record the reason in `.agent-loop/orchestrator.log` (and a
  Phase 6 memory-log file if a later slice introduces one)
- do not silently fall back to "no memory" without surfacing the
  refusal in audit artifacts
- require human resolution when the inconsistency touches resume
  semantics, cycle ownership, or any of the gates listed above

#### Implementation constraints for later 6x slices

Any later 6x implementation must:

- preserve the Phase 2A Evidence Collection Contract
- preserve the Phase 3A Orchestrator Contract
- preserve the Phase 4A Planning Contract
- preserve the shipped Phase 5B / 5C / 5D / 5E / 5F runtime behavior
  (review default, strict gates and resume, autonomous bypass log
  signature, post-review reconciliation, atomic-or-rollback
  activation that includes the bootstrapped claude-prompt.md)
- treat `.agent-loop/claude-done.json` as a routing/timing artifact,
  not a correctness artifact, exactly as Phase 5A and Phase 5B define
- keep all memory behavior auditable from on-disk artifacts; no
  memory may live only in transient process state
- document any user-visible behavior change in `README.md`
- ship behind explicit, opt-in operator action (a subcommand, an env
  var, or both); no memory layer may auto-activate on a repo that
  was operating without it

## Phase 6B - Structured Durable Memory Storage

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement the structured in-repo durable memory storage layer defined by
the Phase 6A contract. This slice should create the append-mostly
on-disk memory surface under `.agent-loop/memory/`, enforce the five
allowed memory categories plus the required metadata fields, and preserve
the existing Phase 5 runtime behavior by deferring retrieval,
checkpoint-consumption, and continuation-driving behavior to later 6x
slices.

### Definition of done

- `scripts/agent_loop.py` implements a narrow durable memory storage
  surface scoped under `.agent-loop/memory/`
- the implementation supports the five Phase 6A categories:
  `decision`, `failure`, `preference`, `summary`, and `checkpoint`
- durable memory writes enforce the required Phase 6A metadata fields
  (`category`, `phase`, `sub_phase`, `cycle_count`,
  `source_artifact_path`, `created_at`, `signal_version`) and refuse
  malformed entries fail-closed
- durable memory writes are append-mostly and record supersession via
  explicit references rather than silent in-place mutation
- the implementation never mutates canonical task / state artifacts and
  never writes outside `.agent-loop/memory/`
- no normal runtime path automatically retrieves durable memory into a
  Claude or Codex prompt in this slice
- no normal runtime path consumes checkpoint memory for resume or
  token-exhaustion continuation in this slice
- focused tests cover valid writes, invalid-category refusal,
  missing-metadata refusal, append-mostly behavior, supersession
  handling, and write-boundary enforcement
- `README.md` reflects that Phase 6B is active and that structured
  durable memory storage is now the implementation focus

### Exclusions

- no retrieval pipeline that injects durable memory into Claude or Codex
  prompts
- no automatic checkpoint creation during live runs
- no resume-path consumption of checkpoint memory
- no token-exhaustion continuation chaining or automatic continuation
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6C - Selective Memory Retrieval Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement selective retrieval of durable memory entries from the shipped
Phase 6B storage layer. This slice should validate stored entries,
filter them down to a bounded set relevant to the active phase, sub-phase,
or task, and expose an advisory-only retrieval surface suitable for
future prompt construction without enabling checkpoint-consumption,
resume-path continuation, or token-exhaustion chaining.

### Definition of done

- `scripts/agent_loop.py` implements a narrow retrieval surface on top of
  `.agent-loop/memory/`
- retrieval reads only valid Phase 6A / 6B memory entries and refuses
  malformed, unknown-category, or unrecognized-`signal_version` entries
  fail-closed
- retrieval supports filtering by active `phase`, optional `sub_phase`,
  and optional category filters, with task-level scoping implicit in the
  active `(phase, sub_phase)` pair rather than a separate entry-side task
  field
- retrieval enforces a hard bounded result set so prompt enrichment never
  loads all memory entries by default
- the retrieval surface marks returned memory as advisory-only and does
  not override canonical task / state artifacts, verdicts, halt statuses,
  or `awaiting_human_for`
- no normal runtime path consumes checkpoint memory for resume or
  token-exhaustion continuation in this slice
- focused tests cover relevant-entry filtering, result bounding,
  malformed-entry refusal, unknown-category refusal, and preservation of
  canonical-artifact precedence
- `README.md` reflects that Phase 6C is active and that selective memory
  retrieval is now the implementation focus

### Exclusions

- no automatic checkpoint creation during live runs
- no resume-path consumption of checkpoint memory
- no token-exhaustion continuation chaining or automatic continuation
- no phase-boundary memory distillation or repeated-failure memory
  synthesis
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6D - Checkpoint Artifact Storage Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement structured checkpoint artifact storage for interrupted Claude
and Codex work. This slice should create dedicated checkpoint artifacts
and storage paths that satisfy the Phase 6A checkpoint contract while
remaining additive: checkpoint records are written and validated, but not
yet consumed by `resume`, token-exhaustion continuation, or any other
continuation-driving runtime path.

### Definition of done

- `scripts/agent_loop.py` implements a narrow checkpoint artifact storage
  surface for interrupted Claude/Codex work
- checkpoint writes enforce the required Phase 6A checkpoint metadata,
  including cycle context, prompt path, suspension reason, and bounded
  continuation-budget fields
- checkpoint artifacts live only under dedicated Phase 6 checkpoint
  storage paths and never mutate canonical task / state artifacts
- checkpoint reads used for validation refuse malformed, stale,
  unknown-category, or out-of-scope checkpoint artifacts fail-closed
- no normal runtime path consumes checkpoint artifacts for `resume` or
  token-exhaustion continuation in this slice
- focused tests cover valid checkpoint writes, malformed-checkpoint
  refusal, checkpoint write-boundary enforcement, and preservation of
  canonical-artifact precedence
- `README.md` reflects that Phase 6D is active and that checkpoint
  artifact storage is now the implementation focus

### Exclusions

- no `resume`-path consumption of checkpoint artifacts
- no token-exhaustion continuation chaining or automatic continuation
- no phase-boundary memory distillation or repeated-failure memory
  synthesis
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6E - Checkpoint Resume Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement checkpoint-backed resume handling for interrupted Claude and
Codex work. This slice should consume the stored checkpoint artifacts
shipped in Phase 6D during explicit `resume`, validate checkpoint
context against the canonical loop state, and preserve the existing
Phase 5 strict-gate routing semantics while refusing stale or
contradictory checkpoints fail-closed.

### Definition of done

- `scripts/agent_loop.py` implements a narrow checkpoint-backed resume
  surface for explicit `resume`
- resume-path checkpoint handling validates stored checkpoint artifacts
  against the canonical loop-state context and refuses stale,
  contradictory, malformed, or unrecognized checkpoint records fail-closed
- checkpoint-backed resume preserves the shipped Phase 5 strict-gate
  routing semantics and does not widen autonomy or bypass human gates
- resume consumption remains explicit; no token-exhaustion continuation
  chaining or automatic continuation is enabled in this slice
- focused tests cover valid checkpoint-backed resume handling,
  stale-checkpoint refusal, contradictory-context refusal,
  malformed-checkpoint refusal, and preservation of canonical-artifact
  precedence
- `README.md` reflects that Phase 6E is active and that checkpoint-backed
  resume handling is now the implementation focus

### Exclusions

- no token-exhaustion continuation chaining or automatic continuation
- no phase-boundary memory distillation or repeated-failure memory
  synthesis
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  checkpoint-backed resume implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6F - Token Exhaustion Continuation Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement token-exhaustion continuation handling for interrupted Claude and
Codex work. This slice should classify token or context exhaustion as a
resumable interruption, persist and consume the checkpoint continuation state
required for bounded continuation attempts, and preserve the existing Phase 5
approval-mode and strict-gate semantics while still deferring automatic
continuation chaining.

### Definition of done

- `scripts/agent_loop.py` implements a narrow token-exhaustion continuation
  surface on top of the shipped checkpoint storage and resume layers
- token or context exhaustion is treated as an interrupted-run state rather
  than silent success
- continuation handling persists and consumes checkpoint state that captures
  the active cycle context, prompt path, suspension reason, and bounded
  continuation budget
- bounded continuation attempts are enforced for the active checkpoint and
  refused fail-closed when exhausted, stale, contradictory, or malformed
- token-exhaustion continuation preserves the shipped Phase 5 approval-mode
  and strict-gate routing semantics and does not widen autonomy or bypass
  human gates
- no automatic continuation chaining or background continuation behavior is
  enabled in this slice
- focused tests cover valid token-exhaustion continuation handling,
  interruption classification, bounded-budget enforcement, exhausted-budget
  refusal, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6F is active and that token-exhaustion
  continuation handling is now the implementation focus

### Exclusions

- no automatic continuation chaining or any other background continuation
  behavior
- no phase-boundary memory distillation or repeated-failure memory synthesis
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  token-exhaustion continuation implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6G - Automatic Continuation Chaining Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement automatic continuation chaining for interrupted Claude and Codex
work. This slice should automatically continue from eligible
token-exhaustion interruptions using the shipped checkpoint continuation
layer, keep that continuation bounded and auditable, and preserve the
existing Phase 5 approval-mode and strict-gate semantics while still
deferring phase-boundary memory distillation and broader optional-context
behavior.

### Definition of done

- `scripts/agent_loop.py` implements a narrow automatic continuation-chaining
  surface on top of the shipped checkpoint storage, checkpoint resume, and
  token-exhaustion continuation layers
- eligible token or context exhaustion interruptions can continue
  automatically within bounded continuation policy
- continuation chaining consumes checkpoint state deterministically and
  refuses fail-closed when the active checkpoint is stale, contradictory,
  malformed, unsupported-stage, unrecognized, or budget-exhausted
- automatic continuation chaining preserves the shipped Phase 5
  approval-mode and strict-gate routing semantics and does not widen
  autonomy or bypass human gates
- no phase-boundary memory distillation or broader optional-context loading
  is enabled in this slice
- focused tests cover valid automatic continuation chaining, bounded
  multi-hop continuation, exhausted-budget refusal, unsupported-stage
  refusal, and preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6G is active and that automatic
  continuation chaining is now the implementation focus

### Exclusions

- no phase-boundary memory distillation or repeated-failure memory synthesis
- no broader optional context-file loading or retrieval expansion
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  automatic continuation-chaining implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6H - Bounded Continuation Prompt Construction Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement bounded continuation prompt construction for interrupted Claude and
Codex work. This slice should assemble continuation-safe prompt/context input
from canonical task and loop-state artifacts, the active checkpoint,
selectively retrieved durable memory, and bounded evidence so a later runtime
can resume work from persisted artifacts rather than raw transcript history,
while preserving the shipped Phase 5 approval-mode and strict-gate semantics
and still deferring phase-boundary memory distillation and broader
optional-context behavior.

### Definition of done

- `scripts/agent_loop.py` implements a narrow continuation prompt/context
  construction surface on top of the shipped memory retrieval, checkpoint, and
  token-exhaustion continuation layers
- continuation prompt construction reads canonical task / phase / loop-state
  artifacts plus the active checkpoint and bounded objective evidence rather
  than requiring raw transcript replay
- continuation prompt construction can include selectively retrieved durable
  memory entries relevant to the active phase / sub-phase while preserving
  advisory-only precedence over canonical artifacts
- continuation prompt construction enforces explicit bounds on included memory
  entries and evidence payloads so a continuation cannot silently expand into
  an unbounded repo dump
- stale, contradictory, malformed, unsupported-stage, or unrecognized
  checkpoint / loop-state / memory inputs refuse fail-closed
- continuation prompt construction preserves the shipped Phase 5 approval-mode
  and strict-gate routing semantics and does not widen autonomy or bypass human
  gates
- no phase-boundary memory distillation or broader optional-context loading is
  enabled in this slice
- focused tests cover valid continuation prompt construction, bounded evidence
  and memory inclusion, stale-or-contradictory checkpoint refusal, and
  preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6H is active and that bounded continuation
  prompt construction is now the implementation focus

### Exclusions

- no phase-boundary memory distillation or repeated-failure memory synthesis
- no broader optional context-file loading or retrieval expansion
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  continuation prompt construction implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6I - Phase-Boundary Memory Distillation Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement phase-boundary memory distillation for approved Claude/Codex work.
This slice should distill durable summary, decision, and failure knowledge from
canonical phase-boundary artifacts plus bounded review/evidence context into
append-mostly memory entries so later phases can preserve important project
knowledge across phase transitions without treating raw transcripts as memory,
while preserving the shipped Phase 5 approval-mode and strict-gate semantics
and still deferring broader optional-context behavior.

### Definition of done

- `scripts/agent_loop.py` implements a narrow phase-boundary memory
  distillation surface on top of the shipped memory storage, retrieval,
  checkpoint, continuation, and continuation-context layers
- distillation reads canonical task / phase / loop-state artifacts plus bounded
  review/evidence context rather than replaying raw transcript history
- distillation writes append-mostly durable memory entries in allowed Phase 6
  categories using explicit, documented source-artifact references
- distillation preserves canonical task / state precedence and does not mutate
  canonical planning or loop-state artifacts
- stale, contradictory, malformed, unsupported, or unrecognized distillation
  inputs refuse fail-closed
- phase-boundary distillation preserves the shipped Phase 5 approval-mode and
  strict-gate routing semantics and does not widen autonomy or bypass human
  gates
- no broader optional-context loading is enabled in this slice
- focused tests cover valid phase-boundary distillation, bounded source
  selection, malformed-or-contradictory input refusal, and preservation of
  canonical-artifact precedence
- `README.md` reflects that Phase 6I is active and that phase-boundary memory
  distillation is now the implementation focus

### Exclusions

- no repeated-failure memory synthesis beyond the narrow phase-boundary
  distillation helpers needed for this slice
- no broader optional context-file loading or retrieval expansion
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  phase-boundary distillation implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6J - Optional Context File Loading Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Implement declared optional-context file loading on top of the shipped memory,
checkpoint, continuation-context, and phase-boundary distillation layers. This
slice should let the system validate a narrow, explicit set of in-repo context
files and read bounded advisory excerpts from them into an auditable payload so
later prompts can benefit from project docs without treating arbitrary repo
files as implicit truth, while preserving canonical task/state precedence and
the shipped Phase 5 approval-mode and strict-gate semantics.

### Definition of done

- `scripts/agent_loop.py` implements a narrow optional-context declaration and
  loading surface on top of the shipped Phase 6 memory and continuation-context
  primitives
- optional-context loading accepts only explicitly declared in-repo file paths;
  arbitrary repo traversal, glob expansion, and out-of-repo targets are refused
  fail-closed
- loaded context is advisory-only, records explicit source-path provenance, and
  never overrides canonical task / phase / loop-state artifacts
- context loading enforces explicit bounds on the number of files and bytes
  included so a prompt cannot silently expand into an unbounded repo dump
- stale, contradictory, malformed, unreadable, unsupported, out-of-bound, or
  unrecognized optional-context inputs refuse fail-closed
- optional-context loading preserves the shipped Phase 5 approval-mode and
  strict-gate routing semantics and does not widen autonomy or bypass human
  gates
- no repeated-failure memory synthesis, arbitrary repo-file ingestion, or
  broader framework-backed context loading is enabled in this slice
- focused tests cover valid optional-context loading, declaration/path
  validation, excerpt bounding, malformed-or-unreadable input refusal, and
  preservation of canonical-artifact precedence
- `README.md` reflects that Phase 6J is active and that optional-context file
  loading is now the implementation focus

### Exclusions

- no repeated-failure memory synthesis in this slice
- no automatic loading of arbitrary repo files outside an explicit declaration
- no semantic retrieval, embedding index, or broader RAG layer
- no LangChain, LangGraph, CrewAI, or other framework-backed runtime path in
  this slice
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  optional-context loading implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6K - Optional Context Prompt Integration Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Integrate the shipped Phase 6J declared optional-context payload into
prompt/context construction on top of the shipped memory, checkpoint,
continuation, continuation-context, phase-boundary distillation, and
optional-context loading layers. This slice should let the system consume only
the existing bounded `.agent-loop/optional-context.json` advisory payload and
surface it in a later prompt/context path while preserving canonical
task/state/checkpoint precedence, explicit advisory semantics, and the shipped
Phase 5 approval-mode and strict-gate behavior.

### Definition of done

- `scripts/agent_loop.py` implements a narrow optional-context
  prompt/context-integration surface on top of the shipped Phase 6 memory,
  continuation-context, and 6J optional-context payload primitives
- prompt/context integration reads only the existing Phase 6J
  `.agent-loop/optional-context.json` artifact and does not reopen arbitrary
  repo files or silently expand into new repo-ingestion behavior
- integrated optional context preserves canonical task / phase / loop-state /
  checkpoint precedence and remains explicitly advisory-only
- integrated optional context preserves explicit source-path provenance and
  bounded inclusion behavior from the shipped 6J payload rather than replacing
  it with raw repo reads
- missing, malformed, contradictory, unreadable, unsupported, out-of-bound, or
  unrecognized optional-context payloads refuse fail-closed
- optional-context prompt/context integration preserves the shipped Phase 5
  approval-mode and strict-gate routing semantics and does not widen autonomy
  or bypass human gates
- no repeated-failure synthesis, arbitrary repo-file ingestion, or broader
  framework-backed context loading is enabled in this slice
- focused tests cover valid optional-context prompt/context integration,
  advisory-precedence preservation, bounded inclusion behavior, and
  malformed-or-contradictory payload refusal
- `README.md` reflects that Phase 6K is active and that optional-context
  prompt integration is now the implementation focus

### Exclusions

- no repeated-failure memory synthesis in this slice
- no automatic loading or reopening of arbitrary repo files outside the shipped
  6J payload
- no semantic retrieval, embedding index, or broader RAG layer
- no LangChain, LangGraph, CrewAI, or other framework-backed runtime path in
  this slice
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  optional-context prompt/context integration implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6L - Repeated-Failure Memory Synthesis Initial Slice

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Distill recurring review/fix failure patterns into durable advisory failure
knowledge on top of the shipped memory, checkpoint, continuation,
continuation-context, phase-boundary distillation, optional-context loading,
and optional-context prompt-integration layers. This slice should synthesize
bounded failure knowledge only from canonical loop-state plus bounded canonical
artifacts and prior fix/review evidence, while preserving canonical
task/state/checkpoint precedence, append-mostly memory behavior, explicit
provenance, and the shipped Phase 5 approval-mode and strict-gate behavior.

### Definition of done

- `scripts/agent_loop.py` implements a narrow repeated-failure memory synthesis
  surface on top of the shipped Phase 6 memory and continuation primitives
- repeated-failure synthesis reads only bounded canonical artifacts and
  existing loop-state context and does not treat arbitrary repo files, raw logs,
  or whole transcripts as durable memory input
- synthesized failure knowledge is explicitly advisory-only, provenance-carrying,
  and append-mostly inside the existing memory model
- synthesized failure knowledge preserves canonical task / phase / loop-state /
  checkpoint precedence and does not override Phase 5 approval-mode or
  strict-gate decisions
- missing, malformed, contradictory, unreadable, unsupported, out-of-bound, or
  ineligible repeated-failure synthesis inputs refuse fail-closed
- repeated-failure synthesis preserves the shipped Phase 5 approval-mode and
  strict-gate routing semantics and does not widen autonomy or bypass human
  gates
- no arbitrary repo-file ingestion, broader optional-context loading, or
  broader framework-backed context behavior is enabled in this slice
- focused tests cover valid repeated-failure synthesis, malformed-or-
  contradictory input refusal, bounded source selection, and
  canonical-precedence preservation
- `README.md` reflects that Phase 6L is active and that repeated-failure
  memory synthesis is now the implementation focus

### Exclusions

- no arbitrary repo-file ingestion or raw-transcript-as-memory behavior
- no semantic retrieval, embedding index, or broader RAG layer
- no LangChain, LangGraph, CrewAI, or other framework-backed runtime path in
  this slice
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  repeated-failure memory synthesis implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6M - Runtime Adapter Contract For Framework Evaluation

### Status

Closed after Codex review approval and human phase progression.
Historical record preserved.

### Objective

Define the adapter contract that any future framework-backed runtime must honor
before it can be evaluated against the shipped local orchestrator. This slice
should specify canonical inputs, allowed writes, halt/refusal behavior,
checkpoint and durable-memory interaction rules, approval-mode preservation,
artifact-precedence guarantees, audit expectations, and evaluation constraints
so alternate runtimes can be compared without replacing repo-artifact truth or
the default local runtime.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 6 / 6M as active
- `.agent-loop/phase-plan.md` records Phase 6L as closed history and contains a
  `## Phase 6M - Runtime Adapter Contract For Framework Evaluation` section
  with concrete contract requirements
- the contract defines which canonical repo artifacts remain the source of
  truth for any alternate runtime, including task / phase files, loop-state,
  evidence, review artifacts, durable memory, and checkpoints
- the contract defines what an alternate runtime may read, what it may write,
  what it must never write, and how it must preserve Codex/Claude/human
  ownership boundaries
- the contract defines how an alternate runtime must mirror approval-mode,
  strict-gate, halt, refusal, checkpoint, continuation, and audit semantics
  from the shipped local orchestrator
- the contract defines evaluation constraints that keep the existing local
  orchestrator as the default runtime while allowing opt-in framework
  experiments later
- the contract explicitly forbids framework state, in-memory graphs, or
  provider-native metadata from superseding canonical repo artifacts
- `README.md` reflects that Phase 6M is active and that runtime-adapter
  contract definition is now the implementation focus

### Exclusions

- no implementation of LangGraph, LangChain, CrewAI, or any other
  framework-backed runtime path in this slice
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no arbitrary repo-file ingestion, semantic retrieval expansion, or broader
  RAG/runtime behavior beyond documenting future adapter constraints
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond defining a future
  adapter boundary around the shipped runtime
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

### Contract

This section is the runtime adapter contract proper. Any future
slice that adds a framework-backed runtime (LangGraph, LangChain,
CrewAI, an in-house planner runtime, an external supervisor process,
etc.) must satisfy every requirement below before that runtime can
be evaluated in this repository. The shipped local orchestrator
(`scripts/agent_loop.py`) is the reference implementation and the
default runtime; this contract describes how an alternate runtime
must mirror it without superseding it.

The contract uses three terms:

- "alternate runtime" - a Phase 6N+ framework-backed runtime built
  against this contract.
- "canonical repo artifact" - a file enumerated under "Canonical
  source-of-truth artifacts" below.
- "framework state" - any in-memory graph, agent state, scratchpad,
  provider-native metadata, or vendor-managed checkpoint owned by an
  alternate runtime's framework layer.

When the two disagree, the canonical repo artifact always wins.

#### Canonical source-of-truth artifacts

The following on-disk artifacts are canonical for any alternate
runtime. The alternate runtime MUST read them as authoritative and
MUST NOT replace, shadow, or override them with framework state:

- `TASK.md` (human objective + active phase / sub-phase / task)
- `.agent-loop/current-task.md`
- `.agent-loop/current-phase.md`
- `.agent-loop/phase-plan.md`
- `.agent-loop/loop-state.json` (status, cycle_count, max_cycles,
  last_verdict, approval_mode, awaiting_human_for, halt_status,
  contract_version, claude_version, codex_version,
  orchestrator_version)
- `.agent-loop/claude-prompt.md` and `.agent-loop/fix-prompt.md`
- `.agent-loop/claude-summary.md`
- `.agent-loop/codex-review.md`
- `.agent-loop/claude-done.json`
- the Phase 2A evidence files: `.agent-loop/git-diff.patch`,
  `.agent-loop/git-status.log`, `.agent-loop/test-output.log`,
  `.agent-loop/lint-output.log`, `.agent-loop/typecheck-output.log`,
  `.agent-loop/build-output.log`
- the Phase 6B durable memory tree at
  `.agent-loop/memory/<category>/` for every Phase 6A category
  (`decision`, `failure`, `preference`, `summary`, `checkpoint`)
- the Phase 6D / 6F / 6G checkpoint entries under
  `.agent-loop/memory/checkpoint/`
- the Phase 6H continuation-context artifact at
  `.agent-loop/continuation-context.json`
- the Phase 6J optional-context payload at
  `.agent-loop/optional-context.json`
- the Phase 6K optional-context prompt-integration artifact at
  `.agent-loop/optional-context-prompt.json`

This list IS the canonical set. A later slice that adds a new
canonical artifact MUST add it to this list before any alternate
runtime can rely on it.

`.agent-loop/orchestrator.log` is intentionally NOT in the canonical
source-of-truth set. Per the Phase 3A contract the log is OPTIONAL
("not required to exist") and is NEVER authoritative evidence; it is
a supplementary audit trail of orchestrator decisions, scoped to
`.agent-loop/`, that an alternate runtime MAY append to per the
"Allowed writes" and "Audit expectations" subsections below. When
`orchestrator.log` and a canonical repo artifact disagree, the
canonical artifact wins; the log is for reconstructing decisions,
not for driving them.

#### Allowed reads

An alternate runtime MAY read every canonical artifact above
through the same validators the shipped local orchestrator uses
(`load_loop_state`, `validate_loop_state`, `check_contract_version`,
`validate_claude_summary`, `validate_codex_review_and_parse_verdict`,
`read_memory_entry`, `list_memory_entries`, and the structural
validators for the 6H / 6J / 6K artifacts). The alternate runtime
MUST refuse fail-closed on every refusal the validator raises,
using the existing `HaltError` vocabulary; it MUST NOT swallow or
re-label a refusal.

An alternate runtime MAY read the existing planner / activator /
review artifacts (`.agent-loop/proposed-phase.md`,
`.agent-loop/planner.log`, etc.) only through the same code paths
the shipped orchestrator uses; it MUST NOT hand-parse them with a
framework-native parser that diverges from the shipped validator.

An alternate runtime MUST NOT read arbitrary repo files outside the
explicit Phase 6J declared-paths surface. Repo-file ingestion remains
opt-in, declared, bounded, and advisory-only per the Phase 6J / 6K
contracts.

#### Allowed writes

An alternate runtime MAY write only to the following paths, and only
through the shipped writer surface:

- the Phase 6B durable memory tree at
  `.agent-loop/memory/<category>/` through `write_memory_entry(...)`
  (no direct file writes; the Phase 6B append-mostly guarantee,
  deterministic filename, and write-time collision refusal must be
  inherited)
- the Phase 6D / 6F / 6G checkpoint entries under
  `.agent-loop/memory/checkpoint/` through
  `write_checkpoint_entry(...)`
- the Phase 6H continuation-context artifact at
  `.agent-loop/continuation-context.json` through the shipped
  `build_continuation_prompt_context(...)` + handler write
- the Phase 6J optional-context payload at
  `.agent-loop/optional-context.json` through the shipped
  `load_optional_context(...)` + handler write
- the Phase 6K optional-context prompt artifact at
  `.agent-loop/optional-context-prompt.json` through the shipped
  `integrate_optional_context(...)` + handler write
- `.agent-loop/orchestrator.log` through `_log_note(...)` only

An alternate runtime MUST emit a `runtime adapter:` audit note to
`.agent-loop/orchestrator.log` on every entry into a runtime hop and
on every refusal, naming the alternate runtime's identifier and the
hop kind so the chain is reconstructable from the canonical log.

#### Forbidden writes

An alternate runtime MUST NOT write to:

- `TASK.md`, `.agent-loop/current-task.md`,
  `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`
  (planning state; Codex-owned)
- `.agent-loop/loop-state.json` outside the shipped
  `save_loop_state(...)` / `_halt(...)` paths (the Phase 3A
  write-ownership rules pin the allowed fields per writer; an
  alternate runtime that wants to advance loop-state MUST go through
  the shipped writer)
- `.agent-loop/claude-prompt.md`, `.agent-loop/fix-prompt.md`,
  `.agent-loop/claude-done.json` outside the shipped Phase 5
  bootstrap / completion paths (alternate runtimes consume these
  artifacts; they do not produce them)
- `.agent-loop/claude-summary.md` (Claude-owned)
- `.agent-loop/codex-review.md` (Codex-owned)
- the Phase 2A evidence files (orchestrator-owned; produced by the
  shipped evidence-capture step)
- `AGENTS.md`, `CLAUDE.md` (governance documents; human-owned)
- `README.md`, `ROADMAP.md` (Claude-routed implementation surface
  per `CLAUDE.md`'s ownership-boundaries section, the same as
  `scripts/` / `tests/` / application code; an alternate runtime
  MAY only mutate them by routing an implementation prompt through
  the shipped Claude adapter surface, not by writing them directly,
  exactly as the alternate runtime is forbidden from directly
  editing Claude-owned implementation code)
- any path that resolves outside the repo root (the Phase 6J / 6K
  write-boundary policy applies repository-wide for alternate
  runtimes)
- any framework-native sidecar file under `.agent-loop/` not
  enumerated under "Allowed writes" above (alternate runtimes MUST
  NOT introduce a parallel artifact tree under `.agent-loop/`;
  framework state lives outside `.agent-loop/`)

An alternate runtime MUST refuse fail-closed via `HaltError(...)`
before any forbidden write would land on disk. The refusal MUST go
through `_halt(...)` so the structural failure vocabulary is
recorded on `loop-state.json` and `orchestrator.log` exactly as the
shipped orchestrator records it.

#### Ownership boundaries

An alternate runtime MUST honor the existing Codex / Claude / human
ownership boundaries documented in `AGENTS.md` and `CLAUDE.md`:

- planning artifacts (`TASK.md`, `current-task.md`,
  `current-phase.md`, `phase-plan.md`, `proposed-phase.md`,
  `planner.log`) are Codex-owned and the alternate runtime MAY only
  invoke the shipped planner / activator surfaces to mutate them
- implementation artifacts (`scripts/`, `tests/`, application code,
  `README.md`-class docs reachable through normal implementation
  work) are Claude-owned and the alternate runtime MAY only route an
  implementation prompt through the shipped Claude adapter surface
  to mutate them
- review artifacts (`.agent-loop/codex-review.md`,
  `.agent-loop/fix-prompt.md`) are Codex-owned through the shipped
  review surface
- approval and phase progression are human-owned through the shipped
  `activate` flow; an alternate runtime MUST NOT advance phases,
  approve a proposal, or set `awaiting_human_for = null` outside the
  shipped writers

An alternate runtime MUST surface routing mismatches (an issue
classified as Codex-owned arriving on the Claude path, or vice
versa) rather than silently re-routing.

#### Approval-mode preservation

An alternate runtime MUST mirror the Phase 5A approval-mode
vocabulary exactly:

- `review` (default): the alternate runtime MUST persist
  `awaiting_human_for = "phase_complete_awaiting_human_approval"`
  on `APPROVED_FOR_HUMAN_REVIEW` and leave it null on
  `NEEDS_FIXES` / `FAILED_REQUIRES_HUMAN`, exactly as the shipped
  Phase 5B handler does
- `strict`: the alternate runtime MUST pause at each of the four
  Phase 5C gates (`pre_claude_prompt`, `pre_codex_review` for the
  normal cycle, `pre_fix_prompt`, `pre_codex_review` for the fix
  cycle), persist the matching halt status, write the matching
  `note:` line, and exit cleanly with code 2. Resume MUST go
  through the shipped `resume` subcommand
- `autonomous`: the alternate runtime MUST log each gate bypass
  with the Phase 5D `autonomous mode: bypassing <gate> gate at
  <where>` audit note and MUST preserve every hard stop the shipped
  Phase 5D preserves (`FAILED_REQUIRES_HUMAN`, missing evidence,
  the `cycle_count >= max_cycles` threshold on `NEEDS_FIXES`, the
  `APPROVED_FOR_HUMAN_REVIEW` phase-complete gate)

An alternate runtime MUST NOT introduce a new approval mode without
a Phase 5A contract revision.

#### Strict-gate, halt, and refusal vocabulary preservation

An alternate runtime MUST use the existing halt-status vocabulary
verbatim:

- the four Phase 5C strict-gate halts:
  `halted_awaiting_human_pre_claude_prompt`,
  `halted_awaiting_human_pre_fix_prompt`,
  `halted_awaiting_human_pre_codex_review_normal`,
  `halted_awaiting_human_pre_codex_review_fix`
- the Phase 6F token-exhaustion halt:
  `halted_awaiting_token_exhaustion_continuation`
- the structural refusal statuses `halted_input_missing`,
  `halted_contract_version_mismatch`, `halted_summary_malformed`,
  `halted_review_malformed`, `halted_review_parse_failed`,
  `halted_human_stop`, and any other halt status the shipped
  orchestrator already writes
- the existing `awaiting_human_for` vocabulary

An alternate runtime MUST NOT invent a new halt status. Adding a
new halt category requires a contract revision in this file plus a
corresponding update to the shipped `validate_loop_state` /
`_halt(...)` surface.

An alternate runtime MUST exit with code 2 on every refusal that
goes through `_halt(...)` and MUST exit with code 0 on a clean
terminal (matching the shipped orchestrator's exit-code discipline).

#### Checkpoint and continuation interaction

An alternate runtime MUST treat the Phase 6D checkpoint contract as
authoritative for interrupted runs:

- checkpoint entries MUST be written through
  `write_checkpoint_entry(...)`; the alternate runtime MUST NOT
  shadow the on-disk checkpoint with a framework-native checkpoint
- the Phase 6E `_load_active_checkpoint(...)` selection rule (most-
  recently-written by mtime, lexical filename as tie-breaker) is
  authoritative; an alternate runtime MUST NOT cache a different
  "active checkpoint"
- the Phase 6F token-exhaustion resume MUST consume the checkpoint
  through `run_token_exhaustion_resume(...)` and respect the
  `continuation_budget` field exactly; a fresh exhaustion event
  MUST go through `record_token_exhaustion(...)`
- the Phase 6G `AUTO_CONTINUE_MAX_HOPS = 4` defense-in-depth cap is
  authoritative; an alternate runtime MUST NOT widen it without a
  contract revision
- the Phase 6H continuation-context construction
  (`build_continuation_prompt_context(...)`) is the only sanctioned
  builder for a continuation prompt; an alternate runtime MAY
  consume the JSON artifact but MUST NOT build a framework-native
  alternative that diverges from the schema

#### Durable memory interaction

An alternate runtime MUST treat the Phase 6A durable memory
contract as the only durable-memory surface:

- the five Phase 6A categories are exhaustive; an alternate runtime
  MUST NOT introduce a sixth category
- the Phase 6B `signal_version = "phase-6b-v1"` envelope is the
  only recognized schema; an alternate runtime MUST NOT write
  entries with a different `signal_version`
- the Phase 6C retrieval is advisory-only; an alternate runtime
  MUST carry the `MEMORY_RETRIEVAL_ADVISORY_FIELD = True`
  structural marker through to any framework-native consumer, and
  MUST treat retrieved memory as advice that never overrides
  canonical state
- the Phase 6I phase-boundary distillation, Phase 6L repeated-
  failure synthesis, and the Phase 6D / 6F / 6G checkpoint writers
  are the only writers a framework runtime MAY route through; the
  alternate runtime MUST NOT bypass them with a direct file write
- the Phase 6J / 6K optional-context loading + integration is the
  only sanctioned repo-file ingestion path; an alternate runtime
  MUST NOT read arbitrary repo files for advisory context

The advisory-vs-canonical boundary is structural: an alternate
runtime that promotes advisory memory to canonical state (e.g. by
overwriting `loop-state.json` from a retrieved memory entry) MUST
be refused fail-closed in code review and MUST NOT ship.

#### Audit expectations

Every alternate-runtime hop MUST be reconstructable from the
canonical on-disk artifacts. Specifically:

- every refusal goes through `_halt(...)` so `loop-state.json` and
  `.agent-loop/orchestrator.log` carry the halt status and reason
- every transition logs a `note:` line to
  `.agent-loop/orchestrator.log` through `_log_note(...)`
- every memory write emits the shipped Phase 6B `memory write:`
  audit note when a `log_path` is supplied
- every checkpoint write emits the same `memory write:` note with
  `category='checkpoint'`
- every token-exhaustion event emits the Phase 6F / 6G audit notes
  (`token exhaustion recorded:`,
  `token-exhaustion resume consumed:`,
  `auto-continue chain hop N begin`)
- every approval-mode bypass under `autonomous` emits the Phase 5D
  `autonomous mode: bypassing <gate> gate at <where>` note
- every alternate-runtime hop additionally emits a
  `runtime adapter: <runtime_id> <hop_kind> ...` note so the
  alternate path is attributable in the same canonical log

An alternate runtime MUST NOT emit audit notes to a framework-
native log instead of `orchestrator.log`. A framework log MAY exist
as a sidecar (outside `.agent-loop/`) but the canonical audit trail
MUST land in `orchestrator.log`.

#### Default-runtime and evaluation constraints

The shipped local orchestrator at `scripts/agent_loop.py` is the
default runtime in this repository. An alternate runtime is opt-in
for evaluation and MUST satisfy:

- the alternate runtime is selectable via an explicit operator flag
  (e.g. `--runtime=langgraph`) or environment variable; absent the
  flag, the shipped local orchestrator runs unchanged
- the alternate runtime ships behind a feature flag in
  `.agent-loop/` (e.g. an opt-in line in a runtime-config file)
  AND a flag default of "off"; an alternate runtime MUST NOT be the
  active runtime on a clean checkout
- the alternate runtime MUST be evaluated by running the shipped
  full test suite (`python -m pytest tests/ -q`) against a
  workspace where the alternate runtime is selected; every shipped
  test MUST still pass without regression
- the alternate runtime MUST be evaluated by running a complete
  Phase 1 / 2 / 3 cycle end-to-end with the alternate runtime
  selected, producing the same canonical artifacts (TASK.md +
  loop-state.json + claude-summary.md + codex-review.md + evidence
  files) the shipped runtime produces, with the same verdict
- the alternate runtime MUST be evaluated on at least one
  representative refusal path (a strict-gate halt, a token-
  exhaustion halt, and a malformed-evidence halt) and MUST land
  the matching halt status on `loop-state.json` byte-for-byte
- the evaluation artifacts (runtime-config, alternate-runtime hop
  log, comparison report) live OUTSIDE the canonical artifacts; a
  comparison report MUST cite the canonical artifacts by content
  hash so a future audit can verify the alternate runtime produced
  byte-equivalent canonical state
- the evaluation MUST cover at least one full `auto-continue` chain
  (Phase 6G) to prove the alternate runtime preserves the bounded
  continuation behavior
- the shipped local orchestrator remains the default after the
  evaluation phase concludes; an alternate runtime is NOT promoted
  to default by this contract or by any evaluation phase. Promoting
  an alternate runtime to default requires a separate, explicit
  human decision recorded as a phase-plan revision

#### Framework-state subordination rule

This subsection is the load-bearing precedence rule. When framework
state and a canonical repo artifact disagree, the canonical repo
artifact wins, every time:

- in-memory graph nodes, agent state, scratchpads, vendor-managed
  checkpoints, and any other framework-native state MUST be treated
  as transient
- on every framework-runtime entry point, the runtime MUST re-load
  loop-state.json, the active checkpoint, and any consumed
  canonical artifact from disk (no caching across hops)
- on every framework-runtime exit, the runtime MUST flush any
  durable state through the shipped Phase 6B / 6D / 6F / 6G / 6H /
  6I / 6J / 6K / 6L writers (no direct file writes)
- a framework-managed checkpoint that disagrees with the on-disk
  Phase 6D checkpoint MUST be treated as stale; the on-disk
  checkpoint wins
- a framework-managed conversation history that disagrees with
  `claude-prompt.md` / `fix-prompt.md` / `claude-summary.md` MUST
  be treated as stale; the on-disk artifact wins
- a framework-managed memory tree that disagrees with
  `.agent-loop/memory/` MUST be treated as stale; the on-disk
  memory tree wins
- a framework-managed status / verdict / approval-mode that
  disagrees with `loop-state.json` MUST be treated as stale; the
  on-disk loop-state wins

An alternate runtime that violates this rule MUST be refused
fail-closed in code review and MUST NOT ship.

#### Open questions deferred to a later slice

The following are intentionally NOT pinned by this contract; a
later phase that actually implements a framework-backed runtime
must resolve each before shipping:

- the exact alternate-runtime selection mechanism (CLI flag vs.
  env var vs. runtime-config file vs. some combination) is a Phase
  6N implementation choice
- the alternate-runtime feature-flag file format (TOML, JSON, INI,
  shell env) is a Phase 6N implementation choice
- the exact comparison-report schema is a Phase 6N implementation
  choice; this contract pins only that a report MUST cite canonical
  artifacts by content hash
- the exact runtime-adapter audit-note format beyond the prefix
  `runtime adapter: <runtime_id> <hop_kind>` is a Phase 6N
  implementation choice
- the procedure for promoting an alternate runtime to default
  (separate human decision plus phase-plan revision) is
  intentionally unspecified beyond the requirement; the actual
  promotion criteria belong to a future governance phase

Resolving any open question above MUST be accompanied by an update
to this contract or to a downstream Phase 6 contract before the
implementation slice ships.

## Phase 6N - Experimental LangGraph Runtime Mirror

### Status

Complete and approved by human to advance to Phase 6O. Phase 6N closed with terminal verdict `APPROVED_FOR_HUMAN_REVIEW` after the experimental LangGraph runtime mirror, persisted runtime-config surface, wired runtime selection, and malformed-artifact recovery path were all verified in the current repo state.

### Objective

Implement a narrow experimental LangGraph-backed runtime mirror that exercises
the Phase 6M adapter contract in code. This slice should add an opt-in
alternate runtime path that mirrors the shipped local orchestrator's state
machine, halt/refusal vocabulary, checkpoint and continuation behavior,
durable-memory boundaries, and approval-mode semantics closely enough to be
evaluated against the local runtime, while preserving canonical repo-artifact
truth and keeping `scripts/agent_loop.py`'s existing local path as the default.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 6 / 6N as active
- `.agent-loop/phase-plan.md` records Phase 6M as closed history and contains a
  `## Phase 6N - Experimental LangGraph Runtime Mirror` section with concrete
  objective, done criteria, and exclusions
- `scripts/agent_loop.py` exposes a narrow opt-in alternate-runtime selection
  surface for an experimental LangGraph-backed runtime mirror while preserving
  the shipped local runtime as the default when no explicit selection is made
- the experimental runtime mirrors the shipped halt/refusal vocabulary,
  approval-mode behavior, checkpoint/continuation handling, durable-memory
  boundaries, and audit-note expectations closely enough to be compared against
  the default runtime under the Phase 6M contract
- the experimental runtime preserves canonical repo-artifact precedence over
  framework-managed state and refuses fail-closed when framework state
  contradicts canonical task, loop-state, checkpoint, memory, or review
  artifacts
- the experimental runtime remains explicitly opt-in, evaluation-oriented, and
  non-default; Phase 6N does not promote it to the repo's default runtime
- focused tests cover runtime selection, default-runtime preservation,
  representative halt/refusal mirroring, checkpoint/continuation compatibility,
  and canonical-precedence preservation for the experimental mirror
- `README.md` reflects that Phase 6N is active and that experimental LangGraph
  runtime mirroring is now the implementation focus

### Exclusions

- no LangChain support-layer implementation in this slice
- no CrewAI or broader multi-agent framework evaluation in this slice
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no arbitrary repo-file ingestion, semantic retrieval expansion, or broader
  RAG/runtime behavior beyond the narrow experimental mirror needed here
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  opt-in experimental mirror implementation
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 6O - LangChain Support Layer

### Status

Complete and approved by human to advance to Phase 7A. Phase 6O closed with terminal verdict `APPROVED_FOR_HUMAN_REVIEW` after the optional LangChain support layer, read-only tool registry, eval surface, and canonical-state validation fix were all verified in the current repo state.

### Objective

Implement an optional LangChain-based support layer that can assist prompt
construction, selective retrieval, and tool abstraction without becoming the
top-level orchestrator. This slice should preserve the shipped local runtime as
the authoritative default control path, keep the shipped 6N LangGraph runtime
mirror subordinate and opt-in, preserve canonical repo-artifact precedence, and
refuse fail-closed on any attempt to let LangChain-managed state override
loop-state, checkpoints, memory, evidence, review artifacts, or phase/task
planning state.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 6 / 6O as active
- `.agent-loop/phase-plan.md` records Phase 6N as closed history and contains a
  `## Phase 6O - LangChain Support Layer` section with concrete objective, done
  criteria, and exclusions
- `scripts/agent_loop.py` exposes a narrow optional LangChain support-layer
  surface only for prompt construction, selective retrieval, and tool
  abstraction, not as the top-level orchestrator or runtime owner
- the LangChain support layer preserves canonical repo-artifact precedence over
  LangChain-managed state and refuses fail-closed when LangChain state
  contradicts canonical task, loop-state, checkpoint, memory, review, or
  evidence artifacts
- the LangChain support layer preserves the shipped halt/refusal vocabulary,
  approval-mode behavior, checkpoint/continuation handling, durable-memory
  boundaries, and audit-note expectations where it touches existing runtime
  surfaces
- the shipped local orchestrator remains the default runtime when no explicit
  support-layer selection is made, and the shipped 6N LangGraph runtime mirror
  remains opt-in and non-default
- focused tests cover support-layer activation boundaries, default-runtime
  preservation, canonical-precedence preservation, representative refusal
  behavior, and proof that LangChain does not become a top-level runtime
  controller
- `README.md` reflects that Phase 6O is active and that LangChain support-layer
  work is now the implementation focus

### Exclusions

- no promotion of LangChain into the top-level orchestrator, runtime owner, or
  phase-transition controller
- no CrewAI evaluation or broader delegated-role multi-agent framework work in
  this slice
- no broader autonomy model than the shipped Phase 5D runtime behavior
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body beyond the narrow
  support-layer integration needed here
- no change to the Phase 4A Planning Contract body
- no regression of the shipped Phase 5 review, strict, autonomous,
  reconciliation, or prompt-bootstrap runtime behavior
- no arbitrary repo-file ingestion, semantic retrieval expansion, or broader
  RAG/runtime behavior beyond the narrow LangChain support layer needed here
- no change to `AGENTS.md` or `CLAUDE.md`
- no Phase 7 editor integration
- no Git automation

## Phase 7A - VS Code Task Entrypoints

### Status

Complete and approved by human to advance to Phase 7B. Phase 7A closed with terminal verdict `APPROVED_FOR_HUMAN_REVIEW` after the VS Code task entrypoints, evidence-collection task, focused validation, and README alignment were all verified in the current repo state.

### Objective

Implement `.vscode/tasks.json` entries for the common operator flows so the
project is easier to run from VS Code without changing the underlying runtime
contract. This slice should surface existing CLI commands for loop execution,
evidence collection, review-artifact access, and adjacent operator entrypoints
while keeping repo artifacts as the source of truth, preserving halt and
approval behavior, and avoiding any IDE-owned replacement for the shipped
orchestrator.

### Definition of done

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

### Exclusions

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

## Phase 7B - Artifact Inspection And Review Workflow

### Status

Complete and approved by human to advance to Phase 7C. Phase 7B closed with terminal verdict `APPROVED_FOR_HUMAN_REVIEW` after the read-only artifact inspector, workspace settings layer, live-editor acceptance checklist, focused validation, and README alignment were all verified in the current repo state.

### Objective

Implement the VS Code artifact-inspection and review workflow layer for the
agent loop. This slice should make Codex review artifacts, fix prompts, active
task/phase artifacts, and evidence logs easy to open and inspect from VS Code
while keeping repo artifacts as the source of truth, preserving halt and
approval behavior, and avoiding any IDE-owned replacement for the shipped
orchestrator.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 7 / 7B as active
- `.agent-loop/phase-plan.md` records Phase 7A as closed history and contains a
  `## Phase 7B - Artifact Inspection And Review Workflow` section with concrete
  objective, done criteria, and exclusions
- the VS Code integration exposes an inspection workflow that makes
  `.agent-loop/codex-review.md`, `.agent-loop/fix-prompt.md`,
  `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and the shipped
  evidence logs easy to open and inspect from the editor
- any new VS Code entrypoints preserve canonical repo-artifact truth by opening
  or delegating to existing repo artifacts and shipped commands rather than
  synthesizing alternate state
- the VS Code inspection layer preserves the shipped halt/refusal vocabulary,
  approval-mode behavior, checkpoint/continuation behavior, and artifact
  ownership boundaries by remaining a thin operator convenience layer over the
  existing workflow
- the repository remains fully usable without VS Code, and the inspection
  workflow does not become a VS Code-only control plane
- focused validation covers artifact-path mapping, command mapping where
  applicable, and proof that the inspection layer does not widen runtime or
  ownership scope
- `README.md` reflects that Phase 7B is active and that artifact inspection and
  review workflow ergonomics are now the implementation focus

### Exclusions

- no artifact dashboard or reset/recovery UX beyond the narrow
  artifact-inspection layer for this slice
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

## Phase 7C - Status, Reset, And Recovery UX

### Status

Complete and approved by human to advance to Phase 8A. Phase 7C closed with terminal verdict `APPROVED_FOR_HUMAN_REVIEW` after the read-only status reporter, the recovery-hint coverage expansion, the contract-accurate halt guidance fix, focused validation, and README alignment were all verified in the current repo state.

### Objective

Implement the VS Code status, reset, and recovery UX layer for the agent loop.
This slice should add clear operator-facing run/status/reset ergonomics in VS
Code while keeping repo artifacts as the source of truth, preserving halt and
approval behavior, and avoiding any IDE-owned replacement for the shipped
orchestrator.

### Definition of done

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

### Exclusions

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

## Phase 8A - Architecture And Usage Docs

### Status

Active. First documentation/polish slice focused on explaining the shipped system accurately from a clean clone without relying on prior chat context or inventing unimplemented behavior.

### Objective

Implement the Architecture And Usage Docs slice for the agent loop. This slice
should document the real shipped workflow from a clean clone, including the
end-to-end loop, active CLI/runtime surfaces, artifact ownership model, and
practical operator flows, while preserving the current runtime behavior and
avoiding any documentation that promises unshipped automation, hidden
capabilities, or alternate sources of truth.

### Definition of done

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and
  `.agent-loop/loop-state.json` identify Phase 8 / 8A as active
- `.agent-loop/phase-plan.md` records Phase 7C as closed history and contains a
  `## Phase 8A - Architecture And Usage Docs` section with concrete objective,
  done criteria, and exclusions
- the repository ships architecture and usage documentation that explains the
  real end-to-end loop, runtime surfaces, artifact ownership, and operator
  flows from a clean clone without requiring prior chat context
- documentation distinguishes current shipped behavior from future roadmap items
  and does not present future capabilities as if they already exist
- operator docs remain aligned with the CLI-first workflow, approval semantics,
  halt/recovery boundaries, and repo-artifact source-of-truth model
- focused validation or review coverage proves the docs match the actual repo
  state and do not claim unimplemented behavior
- `README.md` reflects that Phase 8A is active and that architecture/usage
  documentation is now the implementation focus

### Exclusions

- no new runtime, planner, activator, evidence-collection, review-routing,
  checkpoint, continuation, memory, runtime-adapter, LangChain, or VS Code
  feature work
- no contract rewrites in `AGENTS.md` or `CLAUDE.md`
- no documentation that invents behavior the repo does not currently ship
- no collapsing of future roadmap items into present-tense product behavior
- no MCP support, external UI, concurrent-agent operation, or fully autonomous
  PRD-to-product mode in this slice
- no change to the Phase 2A Evidence Collection Contract
- no change to the Phase 3A Orchestrator Contract body
- no change to the Phase 4A Planning Contract body
- no change to `scripts/run_checks.sh`
- no Git automation
