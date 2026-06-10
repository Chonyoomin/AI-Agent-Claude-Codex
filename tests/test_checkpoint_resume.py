"""Focused tests for the Phase 6E checkpoint-backed resume slice.

Scope of this suite (Phase 6E, narrow):
- `_load_active_checkpoint(...)` returns None when no checkpoint
  exists, returns the single payload when one exists, returns the
  newest by `created_at` when several exist, and propagates the
  Phase 6D read-side HaltError when an on-disk entry is malformed.
- `_validate_checkpoint_against_loop_state(...)` refuses fail-closed
  when any of `phase`, `sub_phase`, `task`, `cycle_count`,
  `approval_mode`, or `awaiting_human_for` disagrees between the
  checkpoint and the canonical loop-state; refuses when the
  checkpoint's `suspension_reason` does not match the active
  strict-gate halt status; and accepts a fully matching checkpoint
  silently.
- `run_strict_resume(...)` proceeds backward-compatibly when no
  checkpoint exists (pre-6D paused cycles still resume), proceeds
  when a fully matching checkpoint exists, refuses fail-closed on a
  stale / contradictory / malformed / unrecognized checkpoint, and
  preserves the saved strict-gate `status` + `awaiting_human_for` on
  every refusal (so a corrected operator state allows a fresh resume
  to dispatch). Refusals never widen autonomy, never bypass any
  Phase 5 human gate, and never call any of the dispatch helpers.

This slice does not enable token-exhaustion continuation chaining,
automatic continuation, or any other continuation-driving runtime
behavior; no test in this suite exercises those paths.
"""

from __future__ import annotations

import json
import sys
import time
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


_ACTIVE_PHASE = "Phase 6 - Durable Memory and Optional Context Layer"
_ACTIVE_SUB_PHASE = "Phase 6E - Checkpoint Resume Initial Slice"
_ACTIVE_TASK = "Implement checkpoint-backed resume."
_SOURCE_ARTIFACT = ".agent-loop/current-task.md"


def _baseline_loop_state(**overrides) -> dict:
    """Loop-state suitable for a strict-gate pause. Required Phase 3A
    keys are present, `contract_version` is the only supported value,
    `approval_mode` is `strict`, and `status` is the
    `pre_claude_prompt` strict-gate halt with the matching
    `awaiting_human_for` value."""
    data = {
        "phase": _ACTIVE_PHASE,
        "sub_phase": _ACTIVE_SUB_PHASE,
        "task": _ACTIVE_TASK,
        "status": agent_loop.HALTED_PRE_CLAUDE_PROMPT,
        "cycle_count": 0,
        "max_cycles": 3,
        "last_verdict": None,
        "last_verdict_phase": None,
        "contract_version": "phase-3a-v2",
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": agent_loop.APPROVAL_MODE_STRICT,
        "awaiting_human_for": agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
    }
    data.update(overrides)
    return data


class _ResumeTestCase(unittest.TestCase):
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

    def _write_checkpoint(self, **overrides) -> Path:
        kwargs = dict(
            phase=_ACTIVE_PHASE,
            sub_phase=_ACTIVE_SUB_PHASE,
            task=_ACTIVE_TASK,
            cycle_count=0,
            status=agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            approval_mode=agent_loop.APPROVAL_MODE_STRICT,
            awaiting_human_for=agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
            active_prompt_path=".agent-loop/claude-prompt.md",
            suspension_reason=agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            continuation_budget=2,
            source_artifact_path=_SOURCE_ARTIFACT,
        )
        kwargs.update(overrides)
        return agent_loop.write_checkpoint_entry(self.repo_root, **kwargs)

    def _state_on_disk(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))


# ----- _load_active_checkpoint -----


class LoadActiveCheckpointTests(_ResumeTestCase):

    def test_returns_none_when_no_checkpoint_directory(self) -> None:
        self.assertIsNone(
            agent_loop._load_active_checkpoint(self.repo_root),
        )

    def test_returns_only_payload_when_single_checkpoint_exists(self) -> None:
        path = self._write_checkpoint()
        loaded = agent_loop._load_active_checkpoint(self.repo_root)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["phase"], _ACTIVE_PHASE)
        self.assertEqual(loaded["sub_phase"], _ACTIVE_SUB_PHASE)
        self.assertEqual(
            loaded["suspension_reason"], agent_loop.HALTED_PRE_CLAUDE_PROMPT,
        )
        self.assertTrue(path.is_file())  # storage not mutated

    def test_returns_newest_by_created_at_when_multiple_exist(self) -> None:
        # Plant three checkpoints with distinct bodies, spaced apart so
        # their created_at timestamps differ. The newest should win.
        self._write_checkpoint(task=f"{_ACTIVE_TASK} 1")
        time.sleep(1.05)
        self._write_checkpoint(task=f"{_ACTIVE_TASK} 2")
        time.sleep(1.05)
        self._write_checkpoint(task=f"{_ACTIVE_TASK} 3")
        loaded = agent_loop._load_active_checkpoint(self.repo_root)
        self.assertEqual(loaded["task"], f"{_ACTIVE_TASK} 3")

    def test_propagates_haltError_for_malformed_checkpoint(self) -> None:
        # Plant a hand-crafted checkpoint with a missing required body
        # field; read_checkpoint_entry refuses fail-closed and the
        # refusal propagates out of _load_active_checkpoint.
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "signal_version": agent_loop.MEMORY_SIGNAL_VERSION,
            "category": agent_loop.MEMORY_CATEGORY_CHECKPOINT,
            "phase": _ACTIVE_PHASE,
            "sub_phase": _ACTIVE_SUB_PHASE,
            "cycle_count": 0,
            "source_artifact_path": _SOURCE_ARTIFACT,
            "created_at": "2026-06-09T12:00:00Z",
            "supersedes": None,
            "body": json.dumps({}),  # missing every checkpoint-body field
        }
        (self.checkpoint_dir / "20260609T120000Z-deadbeef.json").write_text(
            json.dumps(entry), encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._load_active_checkpoint(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")


# ----- _validate_checkpoint_against_loop_state -----


class ValidateCheckpointAgainstLoopStateTests(_ResumeTestCase):

    def _both(self, **checkpoint_overrides):
        """Return a matched (loop_state, checkpoint) pair where the
        checkpoint dict carries the same context fields plus the
        suspension_reason matching the strict-gate status. Apply
        overrides only to the checkpoint side so the test can
        introduce a deliberate mismatch."""
        loop_state = _baseline_loop_state()
        checkpoint = {
            "phase": loop_state["phase"],
            "sub_phase": loop_state["sub_phase"],
            "task": loop_state["task"],
            "cycle_count": loop_state["cycle_count"],
            "approval_mode": loop_state["approval_mode"],
            "awaiting_human_for": loop_state["awaiting_human_for"],
            "suspension_reason": loop_state["status"],
            "active_prompt_path": ".agent-loop/claude-prompt.md",
            "continuation_budget": 2,
        }
        checkpoint.update(checkpoint_overrides)
        return loop_state, checkpoint

    def test_matching_checkpoint_accepts(self) -> None:
        loop_state, checkpoint = self._both()
        # Must not raise.
        agent_loop._validate_checkpoint_against_loop_state(
            checkpoint, loop_state,
        )

    def test_phase_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(phase="Phase 5 - Approval Modes")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_checkpoint_against_loop_state(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("phase", cm.exception.reason)

    def test_sub_phase_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(sub_phase="Phase 6D - Other")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_checkpoint_against_loop_state(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("sub_phase", cm.exception.reason)

    def test_task_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(task="some other task string")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_checkpoint_against_loop_state(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("task", cm.exception.reason)

    def test_cycle_count_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(cycle_count=5)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_checkpoint_against_loop_state(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("cycle_count", cm.exception.reason)

    def test_approval_mode_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(
            approval_mode=agent_loop.APPROVAL_MODE_REVIEW,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_checkpoint_against_loop_state(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("approval_mode", cm.exception.reason)

    def test_awaiting_human_for_mismatch_refuses(self) -> None:
        loop_state, checkpoint = self._both(
            awaiting_human_for="something_else",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_checkpoint_against_loop_state(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("awaiting_human_for", cm.exception.reason)

    def test_suspension_reason_mismatch_at_strict_gate_refuses(self) -> None:
        # Loop is paused at the pre_claude_prompt strict gate, but the
        # checkpoint claims it was suspended for token_exhaustion. The
        # Phase 6A contract refuses this: a strict-gate halt's
        # suspension_reason must equal the halt status.
        loop_state, checkpoint = self._both(suspension_reason="token_exhaustion")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._validate_checkpoint_against_loop_state(
                checkpoint, loop_state,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("suspension_reason", cm.exception.reason)


# ----- run_strict_resume integration -----


class StrictResumeWithoutCheckpointTests(_ResumeTestCase):
    """Backward compatibility: a pre-6D paused cycle has no
    checkpoint on disk. The resume must still dispatch into the
    existing strict-gate continuation. This pins the
    "missing memory layer must not block a cycle the canonical
    artifacts can already drive" Phase 6A rule for the resume path.
    """

    def test_resume_dispatches_when_no_checkpoint_exists(self) -> None:
        self._write_state()  # status = pre_claude_prompt
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 0)
        dispatch.assert_called_once()


class StrictResumeWithValidCheckpointTests(_ResumeTestCase):

    def test_resume_dispatches_when_checkpoint_matches_loop_state(self) -> None:
        self._write_state()
        self._write_checkpoint()
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 0)
        dispatch.assert_called_once()
        # The validation note is in the orchestrator log.
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("checkpoint validated for resume:", log_text)

    def test_resume_uses_newest_checkpoint_when_multiple_exist(self) -> None:
        self._write_state()
        # Plant a stale + a fresh checkpoint; only the fresh one matches
        # the loop-state, and only the newest is consulted.
        self._write_checkpoint(task="some stale task")
        time.sleep(1.05)
        self._write_checkpoint()  # matches loop-state exactly
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 0)
        dispatch.assert_called_once()


class StrictResumeStaleCheckpointRefusalTests(_ResumeTestCase):
    """A stale or contradictory checkpoint refuses fail-closed and the
    saved strict-gate state is preserved so a corrected operator state
    allows a fresh resume to dispatch."""

    def _assert_refused_and_state_preserved(self, dispatch_mock) -> None:
        # The strict-gate state must be intact after refusal.
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
        )
        self.assertEqual(after["approval_mode"], agent_loop.APPROVAL_MODE_STRICT)
        # Dispatch was never reached.
        dispatch_mock.assert_not_called()
        # The refusal landed in the audit log.
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("strict resume refused:", log_text)

    def test_stale_cycle_count_refuses(self) -> None:
        self._write_state(cycle_count=1)
        self._write_checkpoint(cycle_count=2)
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 2)
        self._assert_refused_and_state_preserved(dispatch)

    def test_stale_task_refuses(self) -> None:
        self._write_state()
        self._write_checkpoint(task="a completely different task")
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 2)
        self._assert_refused_and_state_preserved(dispatch)

    def test_stale_sub_phase_refuses(self) -> None:
        self._write_state()
        self._write_checkpoint(
            sub_phase="Phase 6D - Checkpoint Artifact Storage Initial Slice",
        )
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 2)
        self._assert_refused_and_state_preserved(dispatch)

    def test_contradictory_suspension_reason_refuses(self) -> None:
        # Loop is paused at pre_claude_prompt strict gate but the
        # checkpoint claims token_exhaustion.
        self._write_state()
        self._write_checkpoint(suspension_reason="token_exhaustion")
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 2)
        self._assert_refused_and_state_preserved(dispatch)


class StrictResumeMalformedCheckpointRefusalTests(_ResumeTestCase):

    def test_malformed_checkpoint_on_disk_refuses(self) -> None:
        self._write_state()
        # Plant a hand-crafted checkpoint with a missing required body
        # field (`task`). read_checkpoint_entry refuses fail-closed and
        # _load_active_checkpoint propagates the HaltError, which the
        # resume handler converts into a "strict resume refused" exit 2.
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        body = {
            "checkpoint_signal_version": agent_loop.CHECKPOINT_SIGNAL_VERSION,
            # missing "task"
            "status": agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            "approval_mode": agent_loop.APPROVAL_MODE_STRICT,
            "awaiting_human_for": (
                agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT
            ),
            "active_prompt_path": ".agent-loop/claude-prompt.md",
            "suspension_reason": agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            "continuation_budget": 2,
        }
        entry = {
            "signal_version": agent_loop.MEMORY_SIGNAL_VERSION,
            "category": agent_loop.MEMORY_CATEGORY_CHECKPOINT,
            "phase": _ACTIVE_PHASE,
            "sub_phase": _ACTIVE_SUB_PHASE,
            "cycle_count": 0,
            "source_artifact_path": _SOURCE_ARTIFACT,
            "created_at": "2026-06-09T12:00:00Z",
            "supersedes": None,
            "body": json.dumps(body),
        }
        (self.checkpoint_dir / "20260609T120000Z-deadbeef.json").write_text(
            json.dumps(entry), encoding="utf-8",
        )
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 2)
        dispatch.assert_not_called()
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("strict resume refused:", log_text)
        self.assertIn("malformed", log_text)

    def test_unrecognized_checkpoint_signal_version_refuses(self) -> None:
        self._write_state()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        body = {
            "checkpoint_signal_version": "phase-6d-vNEXT",
            "task": _ACTIVE_TASK,
            "status": agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            "approval_mode": agent_loop.APPROVAL_MODE_STRICT,
            "awaiting_human_for": (
                agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT
            ),
            "active_prompt_path": ".agent-loop/claude-prompt.md",
            "suspension_reason": agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            "continuation_budget": 2,
        }
        entry = {
            "signal_version": agent_loop.MEMORY_SIGNAL_VERSION,
            "category": agent_loop.MEMORY_CATEGORY_CHECKPOINT,
            "phase": _ACTIVE_PHASE,
            "sub_phase": _ACTIVE_SUB_PHASE,
            "cycle_count": 0,
            "source_artifact_path": _SOURCE_ARTIFACT,
            "created_at": "2026-06-09T12:00:00Z",
            "supersedes": None,
            "body": json.dumps(body),
        }
        (self.checkpoint_dir / "20260609T120000Z-cafebabe.json").write_text(
            json.dumps(entry), encoding="utf-8",
        )
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ) as dispatch:
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 2)
        dispatch.assert_not_called()
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT)


class CanonicalPrecedencePreservationTests(_ResumeTestCase):
    """The Phase 6E resume path never mutates checkpoint files and
    never widens the orchestrator's loop-state writes beyond what
    Phase 5C already does. A refused resume preserves both the
    canonical loop-state and the on-disk checkpoint bytes."""

    def test_refused_resume_does_not_mutate_checkpoint_files(self) -> None:
        self._write_state(cycle_count=1)
        path = self._write_checkpoint(cycle_count=2)  # stale
        before = path.read_bytes()
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ):
            rc = agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(rc, 2)
        self.assertEqual(path.read_bytes(), before)

    def test_successful_resume_does_not_mutate_checkpoint_files(self) -> None:
        self._write_state()
        path = self._write_checkpoint()
        before = path.read_bytes()
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_from_increment",
            return_value=0,
        ):
            agent_loop.run_strict_resume(self.repo_root)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
