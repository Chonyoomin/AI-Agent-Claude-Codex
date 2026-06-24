# Local Adapter Contract

## Status

This contract is shipped as part of Fix Phase A (Automatic Local
Claude/Codex Invocation Reliability). It pins the concrete
operator-facing behavior the orchestrator expects from
`AGENT_LOOP_CLAUDE_CMD` and `AGENT_LOOP_CODEX_CMD` so a configured
local machine can run the existing intra-phase loop without manual
chat-to-chat prompt transfer between Claude and Codex.

## Scope

This document describes the local-adapter contract for the SHIPPED
subprocess adapter seams (`SubprocessClaudeAdapter` and
`SubprocessCodexAdapter` in [scripts/agent_loop.py](../scripts/agent_loop.py)).
It is the load-bearing specification a wrapper script MUST satisfy
to be used as `AGENT_LOOP_CLAUDE_CMD` or `AGENT_LOOP_CODEX_CMD`.

This contract is NOT a description of fully autonomous PRD-to-product
execution. Automatic local invocation through these adapter seams
reduces operator copy-paste between Claude and Codex within an active
phase; it does NOT replace the shipped Phase 4 planner / activator
separation, the shipped Phase 5 approval-mode semantics, the shipped
Phase 9 fully autonomous track, or any other human-approval gate. See
the bottom-of-document "Distinction From Fully Autonomous Mode"
section for the precise boundary.

## Environment Variables

Two environment variables select which adapter the orchestrator uses
for each agent role:

- `AGENT_LOOP_CLAUDE_CMD` - shell command the orchestrator invokes for
  every Claude implementation or fix cycle. When unset, the
  orchestrator falls back to the manual-handoff adapter
  (`ManualHandoffClaudeAdapter`) that pauses for a human to drive
  Claude Code with the active prompt.
- `AGENT_LOOP_CODEX_CMD` - shell command the orchestrator invokes for
  every Codex review cycle. When unset, the orchestrator falls back
  to the manual-handoff adapter (`ManualHandoffCodexAdapter`) that
  pauses for a human to drive Codex against the captured evidence.

Two optional model-identifier overrides:

- `AGENT_LOOP_CLAUDE_MODEL` - explicit `claude_version` recorded in
  `.agent-loop/loop-state.json`. When unset, the Claude adapter falls
  back to the first token of `AGENT_LOOP_CLAUDE_CMD` as the model
  identifier (e.g. `claude` for `AGENT_LOOP_CLAUDE_CMD="claude ..."`).
- `AGENT_LOOP_CODEX_MODEL` - explicit `codex_version` recorded in
  `.agent-loop/loop-state.json`. The Codex adapter has NO derived
  fallback per the Phase 3A contract; when unset the adapter returns
  `model_id=None` and the orchestrator's null-note path writes the
  contract-required line to `.agent-loop/orchestrator.log`.

## Adapter Invocation Contract

The orchestrator invokes the configured command via the platform
shell (`subprocess.run(..., shell=True)`) with the following
guarantees and obligations:

### Guarantees the orchestrator provides

1. **cwd is the repository root.** The orchestrator sets the
   subprocess working directory to the repo root (the directory
   containing `AGENTS.md`, `CLAUDE.md`, and the `.agent-loop/`
   subdirectory). The wrapper MUST NOT `cd` into a different
   directory; canonical artifact paths in this contract are
   relative to this cwd.
2. **Active prompt is piped on stdin for the Claude adapter.** For
   `AGENT_LOOP_CLAUDE_CMD`, the orchestrator pipes the content of
   `.agent-loop/claude-prompt.md` (or `.agent-loop/fix-prompt.md`,
   whichever the current cycle uses) on the subprocess's stdin. The
   wrapper MAY read stdin to obtain the prompt text directly or MAY
   ignore stdin and read the on-disk prompt file (cwd is the repo
   root, so the relative path `.agent-loop/claude-prompt.md` always
   resolves to the correct file).
3. **Empty stdin for the Codex adapter.** For
   `AGENT_LOOP_CODEX_CMD`, the orchestrator pipes empty stdin. Codex
   is expected to read the canonical `.agent-loop/` artifacts (the
   active prompt, summary, evidence files) directly from disk.
4. **Pre-invocation mtime snapshot.** Before invoking the wrapper the
   orchestrator captures the target canonical artifact's mtime (or
   `0.0` when the artifact does not yet exist). After the wrapper
   exits the orchestrator compares the artifact's current mtime to
   this snapshot; see the freshness rule below.

### Obligations the wrapper MUST satisfy

1. **Write the target canonical artifact.** The Claude wrapper MUST
   cause the local Claude CLI to overwrite
   `.agent-loop/claude-summary.md` with a fresh summary describing
   what Claude changed in this cycle (the required Claude
   Implementation Summary format is enumerated in
   [CLAUDE.md](../CLAUDE.md#structured-summary-requirement)). The
   Codex wrapper MUST cause the local Codex CLI to overwrite
   `.agent-loop/codex-review.md` with a fresh review carrying one
   of the three shipped verdicts (`APPROVED_FOR_HUMAN_REVIEW`,
   `NEEDS_FIXES`, `FAILED_REQUIRES_HUMAN`).
2. **Advance the target artifact mtime.** The orchestrator's
   freshness check requires the post-invocation mtime to be
   STRICTLY GREATER than the pre-invocation snapshot. A wrapper that
   exits 0 but leaves the artifact unchanged (no write at all),
   missing, or backdated (rewritten with an older mtime) is REFUSED
   as a stale/no-op invocation: the orchestrator emits an
   `mtime did not advance` line on stderr and the cycle halts as
   if the wrapper had returned a non-zero exit code.
3. **Forward exit code honestly.** A non-zero exit code from the
   wrapper is forwarded directly to the orchestrator and treated as
   wrapper failure. The orchestrator then routes the cycle through
   its standard halt path. The wrapper MUST NOT mask a CLI failure
   by exiting 0 when the underlying CLI exited non-zero.
4. **Preserve the canonical-artifact source-of-truth.** The wrapper
   MUST NOT parse the local CLI's stdout/stderr to derive the
   verdict or summary. The on-disk artifacts
   (`.agent-loop/claude-summary.md` and `.agent-loop/codex-review.md`)
   remain the canonical source of truth; the orchestrator only
   reads those files, never the wrapper's captured stdout.
5. **Do not perform Git automation.** The wrapper MUST NOT commit,
   push, branch, stash, reset, checkout, or tag in either the
   controller or any target repository. The shipped
   no-Git-automation boundary applies to the wrapper exactly as it
   applies to the rest of the agent-loop runtime.
6. **Do not mutate orchestrator-owned artifacts.** The wrapper MAY
   let the local CLI write the canonical claude-summary or
   codex-review artifact; it MUST NOT directly write
   `.agent-loop/loop-state.json`, `.agent-loop/orchestrator.log`,
   `.agent-loop/git-diff.patch`, `.agent-loop/git-status.log`, or
   any of the four Phase 2A evidence files. Those remain
   orchestrator- or script-owned per
   [CLAUDE.md](../CLAUDE.md#ownership-boundaries).

## Success vs Failure Semantics

The orchestrator computes a single `ExecutionResult` per adapter
invocation. The result is **success** when ALL of the following are
true:

- the wrapper subprocess exited with status code `0`
- the target canonical artifact exists on disk after the wrapper
  exits (`.agent-loop/claude-summary.md` for Claude,
  `.agent-loop/codex-review.md` for Codex)
- the target canonical artifact's mtime is STRICTLY GREATER than the
  pre-invocation snapshot mtime

The result is **failure** when ANY of the following are true:

- the configured command is empty (no `AGENT_LOOP_*_CMD` env var was
  set); in this case the factory returns the manual-handoff adapter
  instead of the subprocess adapter, so this case never reaches the
  subprocess adapter's `invoke(...)`
- the subprocess raised `FileNotFoundError` (the shell could not
  locate the wrapper binary or interpreter); exit code `127` is
  returned and the orchestrator halts via its standard
  `halted_input_missing` branch
- the subprocess exited with a non-zero status code
- the subprocess exited 0 but the target canonical artifact does
  not exist
- the subprocess exited 0 and the target artifact exists, but its
  mtime is less than OR equal to the pre-invocation snapshot
  (unchanged or backdated)

On failure the orchestrator routes the cycle through the existing
halt vocabulary (`halted_input_missing`, `halted_summary_malformed`,
`halted_review_parse_failed`, etc.). The wrapper is NEVER given a
"retry" affordance directly; recovery is via the shipped operator
CLI (`status`, `inspect-artifacts`, `run`, etc.).

## Wrapper Templates

Two starting-point wrapper templates ship in the repository:

- [scripts/claude-wrapper.sh.template](../scripts/claude-wrapper.sh.template) -
  bash template for `AGENT_LOOP_CLAUDE_CMD`
- [scripts/codex-wrapper.sh.template](../scripts/codex-wrapper.sh.template) -
  bash template for `AGENT_LOOP_CODEX_CMD`

The shipped templates are intentionally non-functional placeholders
that exit 1 with an instructional message. To use them:

1. Copy the template to a personal location outside the repository
   (e.g. `~/bin/claude-wrapper.sh`).
2. Replace the marked `# ----- REPLACE THIS BLOCK -----` section with
   the actual invocation of your locally-installed Claude or Codex
   CLI. The exact flags depend on which CLI you have installed; the
   orchestrator does not depend on the flag shape.
3. Make the script executable (`chmod +x ~/bin/claude-wrapper.sh`).
4. Export the environment variable pointing at your copy:

       export AGENT_LOOP_CLAUDE_CMD="bash /absolute/path/to/claude-wrapper.sh"
       export AGENT_LOOP_CODEX_CMD="bash /absolute/path/to/codex-wrapper.sh"

5. Optionally export `AGENT_LOOP_CLAUDE_MODEL` and
   `AGENT_LOOP_CODEX_MODEL` if you want to override the auto-derived
   model identifier recorded in `loop-state.json`.

The orchestrator does not require the wrappers to live inside the
repository; pointing the env vars at a personal `~/bin/` location is
encouraged so wrapper customizations remain operator-local and do
NOT pollute the public repo.

## Distinction From Fully Autonomous Mode

Configuring `AGENT_LOOP_CLAUDE_CMD` and `AGENT_LOOP_CODEX_CMD`
enables **automatic local invocation within the existing phase loop**.
The orchestrator can now dispatch Claude for an implementation cycle,
capture evidence via `scripts/run_checks.sh`, dispatch Codex for the
review cycle, and (on `NEEDS_FIXES`) automatically regenerate a fix
prompt and dispatch Claude again, all without manual chat-to-chat
prompt transfer.

What this slice does **not** enable:

- **Fully autonomous phase-to-phase PRD execution** remains
  human-gated. The shipped Phase 4 planner / activator separation,
  the human-authored `APPROVED_FOR_ACTIVATION` token, the Phase 5
  approval modes, the Phase 6 strict-mode gates, the Phase 9G final
  human acceptance gate, and every other shipped human-approval
  gate continue to fire as before.
- **Automatic next-phase activation** is NOT introduced. A cycle that
  reaches `phase_complete_awaiting_human_approval` still halts there
  until a human runs `python scripts/agent_loop.py plan` (and then
  edits the proposed-phase to add the activation token) and finally
  `python scripts/agent_loop.py activate`.
- **Multi-target orchestration** through this adapter contract is
  out of scope; the contract pins single-target single-attach
  behavior matching the Phase 10D-10F shipped surfaces.
- **MCP integration, RAG layer, GitHub integration, model-policy
  extensibility,** and concurrent Claude/Codex overlap execution are
  all explicitly out of scope for Fix Phase A; they remain tracked in
  `ROADMAP.md` as later work.

Operators who want to verify the boundary: with a configured
`AGENT_LOOP_CLAUDE_CMD` + `AGENT_LOOP_CODEX_CMD` pair, running
`python scripts/agent_loop.py run` from
`status=awaiting_claude_implementation` should advance the cycle to a
terminal verdict without human input, BUT the loop will halt at any
existing human-approval gate (strict-mode pause, `NEEDS_FIXES` after
`max_cycles` exhausted, `phase_complete_awaiting_human_approval`,
`halted_failed_requires_human`, etc.). The boundary is unchanged from
the shipped Phase 1 - 10H runtime.

## Audit Expectations

Every subprocess adapter invocation is auditable from the canonical
artifacts the cycle already writes:

- the `claude_version` / `codex_version` fields in
  `.agent-loop/loop-state.json` record which model identifier was
  resolved for the cycle
- the `.agent-loop/claude-summary.md` and `.agent-loop/codex-review.md`
  files carry the agents' own structured output for the cycle
- the four Phase 2A/2B evidence files
  (`.agent-loop/git-diff.patch`, `.agent-loop/git-status.log`,
  `.agent-loop/test-output.log`, `.agent-loop/lint-output.log`,
  `.agent-loop/typecheck-output.log`, `.agent-loop/build-output.log`)
  carry the per-cycle evidence
- the `.agent-loop/orchestrator.log` carries the orchestrator's own
  audit lines, including the freshness-refusal line when an adapter
  invocation is rejected as stale/no-op

The wrapper MAY emit its own diagnostic output to stderr for local
debugging; that output is NOT considered part of the canonical
record and MAY be silently dropped on the operator's machine.
