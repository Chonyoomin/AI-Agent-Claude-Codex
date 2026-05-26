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
})

CODEX_OR_HUMAN_OWNED_FIELDS = frozenset({
    "phase",
    "sub_phase",
    "task",
    "max_cycles",
    "contract_version",
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


def validate_codex_review_and_parse_verdict(review_path: Path) -> str:
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
    return matches[0]


def validate_fix_prompt(fix_prompt_path: Path) -> None:
    if not fix_prompt_path.exists() or not fix_prompt_path.read_text(encoding="utf-8").strip():
        raise HaltError(
            "halted_fix_prompt_malformed",
            f"{fix_prompt_path.name} is missing or empty",
        )
    _validate_header_order(
        fix_prompt_path, FIX_PROMPT_HEADERS, "halted_fix_prompt_malformed",
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


def run_normal_cycle(repo_root: Path) -> int:
    al = repo_root / ".agent-loop"
    state_path = al / "loop-state.json"
    prompt_path = al / "claude-prompt.md"
    summary_path = al / "claude-summary.md"
    review_path = al / "codex-review.md"
    log_path = al / "orchestrator.log"

    # 1. Load + structurally validate loop-state.json before doing anything.
    try:
        data = load_loop_state(state_path)
        validate_loop_state(data)
        check_contract_version(data)
    except HaltError as halt:
        # We may have an invalid `data` here, so pass {} to avoid clobbering.
        return _halt(state_path, {} if "data" not in dir() else data, halt, log_path)

    # 2. Record this orchestrator's version (allowed write).
    data = save_loop_state(
        state_path, data, {"orchestrator_version": ORCHESTRATOR_VERSION},
    )

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
        verdict = validate_codex_review_and_parse_verdict(review_path)
    except HaltError as halt:
        return _halt(state_path, data, halt, log_path)

    # 11. Hand off to the verdict-handling loop (Phase 3C). The loop
    #     either reaches a terminal state and returns, or drives one or
    #     more fix cycles before reaching a terminal state.
    return _handle_verdict_loop(state_path, data, verdict, repo_root, log_path)


def _handle_verdict_loop(
    state_path: Path,
    data: dict,
    verdict: str,
    repo_root: Path,
    log_path: Path,
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
            save_loop_state(state_path, data, {
                "status": "phase_complete_awaiting_human_approval",
                "last_verdict": verdict,
                "last_verdict_phase": last_verdict_phase,
            })
            print(
                f"[orchestrator] verdict={verdict}; phase complete, "
                f"awaiting human approval to start the next phase."
            )
            return 0
        if verdict == "FAILED_REQUIRES_HUMAN":
            save_loop_state(state_path, data, {
                "status": "halted_failed_requires_human",
                "last_verdict": verdict,
                "last_verdict_phase": last_verdict_phase,
            })
            print(
                f"[orchestrator] verdict={verdict}; halted, human "
                f"intervention required.",
                file=sys.stderr,
            )
            return 2
        # NEEDS_FIXES from here on. Record the verdict regardless of
        # whether we go on to run a fix cycle or halt on the threshold.
        data = save_loop_state(state_path, data, {
            "last_verdict": verdict,
            "last_verdict_phase": last_verdict_phase,
        })
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
        # Run one fix cycle. On success, get a new verdict and loop.
        try:
            verdict, data = _run_fix_cycle(state_path, data, repo_root, log_path)
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
) -> tuple[str, dict]:
    """Execute one fix cycle per the contract's `#### Fix cycle` steps.

    Returns `(new_verdict, updated_data)` on success. On any halt path
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
        verdict = validate_codex_review_and_parse_verdict(review_path)
    except HaltError as halt:
        raise _FixCycleHalt(_halt(state_path, data, halt, log_path))

    return verdict, data


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
    """Append a single timestamped `note:` / `refused:` line. Best-effort.

    The contract treats `.agent-loop/planner.log` as optional and never
    authoritative, so a write failure must not raise. The line format is
    deliberately simple so a future tool can `grep` for refusals.
    """
    path = _planner_log_path(repo_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {message}\n")
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


def generate_proposal_draft(inputs: PlannerInputs) -> ProposalDraft:
    """Produce a templated, deterministic next-sub-phase proposal.

    The initial slice is heuristic: increment the active sub-phase letter
    (4B -> 4C), depend only on already-CLOSED prior sub-phases (so the
    proposal does not list the active phase as `active-in-flight`, which
    would be invalid), and pre-fill the structural fields with content
    derived from the active task context. Codex / human review is
    expected to refine the body before activation.
    """
    state = inputs.loop_state
    active_sub_phase = state.get("sub_phase") or ""
    active_phase = state.get("phase") or ""

    next_token = _bump_subphase_letter(active_sub_phase) or "Phase TBD"
    label = (
        f"{next_token} - Next planner-implementation slice "
        f"(planner-generated stub for review)"
    )

    objective = (
        f"Continue the {active_phase} series by implementing the next concrete "
        f"slice of work that {active_sub_phase or 'the currently active sub-phase'} "
        f"sets up. This proposal is planner-generated as a stub against the Phase 4A "
        f"contract and is intended to be refined by Codex and approved by a human "
        f"before activation. The implementing sub-phase will pick exactly one of the "
        f"deferred Phase 4 capabilities (planner activation writes, planner-orchestrator "
        f"integration, or an optional planner adapter), narrow scope to that capability, "
        f"and ship it behind the same structural validators the orchestrator already "
        f"applies to per-cycle artifacts."
    )

    definition_of_done = [
        (
            "the implementing sub-phase ships planner-owned code whose exit code is "
            "0 on success and 2 on refusal, exactly as the Phase 4B `plan` subcommand "
            "already behaves"
        ),
        (
            "`tests/` gains at least one new test case that covers the new capability "
            "and at least one new test case that covers a refusal path the new code "
            "introduces (no new capability ships without a refusal test)"
        ),
        (
            "the new capability never writes any file in the Phase 4A "
            "'Files the planner must never write' set without an explicit, contract-"
            "disclosed activation step approved by a human"
        ),
        (
            "`README.md` is updated so the Current Status section names the new "
            "sub-phase as active and documents the new CLI invocation, if any"
        ),
    ]

    exclusions = [
        "no Phase 5 approval-mode behavior",
        "no Phase 7 editor integration",
        "no MCP support",
        "no Git automation (commit, push, branch, stash, reset, checkout, tag)",
        "no changes to the Phase 2A Evidence Collection Contract or `scripts/run_checks.sh`",
        "no changes to the Phase 3A Orchestrator Contract body",
        "no changes to the Phase 4A Planning Contract body",
        "no changes to `AGENTS.md` or `CLAUDE.md`",
        "no removal or rewrite of any historical phase-plan section",
    ]

    files_likely_involved = [
        "scripts/agent_loop.py",
        "tests/",
        ".agent-loop/proposed-phase.md",
        ".agent-loop/planner.log",
        ".agent-loop/phase-plan.md",
        "README.md",
    ]

    required_contract_changes = "None"
    cycle_size_estimate = 2

    # Depend only on CLOSED prior sub-phases. The active sub-phase is
    # deliberately omitted because listing it as `active-in-flight` would
    # invalidate the proposal per the Phase 4A contract; the implicit
    # ordering ("4C runs after 4B") is captured in the Risk areas instead.
    dep_labels = list(inputs.closed_labels)
    # Trim to the two most recent closed sub-phases so the dependency
    # list stays focused; older history is implicit.
    recent_closed = dep_labels[-2:] if len(dep_labels) > 2 else dep_labels
    dependencies = [(lbl, "complete-approved") for lbl in recent_closed]
    if not dependencies:
        # Fresh repository: no closed sub-phases yet. Use "pending"
        # against a placeholder; the per-proposal validator will then
        # refuse this draft, which is the correct fail-closed behavior.
        dependencies = [("(no closed prior sub-phase found)", "pending")]

    risk_areas = [
        (
            f"this proposal implicitly assumes {active_sub_phase or 'the active sub-phase'} "
            f"will reach `APPROVED_FOR_HUMAN_REVIEW` before activation; the active "
            f"sub-phase is intentionally omitted from `## Dependencies` to satisfy "
            f"the Phase 4A 'no active-in-flight dependency' rule, but the proposal "
            f"is not meaningful until the active sub-phase is closed"
        ),
        (
            "the body is planner-generated stub content; Codex or a human must "
            "refine the `## Objective`, `## Definition of done`, and "
            "`## Files likely involved` sections to match the chosen next capability "
            "before activation"
        ),
        (
            "no activation writes are performed by this proposal-generation step; "
            "activation remains a separate, human-approved sub-phase (deferred from "
            "Phase 4B)"
        ),
    ]

    return ProposalDraft(
        label=label,
        objective=objective,
        definition_of_done=definition_of_done,
        exclusions=exclusions,
        files_likely_involved=files_likely_involved,
        required_contract_changes=required_contract_changes,
        cycle_size_estimate=cycle_size_estimate,
        cycle_size_justification=None,
        dependencies=dependencies,
        risk_areas=risk_areas,
    )


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

    # Label collision against existing historical sub-phase labels.
    if _label_exists(draft.label, inputs.existing_labels):
        return (
            f"## Label {draft.label!r} collides with an existing phase-plan heading "
            f"(re-use of labels is forbidden by the Phase 4A contract)"
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
    return run_planner(repo_root)


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
    return parser


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "check-state": cmd_check_state,
    "validate-artifacts": cmd_validate_artifacts,
    "run": cmd_run,
    "plan": cmd_plan,
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
