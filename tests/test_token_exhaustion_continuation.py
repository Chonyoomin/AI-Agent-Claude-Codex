"""Focused tests for the Phase 6F token-exhaustion continuation slice.

Scope of this suite (Phase 6F, narrow):
- `record_token_exhaustion(...)` classifies a token / context
  exhaustion event as a resumable interrupted-run state: writes a
  token-exhaustion checkpoint capturing the pre-suspension cycle
  context plus a bounded continuation budget, transitions
  loop-state to `HALTED_TOKEN_EXHAUSTION` so the halt is auditable
  from the canonical state artifacts, and refuses fail-closed when
  the loop is already halted, terminally complete, or the active
  prompt path is out of vocabulary.
- `_validate_token_exhaustion_checkpoint(...)` compares the cycle
  identity (`phase`, `sub_phase`, `task`, `cycle_count`,
  `approval_mode`) between the checkpoint and the canonical
  loop-state and refuses fail-closed on any mismatch; it does NOT
  compare `status` or `awaiting_human_for` because the halt
  vocabulary on the loop-state side intentionally diverges from the
  pre-suspension vocabulary preserved inside the checkpoint.
- `run_token_exhaustion_resume(...)` refuses unless the loop-state
  is at `HALTED_TOKEN_EXHAUSTION`, the active checkpoint exists,
  the checkpoint is schema-valid, the checkpoint's
  cycle-identity matches loop-state, the checkpoint's
  `suspension_reason` is `"token_exhaustion"`, and the checkpoint's
  `continuation_budget` is greater than zero. On success it writes a
  new checkpoint with `continuation_budget - 1` and an explicit
  `supersedes` reference, restores loop-state to the pre-suspension
  cycle status / `awaiting_human_for`, logs a
  `token-exhaustion resume consumed:` audit note, and exits 0.
- `cmd_resume(...)` routes by persisted halt status:
  `HALTED_TOKEN_EXHAUSTION` dispatches to
  `run_token_exhaustion_resume`; any other status (including the
  four Phase 5C strict-gate halts) routes to the existing
  `run_strict_resume` unchanged.
- Canonical-precedence preservation: every refusal leaves the saved
  `HALTED_TOKEN_EXHAUSTION` status + `awaiting_human_for` intact so a
  corrected operator state allows a fresh resume to dispatch (same
  recovery pattern as the Phase 5C mode-coherence and Phase 6E
  checkpoint refusals); successful resume restores the pre-suspension
  status but never auto-progresses phases, widens autonomy, or
  bypasses any Phase 5 human gate.

This slice does not implement automatic continuation chaining,
background continuation, or any cycle auto-restart; no test in this
suite exercises those paths.
"""

from __future__ import annotations

import argparse
import json
import sys
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


_ACTIVE_PHASE = "Phase 6 - Durable Memory and Optional Context Layer"
_ACTIVE_SUB_PHASE = "Phase 6F - Token Exhaustion Continuation Initial Slice"
_ACTIVE_TASK = "Implement token-exhaustion continuation."
_PRE_SUSPENSION_STATUS = "awaiting_codex_review"
_PRE_SUSPENSION_AWAITING_HUMAN_FOR = None


def _baseline_loop_state(**overrides) -> dict:
    """Loop-state at a typical mid-cycle moment where token exhaustion
    might be recorded (Codex review awaited, no halt in effect)."""
    data = {
        "phase": _ACTIVE_PHASE,
        "sub_phase": _ACTIVE_SUB_PHASE,
        "task": _ACTIVE_TASK,
        "status": _PRE_SUSPENSION_STATUS,
        "cycle_count": 1,
        "max_cycles": 3,
        "last_verdict": None,
        "last_verdict_phase": None,
        "contract_version": "phase-3a-v2",
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": agent_loop.APPROVAL_MODE_REVIEW,
        "awaiting_human_for": _PRE_SUSPENSION_AWAITING_HUMAN_FOR,
    }
    data.update(overrides)
    return data


class _TokenExhaustionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.al = self.repo_root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        self.state_path = self.al / "loop-state.json"
        self.log_path = self.al / "orchestrator.log"
        self.memory_dir = self.repo_root / agent_loop.MEMORY_DIR_REL
        self.checkpoint_dir = (
            self.memory_dir / agent_loop.MEMORY_CATEGORY_CHECKPOINT
        )

    def _write_state(self, **overrides) -> dict:
        data = _baseline_loop_state(**overrides)
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return data

    def _record(self, **overrides) -> Path:
        kwargs = dict(active_prompt_path=".agent-loop/claude-prompt.md")
        kwargs.update(overrides)
        return agent_loop.record_token_exhaustion(self.repo_root, **kwargs)

    def _state_on_disk(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))


# ----- record_token_exhaustion -----


class RecordTokenExhaustionTests(_TokenExhaustionTestCase):

    def test_record_writes_checkpoint_and_transitions_loop_state(self) -> None:
        self._write_state()
        path = self._record()
        # Checkpoint file lives under .agent-loop/memory/checkpoint/.
        self.assertTrue(path.is_file())
        self.assertEqual(path.parent, self.checkpoint_dir)
        # Loop-state transitioned to the HALTED_TOKEN_EXHAUSTION halt.
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION,
        )
        # Cycle identity preserved on loop-state.
        self.assertEqual(after["phase"], _ACTIVE_PHASE)
        self.assertEqual(after["sub_phase"], _ACTIVE_SUB_PHASE)
        self.assertEqual(after["cycle_count"], 1)
        # Audit note landed in the orchestrator log.
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("token exhaustion recorded:", log_text)
        self.assertIn(
            f"continuation_budget={agent_loop.TOKEN_EXHAUSTION_DEFAULT_BUDGET}",
            log_text,
        )

    def test_recorded_checkpoint_payload_preserves_pre_suspension_context(
        self,
    ) -> None:
        self._write_state()
        path = self._record(continuation_budget=3)
        payload = agent_loop.read_checkpoint_entry(path)
        self.assertEqual(payload["phase"], _ACTIVE_PHASE)
        self.assertEqual(payload["sub_phase"], _ACTIVE_SUB_PHASE)
        self.assertEqual(payload["task"], _ACTIVE_TASK)
        self.assertEqual(payload["cycle_count"], 1)
        # The checkpoint records the PRE-suspension status, not the
        # halt vocabulary. This is what `run_token_exhaustion_resume`
        # restores on success.
        self.assertEqual(payload["status"], _PRE_SUSPENSION_STATUS)
        self.assertEqual(
            payload["awaiting_human_for"],
            _PRE_SUSPENSION_AWAITING_HUMAN_FOR,
        )
        self.assertEqual(
            payload["approval_mode"], agent_loop.APPROVAL_MODE_REVIEW,
        )
        self.assertEqual(
            payload["suspension_reason"],
            agent_loop.TOKEN_EXHAUSTION_SUSPENSION_REASON,
        )
        self.assertEqual(payload["continuation_budget"], 3)
        self.assertEqual(
            payload["active_prompt_path"], ".agent-loop/claude-prompt.md",
        )

    def test_record_refuses_when_loop_state_already_halted(self) -> None:
        # Pre-existing halt (Phase 5C strict-gate); recording token
        # exhaustion on top would clobber the saved recovery point.
        self._write_state(status=agent_loop.HALTED_PRE_CLAUDE_PROMPT)
        before = self._state_on_disk()
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._record()
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("already a halt", cm.exception.reason)
        # Loop-state untouched.
        self.assertEqual(self._state_on_disk(), before)
        # No checkpoint file written.
        self.assertFalse(self.checkpoint_dir.exists())

    def test_record_refuses_when_phase_terminally_complete(self) -> None:
        self._write_state(
            status=agent_loop.AWAITING_HUMAN_FOR_PHASE_COMPLETE,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._record()
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("terminally complete", cm.exception.reason)

    def test_record_refuses_invalid_active_prompt_path(self) -> None:
        self._write_state()
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._record(active_prompt_path=".agent-loop/bogus.md")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("active_prompt_path", cm.exception.reason)

    def test_record_accepts_fix_prompt_path(self) -> None:
        self._write_state()
        path = self._record(active_prompt_path=".agent-loop/fix-prompt.md")
        payload = agent_loop.read_checkpoint_entry(path)
        self.assertEqual(
            payload["active_prompt_path"], ".agent-loop/fix-prompt.md",
        )

    def test_record_refuses_when_loop_state_missing(self) -> None:
        # No loop-state file at all.
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._record()
        self.assertEqual(cm.exception.status, "halted_input_missing")


# ----- _validate_token_exhaustion_checkpoint -----


class ValidateTokenExhaustionCheckpointTests(_TokenExhaustionTestCase):

    def _both(self, **checkpoint_overrides) -> tuple:
        loop_state = _baseline_loop_state(
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            awaiting_human_for=agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION,
        )
        checkpoint = {
            "phase": loop_state["phase"],
            "sub_phase": loop_state["sub_phase"],
            "task": loop_state["task"],
            "cycle_count": loop_state["cycle_count"],
            "approval_mode": loop_state["approval_mode"],
            # checkpoint preserves the PRE-suspension vocabulary, NOT
            # the halt vocabulary the loop-state carries now.
            "status": _PRE_SUSPENSION_STATUS,
            "awaiting_human_for": _PRE_SUSPENSION_AWAITING_HUMAN_FOR,
            "suspension_reason": (
                agent_loop.TOKEN_EXHAUSTION_SUSPENSION_REASON
            ),
            "active_prompt_path": ".agent-loop/claude-prompt.md",
            "continuation_budget": 2,
        }
        checkpoint.update(checkpoint_overrides)
        return loop_state, checkpoint

    def test_matching_identity_accepts_even_when_status_differs(self) -> None:
        # The halt vocabulary on the loop-state side intentionally
        # differs from the pre-suspension vocabulary in the checkpoint;
        # the validator must ignore `status` and `awaiting_human_for`.
        loop_state, checkpoint = self._both()
        agent_loop._validate_token_exhaustion_checkpoint(
            checkpoint, loop_state,
        )  # must not raise

    def test_phase_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(phase="Phase 5 - Approval Modes")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_token_exhaustion_checkpoint(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("phase", cm.exception.reason)

    def test_sub_phase_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(sub_phase="Phase 6E - Other")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_token_exhaustion_checkpoint(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("sub_phase", cm.exception.reason)

    def test_task_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(task="completely different task")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_token_exhaustion_checkpoint(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("task", cm.exception.reason)

    def test_cycle_count_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(cycle_count=99)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_token_exhaustion_checkpoint(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("cycle_count", cm.exception.reason)

    def test_approval_mode_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(
            approval_mode=agent_loop.APPROVAL_MODE_STRICT,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_token_exhaustion_checkpoint(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("approval_mode", cm.exception.reason)


# ----- run_token_exhaustion_resume -----


class RunTokenExhaustionResumeTests(_TokenExhaustionTestCase):

    def _setup_recorded(self, *, continuation_budget=2) -> Path:
        self._write_state()
        return self._record(continuation_budget=continuation_budget)

    def test_resume_consumes_budget_and_restores_loop_state(self) -> None:
        self._setup_recorded(continuation_budget=2)
        rc = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc, 0)
        # Loop-state restored to pre-suspension cycle vocabulary.
        after = self._state_on_disk()
        self.assertEqual(after["status"], _PRE_SUSPENSION_STATUS)
        self.assertEqual(
            after["awaiting_human_for"], _PRE_SUSPENSION_AWAITING_HUMAN_FOR,
        )
        # cycle_count NOT advanced (continuation, not progression).
        self.assertEqual(after["cycle_count"], 1)
        # Phase / sub_phase / task untouched.
        self.assertEqual(after["phase"], _ACTIVE_PHASE)
        self.assertEqual(after["sub_phase"], _ACTIVE_SUB_PHASE)
        # A NEW checkpoint was written with budget = old - 1 = 1.
        paths = agent_loop.list_checkpoint_entries(self.repo_root)
        self.assertEqual(len(paths), 2)
        newest = max(
            paths, key=lambda p: (p.stat().st_mtime_ns, p.name),
        )
        new_payload = agent_loop.read_checkpoint_entry(newest)
        self.assertEqual(new_payload["continuation_budget"], 1)
        # The new checkpoint records an explicit supersedes reference.
        self.assertIsNotNone(new_payload["supersedes"])
        # Audit note landed.
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("token-exhaustion resume consumed:", log_text)
        self.assertIn("2 -> 1", log_text)

    def test_resume_refuses_when_status_is_not_token_exhaustion_halt(
        self,
    ) -> None:
        # Plant a clean loop-state with no halt.
        self._write_state()
        rc = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc, 2)
        # The mismatched-status path routes through _halt, which
        # rewrites status to halted_input_missing - this is safe
        # because the loop was NOT at a recovery point.
        after = self._state_on_disk()
        self.assertEqual(after["status"], "halted_input_missing")

    def test_resume_refuses_when_no_checkpoint_exists(self) -> None:
        # Plant the halt status by hand but no checkpoint.
        self._write_state(
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
            ),
        )
        rc = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc, 2)
        # Recovery-preserving refusal: the saved halt is unchanged.
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION,
        )
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("no active checkpoint", log_text)

    def test_resume_refuses_when_checkpoint_is_malformed(self) -> None:
        # Plant the halt status but a hand-crafted malformed checkpoint
        # missing required body fields.
        self._write_state(
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
            ),
        )
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "signal_version": agent_loop.MEMORY_SIGNAL_VERSION,
            "category": agent_loop.MEMORY_CATEGORY_CHECKPOINT,
            "phase": _ACTIVE_PHASE,
            "sub_phase": _ACTIVE_SUB_PHASE,
            "cycle_count": 1,
            "source_artifact_path": ".agent-loop/loop-state.json",
            "created_at": "2030-01-01T00:00:00Z",
            "supersedes": None,
            "body": json.dumps({}),  # missing every checkpoint-body field
        }
        (self.checkpoint_dir / "20300101T000000Z-deadbeef.json").write_text(
            json.dumps(entry), encoding="utf-8",
        )
        rc = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("malformed", log_text)

    def test_resume_refuses_when_suspension_reason_is_not_token_exhaustion(
        self,
    ) -> None:
        # Plant the halt status by hand, then write a checkpoint whose
        # suspension_reason is human_interrupt instead of
        # token_exhaustion.
        self._write_state()
        agent_loop.write_checkpoint_entry(
            self.repo_root,
            phase=_ACTIVE_PHASE,
            sub_phase=_ACTIVE_SUB_PHASE,
            task=_ACTIVE_TASK,
            cycle_count=1,
            status=_PRE_SUSPENSION_STATUS,
            approval_mode=agent_loop.APPROVAL_MODE_REVIEW,
            awaiting_human_for=_PRE_SUSPENSION_AWAITING_HUMAN_FOR,
            active_prompt_path=".agent-loop/claude-prompt.md",
            suspension_reason="human_interrupt",
            continuation_budget=2,
            source_artifact_path=".agent-loop/loop-state.json",
        )
        # Force the halt status onto loop-state.
        data = self._state_on_disk()
        data["status"] = agent_loop.HALTED_TOKEN_EXHAUSTION
        data["awaiting_human_for"] = (
            agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
        )
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        rc = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("suspension_reason", log_text)

    def test_resume_refuses_on_exhausted_budget(self) -> None:
        # Budget=0 on the active checkpoint means the operator's
        # bounded continuation is consumed; refuse fail-closed.
        self._setup_recorded(continuation_budget=0)
        rc = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("continuation_budget=0", log_text)
        self.assertIn("exhausted", log_text)

    def test_resume_refuses_on_cycle_identity_mismatch(self) -> None:
        # Record under one cycle_count, then mutate loop-state to a
        # different cycle_count before resume. The cycle-identity
        # validator must refuse.
        self._setup_recorded()
        data = self._state_on_disk()
        data["cycle_count"] = 99
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        rc = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        # The halt status is preserved on refusal (recovery-preserving).
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("cycle_count", log_text)

    def test_two_consecutive_resumes_consume_budget_to_exhaustion(self) -> None:
        # Budget=2 -> first resume produces budget=1 -> second resume
        # produces budget=0; a third resume refuses.
        self._setup_recorded(continuation_budget=2)
        # First resume.
        rc1 = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc1, 0)
        # Re-record (since resume restored the loop-state to non-halt)
        # so we can test consecutive consumption. Mutate loop-state
        # back to the halt to simulate a second token-exhaustion event
        # being recorded.
        data = self._state_on_disk()
        data["status"] = agent_loop.HALTED_TOKEN_EXHAUSTION
        data["awaiting_human_for"] = (
            agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
        )
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        # Second resume against the budget=1 checkpoint (the newest).
        rc2 = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc2, 0)
        # Newest checkpoint is now budget=0.
        paths = agent_loop.list_checkpoint_entries(self.repo_root)
        newest = max(
            paths, key=lambda p: (p.stat().st_mtime_ns, p.name),
        )
        self.assertEqual(
            agent_loop.read_checkpoint_entry(newest)["continuation_budget"], 0,
        )
        # Re-halt and try a third resume: budget=0 must refuse.
        data = self._state_on_disk()
        data["status"] = agent_loop.HALTED_TOKEN_EXHAUSTION
        data["awaiting_human_for"] = (
            agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
        )
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        rc3 = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc3, 2)


# ----- cmd_resume routing -----


class CmdResumeRoutingTests(_TokenExhaustionTestCase):

    def _run_cmd_resume(self) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo_root,
        ):
            return agent_loop.cmd_resume(argparse.Namespace())

    def test_cmd_resume_routes_token_exhaustion_status_to_continuation(
        self,
    ) -> None:
        self._setup_for_token_resume()
        with mock.patch.object(
            agent_loop, "run_token_exhaustion_resume", return_value=42,
        ) as token_resume, mock.patch.object(
            agent_loop, "run_strict_resume", return_value=99,
        ) as strict_resume:
            rc = self._run_cmd_resume()
        self.assertEqual(rc, 42)
        token_resume.assert_called_once_with(self.repo_root)
        strict_resume.assert_not_called()

    def test_cmd_resume_routes_strict_gate_status_to_strict_resume(
        self,
    ) -> None:
        self._write_state(
            status=agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT
            ),
            approval_mode=agent_loop.APPROVAL_MODE_STRICT,
        )
        with mock.patch.object(
            agent_loop, "run_token_exhaustion_resume", return_value=42,
        ) as token_resume, mock.patch.object(
            agent_loop, "run_strict_resume", return_value=99,
        ) as strict_resume:
            rc = self._run_cmd_resume()
        self.assertEqual(rc, 99)
        strict_resume.assert_called_once_with(self.repo_root)
        token_resume.assert_not_called()

    def test_cmd_resume_routes_missing_state_to_strict_resume(self) -> None:
        # No loop-state.json. cmd_resume must defer to
        # run_strict_resume (which has the existing missing-state halt
        # path) rather than try to inspect a missing file.
        with mock.patch.object(
            agent_loop, "run_token_exhaustion_resume", return_value=42,
        ) as token_resume, mock.patch.object(
            agent_loop, "run_strict_resume", return_value=99,
        ) as strict_resume:
            rc = self._run_cmd_resume()
        self.assertEqual(rc, 99)
        strict_resume.assert_called_once_with(self.repo_root)
        token_resume.assert_not_called()

    def _setup_for_token_resume(self) -> None:
        self._write_state(
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
            ),
        )


# ----- canonical-precedence preservation -----


class CanonicalPrecedencePreservationTests(_TokenExhaustionTestCase):

    def test_refused_resume_does_not_mutate_checkpoint_files(self) -> None:
        path = self._setup_recorded_then_corrupt_loop_state()
        before = path.read_bytes()
        rc = agent_loop.run_token_exhaustion_resume(self.repo_root)
        self.assertEqual(rc, 2)
        self.assertEqual(path.read_bytes(), before)

    def _setup_recorded_then_corrupt_loop_state(self) -> Path:
        self._write_state()
        path = agent_loop.record_token_exhaustion(
            self.repo_root,
            active_prompt_path=".agent-loop/claude-prompt.md",
        )
        # Mutate loop-state to a mismatching cycle_count so resume
        # refuses but does not touch the checkpoint file.
        data = self._state_on_disk()
        data["cycle_count"] = 999
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return path

    def test_successful_resume_does_not_advance_cycle_count(self) -> None:
        self._write_state(cycle_count=2)
        self._record()
        agent_loop.run_token_exhaustion_resume(self.repo_root)
        after = self._state_on_disk()
        self.assertEqual(
            after["cycle_count"], 2,
            "continuation must NOT auto-progress cycle_count "
            "(no autonomy widening, no phase progression)",
        )

    def test_successful_resume_preserves_phase_identity(self) -> None:
        self._write_state()
        self._record()
        agent_loop.run_token_exhaustion_resume(self.repo_root)
        after = self._state_on_disk()
        self.assertEqual(after["phase"], _ACTIVE_PHASE)
        self.assertEqual(after["sub_phase"], _ACTIVE_SUB_PHASE)
        self.assertEqual(after["task"], _ACTIVE_TASK)
        self.assertEqual(
            after["approval_mode"], agent_loop.APPROVAL_MODE_REVIEW,
        )

    def test_resume_does_not_overwrite_pre_existing_strict_gate_halt(
        self,
    ) -> None:
        # The cmd_resume routing layer (tested separately) is what
        # prevents this; this test exercises run_strict_resume directly
        # with a token-exhaustion checkpoint on disk to prove the Phase
        # 6E validator catches the suspension_reason mismatch and
        # refuses without clobbering the strict-gate state.
        # (Same recovery semantic as the prior 6E slice.)
        self._write_state(
            status=agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT
            ),
            approval_mode=agent_loop.APPROVAL_MODE_STRICT,
        )
        # Write a token-exhaustion checkpoint directly via the writer.
        agent_loop.write_checkpoint_entry(
            self.repo_root,
            phase=_ACTIVE_PHASE,
            sub_phase=_ACTIVE_SUB_PHASE,
            task=_ACTIVE_TASK,
            cycle_count=1,
            status=_PRE_SUSPENSION_STATUS,
            approval_mode=agent_loop.APPROVAL_MODE_STRICT,
            awaiting_human_for=_PRE_SUSPENSION_AWAITING_HUMAN_FOR,
            active_prompt_path=".agent-loop/claude-prompt.md",
            suspension_reason=(
                agent_loop.TOKEN_EXHAUSTION_SUSPENSION_REASON
            ),
            continuation_budget=2,
            source_artifact_path=".agent-loop/loop-state.json",
        )
        # run_strict_resume must refuse because the checkpoint's
        # suspension_reason does not match the strict-gate halt status.
        rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        # The strict-gate halt is preserved (recovery point intact).
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
        )


if __name__ == "__main__":
    unittest.main()
