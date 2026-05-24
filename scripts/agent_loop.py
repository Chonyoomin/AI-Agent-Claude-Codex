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
from dataclasses import dataclass
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
    return parser


HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "check-state": cmd_check_state,
    "validate-artifacts": cmd_validate_artifacts,
    "run": cmd_run,
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
