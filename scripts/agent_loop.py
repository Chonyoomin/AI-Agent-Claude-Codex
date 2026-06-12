#!/usr/bin/env python3
"""scripts/agent_loop.py - local orchestrator.

Phase 3B scaffold + Phase 3C automated fix cycle + Phase 3D subprocess
adapters. Implements the Phase 3A Orchestrator Contract
(`.agent-loop/phase-plan.md` -> "## Phase 3A - Orchestrator Contract"):

  Normal cycle (Phase 3B):
    load state -> validate inputs -> enforce ready start status ->
    increment cycle_count and set status=claude_implementing -> invoke
    Claude adapter boundary -> wait for `.agent-loop/claude-summary.md`
    -> validate summary structure + `## Phase` match -> set
    status=evidence_capture -> invoke `bash scripts/run_checks.sh` ->
    validate six evidence files -> set status=awaiting_codex_review ->
    wait for `.agent-loop/codex-review.md` -> validate review structure
    and parse exactly one allowed verdict -> hand off to verdict loop.

  Verdict loop (Phase 3C):
    APPROVED_FOR_HUMAN_REVIEW -> persist completion, return 0.
    FAILED_REQUIRES_HUMAN     -> persist halt, return 2.
    NEEDS_FIXES               -> record verdict; if cycle_count >=
      max_cycles, halt halted_max_cycles_reached (no auto-continue,
      raising the limit is a Codex/human action). Otherwise validate
      `.agent-loop/fix-prompt.md`, run one fix cycle (increment
      cycle_count, status=claude_fixing -> Claude adapter ->
      claude-summary validation -> evidence capture -> evidence
      validation -> wait for fresh codex-review.md -> parse verdict),
      then re-enter the verdict loop with the new verdict.

Adapter selection (Phase 3D):
  Subprocess-driven Claude / Codex adapters are selected when the
  operator has configured `AGENT_LOOP_CLAUDE_CMD` / `AGENT_LOOP_CODEX_CMD`
  environment variables. When those are unset, the orchestrator falls
  back to the existing manual-handoff stubs so the documented manual
  workflow keeps working. Model identifiers are resolved from
  `AGENT_LOOP_CLAUDE_MODEL` / `AGENT_LOOP_CODEX_MODEL`; Claude has a
  binary-name fallback (the contract requires non-null claude_version),
  Codex stays null when unconfigured (the contract forbids fabricating
  a codex_version, and the orchestrator's existing null-note path
  writes the contract-required line to orchestrator.log).

Out of scope (deferred to later 3x sub-phases):
  - approval modes (Phase 5)
  - editor integration (Phase 7)
  - any Git automation (commit, push, branch, stash, reset, ...)
  - automatic "materially changed / narrowed" cycle-extension judgment
    (orchestrator only enforces the threshold; the policy escape is
    explicit Codex/human action on max_cycles or a new sub-phase)
  - parsing model-specific Claude / Codex CLI output formats inside
    the core loop (subprocess stdout/stderr is captured but not
    interpreted; this is a contract requirement)
  - streaming subprocess output to a TTY (captured, not streamed)
  - a scripts/agent_loop/ package layout (single-file keeps the diff
    minimal; future slice can split if needed)

The orchestrator must never write any file outside its allowed set
(`.agent-loop/loop-state.json` and the optional `.agent-loop/orchestrator.log`).
All structural validation is fail-closed: a malformed artifact halts the
loop with a contract-vocabulary `halted_*` status, never a silent retry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional


# ----- contract constants -----

ORCHESTRATOR_VERSION = "phase-3d-v0"

# Adapter selection: env-var-driven. When the *_CMD variable is set,
# the subprocess adapter is used; otherwise the manual-handoff stub is
# the fallback (so the documented manual workflow keeps working without
# any extra configuration). The optional *_MODEL variables let the
# operator supply the version identifier the adapter should record into
# loop-state.json; the Phase 3A contract forbids the core loop from
# parsing model-specific output to derive that identifier.
ENV_CLAUDE_CMD = "AGENT_LOOP_CLAUDE_CMD"
ENV_CODEX_CMD = "AGENT_LOOP_CODEX_CMD"
ENV_CLAUDE_MODEL = "AGENT_LOOP_CLAUDE_MODEL"
ENV_CODEX_MODEL = "AGENT_LOOP_CODEX_MODEL"
SUPPORTED_CONTRACT_VERSIONS = frozenset({"phase-3a-v2"})

ALLOWED_VERDICTS = (
    "APPROVED_FOR_HUMAN_REVIEW",
    "NEEDS_FIXES",
    "FAILED_REQUIRES_HUMAN",
)

ISSUE_OWNER_CODEX = "Codex"
ISSUE_OWNER_CLAUDE = "Claude"
ALLOWED_ISSUE_OWNERS = frozenset({ISSUE_OWNER_CODEX, ISSUE_OWNER_CLAUDE})

CODEX_ACTION_SYNC_PHASE5_RUNTIME_DEFAULTS = "sync_phase5_runtime_defaults"
SUPPORTED_CODEX_ACTIONS = frozenset({CODEX_ACTION_SYNC_PHASE5_RUNTIME_DEFAULTS})

# Phase 5E post-review reconciliation: each supported Codex auto-fix
# action declares the exact set of repo paths it may legitimately touch.
# A review issue routed to Codex with a supported codex_action must list
# only files inside its action's allow-list; any file outside that list
# is refused at reconciliation time as "Codex auto-fix attempting to
# write Claude-owned implementation work." The allow-list approach keeps
# the refusal deterministic per-action without depending on a global
# Codex-vs-Claude path partition.
CODEX_ACTION_ALLOWED_FILES: dict = {
    CODEX_ACTION_SYNC_PHASE5_RUNTIME_DEFAULTS: frozenset({
        ".agent-loop/loop-state.json",
    }),
}

EVIDENCE_FILES = (
    ".agent-loop/git-status.log",
    ".agent-loop/git-diff.patch",
    ".agent-loop/test-output.log",
    ".agent-loop/lint-output.log",
    ".agent-loop/typecheck-output.log",
    ".agent-loop/build-output.log",
)

EVIDENCE_STATES = frozenset({"Passed", "Failed", "Not run", "Inconclusive"})

CLAUDE_SUMMARY_HEADERS = (
    "# Claude Implementation Summary",
    "## Phase",
    "## Task",
    "## Files changed",
    "## What was implemented",
    "## What was not implemented",
    "## Tests added or changed",
    "## Validation run",
    "## Assumptions",
    "## Risk areas",
)

CODEX_REVIEW_HEADERS = (
    "# Codex Review",
    "## Verdict",
    "## Review summary",
    "## Claude summary accuracy",
    "## Scope control",
    "## Validation result",
    "## Issues found",
)

FIX_PROMPT_HEADERS = (
    "# Claude Code Fix Task",
    "## Objective",
    "## Context",
    "## Required fixes",
    "## Constraints",
    "## Required output",
)

CODEX_OWNED_REVIEW_PATHS = frozenset({
    "TASK.md",
    ".agent-loop/current-task.md",
    ".agent-loop/current-phase.md",
    ".agent-loop/phase-plan.md",
    ".agent-loop/claude-prompt.md",
    ".agent-loop/codex-review.md",
    ".agent-loop/fix-prompt.md",
    "AGENTS.md",
    "CLAUDE.md",
})

REQUIRED_STATE_KEYS = (
    "phase", "sub_phase", "task", "status", "cycle_count", "max_cycles",
)

ORCHESTRATOR_WRITABLE_FIELDS = frozenset({
    "status",
    "cycle_count",
    "last_verdict",
    "last_verdict_phase",
    "claude_version",
    "codex_version",
    "orchestrator_version",
    # Phase 5B (Approval Modes - review-mode initial slice): the
    # `approval_mode` selector and the `awaiting_human_for` gate name are
    # orchestrator-owned runtime fields. Allowed values for `approval_mode`
    # are the three Phase 5A modes (`strict`, `review`, `autonomous`).
    # `review` (Phase 5B), `strict` (Phase 5C), and the narrow
    # `autonomous` continuation path (Phase 5D) are all implemented; the
    # default-on-init/activation is still `review`.
    "approval_mode",
    "awaiting_human_for",
})

CODEX_OR_HUMAN_OWNED_FIELDS = frozenset({
    "phase",
    "sub_phase",
    "task",
    "max_cycles",
    "contract_version",
})

# Phase 5B approval-mode runtime constants.
APPROVAL_MODE_REVIEW = "review"
APPROVAL_MODE_STRICT = "strict"
APPROVAL_MODE_AUTONOMOUS = "autonomous"
ALLOWED_APPROVAL_MODES = frozenset({
    APPROVAL_MODE_REVIEW, APPROVAL_MODE_STRICT, APPROVAL_MODE_AUTONOMOUS,
})
DEFAULT_APPROVAL_MODE = APPROVAL_MODE_REVIEW

# Named human gates `awaiting_human_for` may carry. Phase 5A's contract
# lists `pre_claude_prompt`, `pre_fix_prompt`,
# `phase_complete_awaiting_human_approval`, and `halt_resolution`. The
# `review` path only ever sets the phase-complete gate; the three
# strict-mode gates (added in Phase 5C) extend the named set with one
# more contract gate name for the post-Claude / pre-Codex-review pause.
AWAITING_HUMAN_FOR_PHASE_COMPLETE = "phase_complete_awaiting_human_approval"
AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT = "pre_claude_prompt"
AWAITING_HUMAN_FOR_PRE_FIX_PROMPT = "pre_fix_prompt"
AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW = "pre_codex_review"

# Phase 5C strict-mode halt statuses. Each strict gate uses a distinct
# `halted_awaiting_human_*` status so the `resume` subcommand can route
# to the correct continuation; the corresponding `awaiting_human_for`
# carries the Phase 5A contract gate-name vocabulary. The pre-codex
# gate has two halt-status flavors because the same gate site appears
# in both the normal cycle and the fix cycle, and resume must dispatch
# to the correct cycle's continuation.
HALTED_PRE_CLAUDE_PROMPT = "halted_awaiting_human_pre_claude_prompt"
HALTED_PRE_FIX_PROMPT = "halted_awaiting_human_pre_fix_prompt"
HALTED_PRE_CODEX_REVIEW_NORMAL = "halted_awaiting_human_pre_codex_review_normal"
HALTED_PRE_CODEX_REVIEW_FIX = "halted_awaiting_human_pre_codex_review_fix"
STRICT_GATE_HALT_STATUSES = frozenset({
    HALTED_PRE_CLAUDE_PROMPT,
    HALTED_PRE_FIX_PROMPT,
    HALTED_PRE_CODEX_REVIEW_NORMAL,
    HALTED_PRE_CODEX_REVIEW_FIX,
})

# Per the contract's "Normal cycle" preconditions, a normal cycle may only
# start from a ready-to-start status. The orchestrator refuses to begin
# a cycle from any other status (including halted_* or in-flight states)
# until a human or Codex explicitly resets `status` to a ready value.
ALLOWED_NORMAL_CYCLE_START_STATUSES = frozenset({
    "awaiting_claude_implementation",
})

REPO_ROOT_MARKERS = ("TASK.md", "AGENTS.md", ".agent-loop")


# ----- domain types -----

class HaltError(Exception):
    """Raised to halt the loop with a specific contract `halted_*` status."""

    def __init__(self, status: str, reason: str) -> None:
        super().__init__(f"{status}: {reason}")
        self.status = status
        self.reason = reason


@dataclass
class ExecutionResult:
    exit_code: int
    model_id: Optional[str]
    duration_seconds: float


@dataclass(frozen=True)
class ReviewIssue:
    title: str
    severity: str
    category: str
    files: tuple[str, ...]
    problem: str
    evidence: str
    required_fix: str
    owner: str
    codex_action: Optional[str] = None


@dataclass(frozen=True)
class ParsedCodexReview:
    verdict: str
    issues: tuple[ReviewIssue, ...]
    fix_prompt_for_claude: str


# ----- adapters (manual-handoff stubs for this slice) -----

class ManualHandoffClaudeAdapter:
    """Phase 3B initial-slice Claude adapter.

    The contract requires the orchestrator's core loop to invoke Claude
    behind an adapter boundary; this implementation pauses for a human
    to drive Claude Code with the active prompt, then continues once the
    human signals that `.agent-loop/claude-summary.md` has been updated.
    A real subprocess-driven adapter is a later-slice concern.
    """

    default_model_id = "manual-handoff"

    def invoke(self, prompt_path: Path, summary_path: Path) -> ExecutionResult:
        start = time.monotonic()
        prev_mtime = summary_path.stat().st_mtime if summary_path.exists() else 0.0
        print(f"[orchestrator] Manual Claude handoff:")
        print(f"[orchestrator]   1. paste {prompt_path} into Claude Code")
        print(f"[orchestrator]   2. let Claude write {summary_path}")
        print(f"[orchestrator]   3. press Enter here once the summary is saved")
        try:
            input()
        except EOFError:
            pass
        duration = time.monotonic() - start
        if not summary_path.exists():
            return ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=duration,
            )
        # Fail closed: if the human pressed Enter without actually saving a
        # fresh summary for this cycle, the file's mtime will match what we
        # captured before the handoff. Treat that as "Claude did not produce
        # an artifact for this cycle" so the orchestrator halts rather than
        # validating a stale summary as if it were current.
        if summary_path.stat().st_mtime == prev_mtime:
            print(
                f"[orchestrator] {summary_path.name} mtime unchanged - "
                f"no fresh summary was produced for this cycle.",
                file=sys.stderr,
            )
            return ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=duration,
            )
        return ExecutionResult(
            exit_code=0,
            model_id=self.default_model_id,
            duration_seconds=duration,
        )


class ManualHandoffCodexAdapter:
    """Phase 3B initial-slice Codex adapter.

    Pauses for a human to drive Codex against the captured evidence, then
    continues once `.agent-loop/codex-review.md` is updated. A real
    subprocess-driven adapter is a later-slice concern.
    """

    default_model_id = None

    def wait_for_review(self, review_path: Path) -> ExecutionResult:
        start = time.monotonic()
        prev_mtime = review_path.stat().st_mtime if review_path.exists() else 0.0
        print(f"[orchestrator] Manual Codex handoff:")
        print(f"[orchestrator]   1. have Codex review the current artifacts")
        print(f"[orchestrator]   2. let Codex write {review_path}")
        print(f"[orchestrator]   3. press Enter here once the review is saved")
        try:
            input()
        except EOFError:
            pass
        duration = time.monotonic() - start
        if not review_path.exists():
            return ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=duration,
            )
        # Fail closed: an unchanged mtime means Codex did not produce a
        # review for this cycle. Treat as "no review" rather than parsing
        # a stale verdict.
        if review_path.stat().st_mtime == prev_mtime:
            print(
                f"[orchestrator] {review_path.name} mtime unchanged - "
                f"no fresh review was produced for this cycle.",
                file=sys.stderr,
            )
            return ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=duration,
            )
        return ExecutionResult(
            exit_code=0,
            model_id=self.default_model_id,
            duration_seconds=duration,
        )


class SubprocessClaudeAdapter:
    """Phase 3D subprocess-driven Claude adapter.

    Invokes a configured shell command (`AGENT_LOOP_CLAUDE_CMD`) with the
    repository root as cwd and the prompt file content piped to stdin.
    The configured command is expected to drive Claude Code in a way
    that writes `.agent-loop/claude-summary.md` as a side effect. The
    adapter then confirms the file exists and its mtime has advanced
    (the same fail-closed-on-stale-mtime check as the manual-handoff
    adapter), and returns an `ExecutionResult` with the captured exit
    code, the resolved model identifier, and wall-clock duration.

    Model-id resolution order: `AGENT_LOOP_CLAUDE_MODEL` env var first,
    then the first token of the configured command (e.g. `claude`). The
    Phase 3A contract requires a non-null `claude_version` (a null
    triggers `halted_input_missing`); the binary-name fallback keeps the
    orchestrator running for operators who have not set the model env
    var, while still honestly recording what was actually invoked.

    The core loop never parses model-specific stdout / stderr formats;
    subprocess output is captured for future logging but is not
    interpreted by the orchestrator beyond the exit code.
    """

    def __init__(
        self,
        command: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> None:
        self.command = command if command is not None else os.environ.get(ENV_CLAUDE_CMD)
        self.explicit_model_id = (
            model_id if model_id is not None else os.environ.get(ENV_CLAUDE_MODEL)
        )

    def _resolved_model_id(self) -> Optional[str]:
        if self.explicit_model_id:
            return self.explicit_model_id
        if self.command:
            # POSIX-style splitting is only used to extract the first
            # token for the binary-name fallback. The actual subprocess
            # invocation goes through the platform shell so quoting and
            # path conventions match what the operator typed.
            try:
                tokens = shlex.split(self.command, posix=True)
            except ValueError:
                tokens = self.command.split()
            if tokens:
                return tokens[0]
        return None

    def invoke(self, prompt_path: Path, summary_path: Path) -> ExecutionResult:
        start = time.monotonic()
        if not self.command:
            return ExecutionResult(
                exit_code=1, model_id=None,
                duration_seconds=time.monotonic() - start,
            )
        prev_mtime = summary_path.stat().st_mtime if summary_path.exists() else 0.0
        prompt_text = prompt_path.read_text(encoding="utf-8")
        try:
            proc = subprocess.run(
                self.command,
                shell=True,
                input=prompt_text,
                cwd=str(prompt_path.parent.parent),  # repo root (.agent-loop/..)
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            # POSIX-style "command not found" exit code so the orchestrator
            # halts via its existing `halted_input_missing` branch.
            return ExecutionResult(
                exit_code=127, model_id=None,
                duration_seconds=time.monotonic() - start,
            )
        duration = time.monotonic() - start
        if proc.returncode != 0:
            return ExecutionResult(
                exit_code=proc.returncode, model_id=None,
                duration_seconds=duration,
            )
        if not summary_path.exists():
            return ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=duration,
            )
        if summary_path.stat().st_mtime == prev_mtime:
            return ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=duration,
            )
        return ExecutionResult(
            exit_code=0,
            model_id=self._resolved_model_id(),
            duration_seconds=duration,
        )


class SubprocessCodexAdapter:
    """Phase 3D subprocess-driven Codex adapter.

    Invokes a configured shell command (`AGENT_LOOP_CODEX_CMD`) with the
    repository root as cwd. The configured command is expected to drive
    Codex in a way that writes `.agent-loop/codex-review.md` as a side
    effect. The adapter confirms the file exists and its mtime has
    advanced, then returns an `ExecutionResult` with the captured exit
    code, the resolved model identifier (or `None` if not configured),
    and wall-clock duration.

    Model-id resolution: `AGENT_LOOP_CODEX_MODEL` env var only. Falling
    back to a derived value is explicitly forbidden for Codex by the
    contract ("the orchestrator must not silently fabricate one"). If
    the env var is unset, the adapter returns `model_id=None` and the
    orchestrator's existing null-note path writes the contract-required
    line to `.agent-loop/orchestrator.log`.
    """

    def __init__(
        self,
        command: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> None:
        self.command = command if command is not None else os.environ.get(ENV_CODEX_CMD)
        self.explicit_model_id = (
            model_id if model_id is not None else os.environ.get(ENV_CODEX_MODEL)
        )

    def wait_for_review(self, review_path: Path) -> ExecutionResult:
        start = time.monotonic()
        if not self.command:
            return ExecutionResult(
                exit_code=1, model_id=None,
                duration_seconds=time.monotonic() - start,
            )
        prev_mtime = review_path.stat().st_mtime if review_path.exists() else 0.0
        try:
            proc = subprocess.run(
                self.command,
                shell=True,
                input="",
                cwd=str(review_path.parent.parent),
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return ExecutionResult(
                exit_code=127, model_id=None,
                duration_seconds=time.monotonic() - start,
            )
        duration = time.monotonic() - start
        if proc.returncode != 0:
            return ExecutionResult(
                exit_code=proc.returncode, model_id=None,
                duration_seconds=duration,
            )
        if not review_path.exists():
            return ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=duration,
            )
        if review_path.stat().st_mtime == prev_mtime:
            return ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=duration,
            )
        return ExecutionResult(
            exit_code=0,
            model_id=self.explicit_model_id,
            duration_seconds=duration,
        )


def make_claude_adapter():
    """Factory: subprocess Claude adapter when configured, else manual-handoff.

    Selection is purely by env-var presence; the core loop calls this
    function instead of instantiating an adapter class directly so
    monkey-patching either `ManualHandoffClaudeAdapter` or
    `SubprocessClaudeAdapter` at the module level still works for tests.
    """
    if os.environ.get(ENV_CLAUDE_CMD):
        return SubprocessClaudeAdapter()
    return ManualHandoffClaudeAdapter()


def make_codex_adapter():
    """Factory: subprocess Codex adapter when configured, else manual-handoff."""
    if os.environ.get(ENV_CODEX_CMD):
        return SubprocessCodexAdapter()
    return ManualHandoffCodexAdapter()


# ----- repo / state helpers -----

def find_repo_root(start: Optional[Path] = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if all((candidate / marker).exists() for marker in REPO_ROOT_MARKERS):
            return candidate
    raise FileNotFoundError(
        f"Could not locate repository root from {here}; "
        f"expected markers {REPO_ROOT_MARKERS}"
    )


def load_loop_state(state_path: Path) -> dict:
    if not state_path.exists():
        raise HaltError("halted_input_missing", f"{state_path} does not exist")
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HaltError(
            "halted_input_missing",
            f"{state_path.name} is not valid JSON: {exc}",
        ) from exc


def validate_loop_state(data: dict) -> None:
    missing = [k for k in REQUIRED_STATE_KEYS if data.get(k) in (None, "")]
    if missing:
        raise HaltError(
            "halted_input_missing",
            f"loop-state.json missing required keys: {missing}",
        )
    if not isinstance(data["cycle_count"], int):
        raise HaltError(
            "halted_input_missing",
            "loop-state.json cycle_count must be an integer",
        )
    if not isinstance(data["max_cycles"], int):
        raise HaltError(
            "halted_input_missing",
            "loop-state.json max_cycles must be an integer",
        )
    contract_version = data.get("contract_version")
    if contract_version is not None and not isinstance(contract_version, str):
        raise HaltError(
            "halted_input_missing",
            "loop-state.json contract_version must be a string when present",
        )
    # Phase 5B fail-closed: a present but non-allowed `approval_mode` is a
    # contract violation, not a runtime curiosity. Missing or empty is fine
    # here (the cycle's runtime block will backfill to the Phase 5A default
    # `"review"`), but a nonempty value MUST be one of the three allowed
    # modes. This is the single source of truth - both `run_normal_cycle`
    # and any future call site rely on it. Refused via
    # `halted_input_missing` to match the existing structural-validation
    # halt vocabulary.
    approval_mode = data.get("approval_mode")
    if approval_mode not in (None, "") and approval_mode not in ALLOWED_APPROVAL_MODES:
        raise HaltError(
            "halted_input_missing",
            (
                f"loop-state.json approval_mode must be one of "
                f"{sorted(ALLOWED_APPROVAL_MODES)}; got {approval_mode!r}"
            ),
        )


def check_contract_version(data: dict) -> None:
    contract_version = data.get("contract_version")
    if not contract_version:
        raise HaltError(
            "halted_contract_version_mismatch",
            "loop-state.json contract_version is missing",
        )
    if contract_version not in SUPPORTED_CONTRACT_VERSIONS:
        raise HaltError(
            "halted_contract_version_mismatch",
            f"orchestrator does not support contract_version "
            f"{contract_version!r}; supported: {sorted(SUPPORTED_CONTRACT_VERSIONS)}",
        )


def save_loop_state(state_path: Path, current: dict, updates: dict) -> dict:
    """Write `updates` into loop-state.json. Refuses any non-orchestrator field.

    Returns the merged dict that was written. The contract gives the
    orchestrator authority only over runtime fields; all planning fields
    (`phase`, `sub_phase`, `task`, `max_cycles`, `contract_version`) are
    Codex- or human-owned and must never be modified here.
    """
    illegal = set(updates) - ORCHESTRATOR_WRITABLE_FIELDS
    if illegal:
        raise RuntimeError(
            f"orchestrator refused to write non-runtime loop-state fields: "
            f"{sorted(illegal)} (Codex- or human-owned)"
        )
    merged = dict(current)
    merged.update(updates)
    state_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return merged


# ----- artifact validators -----

def _validate_header_order(path: Path, headers: Iterable[str], halt_status: str) -> str:
    if not path.exists():
        raise HaltError(halt_status, f"{path.name} does not exist")
    text = path.read_text(encoding="utf-8")
    cursor = 0
    for header in headers:
        idx = text.find(header, cursor)
        if idx == -1:
            raise HaltError(
                halt_status,
                f"{path.name} missing required header {header!r} "
                f"(or out of order)",
            )
        cursor = idx + len(header)
    return text


def _section_body(text: str, header: str) -> str:
    """Return the body text between `header` and the next `## ` header.

    Empty/whitespace-only bodies return ''. This is used to extract the
    `## Phase` and `## Verdict` body lines for substantive checks.
    """
    idx = text.find(header)
    if idx == -1:
        return ""
    start = idx + len(header)
    # Find next top-level (## ) or higher header on a fresh line.
    rest = text[start:]
    m = re.search(r"\n(##? )", rest)
    if m is not None:
        rest = rest[: m.start()]
    return rest.strip()


def _labeled_multiline_body(block: str, label: str, required: bool = True) -> str:
    pattern = rf"(?ms)^{re.escape(label)}:\s*\n(.*?)(?=^\w[\w ]*:\s*$|\Z)"
    match = re.search(pattern, block)
    if match is None:
        if required:
            raise HaltError(
                "halted_review_parse_failed",
                f"codex-review issue block missing required label {label!r}",
            )
        return ""
    return match.group(1).strip()


def _single_line_field(block: str, label: str, *, required: bool = True) -> str:
    match = re.search(rf"(?m)^{re.escape(label)}:\s*(.+?)\s*$", block)
    if match is None:
        if required:
            raise HaltError(
                "halted_review_parse_failed",
                f"codex-review issue block missing required field {label!r}",
            )
        return ""
    return match.group(1).strip()


def _split_issue_files(raw: str) -> tuple[str, ...]:
    if not raw:
        return ()
    parts = [part.strip() for part in raw.split(",")]
    return tuple(part for part in parts if part)


def _infer_issue_owner(files: tuple[str, ...]) -> Optional[str]:
    """Phase 5E ambiguity-aware fallback inference.

    Returns `ISSUE_OWNER_CODEX` when every listed path is a Codex-owned
    review path, `ISSUE_OWNER_CLAUDE` when every listed path is outside
    that set (i.e. an implementation path Claude is responsible for),
    and `None` when the signal is ambiguous - either no files were
    listed at all, or the file list mixes Codex-owned planning paths
    with Claude-owned implementation paths. Phase 5E refuses ambiguous
    inference at parse time rather than silently defaulting to Claude,
    which preserves the contract's "Refuse or halt when ownership is
    ambiguous" rule.
    """
    if not files:
        return None
    codex_paths = [p for p in files if p in CODEX_OWNED_REVIEW_PATHS]
    non_codex_paths = [p for p in files if p not in CODEX_OWNED_REVIEW_PATHS]
    if codex_paths and non_codex_paths:
        return None
    if codex_paths:
        return ISSUE_OWNER_CODEX
    return ISSUE_OWNER_CLAUDE


def _parse_review_issue_block(title: str, block: str) -> ReviewIssue:
    severity = _single_line_field(block, "Severity")
    category = _single_line_field(block, "Category")
    files = _split_issue_files(_single_line_field(block, "File(s)"))
    explicit_owner = _single_line_field(block, "Owner", required=False)
    if explicit_owner:
        owner = explicit_owner
    else:
        inferred = _infer_issue_owner(files)
        if inferred is None:
            # Phase 5E: refuse ambiguous ownership at parse time. The
            # review must either set an explicit `Owner:` field or list
            # files whose Codex-vs-Claude partition is unambiguous.
            # Silently defaulting to Claude (the pre-Phase-5E behavior)
            # would route Codex-owned planning fixes through Claude and
            # the reverse, which the Phase 5E contract forbids.
            raise HaltError(
                "halted_review_parse_failed",
                (
                    f"codex-review issue {title.strip()!r} has no explicit "
                    f"Owner: field and the File(s) list {list(files)!r} "
                    f"provides an ambiguous ownership signal (either empty "
                    f"or mixing Codex-owned planning paths with Claude-owned "
                    f"implementation paths). Add an explicit `Owner: Codex` "
                    f"or `Owner: Claude` line to the issue block, or revise "
                    f"the File(s) list so the partition is unambiguous."
                ),
            )
        owner = inferred
    if owner not in ALLOWED_ISSUE_OWNERS:
        raise HaltError(
            "halted_review_parse_failed",
            f"codex-review issue owner must be one of {sorted(ALLOWED_ISSUE_OWNERS)}; "
            f"got {owner!r}",
        )
    codex_action = _single_line_field(block, "Codex action", required=False) or None
    if codex_action is not None and codex_action not in SUPPORTED_CODEX_ACTIONS:
        raise HaltError(
            "halted_review_parse_failed",
            f"codex-review issue Codex action must be one of "
            f"{sorted(SUPPORTED_CODEX_ACTIONS)}; got {codex_action!r}",
        )
    return ReviewIssue(
        title=title.strip(),
        severity=severity,
        category=category,
        files=files,
        problem=_labeled_multiline_body(block, "Problem"),
        evidence=_labeled_multiline_body(block, "Evidence"),
        required_fix=_labeled_multiline_body(block, "Required fix"),
        owner=owner,
        codex_action=codex_action,
    )


def validate_claude_prompt_present(prompt_path: Path) -> None:
    if not prompt_path.exists() or not prompt_path.read_text(encoding="utf-8").strip():
        raise HaltError(
            "halted_input_missing",
            f"required prompt file {prompt_path.name} is missing or empty",
        )


def validate_claude_summary(
    summary_path: Path, expected_phase: str, expected_sub_phase: Optional[str]
) -> None:
    text = _validate_header_order(
        summary_path, CLAUDE_SUMMARY_HEADERS, "halted_summary_malformed",
    )
    phase_body = _section_body(text, "## Phase")
    if not phase_body:
        raise HaltError(
            "halted_summary_malformed",
            f"{summary_path.name} ## Phase body is empty",
        )
    # The contract says the `## Phase` value must match the active phase
    # OR sub-phase in loop-state.json. Substring match keeps us tolerant
    # of trailing notes (e.g. "Phase 3 ... (sub-phase: Phase 3B ...)").
    candidates = [c for c in (expected_sub_phase, expected_phase) if c]
    if not any(c in phase_body for c in candidates):
        raise HaltError(
            "halted_summary_malformed",
            f"{summary_path.name} ## Phase body {phase_body!r} does not match "
            f"active phase/sub-phase ({expected_phase!r} / {expected_sub_phase!r})",
        )


def parse_codex_review(review_path: Path) -> ParsedCodexReview:
    text = _validate_header_order(
        review_path, CODEX_REVIEW_HEADERS, "halted_review_malformed",
    )
    verdict_body = _section_body(text, "## Verdict")
    if not verdict_body:
        raise HaltError(
            "halted_review_parse_failed",
            f"{review_path.name} ## Verdict body is empty",
        )
    tokens = re.findall(r"[A-Z_]+", verdict_body)
    matches = [t for t in tokens if t in ALLOWED_VERDICTS]
    if len(matches) != 1:
        raise HaltError(
            "halted_review_parse_failed",
            f"{review_path.name} ## Verdict body must contain exactly one "
            f"allowed verdict token; found {matches!r} in {verdict_body!r}",
        )
    issues_body = _section_body(text, "## Issues found")
    if not issues_body:
        raise HaltError(
            "halted_review_parse_failed",
            f"{review_path.name} ## Issues found body is empty",
        )
    issues: list[ReviewIssue] = []
    if issues_body != "None":
        issue_matches = list(re.finditer(r"(?m)^###\s+(Issue[^\n]*)\s*$", issues_body))
        if not issue_matches:
            raise HaltError(
                "halted_review_parse_failed",
                f"{review_path.name} ## Issues found must contain `None` or one or more "
                f"`### Issue ...` blocks",
            )
        for idx, match in enumerate(issue_matches):
            title = match.group(1)
            start = match.end()
            end = issue_matches[idx + 1].start() if idx + 1 < len(issue_matches) else len(issues_body)
            block = issues_body[start:end].strip()
            issues.append(_parse_review_issue_block(title, block))
    return ParsedCodexReview(
        verdict=matches[0],
        issues=tuple(issues),
        fix_prompt_for_claude=_section_body(text, "## Fix prompt for Claude"),
    )


def validate_codex_review_and_parse_verdict(review_path: Path) -> str:
    return parse_codex_review(review_path).verdict


def validate_fix_prompt(fix_prompt_path: Path) -> None:
    if not fix_prompt_path.exists() or not fix_prompt_path.read_text(encoding="utf-8").strip():
        raise HaltError(
            "halted_fix_prompt_malformed",
            f"{fix_prompt_path.name} is missing or empty",
        )
    _validate_header_order(
        fix_prompt_path, FIX_PROMPT_HEADERS, "halted_fix_prompt_malformed",
    )


def _render_fix_prompt(
    review: ParsedCodexReview,
    claude_owned_issues: Iterable[ReviewIssue],
) -> str:
    required_fixes = [
        f"- {issue.required_fix.replace(chr(10), ' ').strip()}"
        for issue in claude_owned_issues
    ]
    context_lines = [
        "The previous implementation was reviewed by Codex and received the verdict "
        "`NEEDS_FIXES`.",
        "",
        "Read:",
        "- `CLAUDE.md`",
        "- `.agent-loop/claude-prompt.md`",
        "- `.agent-loop/codex-review.md`",
        "- `.agent-loop/git-diff.patch`",
        "- `.agent-loop/test-output.log`",
        "- `.agent-loop/lint-output.log`",
        "- `.agent-loop/typecheck-output.log`",
        "- `.agent-loop/build-output.log`",
    ]
    if review.fix_prompt_for_claude:
        context_lines.extend([
            "",
            "Additional Codex guidance from the review:",
            review.fix_prompt_for_claude,
        ])
    return "\n".join([
        "# Claude Code Fix Task",
        "",
        "## Objective",
        "Fix only the Claude-owned issues found in `.agent-loop/codex-review.md`.",
        "",
        "## Context",
        *context_lines,
        "",
        "## Required fixes",
        *required_fixes,
        "",
        "## Constraints",
        "- Fix only the listed issues.",
        "- Do not redesign unrelated code.",
        "- Do not expand the product scope.",
        "- Do not modify `AGENTS.md`.",
        "- Do not modify `CLAUDE.md`.",
        "- Do not delete files unless explicitly required and approved.",
        "- Preserve the original task objective.",
        "- Update tests if behavior changes.",
        "- Prefer minimal, targeted changes.",
        "",
        "## Required output",
        "After applying fixes, update `.agent-loop/claude-summary.md` using the "
        "required Claude Implementation Summary format.",
        "",
    ])


def _sync_phase5_runtime_defaults(repo_root: Path) -> bool:
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    data = load_loop_state(state_path)
    changed = False
    updates: dict[str, object] = {}
    phase = str(data.get("phase") or "")
    sub_phase = str(data.get("sub_phase") or "")
    if "Phase 5" not in phase and "Phase 5" not in sub_phase:
        return False
    if data.get("approval_mode") in (None, ""):
        updates["approval_mode"] = DEFAULT_APPROVAL_MODE
        changed = True
    if "awaiting_human_for" not in data:
        updates["awaiting_human_for"] = None
        changed = True
    if changed:
        save_loop_state(state_path, data, updates)
    return changed


def _prepare_needs_fixes_follow_up(
    repo_root: Path,
    review: ParsedCodexReview,
    log_path: Optional[Path],
) -> dict:
    codex_owned = [issue for issue in review.issues if issue.owner == ISSUE_OWNER_CODEX]
    claude_owned = [issue for issue in review.issues if issue.owner == ISSUE_OWNER_CLAUDE]

    # Phase 5E: surface the post-review classification in
    # .agent-loop/orchestrator.log up front so a reader can reconstruct
    # which side of the ownership boundary every issue landed on, even
    # if a downstream refusal halts the cycle before any side-effect.
    _log_note(
        log_path,
        (
            f"review reconciliation: codex_owned_issues={len(codex_owned)} "
            f"(actions={sorted({issue.codex_action for issue in codex_owned if issue.codex_action})}) "
            f"claude_owned_issues={len(claude_owned)}"
        ),
    )

    unsupported_codex_issues = [
        issue for issue in codex_owned if issue.codex_action not in SUPPORTED_CODEX_ACTIONS
    ]
    if unsupported_codex_issues:
        raise HaltError(
            "halted_input_missing",
            "codex-review.md contains Codex-owned issues without a supported "
            "automatic Codex action; resolve them directly before re-running the loop. "
            f"Unsupported issues: {[issue.title for issue in unsupported_codex_issues]}",
        )

    # Phase 5E: each supported Codex action has a tight per-action
    # allow-list of paths it may legitimately touch. A Codex-owned issue
    # whose File(s) list extends outside that allow-list is refused
    # before any side-effect, even when the action itself is supported.
    # This is the contract guarantee that a Codex auto-fix cannot
    # overwrite Claude-owned implementation work just because the issue
    # was labeled `Owner: Codex`.
    for issue in codex_owned:
        allowed = CODEX_ACTION_ALLOWED_FILES.get(issue.codex_action, frozenset())
        out_of_scope = sorted(p for p in issue.files if p not in allowed)
        if out_of_scope:
            raise HaltError(
                "halted_input_missing",
                (
                    f"Codex-owned review issue {issue.title!r} declares "
                    f"codex_action={issue.codex_action!r} but its File(s) "
                    f"list includes paths outside that action's allowed "
                    f"scope: {out_of_scope}. Codex auto-fixes must not "
                    f"touch Claude-owned implementation work; the only "
                    f"paths {issue.codex_action!r} may repair are "
                    f"{sorted(allowed)}. Resolve manually before "
                    f"re-running the loop."
                ),
            )

    for issue in codex_owned:
        if issue.codex_action == CODEX_ACTION_SYNC_PHASE5_RUNTIME_DEFAULTS:
            changed = _sync_phase5_runtime_defaults(repo_root)
            _log_note(
                log_path,
                (
                    f"note: applied Codex-owned review action {issue.codex_action} "
                    f"for {issue.title}; changed={changed}"
                ),
            )

    fix_prompt_path = repo_root / ".agent-loop" / "fix-prompt.md"
    if claude_owned:
        fix_prompt_path.write_text(
            _render_fix_prompt(review, claude_owned),
            encoding="utf-8",
        )
        _log_note(
            log_path,
            (
                "note: synchronized .agent-loop/fix-prompt.md from Claude-owned "
                f"review issues: {[issue.title for issue in claude_owned]}"
            ),
        )
        return load_loop_state(repo_root / ".agent-loop" / "loop-state.json")
    raise HaltError(
        "halted_input_missing",
        "codex-review.md returned NEEDS_FIXES but no Claude-owned issues remain after "
        "Codex-owned auto-fixes; Codex must produce a fresh review instead of "
        "sending an empty Claude fix cycle.",
    )


def validate_evidence_files(repo_root: Path) -> None:
    missing: list[str] = []
    bad_state: list[str] = []
    for rel in EVIDENCE_FILES:
        path = repo_root / rel
        if not path.exists():
            missing.append(rel)
            continue
        # The contract specifies a small ASCII header block ending with
        # `----` on its own line; the `state:` line lives in that block.
        head_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:25]
        state_line = next(
            (ln for ln in head_lines if ln.lower().startswith("state:")), None,
        )
        if state_line is None:
            bad_state.append(f"{rel}: no `state:` header line in first 25 lines")
            continue
        value = state_line.split(":", 1)[1].strip()
        if value not in EVIDENCE_STATES:
            bad_state.append(
                f"{rel}: state {value!r} not in contract vocabulary "
                f"{sorted(EVIDENCE_STATES)}",
            )
    problems: list[str] = []
    if missing:
        problems.append(f"missing files: {missing}")
    if bad_state:
        problems.append(f"bad state header: {bad_state}")
    if problems:
        raise HaltError("halted_evidence_incomplete", "; ".join(problems))


# ----- evidence capture -----

def invoke_run_checks(repo_root: Path) -> int:
    script = repo_root / "scripts" / "run_checks.sh"
    if not script.exists():
        raise HaltError(
            "halted_evidence_script_unavailable",
            f"{script} does not exist",
        )
    try:
        proc = subprocess.run(
            ["bash", str(script)], cwd=str(repo_root), check=False,
        )
    except FileNotFoundError as exc:
        raise HaltError(
            "halted_evidence_script_unavailable",
            f"could not launch bash: {exc}",
        ) from exc
    # Per the contract, a non-zero exit from run_checks.sh does NOT abort
    # the loop; the per-log `state:` field is the source of truth and
    # gets re-validated in the next step.
    return proc.returncode


# ----- cycle =====

def _log_note(log_path: Optional[Path], message: str) -> None:
    """Append a single line to .agent-loop/orchestrator.log if writable.

    Best-effort: the contract treats the log as optional and never
    authoritative, so a write failure is swallowed.
    """
    if log_path is None:
        return
    try:
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(message + "\n")
    except OSError:
        pass


# ----- Phase 5B claude-done.json handoff artifact -----
#
# The Phase 5A contract requires a machine-readable Claude completion
# signal at `.agent-loop/claude-done.json`. It is a routing/timing
# artifact only - never a substitute for `.agent-loop/claude-summary.md`,
# git diff, or validation evidence in review. A new prompt or fix-prompt
# issuance must clear the prior file so a stale completion signal cannot
# drive the wrong review cycle.

CLAUDE_DONE_PATH_REL = ".agent-loop/claude-done.json"
CLAUDE_DONE_SIGNAL_VERSION = "phase-5a-v1"
CLAUDE_DONE_STATUS_READY = "ready_for_codex_review"
CLAUDE_DONE_MODE_IMPLEMENTATION = "implementation"
CLAUDE_DONE_MODE_FIX = "fix"


def _claude_done_path(repo_root: Path) -> Path:
    return repo_root / CLAUDE_DONE_PATH_REL


def clear_claude_done(repo_root: Path) -> None:
    """Remove any prior `.agent-loop/claude-done.json` so a new prompt or
    fix-prompt cycle cannot inherit a stale completion signal.

    Best-effort: a missing file is the desired post-state, and an OSError
    on removal is swallowed because the orchestrator's structural review
    still depends on `claude-summary.md`, git diff, and validation
    evidence - the done signal is routing/timing only.
    """
    path = _claude_done_path(repo_root)
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def write_claude_done(
    repo_root: Path,
    *,
    phase: Optional[str],
    sub_phase: Optional[str],
    task: Optional[str],
    cycle_count: int,
    mode: str,
    source_prompt_path: str,
) -> Path:
    """Write the Phase 5B Claude completion handoff artifact.

    Carries exactly the minimum-field set the Phase 5A contract requires:
    `signal_version`, `phase`, `sub_phase`, `task`, `cycle_count`,
    `mode` (`implementation` or `fix`), `source_prompt_path`, and
    `status` (`ready_for_codex_review`). The orchestrator writes this
    after Claude returns a fresh summary and before evidence capture, so
    Codex/orchestrator routing can see "Claude believes this prompt is
    done" without having to parse `claude-summary.md`. It is NOT
    correctness evidence; Codex review still depends on the summary,
    diff, and validation outputs.
    """
    if mode not in (CLAUDE_DONE_MODE_IMPLEMENTATION, CLAUDE_DONE_MODE_FIX):
        raise ValueError(
            f"claude-done.json mode must be one of "
            f"{{{CLAUDE_DONE_MODE_IMPLEMENTATION!r}, {CLAUDE_DONE_MODE_FIX!r}}}; "
            f"got {mode!r}"
        )
    payload = {
        "signal_version": CLAUDE_DONE_SIGNAL_VERSION,
        "phase": phase,
        "sub_phase": sub_phase,
        "task": task,
        "cycle_count": cycle_count,
        "mode": mode,
        "source_prompt_path": source_prompt_path,
        "status": CLAUDE_DONE_STATUS_READY,
    }
    path = _claude_done_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


# Phase 6B durable memory storage. Implements the storage half of the
# Phase 6A durable memory contract (see `.agent-loop/phase-plan.md`
# `### Durable Memory Contract`). This slice is storage-only: no
# retrieval into prompts, no checkpoint-consumption on resume, and no
# automatic continuation. Writes are append-mostly: a new entry is a
# new file; superseding a prior entry is recorded via an explicit
# `supersedes` field, never via silent in-place mutation. Every write
# is scoped under `.agent-loop/memory/` and refused if it would resolve
# outside that directory.

MEMORY_DIR_REL = ".agent-loop/memory"
MEMORY_SIGNAL_VERSION = "phase-6b-v1"
MEMORY_CATEGORY_DECISION = "decision"
MEMORY_CATEGORY_FAILURE = "failure"
MEMORY_CATEGORY_PREFERENCE = "preference"
MEMORY_CATEGORY_SUMMARY = "summary"
MEMORY_CATEGORY_CHECKPOINT = "checkpoint"
MEMORY_CATEGORIES = frozenset({
    MEMORY_CATEGORY_DECISION,
    MEMORY_CATEGORY_FAILURE,
    MEMORY_CATEGORY_PREFERENCE,
    MEMORY_CATEGORY_SUMMARY,
    MEMORY_CATEGORY_CHECKPOINT,
})
MEMORY_REQUIRED_FIELDS = (
    "signal_version",
    "category",
    "phase",
    "sub_phase",
    "cycle_count",
    "source_artifact_path",
    "created_at",
)


def _memory_dir(repo_root: Path) -> Path:
    return repo_root / MEMORY_DIR_REL


def _ensure_memory_path_in_scope(path: Path, repo_root: Path) -> None:
    """Refuse any path that resolves outside `.agent-loop/memory/`.

    Phase 6A scope rule: memory writes never mutate canonical workflow
    or state artifacts. A symlink or `..` traversal that escapes the
    memory directory is treated as a hard refusal.
    """
    memory_root = _memory_dir(repo_root).resolve()
    try:
        resolved = path.resolve()
    except OSError as exc:
        raise HaltError(
            "halted_input_missing",
            f"memory path {path} could not be resolved: {exc}",
        )
    try:
        resolved.relative_to(memory_root)
    except ValueError:
        raise HaltError(
            "halted_input_missing",
            (
                f"memory write refused: path {resolved} is outside the "
                f"memory directory {memory_root}. Memory writes are scoped "
                f"to {MEMORY_DIR_REL}/ only."
            ),
        )


def _utc_iso_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _memory_entry_filename(created_at: str, body: Optional[str]) -> str:
    """Stable, sort-friendly filename derived from `created_at` plus a
    short hash of `body` (so two entries written in the same wall-clock
    second do not collide).
    """
    payload = (body or "").encode("utf-8")
    short = hashlib.sha256(payload).hexdigest()[:8]
    safe_ts = created_at.replace(":", "").replace("-", "")
    return f"{safe_ts}-{short}.json"


def write_memory_entry(
    repo_root: Path,
    *,
    category: str,
    phase: str,
    sub_phase: str,
    cycle_count: int,
    source_artifact_path: str,
    body: Optional[str] = None,
    supersedes: Optional[str] = None,
    log_path: Optional[Path] = None,
) -> Path:
    """Write one structured durable memory entry under
    `.agent-loop/memory/<category>/`.

    Enforces the Phase 6A contract:
      - `category` must be one of the five allowed categories.
      - The required metadata fields (`category`, `phase`, `sub_phase`,
        `cycle_count`, `source_artifact_path`, `created_at`,
        `signal_version`) are all populated; `created_at` and
        `signal_version` are filled in by the writer.
      - The write is append-mostly: a fresh file is created with a
        per-entry name derived from `created_at` and the body hash;
        the writer never overwrites an existing entry.
      - Supersession of a prior entry is recorded via the explicit
        `supersedes` field (a path-relative reference to the prior
        entry). The prior entry is left untouched.
      - All writes are scoped to `.agent-loop/memory/`. A path that
        resolves outside that directory raises `HaltError` and no
        file is written.

    Returns the absolute `Path` of the freshly written entry.

    Phase 6B scope: this function is the storage primitive only. No
    runtime path in the orchestrator calls it automatically in this
    slice; retrieval into prompts and checkpoint-driven continuation
    are deferred to later 6x slices.
    """
    if category not in MEMORY_CATEGORIES:
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory category {category!r} is not one of "
                f"{sorted(MEMORY_CATEGORIES)}; the Phase 6A contract "
                f"pins exactly these five categories"
            ),
        )
    if not phase or not sub_phase or not source_artifact_path:
        raise HaltError(
            "halted_input_missing",
            (
                "durable memory write refused: phase, sub_phase, and "
                "source_artifact_path are all required by the Phase 6A "
                f"contract; got phase={phase!r}, sub_phase={sub_phase!r}, "
                f"source_artifact_path={source_artifact_path!r}"
            ),
        )
    if not isinstance(cycle_count, int):
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory write refused: cycle_count must be an int; "
                f"got {type(cycle_count).__name__}={cycle_count!r}"
            ),
        )
    created_at = _utc_iso_now()
    payload = {
        "signal_version": MEMORY_SIGNAL_VERSION,
        "category": category,
        "phase": phase,
        "sub_phase": sub_phase,
        "cycle_count": cycle_count,
        "source_artifact_path": source_artifact_path,
        "created_at": created_at,
        "supersedes": supersedes,
        "body": body,
    }
    category_dir = _memory_dir(repo_root) / category
    category_dir.mkdir(parents=True, exist_ok=True)
    entry_path = category_dir / _memory_entry_filename(created_at, body)
    _ensure_memory_path_in_scope(entry_path, repo_root)
    if entry_path.exists():
        # Append-mostly: never overwrite an existing entry. A collision
        # at the second granularity AND the body-hash level is highly
        # unlikely; if it happens, refuse so the caller can resolve.
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory write refused: target entry "
                f"{entry_path} already exists; the Phase 6A contract "
                f"forbids silent in-place mutation"
            ),
        )
    entry_path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    rel = entry_path.relative_to(repo_root).as_posix()
    _log_note(
        log_path,
        (
            f"memory write: {rel} category={category!r} phase={phase!r} "
            f"sub_phase={sub_phase!r} cycle_count={cycle_count} "
            f"supersedes={supersedes!r}"
        ),
    )
    return entry_path


def read_memory_entry(path: Path) -> dict:
    """Parse and validate a durable memory entry from disk.

    Refuses fail-closed if the file is missing, empty, malformed JSON,
    missing a required Phase 6A metadata field, claims an unknown
    `category`, or carries an unrecognized `signal_version`. The
    returned dict is the parsed payload exactly as written; callers
    must not mutate the entry on disk via this helper.
    """
    if not path.is_file():
        raise HaltError(
            "halted_input_missing",
            f"durable memory entry {path} does not exist",
        )
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise HaltError(
            "halted_input_missing",
            f"durable memory entry {path} is empty",
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HaltError(
            "halted_input_missing",
            f"durable memory entry {path} is not valid JSON: {exc}",
        )
    if not isinstance(payload, dict):
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory entry {path} top-level value must be a "
                f"JSON object; got {type(payload).__name__}"
            ),
        )
    for field in MEMORY_REQUIRED_FIELDS:
        if field not in payload:
            raise HaltError(
                "halted_input_missing",
                (
                    f"durable memory entry {path} missing required Phase 6A "
                    f"metadata field {field!r}"
                ),
            )
    if not payload["phase"] or not payload["sub_phase"] or not payload["source_artifact_path"]:
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory entry {path} has empty required metadata; "
                f"phase={payload['phase']!r} sub_phase={payload['sub_phase']!r} "
                f"source_artifact_path={payload['source_artifact_path']!r}"
            ),
        )
    if not isinstance(payload["cycle_count"], int):
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory entry {path} has non-int cycle_count "
                f"{payload['cycle_count']!r}"
            ),
        )
    if payload["category"] not in MEMORY_CATEGORIES:
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory entry {path} declares category "
                f"{payload['category']!r} which is not one of "
                f"{sorted(MEMORY_CATEGORIES)}"
            ),
        )
    if payload["signal_version"] != MEMORY_SIGNAL_VERSION:
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory entry {path} signal_version "
                f"{payload['signal_version']!r} is not recognized by this "
                f"orchestrator (expected {MEMORY_SIGNAL_VERSION!r})"
            ),
        )
    return payload


def list_memory_entries(
    repo_root: Path, *, category: Optional[str] = None,
) -> list:
    """Return sorted list of memory entry `Path`s under
    `.agent-loop/memory/` (optionally restricted to one category).

    Sorted by filename, which is sort-friendly because filenames begin
    with the entry's `created_at` UTC timestamp. A missing memory
    directory or category subdirectory returns an empty list (the
    Phase 6A contract permits an absent memory layer).
    """
    if category is not None and category not in MEMORY_CATEGORIES:
        raise HaltError(
            "halted_input_missing",
            (
                f"list_memory_entries category={category!r} is not one of "
                f"{sorted(MEMORY_CATEGORIES)}"
            ),
        )
    root = _memory_dir(repo_root)
    if not root.is_dir():
        return []
    unknown_dirs = sorted(
        p.name for p in root.iterdir() if p.is_dir() and p.name not in MEMORY_CATEGORIES
    )
    if unknown_dirs:
        raise HaltError(
            "halted_input_missing",
            (
                "durable memory directory contains unknown categories "
                f"{unknown_dirs!r}; the Phase 6A contract pins exactly "
                f"{sorted(MEMORY_CATEGORIES)}"
            ),
        )
    if category is not None:
        cat_dir = root / category
        if not cat_dir.is_dir():
            return []
        return sorted(
            p for p in cat_dir.iterdir() if p.is_file() and p.suffix == ".json"
        )
    out: list = []
    for cat in sorted(MEMORY_CATEGORIES):
        cat_dir = root / cat
        if cat_dir.is_dir():
            out.extend(
                sorted(
                    p for p in cat_dir.iterdir()
                    if p.is_file() and p.suffix == ".json"
                )
            )
    return out


# Phase 6C - Selective Memory Retrieval Initial Slice.
#
# This block sits directly on top of the Phase 6B storage primitives. It
# is a pure read-side enrichment surface: it never writes to disk, never
# touches any canonical workflow / state artifact, and never feeds
# memory back into a verdict, halt status, or `awaiting_human_for`. Per
# the Phase 6A contract, returned entries are advisory only and the
# caller must treat them as such when constructing future prompts.

MEMORY_RETRIEVAL_DEFAULT_LIMIT = 8
MEMORY_RETRIEVAL_MAX_LIMIT = 32
# Structural marker applied to every retrieved entry. Per the Phase 6A
# contract, returned memory is advisory-only and must not be fed back
# into canonical workflow / state fields (verdicts, halt statuses,
# `awaiting_human_for`). The marker lets a caller assert "is this
# advisory?" structurally rather than relying on documentation.
MEMORY_RETRIEVAL_ADVISORY_FIELD = "advisory_only"


def _validate_retrieval_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory retrieval limit must be an int; got "
                f"{type(limit).__name__}={limit!r}"
            ),
        )
    if limit <= 0:
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory retrieval limit must be > 0; got {limit}. "
                f"The Phase 6A contract requires a bounded, positive result set"
            ),
        )
    if limit > MEMORY_RETRIEVAL_MAX_LIMIT:
        raise HaltError(
            "halted_input_missing",
            (
                f"durable memory retrieval limit {limit} exceeds the "
                f"hard upper bound {MEMORY_RETRIEVAL_MAX_LIMIT}; the "
                f"Phase 6A contract pins retrieval as bounded by design"
            ),
        )


def _is_entry_in_active_scope(
    payload: dict,
    *,
    phase: str,
    sub_phase: Optional[str],
) -> bool:
    """An entry is in the active scope when its `phase` matches and any
    optionally supplied `sub_phase` filter also matches.

    Phase is required; sub_phase narrows the scope further when the
    caller provides it. The canonical state model assigns one active
    task per active (phase, sub_phase) pair, so task-level scoping is
    implicit in the (phase, sub_phase) match. A 6B entry does not carry
    a task field of its own; the `source_artifact_path` it does carry
    is the canonical artifact the entry was derived from, not the
    active task string.
    """
    if payload["phase"] != phase:
        return False
    if sub_phase is not None and payload["sub_phase"] != sub_phase:
        return False
    return True


def retrieve_memory_entries(
    repo_root: Path,
    *,
    phase: str,
    sub_phase: Optional[str] = None,
    categories: Optional[Iterable[str]] = None,
    limit: int = MEMORY_RETRIEVAL_DEFAULT_LIMIT,
    log_path: Optional[Path] = None,
) -> list:
    """Return a bounded, sorted list of durable memory entries relevant
    to the active phase / sub_phase scope.

    Phase 6C scope: pure retrieval primitive. The returned list is a
    list of validated payload dicts (newest-first by `created_at`),
    each one re-validated through `read_memory_entry` so a malformed,
    missing-field, unknown-category, or unrecognized-`signal_version`
    entry on disk causes the entire retrieval call to halt fail-closed.

    Each returned dict carries `MEMORY_RETRIEVAL_ADVISORY_FIELD` set to
    `True` as a structural marker. Per the Phase 6A contract, returned
    memory is advisory-only: callers must not feed the returned entries
    back into canonical workflow / state fields (verdicts, halt
    statuses, `awaiting_human_for`). The structural marker lets a
    consumer assert advisory-only status rather than relying on
    docstrings.

    Active-task scoping is implicit in the (phase, sub_phase) match
    because the canonical state model assigns one active task per
    active (phase, sub_phase) pair. The 6B storage schema does not
    carry a task field of its own; this slice intentionally narrows
    retrieval to phase / sub_phase / category filters rather than
    inventing an entry-side task field outside the 6B schema.

    Args:
      repo_root: workspace root that contains `.agent-loop/memory/`.
      phase: required active phase string. An entry whose `phase` does
        not match is excluded.
      sub_phase: optional narrowing filter against the entry's
        `sub_phase`. If omitted, all sub_phases under the active phase
        are eligible.
      categories: optional iterable that restricts results to one or
        more of the five Phase 6A categories. An out-of-vocabulary
        category in the filter is refused (the same five-category set
        the writer pins is the only valid input).
      limit: hard upper bound on the returned list length. Must be a
        positive int and must not exceed MEMORY_RETRIEVAL_MAX_LIMIT.
      log_path: optional orchestrator-log path; when supplied a single
        `memory retrieval:` audit note is appended describing the
        scope / category filter / limit / matched / returned counts.

    Returns:
      A new list of payload dicts (newest-first) each carrying
      `MEMORY_RETRIEVAL_ADVISORY_FIELD = True`. The list is at most
      `limit` long. Returns an empty list when the memory directory is
      absent or when no entry matches the active scope.
    """
    if not phase:
        raise HaltError(
            "halted_input_missing",
            (
                "durable memory retrieval requires a non-empty active phase "
                "string"
            ),
        )
    _validate_retrieval_limit(limit)

    category_filter: Optional[set] = None
    if categories is not None:
        category_filter = set()
        for c in categories:
            if c not in MEMORY_CATEGORIES:
                raise HaltError(
                    "halted_input_missing",
                    (
                        f"durable memory retrieval category {c!r} is not "
                        f"one of {sorted(MEMORY_CATEGORIES)}"
                    ),
                )
            category_filter.add(c)

    # list_memory_entries already refuses unknown on-disk category
    # subdirectories and returns [] when the memory directory is absent;
    # both of those are exactly the right Phase 6A behavior here.
    paths = list_memory_entries(repo_root)
    matched: list = []
    for p in paths:
        payload = read_memory_entry(p)
        if (
            category_filter is not None
            and payload["category"] not in category_filter
        ):
            continue
        if not _is_entry_in_active_scope(
            payload, phase=phase, sub_phase=sub_phase,
        ):
            continue
        # Wrap with a structural advisory marker. read_memory_entry
        # already returns a fresh dict per call (json.loads), so the
        # copy below is defensive and pins the boundary explicitly.
        entry = dict(payload)
        entry[MEMORY_RETRIEVAL_ADVISORY_FIELD] = True
        matched.append(entry)

    matched.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    bounded = matched[:limit]

    if log_path is not None:
        cats_str = (
            sorted(category_filter) if category_filter is not None else None
        )
        _log_note(
            log_path,
            (
                f"memory retrieval: phase={phase!r} sub_phase={sub_phase!r} "
                f"categories={cats_str} limit={limit} "
                f"matched={len(matched)} returned={len(bounded)}"
            ),
        )
    return bounded


# Phase 6D - Checkpoint Artifact Storage Initial Slice.
#
# Checkpoint artifacts capture the structured continuation state of an
# interrupted Claude or Codex run per the Phase 6A "Checkpoint and
# resume behavior" subsection. They are a specialization of the Phase 6B
# memory storage layer (category="checkpoint") with additional required
# fields encoded in the entry body.
#
# Scope of this slice: storage only. Writing and read-side schema
# validation are implemented. No orchestrator runtime path consumes a
# checkpoint on resume in this slice, and no token-exhaustion
# continuation chaining is enabled. Those are deferred to later 6x
# slices.

CHECKPOINT_SIGNAL_VERSION = "phase-6d-v1"

CHECKPOINT_ACTIVE_PROMPT_PATHS = frozenset({
    ".agent-loop/claude-prompt.md",
    ".agent-loop/fix-prompt.md",
})

CHECKPOINT_BASE_SUSPENSION_REASONS = frozenset({
    "token_exhaustion",
    "human_interrupt",
    "process_killed",
    "orchestrator_restart",
})

# Phase 5C strict-gate halt statuses that the Phase 6A contract names as
# valid checkpoint suspension reasons. Adding a new strict-gate halt in
# a later slice requires extending this set in lockstep.
CHECKPOINT_STRICT_GATE_HALT_REASONS = frozenset({
    "halted_awaiting_human_pre_claude_prompt",
    "halted_awaiting_human_pre_fix_prompt",
    "halted_awaiting_human_pre_codex_review_normal",
    "halted_awaiting_human_pre_codex_review_fix",
})

CHECKPOINT_ALLOWED_SUSPENSION_REASONS = (
    CHECKPOINT_BASE_SUSPENSION_REASONS | CHECKPOINT_STRICT_GATE_HALT_REASONS
)

# Checkpoint-specific required fields encoded in the memory entry body.
# These are ADDITIONAL to the seven Phase 6A required memory metadata
# fields enforced by write_memory_entry / read_memory_entry.
CHECKPOINT_REQUIRED_BODY_FIELDS = (
    "checkpoint_signal_version",
    "task",
    "status",
    "approval_mode",
    "awaiting_human_for",
    "active_prompt_path",
    "suspension_reason",
    "continuation_budget",
)


def _validate_continuation_budget(value) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint continuation_budget must be an int; got "
                f"{type(value).__name__}={value!r}"
            ),
        )
    if value < 0:
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint continuation_budget must be >= 0; got {value}. "
                f"The Phase 6A contract requires a bounded continuation "
                f"budget; a value of 0 means no further continuation is "
                f"permitted without explicit human approval"
            ),
        )


def write_checkpoint_entry(
    repo_root: Path,
    *,
    phase: str,
    sub_phase: str,
    task: str,
    cycle_count: int,
    status: str,
    approval_mode: str,
    awaiting_human_for: Optional[str],
    active_prompt_path: str,
    suspension_reason: str,
    continuation_budget: int,
    source_artifact_path: str,
    supersedes: Optional[str] = None,
    log_path: Optional[Path] = None,
) -> Path:
    """Write one structured checkpoint artifact under
    `.agent-loop/memory/checkpoint/`.

    Per the Phase 6A contract, a checkpoint memory entry must capture
    the cycle context being suspended, the active prompt path, the
    reason for suspension, and a bounded continuation budget. This
    function wraps the existing Phase 6B `write_memory_entry` primitive
    with category=`checkpoint`; the checkpoint-specific fields are
    encoded in the memory entry body as a JSON object.

    Refuses fail-closed (`halted_input_missing`) on:
      - empty `task` / `status` / `approval_mode`
      - `awaiting_human_for` that is not None and not a non-empty string
      - `active_prompt_path` not in CHECKPOINT_ACTIVE_PROMPT_PATHS
      - `suspension_reason` not in CHECKPOINT_ALLOWED_SUSPENSION_REASONS
      - `continuation_budget` not a non-negative int (bool refused)

    The Phase 6B write-boundary scope guard is inherited via the
    underlying `write_memory_entry` call, so a checkpoint write can
    never mutate any canonical workflow / state artifact.

    Phase 6D scope: storage primitive only. No runtime path in the
    orchestrator consumes the checkpoint in this slice; resume-path
    consumption and token-exhaustion continuation chaining are deferred
    to later 6x slices.
    """
    if not task:
        raise HaltError(
            "halted_input_missing",
            "checkpoint write refused: task is required by the Phase 6A "
            "checkpoint contract",
        )
    if not status:
        raise HaltError(
            "halted_input_missing",
            "checkpoint write refused: status is required by the Phase 6A "
            "checkpoint contract",
        )
    if not approval_mode:
        raise HaltError(
            "halted_input_missing",
            "checkpoint write refused: approval_mode is required by the "
            "Phase 6A checkpoint contract",
        )
    if awaiting_human_for is not None:
        if not isinstance(awaiting_human_for, str) or not awaiting_human_for:
            raise HaltError(
                "halted_input_missing",
                (
                    f"checkpoint awaiting_human_for must be None or a "
                    f"non-empty string; got "
                    f"{type(awaiting_human_for).__name__}="
                    f"{awaiting_human_for!r}"
                ),
            )
    if active_prompt_path not in CHECKPOINT_ACTIVE_PROMPT_PATHS:
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint active_prompt_path {active_prompt_path!r} "
                f"is not one of {sorted(CHECKPOINT_ACTIVE_PROMPT_PATHS)}; "
                f"the Phase 6A contract pins these as the only valid "
                f"active prompt paths"
            ),
        )
    if suspension_reason not in CHECKPOINT_ALLOWED_SUSPENSION_REASONS:
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint suspension_reason {suspension_reason!r} is "
                f"not one of {sorted(CHECKPOINT_ALLOWED_SUSPENSION_REASONS)}"
            ),
        )
    _validate_continuation_budget(continuation_budget)

    body_payload = {
        "checkpoint_signal_version": CHECKPOINT_SIGNAL_VERSION,
        "task": task,
        "status": status,
        "approval_mode": approval_mode,
        "awaiting_human_for": awaiting_human_for,
        "active_prompt_path": active_prompt_path,
        "suspension_reason": suspension_reason,
        "continuation_budget": continuation_budget,
    }
    body = json.dumps(body_payload, indent=2)

    return write_memory_entry(
        repo_root,
        category=MEMORY_CATEGORY_CHECKPOINT,
        phase=phase,
        sub_phase=sub_phase,
        cycle_count=cycle_count,
        source_artifact_path=source_artifact_path,
        body=body,
        supersedes=supersedes,
        log_path=log_path,
    )


def read_checkpoint_entry(path: Path) -> dict:
    """Parse and validate a checkpoint artifact from disk.

    Re-runs the Phase 6B `read_memory_entry` schema validation first
    (so missing memory-metadata, unknown category, and unrecognized
    memory `signal_version` are caught), then refuses fail-closed when:
      - the entry's `category` is not `checkpoint`
      - the entry has no `body`
      - the body is not valid JSON
      - the body is not a JSON object
      - the body is missing any field in CHECKPOINT_REQUIRED_BODY_FIELDS
      - the body's `checkpoint_signal_version` is not the current
        recognized version (a "stale" checkpoint schema)
      - `active_prompt_path` is not in CHECKPOINT_ACTIVE_PROMPT_PATHS
      - `suspension_reason` is not in CHECKPOINT_ALLOWED_SUSPENSION_REASONS
      - `continuation_budget` is not a non-negative int

    Returns a flat dict combining the Phase 6B memory-level metadata
    and the checkpoint-specific body fields. The two field sets do not
    overlap.

    Phase 6D scope: schema validation only. This function does not
    verify staleness against the current `loop-state.json` cycle
    context; that comparison belongs to a later resume-path slice that
    actually consumes the checkpoint.
    """
    payload = read_memory_entry(path)
    if payload["category"] != MEMORY_CATEGORY_CHECKPOINT:
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint read refused: entry {path} declares category "
                f"{payload['category']!r} which is not "
                f"{MEMORY_CATEGORY_CHECKPOINT!r}"
            ),
        )
    body_str = payload.get("body")
    if not body_str:
        raise HaltError(
            "halted_input_missing",
            f"checkpoint read refused: entry {path} has no body",
        )
    try:
        body = json.loads(body_str)
    except json.JSONDecodeError as exc:
        raise HaltError(
            "halted_input_missing",
            f"checkpoint read refused: entry {path} body is not valid JSON: {exc}",
        )
    if not isinstance(body, dict):
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint read refused: entry {path} body top-level "
                f"value must be a JSON object; got {type(body).__name__}"
            ),
        )
    for field in CHECKPOINT_REQUIRED_BODY_FIELDS:
        if field not in body:
            raise HaltError(
                "halted_input_missing",
                (
                    f"checkpoint read refused: entry {path} body missing "
                    f"required field {field!r}"
                ),
            )
    if body["checkpoint_signal_version"] != CHECKPOINT_SIGNAL_VERSION:
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint read refused: entry {path} body "
                f"checkpoint_signal_version "
                f"{body['checkpoint_signal_version']!r} is not recognized "
                f"by this orchestrator (expected "
                f"{CHECKPOINT_SIGNAL_VERSION!r})"
            ),
        )
    # Per-field shape checks. These mirror the write-side guards in
    # write_checkpoint_entry so a hand-edited or corrupted artifact
    # cannot bypass the checkpoint contract on read.
    for required_non_empty in ("task", "status", "approval_mode"):
        value = body[required_non_empty]
        if not isinstance(value, str) or not value:
            raise HaltError(
                "halted_input_missing",
                (
                    f"checkpoint read refused: entry {path} body field "
                    f"{required_non_empty!r} must be a non-empty string; "
                    f"got {type(value).__name__}={value!r}"
                ),
            )
    awaiting = body["awaiting_human_for"]
    if awaiting is not None and (not isinstance(awaiting, str) or not awaiting):
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint read refused: entry {path} body field "
                f"'awaiting_human_for' must be None or a non-empty string; "
                f"got {type(awaiting).__name__}={awaiting!r}"
            ),
        )
    if body["active_prompt_path"] not in CHECKPOINT_ACTIVE_PROMPT_PATHS:
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint read refused: entry {path} body "
                f"active_prompt_path {body['active_prompt_path']!r} is "
                f"not one of {sorted(CHECKPOINT_ACTIVE_PROMPT_PATHS)}"
            ),
        )
    if body["suspension_reason"] not in CHECKPOINT_ALLOWED_SUSPENSION_REASONS:
        raise HaltError(
            "halted_input_missing",
            (
                f"checkpoint read refused: entry {path} body "
                f"suspension_reason {body['suspension_reason']!r} is "
                f"not one of "
                f"{sorted(CHECKPOINT_ALLOWED_SUSPENSION_REASONS)}"
            ),
        )
    _validate_continuation_budget(body["continuation_budget"])

    result = dict(payload)
    result.update(body)
    return result


def list_checkpoint_entries(repo_root: Path) -> list:
    """Return the sorted list of checkpoint artifact `Path`s under
    `.agent-loop/memory/checkpoint/`.

    Returns an empty list when the checkpoint subdirectory is absent
    (per the Phase 6A "missing memory layer must not block a cycle"
    rule).
    """
    return list_memory_entries(
        repo_root, category=MEMORY_CATEGORY_CHECKPOINT,
    )


# Phase 6E - Checkpoint Resume Initial Slice.
#
# Read-side helpers that consume the Phase 6D checkpoint storage layer
# during explicit `resume`. These helpers validate that a stored
# checkpoint is consistent with the canonical loop-state context BEFORE
# the existing strict-gate dispatch runs. They never write to disk,
# never widen autonomy, never bypass any Phase 5 human gate, and never
# implement token-exhaustion continuation chaining or automatic
# continuation - those remain deferred to later 6x slices.
#
# The Phase 6A contract treats checkpoint memory as advisory in this
# slice: a missing checkpoint MUST NOT block a strict-gate resume that
# the canonical loop-state already supports (backward compatibility
# with pre-6D / pre-6E paused cycles); a checkpoint that exists but
# disagrees with the canonical loop-state MUST refuse fail-closed so
# the operator sees the inconsistency.

# Memory-level fields the loop-state and the checkpoint must agree on
# before resume is permitted. These are the Phase 6A "cycle context"
# subset that names which cycle is being resumed.
CHECKPOINT_RESUME_CONTEXT_FIELDS = (
    "phase",
    "sub_phase",
    "task",
    "cycle_count",
    "approval_mode",
    "awaiting_human_for",
)


def _load_active_checkpoint(repo_root: Path) -> Optional[dict]:
    """Return the active (most recently written) checkpoint payload,
    or None if no checkpoint artifacts exist.

    Active-checkpoint selection rule: the active checkpoint is the
    one with the largest filesystem mtime. Filename (lexical) is the
    deterministic secondary tie-breaker only for the case where two
    files share an identical mtime.

    This rule actually tracks write order rather than filename order.
    The Phase 6D filename format is
    `{YYYYMMDDTHHMMSSZ}-{sha256_short(body)[:8]}.json` whose
    timestamp portion is second-granularity and whose body-hash tail
    is deterministic but uncorrelated with write order. Two
    checkpoints written in the same second can therefore have the
    second-written file carry a lexically-smaller hash suffix - so
    selecting by filename alone would pick the wrong "active"
    checkpoint. Filesystem mtime on the platforms this project
    targets (NTFS / ext4 / APFS) has nanosecond / 100ns resolution,
    so two same-second writes still receive distinct mtimes that
    reflect actual write order.

    Per the Phase 6A "append-mostly" model, older entries are
    historical records of past halts; they are NOT consulted for
    resume consistency once the active checkpoint has been
    identified. A malformed historical checkpoint therefore does not
    block resume; only the chosen active checkpoint is read through
    `read_checkpoint_entry`. If THAT entry is malformed, missing a
    required field, carries an unrecognized
    `checkpoint_signal_version`, or has an out-of-vocabulary value,
    the existing fail-closed `HaltError` propagates so the caller
    surfaces the refusal to the operator rather than silently falling
    back to "no checkpoint".

    Returns None only when the checkpoint subdirectory is absent or
    empty. This preserves backward compatibility with pre-6D paused
    cycles where no checkpoint was ever written.
    """
    paths = list_checkpoint_entries(repo_root)
    if not paths:
        return None
    # Primary key: filesystem mtime (actual write order). Secondary
    # key: filename (deterministic) for the rare case where two files
    # share an identical mtime.
    active = max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name))
    return read_checkpoint_entry(active)


def _validate_checkpoint_against_loop_state(
    checkpoint: dict, loop_state: dict,
) -> None:
    """Refuse fail-closed when the checkpoint does not name the same
    cycle context as the canonical loop-state.

    Per the Phase 6A contract: "on resume, the loop must verify that
    the checkpoint's (phase, sub_phase, task, cycle_count) matches the
    current loop-state.json; on any mismatch the loop must refuse and
    require human resolution". This helper extends the comparison to
    `approval_mode` and `awaiting_human_for` because the Phase 6A
    contract also requires "token-exhaustion checkpoints inherit the
    existing approval-mode vocabulary" and the strict-gate halt's
    `awaiting_human_for` is the operator-facing gate identity.

    When the loop-state is sitting at a Phase 5C strict-gate halt, the
    checkpoint's `suspension_reason` must equal the halt status. This
    is the contract's "a strict-gate halt that has its own resume path
    must continue to dispatch through the existing strict-gate flow;
    the checkpoint memory is advisory and does not replace strict-gate
    dispatch" requirement: the checkpoint may name the same gate, but
    it may not claim a different suspension reason.

    The helper raises `HaltError("halted_input_missing", ...)` on any
    mismatch. The caller is responsible for the resume-time recovery
    pattern (preserve the saved strict-gate state, log the refusal,
    exit 2 without going through `_halt`).
    """
    for field in CHECKPOINT_RESUME_CONTEXT_FIELDS:
        checkpoint_value = checkpoint.get(field)
        loop_state_value = loop_state.get(field)
        if checkpoint_value != loop_state_value:
            raise HaltError(
                "halted_input_missing",
                (
                    f"checkpoint {field}={checkpoint_value!r} does not match "
                    f"loop-state {field}={loop_state_value!r}; the Phase 6A "
                    f"contract refuses a stale or contradictory checkpoint "
                    f"at resume time"
                ),
            )
    loop_status = loop_state.get("status")
    if loop_status in STRICT_GATE_HALT_STATUSES:
        checkpoint_reason = checkpoint.get("suspension_reason")
        if checkpoint_reason != loop_status:
            raise HaltError(
                "halted_input_missing",
                (
                    f"checkpoint suspension_reason={checkpoint_reason!r} "
                    f"does not match the active strict-gate halt status "
                    f"{loop_status!r}; the Phase 6A contract requires the "
                    f"checkpoint to name the same gate the loop is paused at"
                ),
            )


# Phase 6F - Token Exhaustion Continuation Initial Slice.
#
# Token exhaustion (Claude / Codex running out of context, the CLI
# process being killed before the cycle terminates, etc.) must NOT be
# treated as silent success. Per the Phase 6A "checkpoint and resume
# behavior" subsection, token exhaustion is one of the named
# `suspension_reason` values; the cycle must be classified as
# interrupted, a checkpoint must record the pre-suspension cycle
# context plus a bounded continuation budget, and resume must consume
# the budget deterministically.
#
# This slice is narrow: it implements RECORD + RESUME for explicit
# token-exhaustion checkpoints. It does NOT implement automatic
# continuation chaining, background continuation, or any cycle
# auto-restart. Resume restores the loop-state to a non-halt status
# (the pre-suspension cycle status the checkpoint captured) and
# returns to the operator, who then invokes the orchestrator again to
# pick up the cycle from the restored status.

HALTED_TOKEN_EXHAUSTION = "halted_awaiting_token_exhaustion_continuation"
AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION = "token_exhaustion_continuation"
TOKEN_EXHAUSTION_SUSPENSION_REASON = "token_exhaustion"
# Default budget for a freshly recorded token-exhaustion event. Bounded
# by design: a caller may override for special cases, but the writer
# refuses a negative value via the Phase 6D continuation-budget guard.
TOKEN_EXHAUSTION_DEFAULT_BUDGET = 2

# Cycle-identity fields the token-exhaustion validator compares between
# the checkpoint and the canonical loop-state. NOTE: this set is a
# strict subset of CHECKPOINT_RESUME_CONTEXT_FIELDS - `status` and
# `awaiting_human_for` are intentionally omitted because the loop-state
# carries the HALT vocabulary while the checkpoint records the
# pre-suspension cycle vocabulary; comparing them would always refuse.
TOKEN_EXHAUSTION_IDENTITY_FIELDS = (
    "phase",
    "sub_phase",
    "task",
    "cycle_count",
    "approval_mode",
)

# Interrupted-cycle stages this initial Phase 6F slice can actually
# dispatch back into. Each entry must have an existing continuation
# entry-point that does NOT re-issue cycle_count for the same cycle, so
# the resume path lands on the same logical work the suspension
# interrupted rather than starting a fresh cycle. Statuses outside this
# set are intentionally unsupported: the operator must drive the cycle
# forward manually or activate a new sub-phase. Widening this set is a
# later-slice concern (it would require new no-increment continuation
# entry-points for `claude_implementing`, `evidence_capture`, and the
# fix-cycle equivalents).
TOKEN_EXHAUSTION_SUPPORTED_RESUME_STATUSES = frozenset({
    "awaiting_claude_implementation",
    "awaiting_codex_review",
})


def _validate_token_exhaustion_checkpoint(
    checkpoint: dict, loop_state: dict,
) -> None:
    """Refuse fail-closed when a token-exhaustion checkpoint does not
    name the same cycle identity as the canonical loop-state.

    Unlike `_validate_checkpoint_against_loop_state`, this validator
    does NOT compare `status` or `awaiting_human_for`. After
    `record_token_exhaustion` runs, loop-state carries the halt
    vocabulary (`HALTED_TOKEN_EXHAUSTION` + the awaiting-human-for
    gate name) while the checkpoint preserves the pre-suspension cycle
    vocabulary. Comparing those fields directly would always refuse;
    the cycle-identity subset is what proves the checkpoint still
    describes the same active phase / sub_phase / task / cycle_count /
    approval_mode the loop is paused at.

    Raises `HaltError("halted_input_missing", ...)` on any mismatch.
    """
    for field in TOKEN_EXHAUSTION_IDENTITY_FIELDS:
        checkpoint_value = checkpoint.get(field)
        loop_state_value = loop_state.get(field)
        if checkpoint_value != loop_state_value:
            raise HaltError(
                "halted_input_missing",
                (
                    f"token-exhaustion checkpoint {field}="
                    f"{checkpoint_value!r} does not match loop-state "
                    f"{field}={loop_state_value!r}"
                ),
            )


def record_token_exhaustion(
    repo_root: Path,
    *,
    active_prompt_path: str,
    continuation_budget: int = TOKEN_EXHAUSTION_DEFAULT_BUDGET,
    log_path: Optional[Path] = None,
) -> Path:
    """Classify a token / context exhaustion event as a resumable
    interrupted-run state.

    Writes a token-exhaustion checkpoint capturing the suspended cycle
    context plus a bounded continuation budget, then transitions
    loop-state status to `HALTED_TOKEN_EXHAUSTION` so the
    operator-visible halt is auditable from the canonical state
    artifacts. Per the Phase 6A contract, token exhaustion must NOT be
    treated as silent success; this function makes the interruption an
    explicit, on-disk halt the operator can recover from via the
    `resume` subcommand.

    The pre-suspension loop-state `status` and `awaiting_human_for`
    are preserved inside the checkpoint body (so resume can restore
    them) but are overwritten on the loop-state with the halt
    vocabulary so subsequent orchestrator invocations refuse to start
    a fresh cycle until the operator runs `resume`.

    Refuses fail-closed via `HaltError("halted_input_missing", ...)`
    when:
      - `loop-state.json` is missing or malformed
      - `contract_version` is unsupported
      - the current `status` is already a `halted_*` value
      - the current `status` is the phase-complete terminal
      - `active_prompt_path` is not in
        `CHECKPOINT_ACTIVE_PROMPT_PATHS`

    Returns the absolute Path of the freshly written checkpoint.
    """
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    log_path = log_path if log_path is not None else (al / "orchestrator.log")

    data = load_loop_state(state_path)
    validate_loop_state(data)
    check_contract_version(data)

    status = data.get("status")
    if isinstance(status, str) and status.startswith("halted_"):
        raise HaltError(
            "halted_input_missing",
            (
                f"token-exhaustion recording refused: loop-state status "
                f"{status!r} is already a halt; cannot record token "
                f"exhaustion on top of an existing halt"
            ),
        )
    if status == AWAITING_HUMAN_FOR_PHASE_COMPLETE:
        raise HaltError(
            "halted_input_missing",
            (
                f"token-exhaustion recording refused: loop-state status "
                f"is {AWAITING_HUMAN_FOR_PHASE_COMPLETE!r}; the cycle is "
                f"terminally complete and has no work to continue"
            ),
        )
    if active_prompt_path not in CHECKPOINT_ACTIVE_PROMPT_PATHS:
        raise HaltError(
            "halted_input_missing",
            (
                f"token-exhaustion active_prompt_path "
                f"{active_prompt_path!r} is not one of "
                f"{sorted(CHECKPOINT_ACTIVE_PROMPT_PATHS)}"
            ),
        )

    checkpoint_path = write_checkpoint_entry(
        repo_root,
        phase=data["phase"],
        sub_phase=data["sub_phase"],
        task=data["task"],
        cycle_count=data["cycle_count"],
        status=status,
        approval_mode=data.get("approval_mode") or APPROVAL_MODE_REVIEW,
        awaiting_human_for=data.get("awaiting_human_for"),
        active_prompt_path=active_prompt_path,
        suspension_reason=TOKEN_EXHAUSTION_SUSPENSION_REASON,
        continuation_budget=continuation_budget,
        source_artifact_path=".agent-loop/loop-state.json",
        log_path=log_path,
    )

    save_loop_state(state_path, data, {
        "status": HALTED_TOKEN_EXHAUSTION,
        "awaiting_human_for": AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION,
    })

    rel = checkpoint_path.relative_to(repo_root).as_posix()
    _log_note(
        log_path,
        (
            f"token exhaustion recorded: continuation_budget="
            f"{continuation_budget} active_prompt_path="
            f"{active_prompt_path!r} checkpoint={rel!r}"
        ),
    )
    return checkpoint_path


def run_token_exhaustion_resume(repo_root: Path) -> int:
    """Resume an interrupted cycle that was suspended by token
    exhaustion.

    Refuses fail-closed unless:
      - loop-state.json is valid and the contract version is supported
      - loop-state `status` is `HALTED_TOKEN_EXHAUSTION`
      - an active checkpoint exists under `.agent-loop/memory/checkpoint/`
      - the active checkpoint validates schema (delegated to
        `_load_active_checkpoint` -> `read_checkpoint_entry`)
      - the active checkpoint's cycle-identity fields match the
        canonical loop-state (delegated to
        `_validate_token_exhaustion_checkpoint`)
      - the active checkpoint's `suspension_reason` is
        `"token_exhaustion"`
      - the active checkpoint's `continuation_budget` is `> 0`

    On success:
      - Writes a NEW checkpoint with `continuation_budget` = old - 1
        and an explicit `supersedes` reference to the prior active
        checkpoint, so the budget is consumed deterministically and
        the consumption is recorded on-disk.
      - Restores loop-state `status` and `awaiting_human_for` to the
        checkpoint's saved pre-suspension cycle values. The operator's
        next orchestrator invocation picks up the cycle from the
        restored status.
      - Logs a `token-exhaustion resume consumed:` audit note.
      - Returns 0.

    On refusal: returns 2. The initial "status is not the token-
    exhaustion halt" check routes through `_halt` (safe because no
    recovery point is destroyed). Every downstream refusal
    (no-checkpoint, malformed, mismatching, budget exhausted) leaves
    the saved `HALTED_TOKEN_EXHAUSTION` state intact - same recovery
    pattern as the Phase 5C mode-coherence and Phase 6E checkpoint
    refusals - so the operator can correct the underlying issue and
    re-run `resume` without losing the recovery point.
    """
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    log_path = al / "orchestrator.log"

    try:
        data = load_loop_state(state_path)
        validate_loop_state(data)
        check_contract_version(data)
    except HaltError as halt:
        return _halt(
            state_path, {} if "data" not in dir() else data, halt, log_path,
        )

    status = data.get("status")
    if status != HALTED_TOKEN_EXHAUSTION:
        return _halt(
            state_path, data,
            HaltError(
                "halted_input_missing",
                (
                    f"token-exhaustion resume requires loop-state.json "
                    f"status to be {HALTED_TOKEN_EXHAUSTION!r}; got "
                    f"{status!r}. Resume is only valid after a token-"
                    f"exhaustion event has been recorded."
                ),
            ),
            log_path,
        )

    def _refuse(reason_body: str) -> int:
        # Recovery-preserving refusal: stderr-print + log note + exit 2
        # WITHOUT routing through `_halt` so the saved
        # HALTED_TOKEN_EXHAUSTION state is not clobbered with
        # halted_input_missing. Same pattern as the Phase 5C
        # mode-coherence and Phase 6E checkpoint refusals.
        msg = f"token-exhaustion resume refused: {reason_body}"
        print(
            f"[orchestrator] TOKEN-EXHAUSTION RESUME REFUSED: {msg}",
            file=sys.stderr,
        )
        _log_note(log_path, msg)
        return 2

    try:
        checkpoint = _load_active_checkpoint(repo_root)
    except HaltError as halt:
        return _refuse(
            f"malformed or unrecognized active checkpoint: {halt.reason}"
        )
    if checkpoint is None:
        return _refuse(
            "no active checkpoint on disk; cannot continue without a "
            "checkpoint that records the suspended cycle context"
        )

    try:
        _validate_token_exhaustion_checkpoint(checkpoint, data)
    except HaltError as halt:
        return _refuse(
            f"checkpoint cycle identity does not match loop-state: "
            f"{halt.reason}"
        )

    if checkpoint["suspension_reason"] != TOKEN_EXHAUSTION_SUSPENSION_REASON:
        return _refuse(
            f"active checkpoint suspension_reason="
            f"{checkpoint['suspension_reason']!r} is not "
            f"{TOKEN_EXHAUSTION_SUSPENSION_REASON!r}; this resume path is "
            f"reserved for token-exhaustion checkpoints only"
        )

    budget = checkpoint["continuation_budget"]
    if budget <= 0:
        return _refuse(
            f"continuation_budget={budget} is exhausted; the Phase 6A "
            f"contract requires explicit human approval before further "
            f"continuation. Edit the operator workflow (e.g. record a "
            f"fresh token-exhaustion event with a non-zero budget, or "
            f"clear the halt manually) to recover."
        )

    # Phase 6F initial slice: dispatch is only safe for a narrow set of
    # interrupted stages where the orchestrator already has a
    # continuation entry that re-uses the same cycle_count. Statuses
    # outside that set are refused fail-closed BEFORE budget
    # consumption so the operator does not silently lose a continuation
    # slot to an unrecoverable saved state.
    restored_status = checkpoint["status"]
    if restored_status not in TOKEN_EXHAUSTION_SUPPORTED_RESUME_STATUSES:
        return _refuse(
            f"saved pre-suspension status {restored_status!r} is not in "
            f"the supported interrupted-stage set "
            f"{sorted(TOKEN_EXHAUSTION_SUPPORTED_RESUME_STATUSES)} for "
            f"this initial Phase 6F slice. The cycle cannot be resumed "
            f"end-to-end from that stage without a dedicated "
            f"continuation entry-point. The operator must intervene "
            f"(e.g. clear the halt manually, restart the active "
            f"sub-phase) rather than have the resume path silently "
            f"reissue the cycle."
        )

    # Resolve the active checkpoint's on-disk path so the new checkpoint
    # can record a deterministic `supersedes` reference. Mirrors
    # `_load_active_checkpoint`'s mtime-first selection.
    paths = list_checkpoint_entries(repo_root)
    active_path = max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name))
    supersedes_ref = active_path.relative_to(repo_root).as_posix()

    new_budget = budget - 1
    new_checkpoint_path = write_checkpoint_entry(
        repo_root,
        phase=checkpoint["phase"],
        sub_phase=checkpoint["sub_phase"],
        task=checkpoint["task"],
        cycle_count=checkpoint["cycle_count"],
        status=checkpoint["status"],
        approval_mode=checkpoint["approval_mode"],
        awaiting_human_for=checkpoint["awaiting_human_for"],
        active_prompt_path=checkpoint["active_prompt_path"],
        suspension_reason=TOKEN_EXHAUSTION_SUSPENSION_REASON,
        continuation_budget=new_budget,
        source_artifact_path=".agent-loop/loop-state.json",
        supersedes=supersedes_ref,
        log_path=log_path,
    )

    # Restore loop-state to the pre-suspension cycle vocabulary. The
    # halt is cleared; the dispatch below picks the cycle back up from
    # the restored status so the interrupted cycle actually continues
    # end-to-end (Issue 2 from the Phase 6F review) instead of just
    # leaving the operator with a restored-but-still-stuck status.
    data = save_loop_state(state_path, data, {
        "status": checkpoint["status"],
        "awaiting_human_for": checkpoint["awaiting_human_for"],
    })

    rel = new_checkpoint_path.relative_to(repo_root).as_posix()
    _log_note(
        log_path,
        (
            f"token-exhaustion resume consumed: continuation_budget "
            f"{budget} -> {new_budget}; new checkpoint={rel!r}; "
            f"restored status={checkpoint['status']!r}; "
            f"restored awaiting_human_for="
            f"{checkpoint['awaiting_human_for']!r}"
        ),
    )

    # Dispatch to the matching continuation entry-point. Mirrors the
    # end-of-function dispatch in `run_strict_resume`: the resume
    # caller is responsible for getting the cycle's work moving again,
    # not just rewriting a status field. Both supported entries skip
    # the cycle_count increment that lives in `run_normal_cycle`'s own
    # pre-amble, so the resumed work is the SAME cycle the suspension
    # interrupted (no cycle_count drift, no Phase 5 gate skipped).
    if restored_status == "awaiting_claude_implementation":
        return _run_normal_cycle_from_increment(repo_root, data, log_path)
    # restored_status == "awaiting_codex_review"; mirror the strict-
    # resume HALTED_PRE_CODEX_REVIEW_NORMAL pattern: write a
    # transitional `evidence_capture` (non-halt, signals "evidence
    # done, about to review") so the dispatched continuation observes
    # a meaningful intermediate state in the log.
    data = save_loop_state(state_path, data, {
        "status": "evidence_capture",
        "awaiting_human_for": None,
    })
    return _run_normal_cycle_codex_review_step(repo_root, data, log_path)


# Phase 6G - Automatic Continuation Chaining Initial Slice.
#
# Builds directly on the shipped Phase 6F single-hop
# `run_token_exhaustion_resume(...)`. The chain primitive performs up to
# AUTO_CONTINUE_MAX_HOPS hops of the existing single-hop resume in a
# bounded loop. Each hop:
#   1. consumes one continuation_budget unit (via the existing 6F
#      writer)
#   2. dispatches the cycle's matching continuation entry-point (via
#      the existing 6F dispatch)
#   3. inspects the post-dispatch loop-state to decide whether to
#      continue the chain
#
# The chain control flow:
#   - rc != 0 from any hop                    -> propagate rc, stop chain
#   - rc == 0 AND status != HALTED_TOKEN_EXHAUSTION
#                                             -> natural termination, rc=0
#   - rc == 0 AND status == HALTED_TOKEN_EXHAUSTION
#                                             -> the dispatched continuation
#                                                re-entered the token-
#                                                exhaustion halt (a fresh
#                                                exhaustion was recorded
#                                                during it); chain another
#                                                hop within the cap
#   - hop counter reaches AUTO_CONTINUE_MAX_HOPS
#                                             -> refuse fail-closed, preserve
#                                                the saved halt
#
# Bounding policy:
#   - per-checkpoint continuation_budget (the existing Phase 6F bound)
#     is the primary policy bound; each hop consumes 1 unit, so a
#     budget of N self-terminates the chain after at most N hops via
#     the existing 6F exhausted-budget refusal
#   - AUTO_CONTINUE_MAX_HOPS is an independent defense-in-depth bound
#     in case a fresh exhaustion event mid-chain resets the budget; it
#     gives the operator a clear "the cycle is not making progress"
#     signal even if the budget arithmetic somehow allows unbounded
#     chaining
#
# Out of scope for this initial slice (deferred per Phase 6G prompt):
#   - phase-boundary memory distillation
#   - repeated-failure memory synthesis
#   - broader optional context-file loading
#   - widening Phase 5 autonomy or bypassing human gates
#   - automatic orchestrator-side DETECTION of token exhaustion
#     (`record_token_exhaustion(...)` remains the explicit recording
#     surface; the chain only handles the case where the dispatched
#     continuation re-records exhaustion via that surface)

AUTO_CONTINUE_MAX_HOPS = 4


def run_auto_continue(repo_root: Path) -> int:
    """Phase 6G: bounded automatic continuation chaining.

    Repeatedly applies the Phase 6F single-hop token-exhaustion resume
    while the persisted halt status is `HALTED_TOKEN_EXHAUSTION`, until
    one of these stop conditions:

      - a hop's return code is non-zero (refusal or non-token halt
        inside the dispatched continuation): propagate the rc unchanged
      - the cycle has cleared the token-exhaustion halt after a
        successful hop (no fresh exhaustion event was recorded during
        the dispatched continuation): return 0
      - `AUTO_CONTINUE_MAX_HOPS` hops have run without natural
        termination: refuse fail-closed (the chain bound is a defense-
        in-depth cap independent of the per-checkpoint budget)

    Refusal handling:
      - the initial "loop-state status is not `HALTED_TOKEN_EXHAUSTION`"
        check uses the recovery-preserving stderr+log+exit-2 pattern
        (NOT `_halt`) so an operator who runs `auto-continue` against a
        strict-gate halt by mistake does not clobber the strict-gate
        recovery point - this is intentionally MORE conservative than
        the existing Phase 6F single-hop resume, which clobbers because
        cmd_resume routes the status before that primitive sees it
      - all downstream refusals come from `run_token_exhaustion_resume`
        which preserves the saved `HALTED_TOKEN_EXHAUSTION` recovery
        point; this function simply propagates their rc

    The chain decision is made on the persisted halt VOCABULARY after
    each hop (`loop-state.status == HALTED_TOKEN_EXHAUSTION`), not the
    rc. The rc tells us "did this hop succeed end-to-end"; the
    post-hop status tells us "is there another exhaustion event ready
    to be continued from."
    """
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    log_path = al / "orchestrator.log"

    try:
        data = load_loop_state(state_path)
        validate_loop_state(data)
        check_contract_version(data)
    except HaltError as halt:
        return _halt(
            state_path, {} if "data" not in dir() else data, halt, log_path,
        )

    def _refuse_no_clobber(reason_body: str) -> int:
        # Recovery-preserving refusal: stderr-print + log note + exit 2
        # WITHOUT routing through `_halt` so any pre-existing halt on
        # disk (in particular a Phase 5C strict-gate halt that the
        # operator mistakenly tried to auto-continue) keeps its
        # recovery point intact. Mirrors the Phase 5C / 6E / 6F refusal
        # pattern, applied here at the chain entry-point too.
        msg = f"auto-continue refused: {reason_body}"
        print(
            f"[orchestrator] AUTO-CONTINUE REFUSED: {msg}",
            file=sys.stderr,
        )
        _log_note(log_path, msg)
        return 2

    initial_status = data.get("status")
    if initial_status != HALTED_TOKEN_EXHAUSTION:
        return _refuse_no_clobber(
            f"loop-state.json status is {initial_status!r}; auto-continue "
            f"requires {HALTED_TOKEN_EXHAUSTION!r}. Use the standard "
            f"`resume` subcommand for strict-gate halts; `auto-continue` "
            f"is reserved for token-exhaustion chaining. The saved halt "
            f"(if any) is preserved for inspection."
        )

    _log_note(
        log_path,
        (
            f"auto-continue chain start: max_hops={AUTO_CONTINUE_MAX_HOPS}; "
            f"phase={data.get('phase')!r} sub_phase={data.get('sub_phase')!r} "
            f"cycle_count={data.get('cycle_count')}"
        ),
    )

    for hop in range(1, AUTO_CONTINUE_MAX_HOPS + 1):
        _log_note(log_path, f"auto-continue chain hop {hop} begin")
        rc = run_token_exhaustion_resume(repo_root)
        if rc != 0:
            # Either the hop refused (budget exhausted, malformed
            # checkpoint, unsupported saved status, etc.) or the
            # dispatched continuation hit a non-token halt or terminal
            # halt (FAILED_REQUIRES_HUMAN, max_cycles, evidence refusal,
            # etc.). Both cases stop the chain; propagate the rc so the
            # operator sees the actual halt vocabulary.
            _log_note(
                log_path,
                f"auto-continue chain stopped at hop {hop}: rc={rc}",
            )
            return rc
        # rc == 0: the hop succeeded end-to-end. Inspect loop-state to
        # see whether the dispatched continuation re-entered the token-
        # exhaustion halt (a fresh `record_token_exhaustion(...)` call
        # during the continuation) or cleanly progressed past it.
        #
        # Run the same structural + contract-version checks the chain
        # entry ran. The dispatched continuation owns its own
        # writes through save_loop_state, but a hop that returns rc=0
        # with loadable-but-invalid loop-state on disk (e.g. a missing
        # required key or an unrecognized contract_version mutated in
        # mid-hop) must NOT be silently logged as a successful
        # completion and must NOT advance into another hop from
        # malformed canonical state. Routing the refusal through `_halt`
        # mirrors the chain-entry treatment of the same checks; the
        # invalid state is best-effort overwritten with the
        # halt_input_missing / halt_contract_version_mismatch
        # vocabulary so the operator sees the structural reason rather
        # than a misleading chain-success record.
        try:
            data = load_loop_state(state_path)
            validate_loop_state(data)
            check_contract_version(data)
        except HaltError as halt:
            return _halt(
                state_path, {} if "data" not in dir() else data, halt,
                log_path,
            )
        next_status = data.get("status")
        if next_status != HALTED_TOKEN_EXHAUSTION:
            _log_note(
                log_path,
                (
                    f"auto-continue chain completed after {hop} hop(s); "
                    f"final status={next_status!r}"
                ),
            )
            return 0
        # Still HALTED_TOKEN_EXHAUSTION: the dispatched continuation
        # re-recorded a fresh exhaustion event. Loop into another hop
        # (the next hop's call to `run_token_exhaustion_resume` will
        # validate the new active checkpoint against its own contract
        # before consuming another budget unit).

    # Reached AUTO_CONTINUE_MAX_HOPS without natural termination. The
    # defense-in-depth cap fires; refuse fail-closed and leave the
    # saved HALTED_TOKEN_EXHAUSTION halt on disk for the operator.
    return _refuse_no_clobber(
        f"chain reached the AUTO_CONTINUE_MAX_HOPS={AUTO_CONTINUE_MAX_HOPS} "
        f"defense-in-depth bound without naturally terminating; refusing "
        f"further automatic continuation. The operator must intervene "
        f"(inspect the checkpoint chain or clear the halt manually) "
        f"rather than let the chain expand without bound."
    )


# Phase 6H - Bounded Continuation Prompt Construction Initial Slice.
#
# Builds on the shipped 6B (storage), 6C (advisory-only retrieval), 6D
# (checkpoint storage), 6E (checkpoint resume), 6F (token-exhaustion
# continuation), and 6G (auto-continuation chaining) primitives. The new
# `build_continuation_prompt_context(...)` surface assembles a
# structured CONTEXT DICT a later continuation runtime can serialize to
# a prompt. The dict is sourced from canonical artifacts (loop-state +
# the active Phase 6F/6G checkpoint) plus BOUNDED evidence excerpts and
# advisory-only memory entries, so a continuation cannot silently
# expand into an unbounded repo dump.
#
# Refusal modes (all `halted_input_missing` unless noted):
#   - missing / malformed `loop-state.json`
#   - unsupported `contract_version`
#     (`halted_contract_version_mismatch`)
#   - loop-state `status` is not in
#     `CONTINUATION_CONTEXT_ELIGIBLE_HALT_STATUSES` (only the Phase 6F
#     token-exhaustion halt is supported in this initial slice; strict-
#     gate halts already have the existing `resume` path and do not
#     require bounded prompt construction)
#   - no active checkpoint on disk
#   - checkpoint schema / suspension_reason / cycle-identity mismatch
#     (delegated to existing 6F validators)
#   - memory_entry_limit out of the 6C bounds (delegated to
#     `_validate_retrieval_limit`)
#   - evidence_byte_limit not a positive int, or above
#     `CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT`
#
# Out of scope for this initial slice (deferred per the 6H prompt):
#   - phase-boundary memory distillation or repeated-failure synthesis
#   - broader optional context-file loading (beyond the EVIDENCE_FILES
#     set; no arbitrary repo file reads)
#   - prompt SERIALIZATION (the slice returns a dict; turning it into a
#     prompt string is a later runtime layer's job)
#   - widening Phase 5 autonomy or bypassing human gates
#
# Canonical precedence: every returned dict carries
# `CONTINUATION_CONTEXT_CANONICAL_PRECEDENCE_NOTE` so a downstream
# consumer cannot accidentally treat advisory memory as canonical
# state.

CONTINUATION_CONTEXT_SIGNAL_VERSION = "phase-6h-v1"
CONTINUATION_CONTEXT_DEFAULT_MEMORY_LIMIT = MEMORY_RETRIEVAL_DEFAULT_LIMIT
CONTINUATION_CONTEXT_DEFAULT_EVIDENCE_BYTE_LIMIT = 4096
CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT = 65536
# Initial slice: only the Phase 6F / 6G token-exhaustion halt has the
# checkpoint vocabulary the context builder relies on. Strict-gate halts
# already have their own `resume` path. Widening this set is a later-
# slice concern (each new halt category needs its own checkpoint-derived
# context surface).
CONTINUATION_CONTEXT_ELIGIBLE_HALT_STATUSES = frozenset({
    HALTED_TOKEN_EXHAUSTION,
})
# Advisory memory retrieval intentionally excludes the `checkpoint`
# category because the active checkpoint is already surfaced under the
# dedicated `checkpoint` key of the returned payload; including it in
# `memory_advisory` would duplicate the data and blur the canonical /
# advisory boundary.
CONTINUATION_CONTEXT_MEMORY_CATEGORIES = frozenset(
    MEMORY_CATEGORIES - {MEMORY_CATEGORY_CHECKPOINT}
)
CONTINUATION_CONTEXT_OUTPUT_REL = ".agent-loop/continuation-context.json"
CONTINUATION_CONTEXT_CANONICAL_PRECEDENCE_NOTE = (
    "Canonical task and loop-state artifacts (TASK.md, "
    ".agent-loop/current-task.md, .agent-loop/current-phase.md, "
    ".agent-loop/loop-state.json) and the active checkpoint are the "
    "source of truth. The `memory_advisory` entries are advisory only "
    "per the Phase 6A / 6C contract and must NOT override canonical "
    "state or any Phase 5 approval-mode / strict-gate decision. "
    "Evidence excerpts are bounded; consult the named on-disk path for "
    "the full content."
)


def _validate_evidence_byte_limit(value) -> None:
    """Refuse fail-closed on an out-of-bounds evidence byte limit.

    Mirrors `_validate_retrieval_limit`'s shape: bool rejected (bool is
    int in Python; accepting True/False would silently coerce to 1/0),
    non-int rejected, non-positive rejected, above the safety cap
    rejected.
    """
    if isinstance(value, bool):
        raise HaltError(
            "halted_input_missing",
            (
                f"continuation-context evidence_byte_limit must be a "
                f"positive int, not bool; got {value!r}"
            ),
        )
    if not isinstance(value, int):
        raise HaltError(
            "halted_input_missing",
            (
                f"continuation-context evidence_byte_limit must be an "
                f"int; got {type(value).__name__}={value!r}"
            ),
        )
    if value <= 0:
        raise HaltError(
            "halted_input_missing",
            (
                f"continuation-context evidence_byte_limit must be "
                f"positive; got {value!r}"
            ),
        )
    if value > CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT:
        raise HaltError(
            "halted_input_missing",
            (
                f"continuation-context evidence_byte_limit {value!r} "
                f"exceeds CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT="
                f"{CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT}; the "
                f"safety cap prevents a continuation from silently "
                f"expanding into an unbounded repo dump"
            ),
        )


def _collect_bounded_evidence(repo_root: Path, byte_limit: int) -> dict:
    """Return a dict of relative path -> excerpt metadata for each
    `EVIDENCE_FILES` entry. Each entry carries `byte_size_on_disk`,
    `excerpt`, `excerpt_byte_size`, and `truncated`. Missing files are
    surfaced with `absent: True` so the continuation runtime sees the
    same absence the orchestrator would see, not a silent omission.

    An evidence file that exists but cannot be read (any `OSError`
    from `Path.read_bytes`) refuses fail-closed via `HaltError` rather
    than producing a success payload with an undocumented schema
    branch. The Phase 6H continuation-context schema only documents
    `absent: True` for missing files and the full metadata block for
    readable files; any other on-disk state is a structural input
    failure the operator must address before the context can be built.
    """
    out: dict = {}
    for rel in EVIDENCE_FILES:
        p = repo_root / rel
        if not p.exists():
            out[rel] = {"absent": True}
            continue
        try:
            raw = p.read_bytes()
        except OSError as exc:
            raise HaltError(
                "halted_input_missing",
                (
                    f"continuation context construction refused: "
                    f"evidence file {rel!r} exists but is unreadable "
                    f"({type(exc).__name__}: {exc}); resolve the read "
                    f"failure before rebuilding the continuation context"
                ),
            )
        total = len(raw)
        excerpt_bytes = raw[:byte_limit]
        # Decode best-effort as UTF-8 (evidence files are text). Replace
        # malformed bytes so a binary or mis-encoded file does not
        # crash the builder.
        excerpt_text = excerpt_bytes.decode("utf-8", errors="replace")
        out[rel] = {
            "absent": False,
            "byte_size_on_disk": total,
            "excerpt": excerpt_text,
            "excerpt_byte_size": len(excerpt_bytes),
            "truncated": total > byte_limit,
        }
    return out


def build_continuation_prompt_context(
    repo_root: Path,
    *,
    memory_entry_limit: Optional[int] = None,
    evidence_byte_limit: Optional[int] = None,
    log_path: Optional[Path] = None,
) -> dict:
    """Assemble a structured continuation prompt/context dict.

    Returns a dict keyed by:
      - `context_signal_version`: schema version tag the consumer
        validates against
      - `built_at`: UTC ISO timestamp of construction
      - `canonical_state`: the canonical loop-state subset
        (phase / sub_phase / task / cycle_count / approval_mode /
        halt_status / awaiting_human_for)
      - `checkpoint`: the active Phase 6F/6G token-exhaustion
        checkpoint subset (suspension_reason / active_prompt_path /
        continuation_budget / pre-suspension status / pre-suspension
        awaiting_human_for / source_artifact_path / created_at)
      - `evidence`: a dict of EVIDENCE_FILES rel path -> bounded
        excerpt metadata (`byte_size_on_disk`, `excerpt`,
        `excerpt_byte_size`, `truncated`, or `absent: True`)
      - `memory_advisory`: a list of Phase 6C-retrieved entries each
        already carrying `advisory_only = True`; bounded by
        `memory_entry_limit`
      - `memory_truncated_at_limit`: True if the retrieval matched
        MORE entries than the limit allowed back; otherwise False
      - `memory_limit_applied`: the limit that was actually used (the
        caller's value or the default)
      - `evidence_byte_limit_applied`: same for evidence
      - `canonical_precedence_note`: the explicit reminder that
        canonical artifacts win over advisory memory

    Raises `HaltError` on any refusal mode. The caller (the CLI
    handler) routes refusals through `_halt`.

    Args:
      repo_root: workspace root.
      memory_entry_limit: optional override for the Phase 6C retrieval
        limit. Defaults to `CONTINUATION_CONTEXT_DEFAULT_MEMORY_LIMIT`.
      evidence_byte_limit: optional override for the per-file evidence
        excerpt byte cap. Defaults to
        `CONTINUATION_CONTEXT_DEFAULT_EVIDENCE_BYTE_LIMIT`.
      log_path: optional orchestrator-log path. When supplied, a single
        `continuation context built:` audit note is appended.
    """
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"

    # 1. Load + validate loop-state with the same structural / contract
    #    checks every Phase 6 surface uses.
    data = load_loop_state(state_path)
    validate_loop_state(data)
    check_contract_version(data)

    # 2. Eligibility: only the Phase 6F token-exhaustion halt has the
    #    checkpoint vocabulary this builder consumes. Other halts (or
    #    a non-halt state) must be refused fail-closed; otherwise the
    #    builder would be advertising a continuation context for a
    #    halt that has no continuation semantics.
    status = data.get("status")
    if status not in CONTINUATION_CONTEXT_ELIGIBLE_HALT_STATUSES:
        raise HaltError(
            "halted_input_missing",
            (
                f"continuation context construction refused: loop-state "
                f"status {status!r} is not in the eligible halt set "
                f"{sorted(CONTINUATION_CONTEXT_ELIGIBLE_HALT_STATUSES)}. "
                f"This initial Phase 6H slice only constructs continuation "
                f"context for token-exhaustion halts; other halt categories "
                f"use their existing resume paths."
            ),
        )

    # 3. Active checkpoint must exist and validate against the Phase
    #    6F cycle-identity + suspension_reason contract. Delegated to
    #    the existing 6F validators so the same refusal vocabulary the
    #    resume path uses applies here.
    checkpoint = _load_active_checkpoint(repo_root)
    if checkpoint is None:
        raise HaltError(
            "halted_input_missing",
            (
                "continuation context construction refused: no active "
                "checkpoint on disk; cannot build continuation context "
                "without a checkpoint that records the suspended cycle"
            ),
        )
    _validate_token_exhaustion_checkpoint(checkpoint, data)
    if checkpoint["suspension_reason"] != TOKEN_EXHAUSTION_SUSPENSION_REASON:
        raise HaltError(
            "halted_input_missing",
            (
                f"continuation context construction refused: active "
                f"checkpoint suspension_reason="
                f"{checkpoint['suspension_reason']!r} is not "
                f"{TOKEN_EXHAUSTION_SUSPENSION_REASON!r}; this initial "
                f"slice only handles token-exhaustion continuation"
            ),
        )

    # 4. Bound the memory retrieval and evidence inclusion. Both are
    #    validated using the same helpers the underlying primitives
    #    use, so an out-of-bounds limit refuses at the boundary rather
    #    than inside `retrieve_memory_entries`.
    mem_limit = (
        memory_entry_limit
        if memory_entry_limit is not None
        else CONTINUATION_CONTEXT_DEFAULT_MEMORY_LIMIT
    )
    _validate_retrieval_limit(mem_limit)
    ev_limit = (
        evidence_byte_limit
        if evidence_byte_limit is not None
        else CONTINUATION_CONTEXT_DEFAULT_EVIDENCE_BYTE_LIMIT
    )
    _validate_evidence_byte_limit(ev_limit)

    # 5. Retrieve advisory memory through the shipped 6C primitive.
    #    Each returned entry already carries the structural
    #    `advisory_only` marker. The retrieval primitive refuses
    #    fail-closed on its own contract violations (malformed
    #    entries, unknown category filter, out-of-bound limit) which
    #    we propagate via HaltError unchanged.
    memory_entries = retrieve_memory_entries(
        repo_root,
        phase=data["phase"],
        sub_phase=data.get("sub_phase"),
        categories=CONTINUATION_CONTEXT_MEMORY_CATEGORIES,
        limit=mem_limit,
    )

    # Count actual matches without applying any limit so truncation
    # detection is honest even when the caller's limit equals
    # MEMORY_RETRIEVAL_MAX_LIMIT. A previous version re-ran
    # retrieve_memory_entries with limit=MEMORY_RETRIEVAL_MAX_LIMIT
    # and compared lengths, but if the caller already used that limit
    # the second call also capped at MEMORY_RETRIEVAL_MAX_LIMIT and
    # reported `memory_truncated_at_limit = False` even when
    # additional matching entries existed on disk. Walking the
    # entries directly with the same scope filters the retrieval
    # primitive uses (category-in-set + phase + sub_phase) gives a
    # truthful count regardless of the caller's chosen limit. The
    # walk re-validates each entry via read_memory_entry so any
    # malformed on-disk entry still surfaces as the same HaltError
    # the retrieval primitive would raise.
    total_matched = 0
    for entry_path in list_memory_entries(repo_root):
        payload = read_memory_entry(entry_path)
        if payload["category"] not in CONTINUATION_CONTEXT_MEMORY_CATEGORIES:
            continue
        if not _is_entry_in_active_scope(
            payload, phase=data["phase"], sub_phase=data.get("sub_phase"),
        ):
            continue
        total_matched += 1
    memory_truncated = total_matched > len(memory_entries)

    # 6. Bounded evidence excerpts.
    evidence = _collect_bounded_evidence(repo_root, ev_limit)

    # 7. Resolve the active checkpoint's on-disk path (mtime-first
    #    selection mirrors `_load_active_checkpoint`) so the dict
    #    records exactly which file was the source.
    paths = list_checkpoint_entries(repo_root)
    active_path = max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name))
    checkpoint_rel = active_path.relative_to(repo_root).as_posix()

    payload = {
        "context_signal_version": CONTINUATION_CONTEXT_SIGNAL_VERSION,
        "built_at": _utc_iso_now(),
        "canonical_state": {
            "phase": data["phase"],
            "sub_phase": data.get("sub_phase"),
            "task": data["task"],
            "cycle_count": data["cycle_count"],
            "approval_mode": data.get("approval_mode"),
            "halt_status": data.get("status"),
            "awaiting_human_for": data.get("awaiting_human_for"),
        },
        "checkpoint": {
            "source_path": checkpoint_rel,
            "suspension_reason": checkpoint["suspension_reason"],
            "active_prompt_path": checkpoint["active_prompt_path"],
            "continuation_budget": checkpoint["continuation_budget"],
            "pre_suspension_status": checkpoint["status"],
            "pre_suspension_awaiting_human_for": (
                checkpoint["awaiting_human_for"]
            ),
            "source_artifact_path": checkpoint.get("source_artifact_path"),
            "created_at": checkpoint.get("created_at"),
        },
        "evidence": evidence,
        "evidence_byte_limit_applied": ev_limit,
        "memory_advisory": memory_entries,
        "memory_limit_applied": mem_limit,
        "memory_truncated_at_limit": memory_truncated,
        "canonical_precedence_note": (
            CONTINUATION_CONTEXT_CANONICAL_PRECEDENCE_NOTE
        ),
    }

    if log_path is not None:
        # Compact one-line audit note. The note records WHICH file the
        # active checkpoint resolved to, the bounds applied, and the
        # counts so the construction is reconstructable from
        # `.agent-loop/orchestrator.log` alone.
        present_evidence = sum(
            1 for v in evidence.values() if not v.get("absent")
        )
        _log_note(
            log_path,
            (
                f"continuation context built: signal_version="
                f"{CONTINUATION_CONTEXT_SIGNAL_VERSION!r} "
                f"checkpoint={checkpoint_rel!r} "
                f"memory_limit={mem_limit} returned={len(memory_entries)} "
                f"truncated={memory_truncated} "
                f"evidence_byte_limit={ev_limit} "
                f"evidence_present={present_evidence}/{len(EVIDENCE_FILES)}"
            ),
        )

    return payload


def _halt(state_path: Path, current: dict, halt: HaltError, log_path: Optional[Path]) -> int:
    print(
        f"[orchestrator] HALT {halt.status}: {halt.reason}",
        file=sys.stderr,
    )
    try:
        save_loop_state(state_path, current, {"status": halt.status})
    except Exception as exc:
        print(
            f"[orchestrator] additionally failed to persist halt status: {exc}",
            file=sys.stderr,
        )
    _log_note(log_path, f"HALT {halt.status}: {halt.reason}")
    return 2


def _fire_strict_gate(
    state_path: Path,
    current: dict,
    *,
    halt_status: str,
    awaiting_human_for: str,
    reason: str,
    log_path: Optional[Path],
) -> int:
    """Persist a Phase 5C strict-mode human gate and exit cleanly with code 2.

    Records the gate in BOTH `status` (a contract `halted_awaiting_human_*`
    value the resume command keys off of) and `awaiting_human_for` (the
    Phase 5A contract gate-name vocabulary), in a single atomic
    save_loop_state call so the gate cannot be observed half-set. The
    orchestrator process exits; the human resumes via the `resume`
    subcommand once they have approved the paused step.

    This is structurally a halt, but it is NOT a `HaltError` because the
    intent is "wait for a human," not "fail." Using a distinct helper
    keeps `_halt`'s "this is a structural failure" semantics intact and
    makes strict-mode pauses visibly different in the log.
    """
    print(
        f"[orchestrator] STRICT GATE {halt_status} ({awaiting_human_for}): "
        f"{reason}",
        file=sys.stderr,
    )
    try:
        save_loop_state(
            state_path, current,
            {"status": halt_status, "awaiting_human_for": awaiting_human_for},
        )
    except Exception as exc:
        print(
            f"[orchestrator] additionally failed to persist strict gate: {exc}",
            file=sys.stderr,
        )
    _log_note(
        log_path,
        (
            f"strict gate {halt_status} awaiting_human_for={awaiting_human_for}: "
            f"{reason}"
        ),
    )
    return 2


def _log_autonomous_bypass(
    log_path: Optional[Path], *, gate: str, where: str,
) -> None:
    """Phase 5D auditable bypass note.

    The narrow `autonomous` runtime path takes the same code paths as
    `review` at the four strict-gate sites (no human pause), but the
    contract requires the mode behavior to be "auditable from repo
    artifacts and runtime state; do not hide mode behavior only in
    transient control flow." This helper makes the bypass observable in
    `.agent-loop/orchestrator.log` so a reader can reconstruct exactly
    which gates were skipped because the cycle was in autonomous mode.
    The line is informational only; the orchestrator never writes a
    `halted_*` status here and never sets `awaiting_human_for`.
    """
    _log_note(
        log_path,
        (
            f"autonomous mode: bypassing {gate} gate at {where}; "
            f"continuing without human pause"
        ),
    )


POST_APPROVAL_PLANNER_EXCEPTION_CODE = -1


def _invoke_post_approval_planner(repo_root: Path, log_path: Optional[Path]) -> int:
    """Invoke the standalone planner after a terminal approval.

    Phase 4D integrates the planner only into the post-approval handoff.
    Phase 4E routes that invocation through the planner-adapter seam
    (`make_planner_adapter().run`) instead of calling `run_planner`
    directly; the default adapter preserves today's behavior, so the
    containment guarantees below are unchanged. The invocation is fully
    contained so it can never change the already-persisted terminal
    orchestrator outcome:

      - a normal planner return code (0 on success, 2 on refusal) is
        logged as a `note:` line to .agent-loop/orchestrator.log; the
        orchestrator still returns 0 after the terminal approval
      - any unexpected exception from planner code is caught and logged
        as a `note:` line; it is NOT re-raised, so an internal planner
        bug cannot crash or halt the already-approved cycle. The
        sentinel `POST_APPROVAL_PLANNER_EXCEPTION_CODE` is returned so a
        caller (and tests) can distinguish "planner raised" from a
        normal exit code.

    The broad `except Exception` is deliberate: this is a fail-closed
    containment boundary at an integration seam, and the whole point is
    to absorb ANY planner-internal failure. `KeyboardInterrupt` /
    `SystemExit` derive from `BaseException`, not `Exception`, so the
    orchestrator's explicit-human-stop halt path is preserved.
    """
    try:
        rc = make_planner_adapter().run(repo_root)
    except Exception as exc:  # noqa: BLE001 - deliberate containment boundary
        _log_note(
            log_path,
            (
                "note: post-approval planner raised an unexpected exception "
                "after APPROVED_FOR_HUMAN_REVIEW; the already-approved cycle "
                f"is unaffected. exception={type(exc).__name__}: {exc}"
            ),
        )
        return POST_APPROVAL_PLANNER_EXCEPTION_CODE
    _log_note(
        log_path,
        (
            "note: post-approval planner invoked after "
            f"APPROVED_FOR_HUMAN_REVIEW; planner_exit_code={rc}"
        ),
    )
    return rc


def run_normal_cycle(repo_root: Path) -> int:
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    prompt_path = al / "claude-prompt.md"
    log_path = al / "orchestrator.log"

    # 1. Load + structurally validate loop-state.json before doing anything.
    try:
        data = load_loop_state(state_path)
        validate_loop_state(data)
        check_contract_version(data)
    except HaltError as halt:
        # We may have an invalid `data` here, so pass {} to avoid clobbering.
        return _halt(state_path, {} if "data" not in dir() else data, halt, log_path)

    # 2. Record this orchestrator's version (allowed write). Phase 5B:
    #    also default `approval_mode` to "review" and ensure
    #    `awaiting_human_for` is null at cycle start when those Phase 5A
    #    fields are not yet present on the loaded state. This keeps
    #    pre-Phase-5 state files working while satisfying the contract's
    #    "newly initialized Phase 5+ runtime state defaults to review"
    #    rule on the first cycle after upgrade.
    runtime_updates: dict = {"orchestrator_version": ORCHESTRATOR_VERSION}
    if data.get("approval_mode") in (None, ""):
        runtime_updates["approval_mode"] = DEFAULT_APPROVAL_MODE
    if "awaiting_human_for" not in data:
        runtime_updates["awaiting_human_for"] = None
    data = save_loop_state(state_path, data, runtime_updates)

    # 2a. Phase 5B: a new normal cycle starts with a fresh prompt
    #     issuance, so any prior `.agent-loop/claude-done.json` is stale
    #     and must be cleared before review can begin again. This is
    #     best-effort (the file may not exist).
    clear_claude_done(repo_root)

    # 3. Validate the active prompt exists and is non-empty.
    try:
        validate_claude_prompt_present(prompt_path)
    except HaltError as halt:
        return _halt(state_path, data, halt, log_path)

    # 3a. Enforce the contract's normal-cycle start precondition: status
    #     must be a ready-to-start value. The orchestrator refuses to
    #     start a cycle from an in-flight, halted, or post-verdict state.
    #     Resetting `status` to a ready value is a human / Codex action.
    current_status = data.get("status")
    if current_status not in ALLOWED_NORMAL_CYCLE_START_STATUSES:
        return _halt(
            state_path, data,
            HaltError(
                "halted_input_missing",
                f"loop-state.json status is {current_status!r}; "
                f"normal cycle requires one of "
                f"{sorted(ALLOWED_NORMAL_CYCLE_START_STATUSES)}. "
                f"Reset status (Codex- or human-owned) before re-running.",
            ),
            log_path,
        )

    # 3b. Phase 5C strict-mode gate: under `strict`, the loop must pause
    #     for explicit human approval BEFORE dispatching a new
    #     implementation prompt. `review` (the default) skips this gate.
    #     Phase 5D: `autonomous` also skips the gate but logs an
    #     auditable bypass note so the mode is observable from
    #     orchestrator.log rather than hidden in transient control flow.
    #     The gate persists the named `awaiting_human_for =
    #     "pre_claude_prompt"` plus a contract `halted_awaiting_human_*`
    #     status and exits cleanly (code 2); the human resumes via the
    #     `resume` subcommand, which dispatches to
    #     `_run_normal_cycle_from_increment` (so the threshold check and
    #     cycle_count increment happen on resume, exactly once).
    approval_mode = data.get("approval_mode")
    if approval_mode == APPROVAL_MODE_STRICT:
        return _fire_strict_gate(
            state_path, data,
            halt_status=HALTED_PRE_CLAUDE_PROMPT,
            awaiting_human_for=AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
            reason=(
                "strict mode: explicit human approval required before "
                "dispatching a new implementation prompt to Claude"
            ),
            log_path=log_path,
        )
    if approval_mode == APPROVAL_MODE_AUTONOMOUS:
        _log_autonomous_bypass(
            log_path,
            gate=AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
            where="run_normal_cycle entry",
        )

    return _run_normal_cycle_from_increment(repo_root, data, log_path)


def _run_normal_cycle_from_increment(
    repo_root: Path, data: dict, log_path: Path,
) -> int:
    """Continuation: threshold check, cycle_count increment, Claude
    invocation, summary validation, evidence capture, claude-done.json
    write, then the Codex-review step. Reached either from
    `run_normal_cycle` (the human is not in strict mode, or strict mode
    was satisfied at the entry-point pre_claude_prompt gate) or from the
    `resume` subcommand after the human approves the pre_claude_prompt
    gate. Factored so resume does not re-fire the same gate it just
    cleared, and so the threshold/increment writes happen exactly once
    per cycle regardless of which entry path was taken.
    """
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    prompt_path = al / "claude-prompt.md"
    summary_path = al / "claude-summary.md"

    # 4. Check the cycle counter before incrementing.
    if data["cycle_count"] + 1 > data["max_cycles"]:
        return _halt(
            state_path, data,
            HaltError(
                "halted_max_cycles_reached",
                f"cycle_count+1 ({data['cycle_count'] + 1}) would exceed "
                f"max_cycles ({data['max_cycles']}); human must raise the "
                f"threshold or activate a new sub-phase",
            ),
            log_path,
        )

    # 5. Increment cycle_count and signal Claude is implementing.
    data = save_loop_state(state_path, data, {
        "cycle_count": data["cycle_count"] + 1,
        "status": "claude_implementing",
    })

    # 6. Invoke Claude adapter boundary (subprocess when configured,
    #    manual-handoff fallback otherwise).
    claude_adapter = make_claude_adapter()
    result = claude_adapter.invoke(prompt_path, summary_path)
    if result.model_id is None:
        # Contract: a Claude adapter that cannot resolve a model id is a
        # halt (halted_input_missing), per the "Failure modes worth naming"
        # subsection.
        return _halt(
            state_path, data,
            HaltError(
                "halted_input_missing",
                "Claude adapter did not resolve a model_id "
                "(no claude-summary.md or aborted handoff)",
            ),
            log_path,
        )
    data = save_loop_state(state_path, data, {"claude_version": result.model_id})

    # 7. Validate Claude's summary structurally.
    try:
        validate_claude_summary(summary_path, data["phase"], data.get("sub_phase"))
    except HaltError as halt:
        return _halt(state_path, data, halt, log_path)

    # 8. Hand off to evidence capture.
    data = save_loop_state(state_path, data, {"status": "evidence_capture"})
    try:
        invoke_run_checks(repo_root)
    except HaltError as halt:
        return _halt(state_path, data, halt, log_path)
    try:
        validate_evidence_files(repo_root)
    except HaltError as halt:
        return _halt(state_path, data, halt, log_path)

    # 8a. Phase 5B: now that the summary AND evidence have both validated,
    #     the cycle is genuinely review-ready. Write the machine-readable
    #     Claude completion handoff signal (`.agent-loop/claude-done.json`).
    #     Writing here (instead of earlier, between summary validation and
    #     evidence capture) means the signal is never left advertising
    #     `ready_for_codex_review` for a cycle that halted on evidence -
    #     any halt path above this point exits before the signal is
    #     written, and `clear_claude_done` at the start of every cycle
    #     drops the prior cycle's signal regardless. The signal is still
    #     routing/timing only - the Codex verdict still drives correctness.
    write_claude_done(
        repo_root,
        phase=data.get("phase"),
        sub_phase=data.get("sub_phase"),
        task=data.get("task"),
        cycle_count=data["cycle_count"],
        mode=CLAUDE_DONE_MODE_IMPLEMENTATION,
        source_prompt_path=".agent-loop/claude-prompt.md",
    )

    # 8b. Phase 5C strict-mode gate: under `strict`, the loop must pause
    #     for explicit human approval AFTER Claude completion + evidence
    #     validation but BEFORE Codex review begins. The previous gates
    #     and writes have already happened (cycle counted, summary
    #     validated, evidence captured, claude-done.json marks
    #     review-ready) so the only thing left is whether Codex review
    #     proceeds now or after the human approves it. Resume dispatches
    #     to `_run_normal_cycle_codex_review_step` so review proceeds
    #     exactly once. Phase 5D: `autonomous` skips the gate and logs an
    #     auditable bypass note.
    approval_mode = data.get("approval_mode")
    if approval_mode == APPROVAL_MODE_STRICT:
        return _fire_strict_gate(
            state_path, data,
            halt_status=HALTED_PRE_CODEX_REVIEW_NORMAL,
            awaiting_human_for=AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW,
            reason=(
                "strict mode: explicit human approval required after Claude "
                "completion / evidence validation and before Codex review begins"
            ),
            log_path=log_path,
        )
    if approval_mode == APPROVAL_MODE_AUTONOMOUS:
        _log_autonomous_bypass(
            log_path,
            gate=AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW,
            where="_run_normal_cycle_from_increment post-evidence",
        )

    return _run_normal_cycle_codex_review_step(repo_root, data, log_path)


def _run_normal_cycle_codex_review_step(
    repo_root: Path, data: dict, log_path: Path,
) -> int:
    """Continuation: Codex review through verdict handling for the normal
    cycle. Reached either from `_run_normal_cycle_from_increment` (the
    human is not in strict mode, or strict mode was satisfied at the
    pre_codex_review gate) or from the `resume` subcommand after the
    human approves the pre_codex_review gate. Codex review (and its
    side-effects on `claude_version` / `codex_version`) happens exactly
    once regardless of entry path because the gate site is BEFORE this
    function and resume only enters here, not at the gate.
    """
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    review_path = al / "codex-review.md"

    # 9. Wait on Codex review (subprocess when configured, manual-handoff
    #    fallback otherwise).
    data = save_loop_state(state_path, data, {"status": "awaiting_codex_review"})
    codex_adapter = make_codex_adapter()
    review_result = codex_adapter.wait_for_review(review_path)
    if review_result.exit_code != 0:
        return _halt(
            state_path, data,
            HaltError(
                "halted_input_missing",
                "Codex adapter returned no review (no codex-review.md)",
            ),
            log_path,
        )
    # Per the Phase 3A contract: codex_version is null when the adapter
    # cannot self-report, and a note must be written to orchestrator.log
    # (the orchestrator must not fabricate a version).
    if review_result.model_id is not None:
        data = save_loop_state(
            state_path, data, {"codex_version": review_result.model_id},
        )
    else:
        _log_note(
            log_path,
            "note: codex_version remains null because the Codex adapter "
            "did not self-report a version for this review cycle",
        )

    # 10. Validate review structure + parse exactly one verdict.
    try:
        review = parse_codex_review(review_path)
    except HaltError as halt:
        return _halt(state_path, data, halt, log_path)

    # 11. Hand off to the verdict-handling loop (Phase 3C). The loop
    #     either reaches a terminal state and returns, or drives one or
    #     more fix cycles before reaching a terminal state.
    return _handle_verdict_loop(
        state_path, data, review.verdict, repo_root, log_path, review=review,
    )


def _handle_verdict_loop(
    state_path: Path,
    data: dict,
    verdict: str,
    repo_root: Path,
    log_path: Path,
    review: Optional[ParsedCodexReview] = None,
) -> int:
    """Drive verdict handling, including any consecutive fix cycles.

    Phase 3C implements the contract's `#### Fix cycle` and the
    `NEEDS_FIXES` branch of `#### Verdict handling`. The function loops
    on the latest verdict until a terminal state is reached:

      - `APPROVED_FOR_HUMAN_REVIEW` -> persist completion, return 0
      - `FAILED_REQUIRES_HUMAN`     -> persist halt, return 2
      - `NEEDS_FIXES` AND `cycle_count >= max_cycles`
                                    -> persist halt_max_cycles_reached, return 2
      - `NEEDS_FIXES` AND threshold not reached
                                    -> validate fix-prompt, run a fix cycle,
                                       re-enter the loop with the new verdict

    Any structural validation failure, fail-closed adapter signal, or
    schema/parse failure in a fix cycle halts via `_halt` as in the
    normal cycle.
    """
    al = repo_root / ".agent-loop"
    while True:
        last_verdict_phase = data.get("sub_phase") or data.get("phase")
        if verdict == "APPROVED_FOR_HUMAN_REVIEW":
            # Phase 5B: in `review` mode the phase-complete gate is the
            # one named human gate this slice surfaces. Record it on
            # `awaiting_human_for` so the runtime state matches the
            # Phase 5A vocabulary. Phase 5D: `autonomous` mode also
            # halts here - the Phase 5D contract preserves the rule
            # "human approval must still be required before phase
            # progression and any future Git action," so autonomy does
            # not bypass the phase-complete gate. The mode is recorded
            # in loop-state.json (approval_mode) and the bypass-vs-halt
            # boundary is logged on autonomous cycles so the audit trail
            # makes clear autonomy stopped here intentionally.
            if data.get("approval_mode") == APPROVAL_MODE_AUTONOMOUS:
                _log_note(
                    log_path,
                    (
                        "autonomous mode: phase_complete_awaiting_human_approval "
                        "halt is preserved; human approval is still required "
                        "before phase progression"
                    ),
                )
            save_loop_state(state_path, data, {
                "status": "phase_complete_awaiting_human_approval",
                "last_verdict": verdict,
                "last_verdict_phase": last_verdict_phase,
                "awaiting_human_for": AWAITING_HUMAN_FOR_PHASE_COMPLETE,
            })
            _invoke_post_approval_planner(repo_root, log_path)
            print(
                f"[orchestrator] verdict={verdict}; phase complete, "
                f"awaiting human approval to start the next phase."
            )
            return 0
        if verdict == "FAILED_REQUIRES_HUMAN":
            # Phase 5B: a hard halt is not one of the named Phase 5A
            # human gates; leave `awaiting_human_for` null so the gate
            # vocabulary stays clean. The halt status itself carries the
            # human-intervention signal.
            save_loop_state(state_path, data, {
                "status": "halted_failed_requires_human",
                "last_verdict": verdict,
                "last_verdict_phase": last_verdict_phase,
                "awaiting_human_for": None,
            })
            print(
                f"[orchestrator] verdict={verdict}; halted, human "
                f"intervention required.",
                file=sys.stderr,
            )
            return 2
        # NEEDS_FIXES from here on. Record the verdict regardless of
        # whether we go on to run a fix cycle or halt on the threshold.
        # Phase 5B: NEEDS_FIXES in `review` mode auto-issues a fix
        # prompt within threshold; no human gate is active, so
        # `awaiting_human_for` stays null.
        data = save_loop_state(state_path, data, {
            "last_verdict": verdict,
            "last_verdict_phase": last_verdict_phase,
            "awaiting_human_for": None,
        })
        if review is not None:
            try:
                data = _prepare_needs_fixes_follow_up(repo_root, review, log_path)
            except HaltError as halt:
                # Phase 5E: a Codex-owned auto-fix inside the
                # reconciliation step may have already written to
                # loop-state.json (e.g. sync_phase5_runtime_defaults).
                # The caller's local `data` does not see those writes,
                # so passing it to `_halt` would clobber the on-disk
                # auto-fix when `_halt` overwrites status. Reload from
                # disk so the persisted halt preserves any side-effect
                # writes the reconciliation made before refusing.
                try:
                    data = load_loop_state(state_path)
                except HaltError:
                    pass
                return _halt(state_path, data, halt, log_path)
        # Threshold-policy enforcement: do not auto-continue past the
        # threshold. The contract's "materially changed / narrowed"
        # judgment is NOT made automatically here; raising max_cycles or
        # activating a new sub-phase is a Codex- or human-owned action.
        if data["cycle_count"] >= data["max_cycles"]:
            return _halt(
                state_path, data,
                HaltError(
                    "halted_max_cycles_reached",
                    f"cycle_count ({data['cycle_count']}) has reached "
                    f"max_cycles ({data['max_cycles']}) on a NEEDS_FIXES "
                    f"verdict; orchestrator will not auto-continue. Raise "
                    f"max_cycles (Codex/human action) or activate a new "
                    f"sub-phase to proceed.",
                ),
                log_path,
            )
        # Validate fix-prompt.md before starting the fix cycle.
        fix_prompt_path = al / "fix-prompt.md"
        try:
            validate_fix_prompt(fix_prompt_path)
        except HaltError as halt:
            return _halt(state_path, data, halt, log_path)
        # Phase 5B: a new fix-prompt issuance supersedes any prior
        # `.agent-loop/claude-done.json` from the implementation cycle
        # (or an earlier fix cycle), so clear the stale signal before
        # Claude is re-invoked.
        clear_claude_done(repo_root)
        # Phase 5C strict-mode gate: under `strict`, the loop must pause
        # for explicit human approval BEFORE dispatching a new fix
        # prompt. The fix-prompt is already authored and validated on
        # disk; only its dispatch to Claude waits. Resume dispatches to
        # `_run_fix_cycle` so the fix cycle proceeds exactly once.
        # Phase 5D: `autonomous` skips the gate and continues into the
        # bounded fix cycle, logging an auditable bypass note. The
        # `cycle_count`/`max_cycles` threshold check above this block
        # still gates the continuation, so autonomy cannot drive past
        # the existing escalation rule.
        approval_mode = data.get("approval_mode")
        if approval_mode == APPROVAL_MODE_STRICT:
            return _fire_strict_gate(
                state_path, data,
                halt_status=HALTED_PRE_FIX_PROMPT,
                awaiting_human_for=AWAITING_HUMAN_FOR_PRE_FIX_PROMPT,
                reason=(
                    "strict mode: explicit human approval required before "
                    "dispatching a new fix prompt to Claude"
                ),
                log_path=log_path,
            )
        if approval_mode == APPROVAL_MODE_AUTONOMOUS:
            _log_autonomous_bypass(
                log_path,
                gate=AWAITING_HUMAN_FOR_PRE_FIX_PROMPT,
                where="_handle_verdict_loop pre-fix-cycle",
            )
        # Run one fix cycle. On success, get a new verdict and loop.
        try:
            verdict, data, review = _run_fix_cycle(state_path, data, repo_root, log_path)
        except _FixCycleHalt as halted:
            return halted.exit_code


class _FixCycleHalt(Exception):
    """Internal carrier: a fix-cycle step has already halted via _halt."""

    def __init__(self, exit_code: int) -> None:
        super().__init__(f"fix cycle halted with exit code {exit_code}")
        self.exit_code = exit_code


def _run_fix_cycle(
    state_path: Path,
    data: dict,
    repo_root: Path,
    log_path: Path,
) -> tuple[str, dict, ParsedCodexReview]:
    """Execute one fix cycle per the contract's `#### Fix cycle` steps.

    Returns `(new_verdict, updated_data, parsed_review)` on success. On any halt path
    raises `_FixCycleHalt(exit_code)`, which the caller surfaces. The
    function increments `cycle_count` exactly once (at the start of the
    Claude fix invocation) so the threshold check in
    `_handle_verdict_loop` reflects the real cycle count after the call
    returns.
    """
    al = repo_root / ".agent-loop"
    fix_prompt_path = al / "fix-prompt.md"
    summary_path = al / "claude-summary.md"
    review_path = al / "codex-review.md"

    # 1. Increment cycle_count and set status = claude_fixing.
    data = save_loop_state(state_path, data, {
        "cycle_count": data["cycle_count"] + 1,
        "status": "claude_fixing",
    })

    # 2. Invoke Claude adapter with the fix prompt (subprocess when
    #    configured, manual-handoff fallback otherwise).
    claude_adapter = make_claude_adapter()
    result = claude_adapter.invoke(fix_prompt_path, summary_path)
    if result.model_id is None:
        raise _FixCycleHalt(_halt(
            state_path, data,
            HaltError(
                "halted_input_missing",
                "Claude adapter did not resolve a model_id in fix cycle "
                "(no fresh claude-summary.md or aborted handoff)",
            ),
            log_path,
        ))
    data = save_loop_state(state_path, data, {"claude_version": result.model_id})

    # 3. Validate fix-cycle claude-summary.md structurally + `## Phase` match.
    try:
        validate_claude_summary(summary_path, data["phase"], data.get("sub_phase"))
    except HaltError as halt:
        raise _FixCycleHalt(_halt(state_path, data, halt, log_path))

    # 4. Evidence capture.
    data = save_loop_state(state_path, data, {"status": "evidence_capture"})
    try:
        invoke_run_checks(repo_root)
    except HaltError as halt:
        raise _FixCycleHalt(_halt(state_path, data, halt, log_path))
    try:
        validate_evidence_files(repo_root)
    except HaltError as halt:
        raise _FixCycleHalt(_halt(state_path, data, halt, log_path))

    # 4a. Phase 5B: now that the fix-cycle summary AND evidence have both
    #     validated, the cycle is genuinely review-ready. Write the
    #     fix-completion handoff signal. Same rationale as the normal
    #     cycle's 8a: writing here means an evidence halt above this
    #     point exits before the signal is written, so the repo never
    #     advertises `ready_for_codex_review` for a fix cycle that
    #     halted on evidence. Routing/timing only - the Codex verdict
    #     still drives the next outcome.
    write_claude_done(
        repo_root,
        phase=data.get("phase"),
        sub_phase=data.get("sub_phase"),
        task=data.get("task"),
        cycle_count=data["cycle_count"],
        mode=CLAUDE_DONE_MODE_FIX,
        source_prompt_path=".agent-loop/fix-prompt.md",
    )

    # 4b. Phase 5C strict-mode gate: under `strict`, the loop must pause
    #     for explicit human approval AFTER fix-cycle Claude completion
    #     + evidence validation but BEFORE Codex fix-cycle review begins.
    #     The fix-cycle context (a fresh cycle_count was already
    #     incremented in step 1, summary validated in step 3, evidence
    #     captured in step 4) is fully on disk; the only thing left is
    #     whether review proceeds now or after the human approves it.
    #     Resume dispatches to `_run_fix_cycle_codex_review_step`, which
    #     synchronously runs review + verdict-handling for this cycle.
    #     Phase 5D: `autonomous` skips the gate and logs an auditable
    #     bypass note before continuing into Codex fix-cycle review.
    approval_mode = data.get("approval_mode")
    if approval_mode == APPROVAL_MODE_STRICT:
        _fire_strict_gate(
            state_path, data,
            halt_status=HALTED_PRE_CODEX_REVIEW_FIX,
            awaiting_human_for=AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW,
            reason=(
                "strict mode: explicit human approval required after fix-cycle "
                "Claude completion / evidence validation and before Codex "
                "fix-cycle review begins"
            ),
            log_path=log_path,
        )
        # Carry the gate exit up through the verdict-loop frame the same
        # way other fix-cycle halts do.
        raise _FixCycleHalt(2)
    if approval_mode == APPROVAL_MODE_AUTONOMOUS:
        _log_autonomous_bypass(
            log_path,
            gate=AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW,
            where="_run_fix_cycle post-evidence",
        )

    return _run_fix_cycle_codex_review_step(state_path, data, repo_root, log_path)


def _run_fix_cycle_codex_review_step(
    state_path: Path,
    data: dict,
    repo_root: Path,
    log_path: Path,
) -> tuple[str, dict, ParsedCodexReview]:
    """Continuation: Codex review through verdict-parse for the fix
    cycle. Reached either from `_run_fix_cycle` directly (no strict
    gate) or from the `resume` subcommand after the human approves the
    pre_codex_review gate. Returns `(verdict, updated_data)` so the
    calling `_handle_verdict_loop` frame can continue from the same
    point it would have continued without the strict gate.
    """
    al = repo_root / ".agent-loop"
    review_path = al / "codex-review.md"

    # 5. Wait for the fix-cycle Codex review (subprocess when configured,
    #    manual-handoff fallback otherwise).
    data = save_loop_state(state_path, data, {"status": "awaiting_codex_review"})
    codex_adapter = make_codex_adapter()
    review_result = codex_adapter.wait_for_review(review_path)
    if review_result.exit_code != 0:
        raise _FixCycleHalt(_halt(
            state_path, data,
            HaltError(
                "halted_input_missing",
                "Codex adapter returned no review in fix cycle "
                "(no fresh codex-review.md)",
            ),
            log_path,
        ))
    # Same contract rule as the normal-cycle Codex handoff: write
    # codex_version when the adapter self-reports, otherwise note the
    # null to orchestrator.log; never fabricate a version.
    if review_result.model_id is not None:
        data = save_loop_state(
            state_path, data, {"codex_version": review_result.model_id},
        )
    else:
        _log_note(
            log_path,
            "note: codex_version remains null because the Codex adapter "
            "did not self-report a version for this fix-cycle review",
        )

    # 6. Validate review + parse exactly one verdict.
    try:
        review = parse_codex_review(review_path)
    except HaltError as halt:
        raise _FixCycleHalt(_halt(state_path, data, halt, log_path))

    return review.verdict, data, review


# ----- Phase 4B planner (proposal generation only) -----
#
# This block implements the first working slice of the automatic phase
# planner against the Phase 4A Planning Contract
# (`.agent-loop/phase-plan.md` -> "## Phase 4A - Planning Contract").
#
# Scope of this slice:
#   - load the planner inputs the contract enumerates as read-only
#   - apply every refusal / halt condition the contract names
#   - generate one structurally valid `.agent-loop/proposed-phase.md`
#     when planning is allowed
#   - optionally append a single-line note to `.agent-loop/planner.log`
#   - never write any file in the contract's "Files the planner must
#     never write" set; never write the activation files; never write
#     the `APPROVED_FOR_ACTIVATION` token (self-approval is forbidden)
#
# Activation writes (modifying TASK.md / current-task.md /
# current-phase.md / phase-plan.md / loop-state.json on the basis of an
# approved proposal) are deferred to a later 4x sub-phase. The planner
# only WRITES the two planner-owned artifacts.
#
# Failure handling is fail-closed: any refusal or generation failure
# returns a non-zero exit code, logs a single-line `note:` (best-effort)
# to `.agent-loop/planner.log`, and leaves `.agent-loop/proposed-phase.md`
# untouched.

PLANNER_VERSION = "phase-4b-v0"
APPROVAL_TOKEN = "APPROVED_FOR_ACTIVATION"
PROPOSAL_PATH_REL = ".agent-loop/proposed-phase.md"
PLANNER_LOG_PATH_REL = ".agent-loop/planner.log"

PROPOSAL_TITLE = "# Proposed Phase"
PROPOSAL_REQUIRED_SECTIONS = (
    "## Label",
    "## Objective",
    "## Definition of done",
    "## Exclusions",
    "## Files likely involved",
    "## Required contract changes",
    "## Cycle-size estimate",
    "## Dependencies",
    "## Risk areas",
)

PROPOSAL_MAX_FILES = 10
PROPOSAL_MAX_CONTRACT_REVISIONS = 1
PROPOSAL_DEFAULT_MAX_CYCLE_SIZE = 3

# Per the Phase 4A "Failure modes worth naming" subsection: when the
# orchestrator is in flight on a cycle (mid-implement, mid-fix, mid-capture,
# or mid-review), the cycle's view is not yet terminal and the planner
# refuses to propose the next phase.
ORCHESTRATOR_IN_FLIGHT_STATUSES = frozenset({
    "claude_implementing",
    "claude_fixing",
    "evidence_capture",
    "awaiting_codex_review",
})

DEPENDENCY_STATUS_TOKENS = frozenset({
    "complete-approved",
    "complete-superseded",
    "active-in-flight",
    "pending",
})
# A proposal that depends on an active-in-flight or pending phase is
# invalid per the Phase 4A "Refusal / halt conditions".
DEPENDENCY_BLOCKING_STATUSES = frozenset({
    "active-in-flight",
    "pending",
})

# Mirror of the Phase 4A "Files the planner must never write" list, used
# for both write-time refusal (the planner never opens any of these for
# write) and proposal-content validation (a proposal that names any of
# these in its `## Files likely involved` AND does not itself disclose a
# contract revision authorizing the change is suspect; the contract puts
# the disclosure burden on the proposal author rather than on the
# planner enforcing it line-by-line, but the planner still hard-refuses
# attempting to author over these files itself).
PLANNER_FORBIDDEN_WRITE_FILES = frozenset({
    "scripts/agent_loop.py",
    "scripts/run_checks.sh",
    "AGENTS.md",
    "CLAUDE.md",
    "ROADMAP.md",
    "README.md",
    ".gitattributes",
    ".gitignore",
    ".agent-loop/claude-prompt.md",
    ".agent-loop/claude-summary.md",
    ".agent-loop/codex-review.md",
    ".agent-loop/fix-prompt.md",
    ".agent-loop/git-status.log",
    ".agent-loop/git-diff.patch",
    ".agent-loop/test-output.log",
    ".agent-loop/lint-output.log",
    ".agent-loop/typecheck-output.log",
    ".agent-loop/build-output.log",
    ".agent-loop/orchestrator.log",
})
# Files the planner is allowed to write in this sub-phase (proposal step
# only; activation writes are deferred to a later 4x sub-phase).
PLANNER_ALLOWED_WRITE_FILES = frozenset({
    PROPOSAL_PATH_REL,
    PLANNER_LOG_PATH_REL,
})

# Vague-language tokens forbidden in `## Definition of done` per the
# Phase 4A contract ("Code is cleaner" is not testable; specific
# file-state / CLI-behavior / validator-outcome bullets are required).
VAGUE_DOD_PHRASES = (
    "improve ",
    "make better",
    "make faster",
    "clean up",
    "cleaner",
    "tidy",
    "polish",
    "general improvements",
    "refactor for clarity",
)

# Heuristic: a Definition-of-done bullet counts as "testable" if it
# names a file path, a CLI verb, or one of these markers. The set is
# intentionally conservative; missing it does not silently pass.
TESTABLE_DOD_MARKERS = (
    "scripts/", "tests/", ".agent-loop/", "README.md", "TASK.md",
    "exit code", "exit 0", "exit 2", "CLI", "subcommand",
    "validator", "structurally valid", "structurally invalid",
    "appends a", "writes a", "writes the", "fails closed",
    "refuses", "halts", "is written", "is created", "is updated",
)

# Vague meta-planning phrases that, when found in the `## Objective`
# body, indicate the proposal is a generic stub rather than a concrete
# next-phase plan. The Phase 4A contract requires the Objective to be
# "concrete, actionable, in the present tense" and explicitly forbids
# vague language; the planner refuses proposals that read as meta-talk
# about future planning instead of describing the work itself.
VAGUE_OBJECTIVE_PHRASES = (
    "planner-generated stub",
    "intended to be refined",
    "stub against the",
    "the implementing sub-phase will pick",
    "pick exactly one",
    "narrow scope to that capability",
    "before activation",
    "proposal is planner-generated",
    "to be refined by codex",
    "placeholder for review",
    "tbd",
    "to be determined",
    "will pick one of",
)

# Phase-style references that the `## Exclusions` body must enumerate
# explicitly when the proposal does NOT cover them. The contract says
# "every later 4x / 5+ sub-phase that this proposal does NOT cover must
# appear here"; the planner enforces a concrete floor by requiring at
# least the Phase 5 / Phase 6 / Phase 7 / Phase 8 markers AND any
# known-deferred 4x sub-phases that are not the proposed one. The list
# of known-deferred 4x sub-phases is derived from the dispatch table
# in `_concrete_next_proposal`.
REQUIRED_EXCLUSIONS_FLOOR = (
    "Phase 5",
    "Phase 6",
    "Phase 7",
    "Phase 8",
)


@dataclass
class PlannerInputs:
    repo_root: Path
    loop_state: dict
    summary_mtime: Optional[float]
    review_mtime: Optional[float]
    evidence_captured_ats: dict  # rel_path -> Optional[float epoch]
    evidence_missing: list       # rel_path with no readable captured_at
    phase_plan_text: str
    existing_labels: set         # set[str]
    closed_labels: list          # ordered list[str], oldest-first
    task_md_text: str
    roadmap_md_text: str
    proposed_phase_existing: Optional[str]  # current contents, if any
    # Additional planner inputs the Phase 4A contract enumerates as
    # read-only. Stored on the inputs dataclass so the planner has a
    # single in-memory snapshot of every input it is allowed to read,
    # rather than re-reading from disk during proposal generation. These
    # are best-effort reads: missing optional inputs return empty strings
    # so the planner does not refuse a fresh-start state just because a
    # mid-cycle artifact (e.g. fix-prompt.md) has not been authored.
    current_task_text: str = ""
    current_phase_text: str = ""
    claude_prompt_text: str = ""
    fix_prompt_text: str = ""
    orchestrator_log_text: str = ""
    agents_md_text: str = ""
    claude_md_text: str = ""


@dataclass
class PlannerRefusal:
    code: str
    reason: str


@dataclass
class ProposalDraft:
    label: str
    objective: str
    definition_of_done: list = field(default_factory=list)
    exclusions: list = field(default_factory=list)
    files_likely_involved: list = field(default_factory=list)
    required_contract_changes: object = "None"   # "None" or list[str]
    cycle_size_estimate: int = 2
    cycle_size_justification: Optional[str] = None
    dependencies: list = field(default_factory=list)  # list[(label, status)]
    risk_areas: list = field(default_factory=list)


# --- planner I/O helpers ---

def _planner_log_path(repo_root: Path) -> Path:
    return repo_root / PLANNER_LOG_PATH_REL


def _proposal_path(repo_root: Path) -> Path:
    return repo_root / PROPOSAL_PATH_REL


def _planner_log_note(repo_root: Path, message: str) -> None:
    """Append a single timestamped `note:`-style line. Best-effort.

    The Phase 4A contract's "Refusal / halt conditions" and
    "Failure modes worth naming" subsections both require the planner
    log line to use `note:`-style; this helper prepends the literal
    `note:` token so refusal and success entries share a uniform prefix
    that a future tool can grep. Write failures are swallowed because
    the contract treats the log as optional and never authoritative.
    """
    path = _planner_log_path(repo_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} note: {message}\n")
    except OSError:
        pass


def _parse_captured_at(value: str) -> Optional[float]:
    """Best-effort ISO-8601 -> epoch seconds. Returns None on failure.

    Tolerates a trailing `Z` (UTC marker). Anything else falls through to
    `None`, and the calling code records the file as "no readable
    captured_at" rather than crashing.
    """
    if not value:
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def _read_evidence_captured_at(path: Path) -> Optional[float]:
    if not path.exists():
        return None
    head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:25]
    for ln in head:
        low = ln.lower()
        if low.startswith("captured_at:") or low.startswith("captured-at:"):
            value = ln.split(":", 1)[1].strip()
            return _parse_captured_at(value)
    return None


def _read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


class _ActivationInputError(Exception):
    """Raised by `_read_text_strict` when an activation-required input is
    missing or unreadable. Carries the contract-vocabulary refusal code
    so the caller can route to the appropriate `activation refused [...]`
    log line without re-classifying the failure.
    """

    def __init__(self, code: str, path: Path, reason: str) -> None:
        super().__init__(f"{code}: {path}: {reason}")
        self.code = code
        self.path = path
        self.reason = reason


def _read_text_strict(
    path: Path, *, missing_code: str, unreadable_code: str,
) -> str:
    """Read `path` and return its text, or raise `_ActivationInputError`
    on any failure. Used by the activator for inputs the Phase 4A
    contract requires it to preserve verbatim (TASK.md sections,
    phase-plan.md historical bodies, ROADMAP.md parent-phase lookup):
    a silent best-effort fallback to "" would fabricate replacement
    state instead of preserving real content, so the activator must
    fail closed when these inputs cannot be read.
    """
    if not path.exists():
        raise _ActivationInputError(
            missing_code, path, f"{path} does not exist",
        )
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _ActivationInputError(
            unreadable_code, path, f"could not read {path}: {exc}",
        ) from exc


_PHASE_LABEL_RE = re.compile(r"^## (Phase\s+\S+\s+-\s+[^\n]+)", re.MULTILINE)


def _extract_phase_labels(phase_plan_text: str) -> list:
    """Return phase-plan `## Phase X - ...` headings, in file order.

    The list is ordered as the headings appear in the file. The set of
    "existing labels" is built from this, and the most recent CLOSED
    label is used as the planner's "latest closed historical sub-phase"
    anchor when the loop state is fresh-start.
    """
    return _PHASE_LABEL_RE.findall(phase_plan_text)


_STATUS_PARA_RE = re.compile(
    r"^## (Phase\s+\S+\s+-\s+[^\n]+)\n+### Status\n+([^\n]+)",
    re.MULTILINE,
)


def _extract_closed_labels(phase_plan_text: str) -> list:
    """Return ordered list of phase-plan labels whose `### Status` reads
    as closed/complete. "Closed" is detected by case-insensitive
    substring on the first line of the Status paragraph; the planner
    treats both `Complete.` and `Closed and ...` as closed.
    """
    closed: list = []
    for m in _STATUS_PARA_RE.finditer(phase_plan_text):
        label = m.group(1).strip()
        status_first_line = m.group(2).strip().lower()
        if status_first_line.startswith("complete") or status_first_line.startswith("closed"):
            closed.append(label)
    return closed


# --- planner inputs ---

def load_planner_inputs(repo_root: Path) -> PlannerInputs:
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    summary_path = al / "claude-summary.md"
    review_path = al / "codex-review.md"
    phase_plan_path = al / "phase-plan.md"
    proposed_path = _proposal_path(repo_root)
    task_path = repo_root / "TASK.md"
    roadmap_path = repo_root / "ROADMAP.md"

    # loop-state.json is REQUIRED. A missing / malformed loop-state is a
    # halt-type refusal (the planner cannot reason about cycle state).
    if not state_path.exists():
        raise HaltError(
            "halted_input_missing",
            f"{state_path} does not exist; planner requires loop-state.json",
        )
    try:
        loop_state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HaltError(
            "halted_input_missing",
            f"loop-state.json is not valid JSON: {exc}",
        ) from exc

    summary_mtime = summary_path.stat().st_mtime if summary_path.exists() else None
    review_mtime = review_path.stat().st_mtime if review_path.exists() else None

    evidence_captured_ats: dict = {}
    evidence_missing: list = []
    for rel in EVIDENCE_FILES:
        p = repo_root / rel
        cap = _read_evidence_captured_at(p)
        if cap is None:
            evidence_missing.append(rel)
        evidence_captured_ats[rel] = cap

    phase_plan_text = _read_text_or_empty(phase_plan_path)
    existing_labels = set(_extract_phase_labels(phase_plan_text))
    closed_labels = _extract_closed_labels(phase_plan_text)
    task_md_text = _read_text_or_empty(task_path)
    roadmap_md_text = _read_text_or_empty(roadmap_path)
    proposed_phase_existing = (
        proposed_path.read_text(encoding="utf-8", errors="replace")
        if proposed_path.exists() else None
    )

    # Additional planner inputs per the Phase 4A "Inputs the planner
    # reads" subsection. Read-only and best-effort: missing optional
    # inputs (e.g. fix-prompt.md outside a fix cycle) return empty
    # strings rather than raising, so the planner can still propose on
    # a fresh-start state.
    current_task_text = _read_text_or_empty(al / "current-task.md")
    current_phase_text = _read_text_or_empty(al / "current-phase.md")
    claude_prompt_text = _read_text_or_empty(al / "claude-prompt.md")
    fix_prompt_text = _read_text_or_empty(al / "fix-prompt.md")
    orchestrator_log_text = _read_text_or_empty(al / "orchestrator.log")
    agents_md_text = _read_text_or_empty(repo_root / "AGENTS.md")
    claude_md_text = _read_text_or_empty(repo_root / "CLAUDE.md")

    return PlannerInputs(
        repo_root=repo_root,
        loop_state=loop_state,
        summary_mtime=summary_mtime,
        review_mtime=review_mtime,
        evidence_captured_ats=evidence_captured_ats,
        evidence_missing=evidence_missing,
        phase_plan_text=phase_plan_text,
        existing_labels=existing_labels,
        closed_labels=closed_labels,
        task_md_text=task_md_text,
        roadmap_md_text=roadmap_md_text,
        proposed_phase_existing=proposed_phase_existing,
        current_task_text=current_task_text,
        current_phase_text=current_phase_text,
        claude_prompt_text=claude_prompt_text,
        fix_prompt_text=fix_prompt_text,
        orchestrator_log_text=orchestrator_log_text,
        agents_md_text=agents_md_text,
        claude_md_text=claude_md_text,
    )


# --- planner refusal checks ---

def check_planner_refusal(inputs: PlannerInputs) -> Optional[PlannerRefusal]:
    """Apply every Phase 4A refusal condition that does NOT depend on a
    generated proposal. Per-proposal bounded-scope checks run separately
    after generation in `validate_proposal_against_contract`.
    """
    state = inputs.loop_state
    status = state.get("status")
    last_verdict = state.get("last_verdict")
    cycle_count = state.get("cycle_count")
    max_cycles = state.get("max_cycles")

    # Unresolved NEEDS_FIXES blocks planning.
    if last_verdict == "NEEDS_FIXES":
        return PlannerRefusal(
            code="needs_fixes_unresolved",
            reason=(
                "last_verdict is NEEDS_FIXES with no subsequent APPROVED verdict; "
                "the fix cycle takes precedence over planning the next phase"
            ),
        )

    # Unresolved FAILED_REQUIRES_HUMAN blocks planning.
    if last_verdict == "FAILED_REQUIRES_HUMAN":
        return PlannerRefusal(
            code="failed_requires_human",
            reason=(
                "last_verdict is FAILED_REQUIRES_HUMAN; human escalation takes "
                "precedence over planning the next phase"
            ),
        )

    # Any halted_* status blocks planning.
    if isinstance(status, str) and status.startswith("halted_"):
        return PlannerRefusal(
            code="halted_state",
            reason=(
                f"loop-state.json status is {status!r}; an existing halt must be "
                f"resolved before planning the next phase"
            ),
        )

    # Orchestrator in flight: the cycle's view is not yet terminal.
    if status in ORCHESTRATOR_IN_FLIGHT_STATUSES:
        return PlannerRefusal(
            code="orchestrator_in_flight",
            reason=(
                f"loop-state.json status is {status!r} (orchestrator in flight); "
                f"the planner refuses because the current cycle is not terminal"
            ),
        )

    # Threshold halt: cycle_count >= max_cycles on NEEDS_FIXES. (The
    # NEEDS_FIXES branch above is already a refusal; this guards the
    # case where last_verdict was previously cleared but counts are
    # still at the threshold.)
    if (
        isinstance(cycle_count, int)
        and isinstance(max_cycles, int)
        and cycle_count >= max_cycles
        and last_verdict == "NEEDS_FIXES"
    ):
        return PlannerRefusal(
            code="threshold_halt",
            reason=(
                f"cycle_count ({cycle_count}) >= max_cycles ({max_cycles}) on a "
                f"NEEDS_FIXES verdict; the threshold halt takes precedence"
            ),
        )

    # Stale evidence: any evidence captured_at older than max(summary, review)
    # mtime indicates the evidence does not reflect the latest review state.
    newest_artifact_mtime: Optional[float] = None
    for mt in (inputs.summary_mtime, inputs.review_mtime):
        if mt is not None and (newest_artifact_mtime is None or mt > newest_artifact_mtime):
            newest_artifact_mtime = mt
    if newest_artifact_mtime is not None:
        stale_files: list = []
        for rel, cap in inputs.evidence_captured_ats.items():
            # Per the contract, an unreadable captured_at is "unreadable
            # input" (separate refusal below). For the stale check we
            # only count evidence whose timestamp parsed.
            if cap is not None and cap < newest_artifact_mtime:
                stale_files.append(rel)
        if stale_files:
            return PlannerRefusal(
                code="stale_evidence",
                reason=(
                    f"evidence captured_at is older than the latest summary/review "
                    f"mtime for: {sorted(stale_files)}; run "
                    f"`bash scripts/run_checks.sh` before re-planning"
                ),
            )

    # Unreadable required input: missing evidence captured_at header.
    if inputs.evidence_missing:
        return PlannerRefusal(
            code="evidence_unreadable",
            reason=(
                f"evidence files lack a readable `captured_at:` header: "
                f"{sorted(inputs.evidence_missing)}; the planner cannot reason "
                f"about evidence freshness without it"
            ),
        )

    # Existing proposal with mismatched approval token: refuse to overwrite.
    existing = inputs.proposed_phase_existing
    if existing and APPROVAL_TOKEN in existing:
        # A previously-approved proposal must be human-archived before a
        # new one is generated; silently overwriting an approved proposal
        # is a contract-prohibited failure mode.
        return PlannerRefusal(
            code="prior_proposal_approved",
            reason=(
                f"{PROPOSAL_PATH_REL} already exists and contains the "
                f"{APPROVAL_TOKEN!r} token; planner refuses to overwrite an "
                f"approved proposal (archive or remove it manually first)"
            ),
        )

    return None


# --- proposal generation ---

_SUBPHASE_TOKEN_RE = re.compile(r"Phase\s+(\d+)([A-Za-z]*)")


def _bump_subphase_letter(active_sub_phase: str) -> Optional[str]:
    """Given an active sub-phase string like 'Phase 4B - ...', return the
    next-letter sub-phase token ('Phase 4C'). Returns None if the input
    does not look like a sub-phased label.
    """
    if not active_sub_phase:
        return None
    m = _SUBPHASE_TOKEN_RE.search(active_sub_phase)
    if m is None:
        return None
    number, letter = m.group(1), m.group(2)
    if not letter:
        # 'Phase 4' with no letter -> 'Phase 4A'
        return f"Phase {number}A"
    if len(letter) > 1:
        # 'Phase 4AB' or similar: planner cannot mechanically increment.
        return None
    ch = letter.upper()
    if ch == "Z":
        # 'Phase 4Z' -> wraparound is not part of the convention.
        return None
    return f"Phase {number}{chr(ord(ch) + 1)}"


def _label_exists(label: str, existing_labels: set) -> bool:
    """Substring match: a generated label 'Phase 4C - ...' collides if
    any existing phase-plan heading starts with 'Phase 4C'. Loose match
    avoids false negatives from minor wording differences in the suffix.
    """
    prefix = label.split(" - ", 1)[0].strip()
    return any(existing.split(" - ", 1)[0].strip() == prefix for existing in existing_labels)


def _recent_closed_dependencies(inputs: PlannerInputs) -> list:
    """Return the dependency list for a generated proposal: the two most
    recent CLOSED prior sub-phases, each marked `complete-approved`. The
    active sub-phase is deliberately omitted because listing it as
    `active-in-flight` would invalidate the proposal per the Phase 4A
    contract; the implicit ordering ('the active sub-phase must close
    first') is captured in the Risk areas instead.
    """
    dep_labels = list(inputs.closed_labels)
    recent_closed = dep_labels[-2:] if len(dep_labels) > 2 else dep_labels
    if not recent_closed:
        # Fresh repository: no closed sub-phases yet. Use "pending"
        # against a placeholder; the per-proposal validator will then
        # refuse this draft, which is the correct fail-closed behavior.
        return [("(no closed prior sub-phase found)", "pending")]
    return [(lbl, "complete-approved") for lbl in recent_closed]


def _build_phase_4c_activation_proposal(inputs: PlannerInputs) -> ProposalDraft:
    """Concrete proposal for the planner's activation-writes sub-phase.

    Activation writes are the work the Phase 4A contract permits ONLY
    after explicit human approval, and which Phase 4B explicitly defers.
    Implementing them is the natural next sub-phase after Phase 4B.

    The proposal text never spells out the literal Phase 4A approval-
    token string (the planner's self-approval guard refuses any proposal
    that contains that token in any section). The implementing slice
    reads the token name from the Phase 4A contract body and the
    `APPROVAL_TOKEN` constant in `scripts/agent_loop.py`.
    """
    active_sub_phase = inputs.loop_state.get("sub_phase") or "the active sub-phase"
    objective = (
        "Add an `activate` CLI subcommand to `scripts/agent_loop.py` that "
        "parses `.agent-loop/proposed-phase.md` for a human-authored "
        "`## Approval` section containing the Phase 4A approval-token "
        "literal (defined in the contract body and mirrored by the "
        "`APPROVAL_TOKEN` constant in `scripts/agent_loop.py`) on its own "
        "line, verifies the approval section names the same `## Label` "
        "the proposal carries, and on success rewrites the Codex-owned "
        "planning files exactly as the Phase 4A contract authorizes: it "
        "rewrites `TASK.md`'s `## Active Phase`, `## Active Sub-Phase`, "
        "`## Phase Status`, `## Active Task`, `## Phase Outcome Required "
        "Now`, `## Next-Phase Gate`, and `## Out Of Scope For Current "
        "Phase` sections (preserving `## Human Objective` and `## Project "
        "Intent` verbatim), rewrites `.agent-loop/current-task.md` and "
        "`.agent-loop/current-phase.md`, appends a new `## Phase NX - ...` "
        "sub-phase section to `.agent-loop/phase-plan.md` without "
        "modifying any prior section, and resets "
        "`.agent-loop/loop-state.json` to "
        "`status = awaiting_claude_implementation`, `cycle_count = 0`, "
        "`last_verdict = null`, `last_verdict_phase = null`, with "
        "`phase` / `sub_phase` / `task` set from the approved proposal "
        "and all orchestrator-owned runtime fields (`max_cycles`, "
        "`contract_version`, `claude_version`, `codex_version`, "
        "`orchestrator_version`) preserved. The approval parser scopes "
        "its token match to the `## Approval` section only, so a stray "
        "mention of the approval-token string in unrelated prose cannot "
        "trigger activation, and refuses any approval line whose label "
        "does not match `## Label` exactly."
    )
    definition_of_done = [
        "scripts/agent_loop.py exposes an `activate` CLI subcommand whose exit code is 0 on a successful activation and 2 on any refusal",
        "the activation parser refuses any .agent-loop/proposed-phase.md that lacks a `## Approval` section, lacks the Phase 4A approval-token literal on its own line within that section, or whose approval label does not exactly match the proposal's `## Label`",
        "the activation path rewrites TASK.md, .agent-loop/current-task.md, .agent-loop/current-phase.md, and .agent-loop/loop-state.json, and appends one new sub-phase section to .agent-loop/phase-plan.md, exactly as the Phase 4A contract's allowed-writes-on-activation list permits; no other file is modified",
        "the activation path preserves TASK.md's `## Human Objective` and `## Project Intent` verbatim; a diff that mutates either of those sections fails closed",
        "tests/test_planner_activation.py covers: one successful activation, one refusal on a missing approval section, one refusal on a forged token outside `## Approval`, one refusal on a label mismatch, and one refusal that confirms the planner.log records the activation-source line (file path, mtime, approval line)",
        "README.md is updated so the Current Status section names Phase 4C as active and documents the new `python scripts/agent_loop.py activate` subcommand",
    ]
    exclusions = [
        "no Phase 4D planner-orchestrator integration; the `activate` subcommand stays standalone in this sub-phase and is not auto-invoked from `run_normal_cycle` or `_run_fix_cycle`",
        "no Phase 4E optional planner adapter (deferred)",
        "no Phase 5 approval-mode behavior beyond the Phase 4A approval-token literal",
        "no Phase 6 optional context and tool layer",
        "no Phase 7 editor / VS Code integration",
        "no Phase 8 documentation polish",
        "no MCP support",
        "no Git automation (commit, push, branch, stash, reset, checkout, tag)",
        "no changes to the Phase 2A Evidence Collection Contract or `scripts/run_checks.sh`",
        "no changes to the Phase 3A Orchestrator Contract body, the Phase 4A Planning Contract body, `AGENTS.md`, or `CLAUDE.md`",
    ]
    files_likely_involved = [
        "scripts/agent_loop.py",
        "tests/test_planner_activation.py",
        ".agent-loop/proposed-phase.md",
        ".agent-loop/planner.log",
        "TASK.md",
        ".agent-loop/current-task.md",
        ".agent-loop/current-phase.md",
        ".agent-loop/phase-plan.md",
        ".agent-loop/loop-state.json",
        "README.md",
    ]
    risk_areas = [
        (
            "approval-token forgery surface: the activation parser must scope the "
            "Phase 4A approval-token match to the `## Approval` section header, "
            "not whole-file substring matching, so a stray mention in unrelated prose "
            "cannot trigger activation"
        ),
        (
            "label-mismatch defense: if the `## Approval` body names a different label "
            "than `## Label`, the activation parser must refuse, because the approval "
            "may be for an earlier draft that was later overwritten by a new proposal"
        ),
        (
            "loop-state.json reset semantics: the activation path must set "
            "`status = awaiting_claude_implementation`, `cycle_count = 0`, "
            "`last_verdict = null`, `last_verdict_phase = null`, and preserve "
            "`max_cycles` / `contract_version` / `claude_version` / `codex_version` / "
            "`orchestrator_version` per the Phase 3A contract's write-ownership rules"
        ),
        (
            "phase-plan.md history is append-only: the activation path must append the "
            "new sub-phase section, never edit any prior section, and never rewrite the "
            "approved Phase 4A Planning Contract body"
        ),
        (
            "TASK.md `## Human Objective` and `## Project Intent` are human-owned: the "
            "activation path must preserve both sections verbatim; "
            f"the activation depends on {active_sub_phase} reaching "
            f"`APPROVED_FOR_HUMAN_REVIEW` first, which is why this sub-phase is "
            "Phase 4C rather than running concurrently with 4B"
        ),
    ]
    return ProposalDraft(
        label="Phase 4C - Planner Activation Writes",
        objective=objective,
        definition_of_done=definition_of_done,
        exclusions=exclusions,
        files_likely_involved=files_likely_involved,
        required_contract_changes="None",
        cycle_size_estimate=2,
        cycle_size_justification=None,
        dependencies=_recent_closed_dependencies(inputs),
        risk_areas=risk_areas,
    )


def _build_phase_4d_integration_proposal(inputs: PlannerInputs) -> ProposalDraft:
    """Concrete proposal for wiring the planner into the orchestrator's
    post-approval handoff. Activated only after Phase 4C ships activation
    writes, so the planner has somewhere to hand its approved proposal off
    to.
    """
    objective = (
        "Wire the planner into `scripts/agent_loop.py` so that after a "
        "`APPROVED_FOR_HUMAN_REVIEW` verdict and the resulting "
        "`phase_complete_awaiting_human_approval` status, the orchestrator "
        "invokes `run_planner` to refresh `.agent-loop/proposed-phase.md` "
        "before returning control to the human. The integration is read-only "
        "with respect to the planner's own write-boundary: planner output "
        "remains scoped to `.agent-loop/proposed-phase.md` and "
        "`.agent-loop/planner.log`, and the orchestrator records the planner's "
        "exit code into `.agent-loop/orchestrator.log` as a `note:` line so the "
        "review chain remains auditable. Activation of the proposal still "
        "requires explicit human approval; the integration does not bypass the "
        "Phase 4A 'never autonomously activate' rule."
    )
    definition_of_done = [
        "scripts/agent_loop.py's `_handle_verdict_loop` invokes `run_planner` after persisting `phase_complete_awaiting_human_approval` and before returning 0; the planner's exit code is logged to `.agent-loop/orchestrator.log` as a `note:` line",
        "the orchestrator never auto-activates the planner's proposal; the existing 'never auto-activate' write boundary is preserved",
        "tests/test_planner_integration.py covers: one successful integration call after APPROVED_FOR_HUMAN_REVIEW, one path where the planner refuses (stale evidence, etc.) and the orchestrator still returns 0 with the refusal logged, and one path verifying no activation-file writes occur from the integration call",
        "README.md is updated so the Current Status section names Phase 4D as active and documents the post-approval planner invocation",
    ]
    exclusions = [
        "no Phase 4E optional planner adapter (deferred)",
        "no Phase 5 approval-mode behavior",
        "no Phase 6 optional context and tool layer",
        "no Phase 7 editor / VS Code integration",
        "no Phase 8 documentation polish",
        "no MCP support",
        "no Git automation",
        "no changes to the Phase 2A Evidence Collection Contract, the Phase 3A Orchestrator Contract body, the Phase 4A Planning Contract body, `AGENTS.md`, or `CLAUDE.md`",
        "no auto-activation of any planner-authored proposal under any verdict",
    ]
    files_likely_involved = [
        "scripts/agent_loop.py",
        "tests/test_planner_integration.py",
        ".agent-loop/proposed-phase.md",
        ".agent-loop/planner.log",
        ".agent-loop/orchestrator.log",
        "README.md",
    ]
    risk_areas = [
        "the integration must not block the orchestrator's return path: a planner refusal must be logged and ignored for control-flow purposes, never escalated to a halt",
        "the planner runs after the verdict is persisted, so a planner failure can never reverse or rewrite the verdict",
        "auto-invocation increases the surface area for planner.log noise; the integration must log exactly one `note:` line per invocation, not duplicates",
    ]
    return ProposalDraft(
        label="Phase 4D - Planner-Orchestrator Integration",
        objective=objective,
        definition_of_done=definition_of_done,
        exclusions=exclusions,
        files_likely_involved=files_likely_involved,
        required_contract_changes="None",
        cycle_size_estimate=2,
        cycle_size_justification=None,
        dependencies=_recent_closed_dependencies(inputs),
        risk_areas=risk_areas,
    )


# Dispatch from the active sub-phase prefix to a concrete proposal-builder
# function. Keeping the mapping explicit makes the planner refuse cleanly
# (rather than emit a generic stub) for any active sub-phase whose next
# step has not been concretely planned. New entries are added as the
# project progresses; the planner is fail-closed by default.
_CONCRETE_NEXT_PHASE_DISPATCH = {
    "Phase 4B": _build_phase_4c_activation_proposal,
    "Phase 4C": _build_phase_4d_integration_proposal,
}


def _known_deferred_4x_labels() -> list:
    """Return the labels of all known-concrete 4x sub-phases (one label
    per dispatch entry). Used by the per-proposal validator to enforce
    explicit enumeration in `## Exclusions`.
    """
    labels: list = []
    for builder in _CONCRETE_NEXT_PHASE_DISPATCH.values():
        # Each builder is a closure that needs PlannerInputs; we only
        # need its label, so build a sentinel inputs object that has just
        # the fields the builder reads (the recent-deps helper tolerates
        # an empty closed_labels list).
        sentinel = PlannerInputs(
            repo_root=Path("."),
            loop_state={},
            summary_mtime=None,
            review_mtime=None,
            evidence_captured_ats={},
            evidence_missing=[],
            phase_plan_text="",
            existing_labels=set(),
            closed_labels=[],
            task_md_text="",
            roadmap_md_text="",
            proposed_phase_existing=None,
        )
        labels.append(builder(sentinel).label)
    return labels


def generate_proposal_draft(inputs: PlannerInputs) -> Optional[ProposalDraft]:
    """Produce a concrete next-sub-phase proposal via the dispatch table.

    Returns the concrete ProposalDraft for the matched active sub-phase
    prefix, or `None` if no concrete proposal is registered for the
    current active sub-phase. The Phase 4A contract forbids vague
    meta-planning content; returning `None` here lets the caller refuse
    cleanly (with a clear `no_concrete_template` log line) rather than
    emit a generic stub that the per-proposal validator would have to
    reject anyway.
    """
    active_sub_phase = inputs.loop_state.get("sub_phase") or ""
    if not active_sub_phase:
        return None
    prefix_match = _SUBPHASE_TOKEN_RE.search(active_sub_phase)
    if prefix_match is None:
        return None
    prefix = f"Phase {prefix_match.group(1)}{prefix_match.group(2).upper()}"
    builder = _CONCRETE_NEXT_PHASE_DISPATCH.get(prefix)
    if builder is None:
        return None
    return builder(inputs)


def validate_proposal_against_contract(
    draft: ProposalDraft, inputs: PlannerInputs,
) -> Optional[str]:
    """Apply the Phase 4A bounded-scope and refusal rules that depend on
    the generated proposal's own content. Returns a human-readable reason
    string when the draft must be refused, or None when it is acceptable.
    """
    if not draft.label or " - " not in draft.label:
        return "## Label is empty or does not follow the 'Phase X - description' convention"
    if not draft.objective.strip():
        return "## Objective body is empty"
    if not draft.definition_of_done:
        return "## Definition of done has no bullets"
    if not draft.exclusions:
        return "## Exclusions has no bullets"
    if not draft.files_likely_involved:
        return "## Files likely involved has no bullets"
    if not draft.risk_areas:
        return "## Risk areas has no bullets"

    # Label collision against existing historical sub-phase labels. Run
    # this before content-quality checks so label problems surface with
    # the most-specific reason; the contract forbids re-use of labels
    # under any circumstances.
    if _label_exists(draft.label, inputs.existing_labels):
        return (
            f"## Label {draft.label!r} collides with an existing phase-plan heading "
            f"(re-use of labels is forbidden by the Phase 4A contract)"
        )

    # Bounded-scope: the Objective must be concrete, not meta-planning prose.
    # The Phase 4A contract: "concrete, actionable, in the present tense.
    # Vague language ('improve X', 'refactor Y to be better') is forbidden."
    objective_low = draft.objective.lower()
    for phrase in VAGUE_OBJECTIVE_PHRASES:
        if phrase in objective_low:
            return (
                f"## Objective contains vague meta-planning phrase {phrase!r}; "
                f"the Phase 4A contract requires concrete, actionable, present-tense "
                f"description of the work the proposed sub-phase performs"
            )

    # Bounded-scope: `## Exclusions` must explicitly enumerate every
    # later 4x / 5+ sub-phase the proposal does NOT cover. The planner
    # enforces a concrete floor (Phase 5 / 6 / 7 / 8) AND any deferred
    # 4x sub-phase known to the dispatch table other than the proposed
    # one itself.
    exclusions_text = "\n".join(draft.exclusions)
    missing_floor: list = []
    for marker in REQUIRED_EXCLUSIONS_FLOOR:
        if marker not in exclusions_text:
            missing_floor.append(marker)
    if missing_floor:
        return (
            f"## Exclusions does not enumerate the required later sub-phases: "
            f"{missing_floor}; the Phase 4A contract requires every later "
            f"4x / 5+ sub-phase the proposal does not cover to appear here"
        )
    proposed_prefix = draft.label.split(" - ", 1)[0].strip()
    deferred_4x_missing: list = []
    for deferred_label in _known_deferred_4x_labels():
        deferred_prefix = deferred_label.split(" - ", 1)[0].strip()
        if deferred_prefix == proposed_prefix:
            continue
        if deferred_prefix not in exclusions_text:
            deferred_4x_missing.append(deferred_label)
    if deferred_4x_missing:
        return (
            f"## Exclusions does not enumerate the deferred 4x sub-phases this "
            f"proposal does not cover: {deferred_4x_missing}; each must be "
            f"explicitly listed (by `Phase 4x` prefix)"
        )

    # Bounded-scope: at most PROPOSAL_MAX_FILES file paths.
    if len(draft.files_likely_involved) > PROPOSAL_MAX_FILES:
        return (
            f"## Files likely involved lists {len(draft.files_likely_involved)} files "
            f"(> {PROPOSAL_MAX_FILES}); split the proposal into smaller sub-phases"
        )

    # Bounded-scope: at most one contract revision.
    rcc = draft.required_contract_changes
    if isinstance(rcc, list):
        if len(rcc) > PROPOSAL_MAX_CONTRACT_REVISIONS:
            return (
                f"## Required contract changes lists {len(rcc)} revisions "
                f"(> {PROPOSAL_MAX_CONTRACT_REVISIONS}); split into separate "
                f"sequential sub-phases"
            )
    elif isinstance(rcc, str):
        # "None" or a single textual revision; nothing further to enforce here.
        pass
    else:
        return "## Required contract changes must be 'None' or a list of revisions"

    # Bounded-scope: at least one testable Definition-of-done bullet.
    if not _any_dod_bullet_is_testable(draft.definition_of_done):
        return (
            "## Definition of done has no bullet that names a file path, CLI verb, "
            "validator outcome, or similar verifiable end state"
        )
    # Bounded-scope: vague-language bullets in Definition of done are refused
    # (each bullet must also not be a pure vague-language sentence).
    for bullet in draft.definition_of_done:
        low = bullet.lower()
        if any(phrase in low for phrase in VAGUE_DOD_PHRASES):
            return (
                f"## Definition of done bullet uses vague language "
                f"forbidden by the Phase 4A contract: {bullet!r}"
            )

    # Bounded-scope: cycle-size estimate.
    if not isinstance(draft.cycle_size_estimate, int) or draft.cycle_size_estimate < 1:
        return "## Cycle-size estimate must be a positive integer"
    if (
        draft.cycle_size_estimate > PROPOSAL_DEFAULT_MAX_CYCLE_SIZE
        and not (draft.cycle_size_justification or "").strip()
    ):
        return (
            f"## Cycle-size estimate {draft.cycle_size_estimate} > "
            f"{PROPOSAL_DEFAULT_MAX_CYCLE_SIZE} requires an explicit justification "
            f"paragraph"
        )

    # Dependencies: each must use an allowed status token; no dependency may
    # be in a blocking status (`active-in-flight`, `pending`).
    if not draft.dependencies:
        return "## Dependencies has no entries"
    for dep_label, dep_status in draft.dependencies:
        if dep_status not in DEPENDENCY_STATUS_TOKENS:
            return (
                f"## Dependencies entry {dep_label!r} has status {dep_status!r}; "
                f"allowed tokens: {sorted(DEPENDENCY_STATUS_TOKENS)}"
            )
        if dep_status in DEPENDENCY_BLOCKING_STATUSES:
            return (
                f"## Dependencies entry {dep_label!r} has blocking status "
                f"{dep_status!r}; a proposal that depends on an active-in-flight "
                f"or pending phase is invalid per the Phase 4A contract"
            )

    # Self-approval guard: the planner must never write APPROVED_FOR_ACTIVATION
    # into a proposal it authored.
    serialized = serialize_proposal(draft)
    if APPROVAL_TOKEN in serialized:
        return (
            f"draft contains the literal {APPROVAL_TOKEN!r} token; self-approval "
            f"is forbidden by the Phase 4A contract"
        )

    return None


def _any_dod_bullet_is_testable(bullets: list) -> bool:
    for bullet in bullets:
        low = bullet.lower()
        if any(marker.lower() in low for marker in TESTABLE_DOD_MARKERS):
            return True
    return False


def serialize_proposal(draft: ProposalDraft) -> str:
    """Render a ProposalDraft into the markdown structure the Phase 4A
    contract requires. Section order is fixed; each section must have a
    non-empty body.
    """
    def bullets(items: list) -> str:
        return "\n".join(f"- {it}" for it in items)

    rcc = draft.required_contract_changes
    if isinstance(rcc, list) and rcc:
        rcc_body = bullets(rcc)
    elif isinstance(rcc, str) and rcc.strip():
        rcc_body = rcc.strip()
    else:
        rcc_body = "None"

    if draft.cycle_size_justification:
        cycle_body = (
            f"{draft.cycle_size_estimate}\n\n{draft.cycle_size_justification.strip()}"
        )
    else:
        cycle_body = str(draft.cycle_size_estimate)

    dep_lines = [f"- {lbl}: {st}" for lbl, st in draft.dependencies]
    dep_body = "\n".join(dep_lines)

    sections = [
        (PROPOSAL_TITLE, ""),
        ("## Label", draft.label),
        ("## Objective", draft.objective.strip()),
        ("## Definition of done", bullets(draft.definition_of_done)),
        ("## Exclusions", bullets(draft.exclusions)),
        ("## Files likely involved", bullets(draft.files_likely_involved)),
        ("## Required contract changes", rcc_body),
        ("## Cycle-size estimate", cycle_body),
        ("## Dependencies", dep_body),
        ("## Risk areas", bullets(draft.risk_areas)),
    ]
    parts: list = []
    for header, body in sections:
        if header == PROPOSAL_TITLE:
            parts.append(header)
            continue
        parts.append("")
        parts.append(header)
        parts.append("")
        parts.append(body)
    return "\n".join(parts).rstrip() + "\n"


def validate_proposal_structure(text: str) -> Optional[str]:
    """Structural re-check on the serialized proposal text. Mirrors the
    artifact validators used by the orchestrator for Claude / Codex
    artifacts: header order + non-empty bodies. Returns None on success.
    """
    if not text.startswith(PROPOSAL_TITLE):
        return f"missing title header {PROPOSAL_TITLE!r}"
    cursor = 0
    for header in PROPOSAL_REQUIRED_SECTIONS:
        idx = text.find(header, cursor)
        if idx == -1:
            return f"missing required header {header!r} (or out of order)"
        cursor = idx + len(header)
    # Each required section must have a non-empty body before the next header.
    for i, header in enumerate(PROPOSAL_REQUIRED_SECTIONS):
        start = text.find(header) + len(header)
        if i + 1 < len(PROPOSAL_REQUIRED_SECTIONS):
            end = text.find(PROPOSAL_REQUIRED_SECTIONS[i + 1], start)
        else:
            end = len(text)
        body = text[start:end].strip()
        if not body:
            return f"section {header!r} has an empty body"
    return None


def write_proposal(repo_root: Path, text: str) -> Path:
    """Write the proposal file. The planner is allowed to write only
    `.agent-loop/proposed-phase.md`; this helper exists so the file path
    is centralized and the planner never opens any other path for write.
    """
    path = _proposal_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run_planner(repo_root: Path) -> int:
    """End-to-end planner cycle: load -> refuse -> generate -> validate -> write.

    Returns 0 when a valid proposal was written, 2 on any refusal or
    structural failure. Always best-effort logs a single line to
    `.agent-loop/planner.log` describing the outcome.
    """
    try:
        inputs = load_planner_inputs(repo_root)
    except HaltError as halt:
        _planner_log_note(
            repo_root,
            f"refused [{halt.status}]: cannot load planner inputs: {halt.reason}",
        )
        print(
            f"[planner] refused: cannot load planner inputs: {halt.reason}",
            file=sys.stderr,
        )
        return 2

    refusal = check_planner_refusal(inputs)
    if refusal is not None:
        _planner_log_note(
            repo_root, f"refused [{refusal.code}]: {refusal.reason}",
        )
        print(
            f"[planner] refused [{refusal.code}]: {refusal.reason}",
            file=sys.stderr,
        )
        return 2

    draft = generate_proposal_draft(inputs)
    if draft is None:
        active_sub_phase = inputs.loop_state.get("sub_phase") or "(unset)"
        reason = (
            f"no concrete next-phase template registered for active sub-phase "
            f"{active_sub_phase!r}; a vague stub is explicitly refused by the "
            f"Phase 4A contract, so a human must extend the planner's "
            f"_CONCRETE_NEXT_PHASE_DISPATCH table before re-running"
        )
        _planner_log_note(repo_root, f"refused [no_concrete_template]: {reason}")
        print(
            f"[planner] refused [no_concrete_template]: {reason}",
            file=sys.stderr,
        )
        return 2
    draft_problem = validate_proposal_against_contract(draft, inputs)
    if draft_problem is not None:
        _planner_log_note(
            repo_root, f"refused [draft_invalid]: {draft_problem}",
        )
        print(
            f"[planner] refused [draft_invalid]: {draft_problem}",
            file=sys.stderr,
        )
        return 2

    text = serialize_proposal(draft)
    struct_problem = validate_proposal_structure(text)
    if struct_problem is not None:
        _planner_log_note(
            repo_root, f"refused [serialization]: {struct_problem}",
        )
        print(
            f"[planner] refused [serialization]: {struct_problem}",
            file=sys.stderr,
        )
        return 2

    # Final guard: the serialized proposal must NOT carry the approval
    # token. Self-approval is forbidden by the Phase 4A contract.
    if APPROVAL_TOKEN in text:
        _planner_log_note(
            repo_root,
            f"refused [self_approval]: serialized proposal contained "
            f"{APPROVAL_TOKEN!r}",
        )
        print(
            f"[planner] refused [self_approval]: serialized proposal contained "
            f"{APPROVAL_TOKEN!r}",
            file=sys.stderr,
        )
        return 2

    path = write_proposal(repo_root, text)
    _planner_log_note(
        repo_root,
        f"proposal written [{PLANNER_VERSION}]: {draft.label}",
    )
    print(f"[planner] proposal written: {path}")
    return 0


# ----- Phase 4E planner-adapter seam -----
#
# Phase 4E routes planner execution through a dedicated adapter boundary
# instead of hard-wiring the `plan` CLI path and the post-approval refresh
# to a direct `run_planner` call. This is a narrow dispatch seam, not a
# behavior change: the only shipped adapter is the in-process default,
# which runs `run_planner` unchanged, so the planner's write boundary
# (`.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` only),
# refusal semantics, and exception/return-code contract are identical to
# Phases 4B-4D. The seam exists so a later slice can supply an alternate
# planner adapter (e.g. out-of-process execution) without touching the
# call sites, and so the boundary stays monkeypatchable in tests. The
# adapter never activates a proposal.

PLANNER_ADAPTER_VERSION = "phase-4e-v0"


class LocalPlannerAdapter:
    """Default planner adapter: in-process `run_planner`.

    Preserves today's local behavior exactly - same refusal handling,
    same exception/return-code contract, and the same write boundary
    (`.agent-loop/proposed-phase.md` and `.agent-loop/planner.log` only).
    `run` is a thin pass-through; it does not widen writes or activate.
    `run_planner` is resolved as a module global at call time, so tests
    that monkeypatch `agent_loop.run_planner` still take effect through
    the adapter.
    """

    name = "local"

    def run(self, repo_root: Path) -> int:
        return run_planner(repo_root)


def make_planner_adapter():
    """Factory: the Phase 4E planner-execution seam.

    Both the `plan` CLI path (`cmd_plan`) and the post-approval planner
    refresh (`_invoke_post_approval_planner`) call this factory and then
    its `run` method instead of calling `run_planner` directly, so all
    planner dispatch flows through one adapter boundary. Today the only
    adapter is the in-process `LocalPlannerAdapter` (the default), which
    preserves current behavior. Selecting an alternate adapter is
    deferred; introducing the seam does not widen the planner write
    boundary and never auto-activates. The core paths call this factory
    rather than instantiating the adapter directly so monkey-patching the
    adapter (or this factory) at the module level works for tests.
    """
    return LocalPlannerAdapter()


# ----- Phase 4C activation (consume approved proposal -> activation writes) -----
#
# This block implements the activation step the Phase 4A Planning Contract
# (`.agent-loop/phase-plan.md` -> "## Phase 4A - Planning Contract") permits
# only AFTER an explicit human approval signal. It is a separate CLI path
# (`python scripts/agent_loop.py activate`); it is NOT folded into `plan`,
# and Phase 4D planner-orchestrator auto-integration remains out of scope.
#
# Inputs the activator reads (read-only outside its allowed-writes set):
#   - .agent-loop/proposed-phase.md (the planner-authored proposal)
#   - .agent-loop/loop-state.json (so the activation's loop-state rewrite
#     preserves the orchestrator-owned runtime fields per the Phase 3A
#     contract)
#   - TASK.md (so `## Human Objective` and `## Project Intent` can be
#     preserved verbatim)
#   - .agent-loop/phase-plan.md (so the new section is appended and the
#     `## Active Phase` line is updated in place)
#   - ROADMAP.md (used to resolve the parent phase's human-readable name,
#     e.g. `Phase 4 - Phase Planning Automation`, from the sub-phase
#     prefix in the proposal's `## Label`)
#
# Approval requirements (exactly):
#   - the proposal must carry a `## Approval` section whose body contains
#     the literal `APPROVED_FOR_ACTIVATION` token on its own line within
#     that section (whole-file substring matching is explicitly NOT used:
#     a stray token mention in unrelated prose cannot trigger activation)
#   - the same section body must reference the proposal's `## Label`, so
#     a stale approval against a different label (e.g. an earlier draft
#     that was overwritten) is refused
#
# Allowed activation writes (Phase 4A + Phase 5F follow-up):
#   - TASK.md (rewrite the active-phase sections; preserve
#     `## Human Objective` and `## Project Intent` verbatim)
#   - .agent-loop/current-task.md and .agent-loop/current-phase.md
#   - .agent-loop/phase-plan.md (update `## Active Phase` and APPEND a
#     new sub-phase section; the activator also flips the previously-
#     active sub-phase's `### Status` opening line from `Active. ...` to
#     `Complete. Closed by activation of ...` as a transition-marking
#     edit so the phase-plan is internally consistent - the substantive
#     historical body content is not modified)
#   - .agent-loop/loop-state.json (reset `cycle_count = 0`,
#     `status = awaiting_claude_implementation`, `last_verdict = null`,
#     `last_verdict_phase = null`; set `phase` / `sub_phase` / `task`
#     from the approved proposal; preserve `max_cycles` /
#     `contract_version` / `claude_version` / `codex_version` /
#     `orchestrator_version` per the Phase 3A write-ownership rules)
#   - .agent-loop/planner.log (single `note:`-style line recording the
#     approval source: file path, mtime, literal approval line)
#   - .agent-loop/claude-prompt.md (Phase 5F phase-start prompt bootstrap
#     artifact synthesized immediately after a successful activation)
#   - .agent-loop/orchestrator.log (single `prompt bootstrap:` audit
#     note emitted by the Phase 5F follow-up)
#
# The activator never opens any other path for write. The planner's
# `plan` write boundary (only `.agent-loop/proposed-phase.md` and
# `.agent-loop/planner.log`) is unchanged outside this explicit
# activation path.

ACTIVATOR_VERSION = "phase-4c-v0"

ACTIVATOR_ALLOWED_WRITE_FILES = frozenset({
    "TASK.md",
    ".agent-loop/current-task.md",
    ".agent-loop/current-phase.md",
    ".agent-loop/phase-plan.md",
    ".agent-loop/loop-state.json",
    ".agent-loop/claude-prompt.md",
    ".agent-loop/orchestrator.log",
    PLANNER_LOG_PATH_REL,
})


@dataclass
class ApprovalSource:
    label: str
    approval_line: str
    file_path: Path
    file_mtime: float


@dataclass
class ActivationRefusal:
    code: str
    reason: str


def _extract_section_body(text: str, header: str) -> str:
    """Return the body text between `header` and the next top-level `## `
    header (or end of file). Returns empty string when header is absent
    or the body is whitespace-only.

    The header MUST appear at the start of a line (or as the first
    character of the file). This anchors `## Approval` matches to a
    real section header so that a documentary mention of `## Approval`
    inside an Objective body cannot be mistaken for the human-authored
    approval section.
    """
    pattern = re.compile(
        rf"(?:^|\n){re.escape(header)}(?=\s|$)", re.MULTILINE,
    )
    m = pattern.search(text)
    if m is None:
        return ""
    start = m.end()
    rest = text[start:]
    # Next top-level `## ` header on a fresh line ends the section.
    m2 = re.search(r"\n## ", rest)
    if m2 is not None:
        rest = rest[: m2.start()]
    return rest.strip()


def parse_proposal_sections(text: str) -> dict:
    """Return a dict of section header -> body for every required section
    in PROPOSAL_REQUIRED_SECTIONS. Bodies are stripped.
    """
    return {header: _extract_section_body(text, header) for header in PROPOSAL_REQUIRED_SECTIONS}


def check_approval(proposal_text: str, proposal_path: Path):
    """Return ApprovalSource on a valid approval signal, or
    ActivationRefusal on any failure. The check enforces three exact
    requirements per the Phase 4A contract:

      1. a `## Approval` section header is present
      2. the section body contains the literal `APPROVED_FOR_ACTIVATION`
         token on its own line (no extra words, no alternate
         capitalization, no leading/trailing characters)
      3. the section body references the proposal's `## Label` text
         verbatim (so a stale approval against a different label is
         rejected)
    """
    label_body = _extract_section_body(proposal_text, "## Label")
    label_lines = [ln.strip() for ln in label_body.splitlines() if ln.strip()]
    if not label_lines:
        return ActivationRefusal(
            "no_label",
            "proposal has no `## Label` body content; cannot verify approval",
        )
    label = label_lines[0]

    # Use a start-of-line anchored search so a documentary mention of
    # `## Approval` inside the Objective body cannot satisfy this check.
    # The human approval section must be an actual top-level `## ` header.
    approval_header_present = re.search(
        r"(?:^|\n)## Approval(?=\s|$)", proposal_text,
    ) is not None
    if not approval_header_present:
        return ActivationRefusal(
            "no_approval_section",
            f"proposal at {proposal_path} has no `## Approval` section header; "
            f"a human must append `## Approval` with the literal "
            f"`{APPROVAL_TOKEN}` token on its own line before activation",
        )
    approval_body = _extract_section_body(proposal_text, "## Approval")
    if not approval_body:
        return ActivationRefusal(
            "no_approval_section",
            f"proposal at {proposal_path} has an empty `## Approval` body; "
            f"the section must contain the literal `{APPROVAL_TOKEN}` token "
            f"on its own line",
        )

    found_line: Optional[str] = None
    for line in approval_body.splitlines():
        # Exact-line match: `line.strip() == APPROVAL_TOKEN` rejects any
        # capitalization variant ("approved_for_activation"), any extra
        # word on the line ("APPROVED_FOR_ACTIVATION yes"), and any
        # leading/trailing characters beyond whitespace.
        if line.strip() == APPROVAL_TOKEN:
            found_line = line.strip()
            break
    if found_line is None:
        return ActivationRefusal(
            "malformed_token",
            f"`## Approval` section does not contain the literal token "
            f"`{APPROVAL_TOKEN}` on its own line; alternate capitalization, "
            f"extra words on the same line, or surrounding characters are "
            f"refused",
        )

    if label not in approval_body:
        return ActivationRefusal(
            "label_mismatch",
            f"`## Approval` body does not reference the proposal's `## Label` "
            f"({label!r}); the approval may be stale or applied to a different "
            f"proposal draft",
        )

    return ApprovalSource(
        label=label,
        approval_line=found_line,
        file_path=proposal_path,
        file_mtime=proposal_path.stat().st_mtime,
    )


def _parse_label_parts(label: str):
    """Given a label like 'Phase 4C - Planner Activation Writes', return
    (parent_prefix='Phase 4', sub_prefix='Phase 4C'). Returns (None, None)
    when the label does not follow the convention.
    """
    m = _SUBPHASE_TOKEN_RE.search(label)
    if m is None:
        return None, None
    number = m.group(1)
    letter = m.group(2).upper()
    return f"Phase {number}", f"Phase {number}{letter}"


def _parent_phase_label_from_roadmap(roadmap_text: str, parent_prefix: str) -> str:
    """Find `## Phase N - <name>` in ROADMAP.md and return
    `Phase N - <name>` so the activator can set TASK.md's `## Active
    Phase` body correctly. Falls back to the bare prefix when ROADMAP
    has no matching heading (e.g. brand-new top-level phase).
    """
    pattern = re.compile(
        rf"^## ({re.escape(parent_prefix)}\s+-\s+[^\n]+)", re.MULTILINE,
    )
    m = pattern.search(roadmap_text)
    if m is not None:
        return m.group(1).strip()
    return parent_prefix


def _split_md_sections(text: str):
    """Return (preamble, [(header_line, body_text), ...]).

    Sections are split at any line beginning with `## `. The preamble is
    everything before the first such line; each section's body includes
    the trailing newlines up to the next `## ` line. Used so the
    activator can rewrite SPECIFIC `## ...` sections in TASK.md while
    leaving non-rewritable sections (`## Human Objective`, `## Project
    Intent`) and the preamble (`# TASK.md\n\n`) exactly as authored.
    """
    lines = text.splitlines(keepends=True)
    preamble_parts: list = []
    sections: list = []
    current_header: Optional[str] = None
    current_body: list = []
    for line in lines:
        if line.startswith("## "):
            if current_header is not None:
                sections.append((current_header, "".join(current_body)))
            current_header = line.rstrip("\n")
            current_body = []
        else:
            if current_header is None:
                preamble_parts.append(line)
            else:
                current_body.append(line)
    if current_header is not None:
        sections.append((current_header, "".join(current_body)))
    return "".join(preamble_parts), sections


def _rewrite_task_md(
    current_text: str, parent_phase_label: str, new_sub_phase: str,
    proposal_sections: dict,
) -> str:
    """Rewrite TASK.md's active-phase sections from the activated proposal
    while preserving `## Human Objective` and `## Project Intent`
    verbatim. Sections that do not exist in the current TASK.md are
    appended in the contract's specified order so a fresh-start
    repository still gets a well-formed file.
    """
    preamble, sections = _split_md_sections(current_text)
    objective = proposal_sections["## Objective"].strip()
    dod_bullets = proposal_sections["## Definition of done"].strip()
    excl_bullets = proposal_sections["## Exclusions"].strip()
    overrides = {
        "## Active Phase":
            f"\n{parent_phase_label}\n\n",
        "## Active Sub-Phase":
            f"\n{new_sub_phase}\n\n",
        "## Phase Status":
            (
                f"\n{new_sub_phase} active. Activated by "
                f"`python scripts/agent_loop.py activate` after a valid Phase 4A "
                f"approval signal on `.agent-loop/proposed-phase.md`. The active "
                f"proposal's `## Objective`, `## Definition of done`, and "
                f"`## Exclusions` drive the sections below.\n\n"
            ),
        "## Active Task":
            f"\n{objective}\n\n",
        "## Phase Outcome Required Now":
            f"\n{dod_bullets}\n\n",
        "## Next-Phase Gate":
            (
                "\nDo not start the next sub-phase until:\n\n"
                f"- this {new_sub_phase} slice receives `APPROVED_FOR_HUMAN_REVIEW`\n"
                "- the human explicitly approves moving to the next sub-phase\n"
                "- Codex updates `TASK.md`, `.agent-loop/current-task.md`, "
                "and `.agent-loop/current-phase.md` for the next sub-phase\n\n"
            ),
        "## Out Of Scope For Current Phase":
            f"\n{excl_bullets}\n",
    }
    # Preserve original section order; rewrite only the overridable ones.
    new_sections: list = []
    seen: set = set()
    for header, body in sections:
        if header in overrides:
            new_sections.append((header, overrides[header]))
        else:
            new_sections.append((header, body))
        seen.add(header)
    # Append any override sections that the current file lacked.
    for header, body in overrides.items():
        if header not in seen:
            new_sections.append((header, body))
    out = preamble
    for header, body in new_sections:
        out += header + "\n" + body
    return out


def _rewrite_current_task_md(
    new_sub_phase: str, parent_phase_label: str, proposal_sections: dict,
) -> str:
    objective = proposal_sections["## Objective"].strip()
    return (
        "# Current Task\n\n"
        "## Phase\n"
        f"{parent_phase_label}\n\n"
        "## Sub-Phase\n"
        f"{new_sub_phase}\n\n"
        "## Status\n"
        f"{new_sub_phase} active. Activated via `python scripts/agent_loop.py activate` "
        f"with a valid Phase 4A approval signal on `.agent-loop/proposed-phase.md`.\n\n"
        "## Task\n"
        f"{objective}\n"
    )


def _rewrite_current_phase_md(new_sub_phase: str, parent_phase_label: str) -> str:
    return (
        "# Current Phase\n\n"
        f"{parent_phase_label} (sub-phase: {new_sub_phase})\n"
    )


def _close_prior_active_status(
    text: str, new_sub_phase: str,
) -> str:
    """Flip the previously-active sub-phase's `### Status` opening line
    from `Active. ...` to `Complete. Closed by activation of ...`. This
    is a minimal, one-line transition-marking edit; the substantive
    body content (`### Objective`, `### Definition of done`,
    `### Exclusions`, etc.) of the previously-active sub-phase is left
    intact, so the historical record of WHAT each phase delivered is not
    rewritten. Without this edit phase-plan.md would carry two
    sub-phases simultaneously marked Active, which would be internally
    inconsistent.
    """
    pattern = re.compile(
        r"(## Phase\s+\S+\s+-\s+[^\n]+\n+### Status\n+)(Active\.[^\n]*)",
        re.MULTILINE,
    )
    new_first_line = (
        f"Complete. Closed by activation of {new_sub_phase}."
    )
    return pattern.sub(rf"\1{new_first_line}", text, count=1)


def _append_phase_plan_section(
    current_text: str, new_sub_phase: str, parent_phase_label: str,
    proposal_sections: dict,
) -> str:
    """Update `## Active Phase` line, close the previously-active
    sub-phase's `### Status` opening line, and APPEND a new sub-phase
    section that mirrors the activated proposal. Historical sub-phase
    BODIES (Objective / Definition of done / Exclusions) are never
    rewritten.
    """
    # 1. Update `## Active Phase` line (single replacement).
    text = re.sub(
        r"^(## Active Phase)\s*\n+([^\n]+)",
        lambda _m: f"{_m.group(1)}\n\n{parent_phase_label} (sub-phase: {new_sub_phase})",
        current_text, count=1, flags=re.MULTILINE,
    )
    # 2. Close the previously-active sub-phase's `### Status` opening line.
    text = _close_prior_active_status(text, new_sub_phase)
    # 3. APPEND a new sub-phase section that mirrors the activated proposal.
    appendage = (
        f"\n## {new_sub_phase}\n\n"
        f"### Status\n\n"
        f"Active. Activated by `python scripts/agent_loop.py activate` after a "
        f"valid Phase 4A approval signal on `.agent-loop/proposed-phase.md`.\n\n"
        f"### Objective\n\n"
        f"{proposal_sections['## Objective'].strip()}\n\n"
        f"### Definition of done\n\n"
        f"{proposal_sections['## Definition of done'].strip()}\n\n"
        f"### Exclusions\n\n"
        f"{proposal_sections['## Exclusions'].strip()}\n"
    )
    if not text.endswith("\n"):
        text += "\n"
    text += appendage
    return text


def _compute_activated_loop_state(
    current: dict, new_phase: str, new_sub_phase: str, new_task: str,
) -> dict:
    """Pure: compute the post-activation loop-state.json dict from the
    pre-activation state and the activated proposal. Separated from the
    write step so the atomic-or-rollback write helper can stage the
    serialized bytes alongside the other activation-owned writes.

    The Phase 4A contract authorizes the activator to set `phase` /
    `sub_phase` / `task` and reset `cycle_count` / `last_verdict` /
    `last_verdict_phase` on activation. Fields not named here are
    preserved verbatim, satisfying the Phase 3A "preserve `max_cycles` /
    `contract_version` / `claude_version` / `codex_version` /
    `orchestrator_version`" rule.

    Phase 5B (review-mode initial slice): newly activated runtime state
    also gets `approval_mode = "review"` (the Phase 5A-required default)
    and `awaiting_human_for = null` whenever those fields are not yet
    present, so a freshly activated phase starts in the baseline review
    mode with no pending human gate. A pre-existing `approval_mode` is
    preserved verbatim (so a human-or-Codex-selected mode survives
    activation); `awaiting_human_for` is always reset to null because
    activation itself clears the prior phase's gate.
    """
    merged = dict(current)
    merged.update({
        "phase": new_phase,
        "sub_phase": new_sub_phase,
        "task": new_task,
        "status": "awaiting_claude_implementation",
        "cycle_count": 0,
        "last_verdict": None,
        "last_verdict_phase": None,
    })
    if "approval_mode" not in merged or merged.get("approval_mode") in (None, ""):
        merged["approval_mode"] = DEFAULT_APPROVAL_MODE
    merged["awaiting_human_for"] = None
    return merged


def _serialize_loop_state_bytes(state: dict) -> bytes:
    return (json.dumps(state, indent=2) + "\n").encode("utf-8")


class _ActivationWriteError(Exception):
    """Raised by `_apply_activation_writes_atomically` when an
    activation-owned write fails. The caller routes to the
    `activation_write_failed` refusal code. By the time this exception
    is raised, the helper has already restored every activation-owned
    file to its exact pre-attempt bytes (or removed any files it had
    newly created), so the repository is guaranteed to be either fully
    activated or fully restored - never partially activated.
    """

    def __init__(self, failed_path: Path, reason: str) -> None:
        super().__init__(f"{failed_path}: {reason}")
        self.failed_path = failed_path
        self.reason = reason


_ACTIVATION_TMP_SUFFIX = ".tmp-activate"


def _apply_activation_writes_atomically(
    planned: list,
) -> None:
    """Apply each `(Path, bytes)` write in `planned` with all-or-nothing
    semantics across the group.

    Approach: snapshot pre-existing bytes for every planned-write path,
    then write each file via a same-directory temp file + `Path.replace`
    (atomic per-file on every supported platform). If any write raises
    `OSError`, roll back EVERY previously-applied write by either
    restoring the snapshotted bytes (for files that existed pre-attempt)
    or removing the file (for files that did not exist pre-attempt),
    then raise `_ActivationWriteError` so the caller can route the
    failure to the `activation_write_failed` refusal code.

    Stray temp files from the failed write are cleaned up best-effort
    before the exception is raised. Rollback errors are swallowed
    (best-effort) so a secondary failure during rollback cannot mask
    the primary write failure that triggered the rollback.
    """
    snapshots: list = []
    for path, _content in planned:
        original = path.read_bytes() if path.is_file() else None
        snapshots.append((path, original))
    written: list = []
    try:
        for path, content in planned:
            tmp_path = path.with_name(path.name + _ACTIVATION_TMP_SUFFIX)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_bytes(content)
            tmp_path.replace(path)
            written.append(path)
    except OSError as exc:
        failed_path = path  # The loop variable at the point of failure.
        # Clean up the failed write's temp file if it landed.
        try:
            tmp_path = failed_path.with_name(
                failed_path.name + _ACTIVATION_TMP_SUFFIX,
            )
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        # Roll back every previously-applied write to its exact
        # pre-attempt bytes (or remove it if it did not exist pre-attempt).
        for done_path in written:
            original = next(
                (orig for snap_path, orig in snapshots if snap_path == done_path),
                None,
            )
            try:
                if original is None:
                    if done_path.exists():
                        done_path.unlink()
                else:
                    done_path.write_bytes(original)
            except OSError:
                # Rollback is best-effort: a secondary OS error during
                # rollback must not mask the primary write failure.
                pass
        raise _ActivationWriteError(failed_path, str(exc)) from exc


def run_activation(repo_root: Path) -> int:
    """End-to-end activation cycle: load -> approve-check -> write -> log.

    Returns 0 on a successful activation, 2 on any refusal. Refusals
    append a `note:`-style line to `.agent-loop/planner.log` and leave
    every other file untouched.
    """
    al = repo_root / ".agent-loop"
    proposal_path = al / "proposed-phase.md"
    state_path = al / "loop-state.json"
    task_path = repo_root / "TASK.md"
    roadmap_path = repo_root / "ROADMAP.md"
    phase_plan_path = al / "phase-plan.md"
    current_task_path = al / "current-task.md"
    current_phase_path = al / "current-phase.md"
    prompt_path = al / "claude-prompt.md"

    if not proposal_path.exists():
        msg = (
            f"{PROPOSAL_PATH_REL} does not exist; activate requires an approved "
            f"proposal generated by `python scripts/agent_loop.py plan`"
        )
        _planner_log_note(repo_root, f"activation refused [no_proposal]: {msg}")
        print(f"[activate] refused [no_proposal]: {msg}", file=sys.stderr)
        return 2

    proposal_text = proposal_path.read_text(encoding="utf-8")
    approval = check_approval(proposal_text, proposal_path)
    if isinstance(approval, ActivationRefusal):
        _planner_log_note(
            repo_root, f"activation refused [{approval.code}]: {approval.reason}",
        )
        print(
            f"[activate] refused [{approval.code}]: {approval.reason}",
            file=sys.stderr,
        )
        return 2

    sections = parse_proposal_sections(proposal_text)
    for header in PROPOSAL_REQUIRED_SECTIONS:
        if not sections.get(header, "").strip():
            msg = f"required section {header!r} body is empty in {PROPOSAL_PATH_REL}"
            _planner_log_note(
                repo_root, f"activation refused [proposal_malformed]: {msg}",
            )
            print(
                f"[activate] refused [proposal_malformed]: {msg}",
                file=sys.stderr,
            )
            return 2

    parent_prefix, _sub_prefix = _parse_label_parts(approval.label)
    if parent_prefix is None:
        msg = (
            f"label {approval.label!r} does not follow the "
            f"`Phase NX - description` convention; cannot resolve parent phase"
        )
        _planner_log_note(
            repo_root, f"activation refused [label_unparseable]: {msg}",
        )
        print(f"[activate] refused [label_unparseable]: {msg}", file=sys.stderr)
        return 2

    if not state_path.exists():
        msg = (
            f"{state_path} does not exist; activate requires loop-state.json "
            f"to preserve orchestrator-owned runtime fields"
        )
        _planner_log_note(
            repo_root, f"activation refused [no_loop_state]: {msg}",
        )
        print(f"[activate] refused [no_loop_state]: {msg}", file=sys.stderr)
        return 2
    try:
        current_loop_state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"loop-state.json malformed: {exc}"
        _planner_log_note(
            repo_root, f"activation refused [loop_state_malformed]: {msg}",
        )
        print(
            f"[activate] refused [loop_state_malformed]: {msg}",
            file=sys.stderr,
        )
        return 2

    # Strict reads for the three activation-required inputs whose contents
    # the activator must preserve (TASK.md's `## Human Objective` /
    # `## Project Intent`, the entirety of phase-plan.md history, and the
    # ROADMAP.md parent-phase lookup body). Missing or unreadable inputs
    # are fail-closed: the activator MUST NOT synthesize replacement
    # content from an empty string, because doing so would silently
    # fabricate human-owned / historical state. The three reads happen
    # BEFORE any activation write so a refusal here leaves no
    # activation-owned file partially written.
    try:
        current_task_md = _read_text_strict(
            task_path,
            missing_code="task_md_missing",
            unreadable_code="task_md_unreadable",
        )
        roadmap_text = _read_text_strict(
            roadmap_path,
            missing_code="roadmap_missing",
            unreadable_code="roadmap_unreadable",
        )
        current_phase_plan = _read_text_strict(
            phase_plan_path,
            missing_code="phase_plan_missing",
            unreadable_code="phase_plan_unreadable",
        )
    except _ActivationInputError as err:
        _planner_log_note(
            repo_root, f"activation refused [{err.code}]: {err.reason}",
        )
        print(
            f"[activate] refused [{err.code}]: {err.reason}",
            file=sys.stderr,
        )
        return 2

    parent_phase_label = _parent_phase_label_from_roadmap(roadmap_text, parent_prefix)
    new_task_md = _rewrite_task_md(
        current_task_md, parent_phase_label, approval.label, sections,
    )

    new_current_task = _rewrite_current_task_md(
        approval.label, parent_phase_label, sections,
    )
    new_current_phase = _rewrite_current_phase_md(approval.label, parent_phase_label)

    new_phase_plan = _append_phase_plan_section(
        current_phase_plan, approval.label, parent_phase_label, sections,
    )

    # Stage every activation-owned write up front, then apply them
    # atomically as a group. The Phase 4A contract forbids leaving the
    # repository in a partially-activated state, so individual sequential
    # writes (which could fail mid-set after one or more files had
    # already been mutated) are unacceptable. The helper below uses
    # temp-file + Path.replace for each individual write AND restores
    # every earlier write on any failure, so the activation set as a
    # whole is fail-closed.
    new_loop_state = _compute_activated_loop_state(
        current_loop_state,
        new_phase=parent_phase_label,
        new_sub_phase=approval.label,
        new_task=sections["## Objective"].strip(),
    )

    # Phase 5F: synthesize the phase-start Claude prompt from the SAME
    # canonical fields that the activation writes are about to commit,
    # then include the prompt write in the same atomic-or-rollback
    # transaction as the other activation-owned files. This keeps the
    # activator fail-closed: if any planned write fails (including the
    # prompt write itself), every previously-applied write is rolled
    # back, so the repository is either fully activated WITH the prompt
    # or fully unmodified - never partially activated. The earlier
    # proposal-section validation (`for header in
    # PROPOSAL_REQUIRED_SECTIONS: ... empty body refusal`) already
    # guarantees the render inputs below are non-empty.
    new_claude_prompt = _render_phase_start_claude_prompt(
        sub_phase=approval.label,
        objective=sections["## Objective"].strip(),
        context=sections["## Objective"].strip(),
        required_work=sections["## Definition of done"].strip(),
        exclusions=sections["## Exclusions"].strip(),
    )

    planned_writes = [
        (task_path, new_task_md.encode("utf-8")),
        (current_task_path, new_current_task.encode("utf-8")),
        (current_phase_path, new_current_phase.encode("utf-8")),
        (phase_plan_path, new_phase_plan.encode("utf-8")),
        (state_path, _serialize_loop_state_bytes(new_loop_state)),
        (prompt_path, new_claude_prompt.encode("utf-8")),
    ]
    try:
        _apply_activation_writes_atomically(planned_writes)
    except _ActivationWriteError as err:
        msg = (
            f"activation-owned write failed on {err.failed_path}; all earlier "
            f"activation-owned files have been restored to their exact "
            f"pre-activation bytes. Underlying error: {err.reason}"
        )
        _planner_log_note(
            repo_root, f"activation refused [activation_write_failed]: {msg}",
        )
        print(
            f"[activate] refused [activation_write_failed]: {msg}",
            file=sys.stderr,
        )
        return 2

    # Phase 5F: log the prompt synthesis as a `note:` line so the
    # auto-bootstrap is auditable from .agent-loop/orchestrator.log the
    # same way the standalone `bootstrap-prompt` subcommand is. The
    # actual prompt bytes are already on disk via the atomic write above.
    _log_note(
        al / "orchestrator.log",
        (
            f"prompt bootstrap: wrote .agent-loop/claude-prompt.md for "
            f"sub_phase={approval.label!r} as part of the atomic activation "
            f"write set"
        ),
    )

    # Record the approval source per the Phase 4A contract: "the planner
    # must record the approval source (file path, mtime, and the literal
    # approval line) into .agent-loop/planner.log so the activation
    # chain is auditable." The success note is only ever appended when
    # the full activation-owned write set has been committed; on any
    # _ActivationWriteError the function has already returned 2 above.
    _planner_log_note(
        repo_root,
        (
            f"activated [{ACTIVATOR_VERSION}]: label={approval.label!r} "
            f"approval_source={approval.file_path} "
            f"approval_mtime={approval.file_mtime} "
            f"approval_line={approval.approval_line!r}"
        ),
    )
    print(f"[activate] activated: {approval.label}")
    return 0


# ----- cli -----

def cmd_check_state(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    try:
        data = load_loop_state(state_path)
        validate_loop_state(data)
    except HaltError as halt:
        print(f"check-state: {halt.status}: {halt.reason}", file=sys.stderr)
        return 2
    try:
        check_contract_version(data)
        contract_status = "ok"
        rc = 0
    except HaltError as halt:
        contract_status = f"{halt.status}: {halt.reason}"
        rc = 2
    snapshot = {
        "repo_root": str(repo_root),
        "orchestrator_version": ORCHESTRATOR_VERSION,
        "state": {
            k: data.get(k)
            for k in (
                "phase", "sub_phase", "task", "status",
                "cycle_count", "max_cycles",
                "contract_version",
                "claude_version", "codex_version", "orchestrator_version",
                "last_verdict", "last_verdict_phase",
            )
        },
        "contract_version_check": contract_status,
    }
    print(json.dumps(snapshot, indent=2))
    return rc


def cmd_validate_artifacts(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    try:
        data = load_loop_state(state_path)
        validate_loop_state(data)
    except HaltError as halt:
        print(
            f"validate-artifacts: cannot load loop-state.json: "
            f"{halt.status}: {halt.reason}",
            file=sys.stderr,
        )
        return 2
    checks: list[tuple[str, Callable[[], None]]] = [
        (
            "claude-summary",
            lambda: validate_claude_summary(
                al / "claude-summary.md",
                data["phase"], data.get("sub_phase"),
            ),
        ),
        (
            "codex-review",
            lambda: validate_codex_review_and_parse_verdict(
                al / "codex-review.md",
            ),
        ),
        (
            "evidence",
            lambda: validate_evidence_files(repo_root),
        ),
    ]
    if (al / "fix-prompt.md").exists():
        checks.insert(
            2,
            ("fix-prompt", lambda: validate_fix_prompt(al / "fix-prompt.md")),
        )
    any_fail = False
    for name, fn in checks:
        try:
            fn()
        except HaltError as halt:
            print(f"{name}: FAIL [{halt.status}] {halt.reason}")
            any_fail = True
            continue
        print(f"{name}: ok")
    return 2 if any_fail else 0


def cmd_run(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    return run_normal_cycle(repo_root)


def cmd_plan(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    return make_planner_adapter().run(repo_root)


def cmd_activate(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    return run_activation(repo_root)


def cmd_build_continuation_context(args: argparse.Namespace) -> int:
    """Phase 6H operator runtime path: build a structured continuation
    prompt/context dict from canonical artifacts + the active
    checkpoint + bounded evidence + advisory memory, and persist it to
    `.agent-loop/continuation-context.json` (or the path supplied via
    `--output`) so the construction is auditable from on-disk
    artifacts.

    The artifact is regenerable from canonical state at any time; this
    handler always overwrites it (NOT append-mostly) because it is an
    audit/inspection artifact, not a canonical store. Refusal routes
    through `_halt` so the structural failure vocabulary lands on disk
    for human inspection, matching the other top-level `cmd_*`
    refusals.
    """
    repo_root = find_repo_root()
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    log_path = al / "orchestrator.log"
    output_path = (
        Path(args.output) if args.output is not None
        else repo_root / CONTINUATION_CONTEXT_OUTPUT_REL
    )
    if not output_path.is_absolute():
        output_path = (repo_root / output_path).resolve()
    kwargs: dict = {}
    if args.memory_entry_limit is not None:
        kwargs["memory_entry_limit"] = args.memory_entry_limit
    if args.evidence_byte_limit is not None:
        kwargs["evidence_byte_limit"] = args.evidence_byte_limit
    try:
        payload = build_continuation_prompt_context(
            repo_root, log_path=log_path, **kwargs,
        )
    except HaltError as halt:
        try:
            data = load_loop_state(state_path)
        except HaltError:
            data = {}
        return _halt(state_path, data, halt, log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    try:
        rel = output_path.relative_to(repo_root).as_posix()
    except ValueError:
        rel = str(output_path)
    print(
        f"[orchestrator] continuation context written to {rel}; "
        f"see {log_path.relative_to(repo_root).as_posix()} for the "
        f"`continuation context built:` audit note."
    )
    return 0


def cmd_auto_continue(_args: argparse.Namespace) -> int:
    """Phase 6G operator runtime path: bounded automatic continuation
    chaining over the shipped Phase 6F single-hop resume.

    Dispatches to `run_auto_continue(...)`, which performs up to
    `AUTO_CONTINUE_MAX_HOPS` token-exhaustion resume hops in a single
    invocation while the persisted halt status keeps re-entering
    `HALTED_TOKEN_EXHAUSTION`. The standard single-hop `resume` is
    unchanged; this is an additional operator entry-point for the
    chained case.
    """
    repo_root = find_repo_root()
    return run_auto_continue(repo_root)


def cmd_record_token_exhaustion(args: argparse.Namespace) -> int:
    """Phase 6F operator runtime path: classify the current cycle as
    interrupted by token / context exhaustion.

    This subcommand is the wired runtime entry for `record_token_exhaustion`:
    when the operator (or a higher-layer supervisor process) observes that
    Claude or Codex ran out of context mid-cycle, running this command
    persists the Phase 6D checkpoint and transitions loop-state to
    `HALTED_TOKEN_EXHAUSTION` so the halt is auditable from the canonical
    state artifacts. The operator then runs `resume` to consume the
    bounded continuation budget and dispatch the cycle's continuation.

    Refusal goes through `_halt` so the saved `halted_input_missing`
    status is left on disk for human inspection - same pattern as the
    other top-level `cmd_*` halts (cycle-start input refusal, evidence
    refusal, etc.).
    """
    repo_root = find_repo_root()
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    log_path = al / "orchestrator.log"
    kwargs = {"active_prompt_path": args.active_prompt_path}
    if args.continuation_budget is not None:
        kwargs["continuation_budget"] = args.continuation_budget
    try:
        path = record_token_exhaustion(repo_root, log_path=log_path, **kwargs)
    except HaltError as halt:
        try:
            data = load_loop_state(state_path)
        except HaltError:
            data = {}
        return _halt(state_path, data, halt, log_path)
    rel = path.relative_to(repo_root).as_posix()
    print(
        f"[orchestrator] token-exhaustion recorded: checkpoint={rel}; "
        f"loop-state now at {HALTED_TOKEN_EXHAUSTION!r}. Run `resume` to "
        f"consume the bounded continuation budget."
    )
    return 0


def run_strict_resume(repo_root: Path) -> int:
    """Resume a cycle that was paused at a Phase 5C strict-mode gate.

    Refuses unless BOTH (a) `status` is one of the four
    `halted_awaiting_human_*` strict-gate values AND (b) `approval_mode`
    is still `"strict"`. Condition (b) prevents a paused strict cycle
    from being silently resumed under different mode semantics (e.g. a
    human or test mutating `approval_mode` from `"strict"` to `"review"`
    after the cycle halted at the pre_claude_prompt gate, to skip the
    later pre_codex_review gate). Per the Phase 5A contract, changing
    `approval_mode` mid-cycle is a human-directed control action; the
    safe resume contract is "the mode that fired the gate is the mode
    that resumes the gate." A mid-cycle mode change is refused fail
    closed and the explicit `halted_input_missing` refusal stays on
    disk for human inspection.

    On success: clears `awaiting_human_for`, restores a ready-to-continue
    status, logs a `note:` line, and dispatches to the continuation
    point matched by the persisted gate halt-status so no earlier work
    is re-done and the next gate (if the same cycle has one) still fires.
    """
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    log_path = al / "orchestrator.log"

    try:
        data = load_loop_state(state_path)
        validate_loop_state(data)
        check_contract_version(data)
    except HaltError as halt:
        return _halt(state_path, {} if "data" not in dir() else data, halt, log_path)

    status = data.get("status")
    if status not in STRICT_GATE_HALT_STATUSES:
        return _halt(
            state_path, data,
            HaltError(
                "halted_input_missing",
                (
                    f"resume requires loop-state.json status to be one of "
                    f"{sorted(STRICT_GATE_HALT_STATUSES)}; got {status!r}. "
                    f"resume is only valid after a Phase 5C strict-mode gate "
                    f"halted the cycle."
                ),
            ),
            log_path,
        )

    # Mode-coherence: a strict-gate halt may only be resumed under the
    # same mode that fired the gate. Mutating `approval_mode` from
    # "strict" to anything else between the halt and the resume would
    # let later gates be silently skipped, which the Phase 5A contract
    # forbids ("changing approval_mode mid-cycle ... must not silently
    # resume an already-in-flight step under different semantics").
    #
    # The refusal must NOT overwrite the saved strict-gate `status` or
    # `awaiting_human_for`. Going through `_halt(...)` would clobber
    # `status` with `halted_input_missing` and destroy the recovery
    # point - the operator could correct `approval_mode` back to
    # "strict" and rerun resume but the original gate's halt status
    # would be gone, so resume would refuse again on the
    # status-not-in-strict-gates branch. Instead we leave the saved
    # gate state intact, log the refusal note, print to stderr, and
    # return 2. After the operator restores `approval_mode = "strict"`,
    # a fresh `resume` invocation sees the original gate halt status
    # and the original `awaiting_human_for`, and continues the cycle
    # from the correct continuation point.
    approval_mode = data.get("approval_mode")
    if approval_mode != APPROVAL_MODE_STRICT:
        reason = (
            f"resume refused: paused at strict gate {status!r} "
            f"(awaiting_human_for={data.get('awaiting_human_for')!r}) "
            f"but approval_mode is {approval_mode!r}, not "
            f"{APPROVAL_MODE_STRICT!r}. A strict-mode pause may only be "
            f"resumed under approval_mode={APPROVAL_MODE_STRICT!r}; "
            f"changing approval_mode mid-cycle is a human-directed "
            f"control action and must not bypass later strict gates. "
            f"The saved strict-gate state is preserved; restore "
            f"approval_mode={APPROVAL_MODE_STRICT!r} and rerun resume to "
            f"continue the original cycle."
        )
        print(
            f"[orchestrator] STRICT RESUME REFUSED: {reason}",
            file=sys.stderr,
        )
        _log_note(log_path, f"strict resume refused: {reason}")
        return 2

    # Phase 6E checkpoint-backed resume validation.
    #
    # The Phase 6A contract treats checkpoint memory as advisory for
    # strict-gate resume: a missing checkpoint must not block a resume
    # the canonical loop-state already supports (backward compatibility
    # with pre-6D paused cycles), but a checkpoint that exists and
    # disagrees with the canonical loop-state must refuse fail-closed.
    # Same recovery pattern as the mode-coherence refusal above: leave
    # the saved strict-gate state intact (do NOT route through `_halt`,
    # which would overwrite `status` with `halted_input_missing` and
    # destroy the recovery point), log the refusal, and exit 2.
    try:
        checkpoint = _load_active_checkpoint(repo_root)
    except HaltError as halt:
        reason = (
            f"strict resume refused: malformed or unrecognized checkpoint "
            f"artifact: {halt.reason}"
        )
        print(
            f"[orchestrator] STRICT RESUME REFUSED: {reason}",
            file=sys.stderr,
        )
        _log_note(log_path, f"strict resume refused: {reason}")
        return 2
    if checkpoint is not None:
        try:
            _validate_checkpoint_against_loop_state(checkpoint, data)
        except HaltError as halt:
            reason = (
                f"strict resume refused: checkpoint inconsistent with "
                f"loop-state: {halt.reason}"
            )
            print(
                f"[orchestrator] STRICT RESUME REFUSED: {reason}",
                file=sys.stderr,
            )
            _log_note(log_path, f"strict resume refused: {reason}")
            return 2
        _log_note(
            log_path,
            (
                f"checkpoint validated for resume: "
                f"phase={checkpoint['phase']!r} "
                f"sub_phase={checkpoint['sub_phase']!r} "
                f"cycle_count={checkpoint['cycle_count']} "
                f"suspension_reason={checkpoint['suspension_reason']!r}"
            ),
        )

    _log_note(
        log_path,
        (
            f"strict resume: {status} -> human approved; continuing. "
            f"awaiting_human_for cleared, prior value="
            f"{data.get('awaiting_human_for')!r}"
        ),
    )

    if status == HALTED_PRE_CLAUDE_PROMPT:
        data = save_loop_state(state_path, data, {
            "status": "awaiting_claude_implementation",
            "awaiting_human_for": None,
        })
        return _run_normal_cycle_from_increment(repo_root, data, log_path)

    if status == HALTED_PRE_CODEX_REVIEW_NORMAL:
        # Continuation immediately sets `awaiting_codex_review`; the
        # intermediate status only needs to be non-halt so the resume
        # write is meaningful in the log. Use the same "evidence done,
        # about to review" value the pre-gate write left visible.
        data = save_loop_state(state_path, data, {
            "status": "evidence_capture",
            "awaiting_human_for": None,
        })
        return _run_normal_cycle_codex_review_step(repo_root, data, log_path)

    if status == HALTED_PRE_FIX_PROMPT:
        data = save_loop_state(state_path, data, {
            # The post-NEEDS_FIXES state in `_handle_verdict_loop` left
            # `last_verdict = NEEDS_FIXES` and `status = halted_*`;
            # _run_fix_cycle expects to do its own increment + status
            # write, so any non-halt status here is fine.
            "status": "awaiting_claude_implementation",
            "awaiting_human_for": None,
        })
        try:
            verdict, data, review = _run_fix_cycle(state_path, data, repo_root, log_path)
        except _FixCycleHalt as halted:
            return halted.exit_code
        return _handle_verdict_loop(
            state_path, data, verdict, repo_root, log_path, review=review,
        )

    # HALTED_PRE_CODEX_REVIEW_FIX
    data = save_loop_state(state_path, data, {
        "status": "evidence_capture",
        "awaiting_human_for": None,
    })
    try:
        verdict, data, review = _run_fix_cycle_codex_review_step(
            state_path, data, repo_root, log_path,
        )
    except _FixCycleHalt as halted:
        return halted.exit_code
    return _handle_verdict_loop(
        state_path, data, verdict, repo_root, log_path, review=review,
    )


def cmd_resume(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    # Phase 6F routing: inspect the persisted halt status BEFORE
    # entering the strict-resume path. A `HALTED_TOKEN_EXHAUSTION`
    # status dispatches to the token-exhaustion continuation; every
    # other status (including the four strict-gate halts and any
    # invalid resume state) routes to the existing `run_strict_resume`
    # which preserves the Phase 5C behavior unchanged.
    #
    # Routing is load-bearing: `run_strict_resume`'s initial
    # "status-is-a-strict-gate-halt" check uses `_halt`, which would
    # clobber `HALTED_TOKEN_EXHAUSTION` if it ever ran on that status.
    # Inspecting status here keeps the token-exhaustion recovery point
    # safe.
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    try:
        data = load_loop_state(state_path)
    except HaltError:
        # Defer to run_strict_resume so the existing missing-loop-state
        # halt path runs unchanged.
        return run_strict_resume(repo_root)
    if data.get("status") == HALTED_TOKEN_EXHAUSTION:
        return run_token_exhaustion_resume(repo_root)
    return run_strict_resume(repo_root)


# Phase 5F automatic phase-start Claude prompt bootstrap.

# H2 sections the bootstrap requires in TASK.md.
PROMPT_BOOTSTRAP_REQUIRED_TASK_SECTIONS = (
    "## Active Phase",
    "## Active Sub-Phase",
    "## Active Task",
    "## Phase Outcome Required Now",
    "## Out Of Scope For Current Phase",
)

# H2 sections the bootstrap requires in .agent-loop/current-task.md.
PROMPT_BOOTSTRAP_REQUIRED_CURRENT_TASK_SECTIONS = (
    "## Phase",
    "## Sub-Phase",
    "## Task",
)

# H3 subsections the bootstrap requires inside the active sub-phase block
# of .agent-loop/phase-plan.md.
PROMPT_BOOTSTRAP_PHASE_PLAN_REQUIRED_SUBSECTIONS = (
    "### Status",
    "### Objective",
    "### Definition of done",
    "### Exclusions",
)

# Bootstrap only fires from the post-activation status (the contract's
# canonical "ready for Claude implementation" state). Any other status
# means a cycle is mid-flight, halted, or post-verdict; the bootstrap
# refuses rather than overwrite a prompt that is in use.
PROMPT_BOOTSTRAP_ALLOWED_STATUSES = frozenset({
    "awaiting_claude_implementation",
})


def _split_h2_sections(text: str) -> dict:
    """Split markdown into `## Header` -> body (stripped). H2 line itself is
    not included in the body; bodies extend until the next H2 or EOF."""
    sections: dict = {}
    pattern = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        header = f"## {m.group(1).strip()}"
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[header] = text[start:end].strip()
    return sections


def _extract_h3_subsections(text: str, h2_header: str) -> dict:
    """Return dict of `### Header` -> body (stripped) within the scope of
    a single named H2. Returns empty dict if the H2 is not present."""
    h2_pat = re.compile(r"^## (.+?)\s*$", re.MULTILINE)
    matches = list(h2_pat.finditer(text))
    target_start = None
    target_end = len(text)
    for i, m in enumerate(matches):
        if f"## {m.group(1).strip()}" == h2_header:
            target_start = m.end()
            target_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            break
    if target_start is None:
        return {}
    scope = text[target_start:target_end]
    h3_pat = re.compile(r"^### (.+?)\s*$", re.MULTILINE)
    h3_matches = list(h3_pat.finditer(scope))
    out: dict = {}
    for i, m in enumerate(h3_matches):
        header = f"### {m.group(1).strip()}"
        start = m.end()
        end = h3_matches[i + 1].start() if i + 1 < len(h3_matches) else len(scope)
        out[header] = scope[start:end].strip()
    return out


def _render_phase_start_claude_prompt(
    *,
    sub_phase: str,
    objective: str,
    context: str,
    required_work: str,
    exclusions: str,
) -> str:
    """Pure: render the bootstrapped claude-prompt.md body from canonical
    inputs. The rendered prompt is deliberately minimal (no
    `## Files likely involved` or `## Validation expected` sections,
    which are not derivable from the canonical artifacts); Codex may
    extend the prompt with those sections before dispatching to Claude
    if the sub-phase needs them."""
    return "\n".join([
        "# Claude Code Task",
        "",
        "## Phase",
        sub_phase,
        "",
        "## Objective",
        objective,
        "",
        "## Context",
        context,
        "",
        "## Required work",
        required_work,
        "",
        "## Constraints",
        "- Follow `CLAUDE.md`.",
        "- Stay within the current task scope.",
        "- Do not modify `AGENTS.md`.",
        "- Do not modify `CLAUDE.md`.",
        "- Do not rewrite unrelated files.",
        "- Do not delete files unless explicitly instructed.",
        "- Prefer small, testable, reversible changes.",
        "- Add or update tests when behavior changes.",
        "",
        "Out of scope for this phase (from `TASK.md` and `phase-plan.md`):",
        exclusions,
        "",
        "## Required output",
        (
            "After implementation, write `.agent-loop/claude-summary.md` "
            "using the required Claude Implementation Summary format."
        ),
        "",
    ])


def bootstrap_claude_prompt(repo_root: Path) -> int:
    """Phase 5F: synthesize .agent-loop/claude-prompt.md from canonical
    active phase/task artifacts.

    Reads TASK.md, .agent-loop/current-task.md, .agent-loop/current-phase.md,
    .agent-loop/phase-plan.md, and .agent-loop/loop-state.json; validates
    each source is present, non-empty, and that the active phase/sub_phase
    is consistent across all four; refuses with halted_input_missing on
    any mismatch, missing source, missing required section, or status
    that is not the post-activation `awaiting_claude_implementation`.

    On success: writes .agent-loop/claude-prompt.md and logs a
    `prompt bootstrap:` note to .agent-loop/orchestrator.log. The prompt
    is derived deterministically: ## Phase from loop-state.sub_phase,
    ## Objective from TASK.md ## Active Task, ## Context from
    phase-plan ### Objective for the active sub-phase, ## Required work
    from phase-plan ### Definition of done, ## Constraints includes
    phase-plan ### Exclusions verbatim. The bootstrap never auto-runs
    a cycle, never auto-activates a proposal, and never writes any
    artifact other than .agent-loop/claude-prompt.md (and the audit
    note in .agent-loop/orchestrator.log).
    """
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    task_path = repo_root / "TASK.md"
    current_task_path = al / "current-task.md"
    current_phase_path = al / "current-phase.md"
    phase_plan_path = al / "phase-plan.md"
    prompt_path = al / "claude-prompt.md"
    log_path = al / "orchestrator.log"

    try:
        data = load_loop_state(state_path)
        validate_loop_state(data)
        check_contract_version(data)
    except HaltError as halt:
        return _halt(
            state_path, {} if "data" not in dir() else data, halt, log_path,
        )

    state_phase = str(data.get("phase") or "")
    state_sub_phase = str(data.get("sub_phase") or "")
    state_task = str(data.get("task") or "")
    state_status = str(data.get("status") or "")

    if state_status not in PROMPT_BOOTSTRAP_ALLOWED_STATUSES:
        return _halt(state_path, data, HaltError(
            "halted_input_missing",
            (
                f"phase-start prompt bootstrap requires loop-state.json status "
                f"in {sorted(PROMPT_BOOTSTRAP_ALLOWED_STATUSES)}; got "
                f"{state_status!r}. Bootstrap is only valid immediately after a "
                f"fresh activation; an in-flight, halted, or post-verdict "
                f"cycle's prompt must not be silently overwritten."
            ),
        ), log_path)

    for p in (task_path, current_task_path, current_phase_path, phase_plan_path):
        if not p.exists() or not p.read_text(encoding="utf-8").strip():
            rel = p.relative_to(repo_root).as_posix()
            return _halt(state_path, data, HaltError(
                "halted_input_missing",
                (
                    f"phase-start prompt bootstrap requires {rel!r} to "
                    f"exist and be non-empty"
                ),
            ), log_path)

    task_text = task_path.read_text(encoding="utf-8")
    task_sections = _split_h2_sections(task_text)
    for header in PROMPT_BOOTSTRAP_REQUIRED_TASK_SECTIONS:
        if not task_sections.get(header, "").strip():
            return _halt(state_path, data, HaltError(
                "halted_input_missing",
                (
                    f"phase-start prompt bootstrap requires TASK.md section "
                    f"{header!r} to exist and be non-empty"
                ),
            ), log_path)

    ct_text = current_task_path.read_text(encoding="utf-8")
    ct_sections = _split_h2_sections(ct_text)
    for header in PROMPT_BOOTSTRAP_REQUIRED_CURRENT_TASK_SECTIONS:
        if not ct_sections.get(header, "").strip():
            return _halt(state_path, data, HaltError(
                "halted_input_missing",
                (
                    f"phase-start prompt bootstrap requires "
                    f".agent-loop/current-task.md section {header!r} to "
                    f"exist and be non-empty"
                ),
            ), log_path)

    cp_text = current_phase_path.read_text(encoding="utf-8").strip()
    if not cp_text:
        return _halt(state_path, data, HaltError(
            "halted_input_missing",
            "phase-start prompt bootstrap requires .agent-loop/current-phase.md "
            "to be non-empty",
        ), log_path)

    task_active_phase = task_sections["## Active Phase"].strip()
    task_active_sub_phase = task_sections["## Active Sub-Phase"].strip()
    task_active_task = task_sections["## Active Task"].strip()
    task_exclusions = task_sections["## Out Of Scope For Current Phase"].strip()
    ct_phase = ct_sections["## Phase"].strip()
    ct_sub_phase = ct_sections["## Sub-Phase"].strip()
    ct_task = ct_sections["## Task"].strip()

    mismatches: list = []
    if state_phase != task_active_phase:
        mismatches.append(
            f"loop-state.json phase={state_phase!r} vs TASK.md "
            f"## Active Phase={task_active_phase!r}"
        )
    if state_phase != ct_phase:
        mismatches.append(
            f"loop-state.json phase={state_phase!r} vs current-task.md "
            f"## Phase={ct_phase!r}"
        )
    if state_sub_phase != task_active_sub_phase:
        mismatches.append(
            f"loop-state.json sub_phase={state_sub_phase!r} vs TASK.md "
            f"## Active Sub-Phase={task_active_sub_phase!r}"
        )
    if state_sub_phase != ct_sub_phase:
        mismatches.append(
            f"loop-state.json sub_phase={state_sub_phase!r} vs current-task.md "
            f"## Sub-Phase={ct_sub_phase!r}"
        )
    if state_task != task_active_task:
        mismatches.append(
            "loop-state.json task does not match TASK.md ## Active Task body"
        )
    if state_task != ct_task:
        mismatches.append(
            "loop-state.json task does not match current-task.md ## Task body"
        )
    if state_phase not in cp_text or state_sub_phase not in cp_text:
        mismatches.append(
            f"current-phase.md body {cp_text!r} does not name both "
            f"{state_phase!r} and {state_sub_phase!r}"
        )
    if mismatches:
        return _halt(state_path, data, HaltError(
            "halted_input_missing",
            (
                f"phase-start prompt bootstrap refused: active phase/task "
                f"artifacts disagree. Mismatches: {mismatches}. Resolve the "
                f"source disagreements before re-running."
            ),
        ), log_path)

    pp_text = phase_plan_path.read_text(encoding="utf-8")
    sub_phase_h2 = f"## {state_sub_phase}"
    if sub_phase_h2 not in pp_text:
        return _halt(state_path, data, HaltError(
            "halted_input_missing",
            (
                f"phase-start prompt bootstrap requires phase-plan.md to "
                f"contain a {sub_phase_h2!r} section for the active sub-phase"
            ),
        ), log_path)
    pp_subs = _extract_h3_subsections(pp_text, sub_phase_h2)
    for sub in PROMPT_BOOTSTRAP_PHASE_PLAN_REQUIRED_SUBSECTIONS:
        if not pp_subs.get(sub, "").strip():
            return _halt(state_path, data, HaltError(
                "halted_input_missing",
                (
                    f"phase-start prompt bootstrap requires phase-plan.md "
                    f"section {sub_phase_h2!r} to contain a non-empty "
                    f"{sub!r} body"
                ),
            ), log_path)

    pp_status = pp_subs["### Status"].strip()
    if not pp_status.lower().startswith("active"):
        return _halt(state_path, data, HaltError(
            "halted_input_missing",
            (
                f"phase-start prompt bootstrap requires phase-plan.md "
                f"section {sub_phase_h2!r} ### Status to begin with 'Active'; "
                f"got first line {pp_status.splitlines()[0]!r}"
            ),
        ), log_path)

    pp_objective = pp_subs["### Objective"].strip()
    pp_dod = pp_subs["### Definition of done"].strip()
    pp_exclusions = pp_subs["### Exclusions"].strip()

    # TASK.md's `## Out Of Scope For Current Phase` and phase-plan.md's
    # `### Exclusions` are both authoritative sources for "out of scope".
    # The bootstrap prefers the phase-plan ### Exclusions because that is
    # the per-sub-phase canonical source; TASK.md's wider set is included
    # only when phase-plan does not list it.
    exclusions_body = pp_exclusions if pp_exclusions else task_exclusions

    prompt_body = _render_phase_start_claude_prompt(
        sub_phase=state_sub_phase,
        objective=task_active_task,
        context=pp_objective,
        required_work=pp_dod,
        exclusions=exclusions_body,
    )

    prompt_path.write_text(prompt_body, encoding="utf-8")
    rel_prompt = prompt_path.relative_to(repo_root).as_posix()
    _log_note(log_path, (
        f"prompt bootstrap: wrote {rel_prompt} for sub_phase="
        f"{state_sub_phase!r} from canonical TASK.md / current-task.md / "
        f"current-phase.md / phase-plan.md / loop-state.json"
    ))
    print(
        f"[orchestrator] bootstrap-prompt: wrote {rel_prompt} for "
        f"sub_phase={state_sub_phase!r}"
    )
    return 0


def cmd_bootstrap_prompt(_args: argparse.Namespace) -> int:
    repo_root = find_repo_root()
    return bootstrap_claude_prompt(repo_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_loop",
        description=(
            "Agentic AI Coding Loop orchestrator. Implements the Phase 3A "
            "Orchestrator Contract: normal-cycle control path (Phase 3B), "
            "automated NEEDS_FIXES handling with threshold-policy "
            "enforcement (Phase 3C), and subprocess-driven Claude/Codex "
            "adapters (Phase 3D). Set AGENT_LOOP_CLAUDE_CMD and "
            "AGENT_LOOP_CODEX_CMD to drive the subprocess adapters; "
            "without them the orchestrator falls back to manual handoff."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-state", help="load and validate .agent-loop/loop-state.json")
    sub.add_parser(
        "validate-artifacts",
        help="validate per-cycle artifact structure against the contract",
    )
    sub.add_parser(
        "run",
        help=(
            "execute one normal cycle and, on NEEDS_FIXES, walk through "
            "automated fix cycles until a terminal state"
        ),
    )
    sub.add_parser(
        "plan",
        help=(
            "Phase 4B planner (proposal generation only): read planner "
            "inputs, enforce the Phase 4A refusal rules, and write one "
            "structurally valid .agent-loop/proposed-phase.md without "
            "activating it. Refusal exits 2 and logs to .agent-loop/planner.log."
        ),
    )
    sub.add_parser(
        "activate",
        help=(
            "Phase 4C activation (consume approved proposal): parse "
            ".agent-loop/proposed-phase.md, verify the literal "
            "APPROVED_FOR_ACTIVATION token on its own line inside a "
            "human-authored ## Approval section whose body references the "
            "proposal's ## Label, then perform only the Phase 4A "
            "activation writes (TASK.md, .agent-loop/current-task.md, "
            ".agent-loop/current-phase.md, .agent-loop/phase-plan.md "
            "append-only, .agent-loop/loop-state.json reset) and log the "
            "approval source to .agent-loop/planner.log. Refusal exits 2."
        ),
    )
    sub.add_parser(
        "resume",
        help=(
            "Phase 5C strict-mode resume: continue a cycle paused at a "
            "strict-mode human gate (pre_claude_prompt, pre_fix_prompt, "
            "or pre_codex_review). Refuses unless loop-state.json status "
            "is one of the halted_awaiting_human_* strict-gate values; "
            "on success clears awaiting_human_for and dispatches to the "
            "continuation matched by the persisted gate, so no earlier "
            "work is re-done and the next gate (if any) still fires."
        ),
    )
    build_ctx = sub.add_parser(
        "build-continuation-context",
        help=(
            "Phase 6H bounded continuation prompt construction: assemble "
            "a structured continuation context dict from canonical "
            "loop-state + the active Phase 6F/6G token-exhaustion "
            "checkpoint + bounded evidence excerpts + advisory durable "
            "memory entries, and persist the JSON to "
            "`.agent-loop/continuation-context.json` (override with "
            "`--output`). Refuses fail-closed for an ineligible halt "
            "status, a missing or contradictory checkpoint, an "
            "out-of-bounds memory entry limit, or an out-of-bounds "
            "evidence byte limit."
        ),
    )
    build_ctx.add_argument(
        "--memory-entry-limit",
        type=int,
        default=None,
        help=(
            "Override the Phase 6C retrieval limit. Defaults to "
            f"CONTINUATION_CONTEXT_DEFAULT_MEMORY_LIMIT="
            f"{CONTINUATION_CONTEXT_DEFAULT_MEMORY_LIMIT}; capped at "
            f"MEMORY_RETRIEVAL_MAX_LIMIT={MEMORY_RETRIEVAL_MAX_LIMIT}."
        ),
    )
    build_ctx.add_argument(
        "--evidence-byte-limit",
        type=int,
        default=None,
        help=(
            "Per-file byte cap on the included evidence excerpt. "
            f"Defaults to CONTINUATION_CONTEXT_DEFAULT_EVIDENCE_BYTE_LIMIT="
            f"{CONTINUATION_CONTEXT_DEFAULT_EVIDENCE_BYTE_LIMIT}; capped "
            f"at CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT="
            f"{CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT}."
        ),
    )
    build_ctx.add_argument(
        "--output",
        default=None,
        help=(
            "Override the output JSON path. Defaults to "
            f"`{CONTINUATION_CONTEXT_OUTPUT_REL}`. Paths are resolved "
            "relative to the repo root."
        ),
    )
    sub.add_parser(
        "auto-continue",
        help=(
            "Phase 6G bounded automatic continuation chaining: while "
            "loop-state.json status is "
            "halted_awaiting_token_exhaustion_continuation, repeatedly "
            "apply the single-hop token-exhaustion resume until either "
            "the cycle clears the halt naturally, a hop refuses (e.g. "
            "exhausted continuation_budget, unsupported saved stage, "
            "malformed checkpoint), a non-token halt fires inside the "
            "dispatched continuation, or AUTO_CONTINUE_MAX_HOPS is "
            "reached. Refuses fail-closed (recovery-preserving, does "
            "not clobber a strict-gate halt) when called from a status "
            "other than the token-exhaustion halt."
        ),
    )
    record_te = sub.add_parser(
        "record-token-exhaustion",
        help=(
            "Phase 6F operator entry point: classify the current cycle "
            "as interrupted by token / context exhaustion. Writes a "
            "Phase 6D checkpoint preserving the pre-suspension cycle "
            "context plus a bounded continuation budget, and transitions "
            "loop-state to halted_awaiting_token_exhaustion_continuation "
            "so the halt is auditable from the canonical state artifacts. "
            "Run `resume` after this command to consume the continuation "
            "budget and dispatch the cycle's continuation."
        ),
    )
    record_te.add_argument(
        "--active-prompt-path",
        required=True,
        choices=sorted(CHECKPOINT_ACTIVE_PROMPT_PATHS),
        help=(
            "Which active prompt the interrupted cycle was driving "
            "(.agent-loop/claude-prompt.md for an implementation cycle, "
            ".agent-loop/fix-prompt.md for a fix cycle)."
        ),
    )
    record_te.add_argument(
        "--continuation-budget",
        type=int,
        default=None,
        help=(
            "Bounded number of resume attempts allowed before further "
            "continuation is refused. Default is "
            f"TOKEN_EXHAUSTION_DEFAULT_BUDGET={TOKEN_EXHAUSTION_DEFAULT_BUDGET}; "
            "the writer refuses negative values."
        ),
    )
    sub.add_parser(
        "bootstrap-prompt",
        help=(
            "Phase 5F phase-start prompt bootstrap: synthesize "
            ".agent-loop/claude-prompt.md from the canonical active "
            "phase/task artifacts (TASK.md, .agent-loop/current-task.md, "
            ".agent-loop/current-phase.md, .agent-loop/phase-plan.md, "
            ".agent-loop/loop-state.json). Refuses with halted_input_missing "
            "when any source is missing, when active phase / sub_phase / "
            "task disagrees across the four sources, when phase-plan.md "
            "lacks an Active sub-phase section with the required "
            "subsections, or when loop-state.json status is not "
            "awaiting_claude_implementation. Never replaces the Phase 5E "
            "fix-prompt path."
        ),
    )
    return parser


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "check-state": cmd_check_state,
    "validate-artifacts": cmd_validate_artifacts,
    "run": cmd_run,
    "plan": cmd_plan,
    "activate": cmd_activate,
    "resume": cmd_resume,
    "auto-continue": cmd_auto_continue,
    "record-token-exhaustion": cmd_record_token_exhaustion,
    "build-continuation-context": cmd_build_continuation_context,
    "bootstrap-prompt": cmd_bootstrap_prompt,
}


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return HANDLERS[args.cmd](args)
    except KeyboardInterrupt:
        # Per the Phase 3A contract: an explicit human stop signal
        # (e.g. SIGINT) must persist `status = halted_human_stop` into
        # loop-state.json. Best-effort: locate the repo, load state,
        # overwrite status. Any failure here is logged but does not
        # change the return code; we still exit 3 to signal interrupt.
        try:
            repo_root = find_repo_root()
            state_path = repo_root / ".agent-loop" / "loop-state.json"
            log_path = repo_root / ".agent-loop" / "orchestrator.log"
            data = load_loop_state(state_path)
            save_loop_state(state_path, data, {"status": "halted_human_stop"})
            _log_note(
                log_path,
                "HALT halted_human_stop: orchestrator received "
                "KeyboardInterrupt / explicit human stop signal",
            )
        except Exception as exc:
            print(
                f"[orchestrator] could not persist halted_human_stop: {exc}",
                file=sys.stderr,
            )
        print("[orchestrator] halted_human_stop: interrupted by human", file=sys.stderr)
        return 3
    except FileNotFoundError as exc:
        print(f"[orchestrator] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
