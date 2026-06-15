"""Focused tests for the Phase 7C status / recovery UX layer.

Scope of this suite (Phase 7C, narrow):
- `STATUS_SIGNAL_VERSION` is the literal `"phase-7c-v1"`.
- `STATUS_RECOVERY_HINTS` maps every status the orchestrator can
  persist to a one-line operator-actionable next-step hint;
  `STATUS_RECOVERY_FALLBACK` is the catch-all string used for any
  unmapped status.
- `_status_recovery_hint(status)` returns the mapped hint for every
  known status, returns the fallback for an unknown status, and
  returns a dedicated "no status set" hint when `status` is None or
  the empty string.
- `compute_status_summary(repo_root)` always returns a dict, never
  raises, includes a `recovery_hint` field on every code path,
  carries a `load_error` field describing the load failure when
  loop-state is missing or malformed, surfaces every active-state
  field on a healthy loop-state, and reports `active_checkpoint_
  present=True` when a Phase 6D checkpoint exists on disk.
- `_render_status_summary(summary)` produces a deterministic table
  whose first line carries the signal version, every row label /
  value is rendered, a load error is surfaced when present, and the
  trailing line carries the recovery hint.
- `cmd_status` routes through `main(argv)` HANDLERS dispatch, always
  returns 0 (missing state, malformed state, healthy state), and
  never mutates any artifact or creates the orchestrator log.
"""

from __future__ import annotations

import io
import json
import sys
import unittest
import unittest.mock as mock
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


def _baseline_state(**overrides) -> dict:
    data = {
        "phase": "Phase 7 - VS Code Polish",
        "sub_phase": "Phase 7C - Status, Reset, And Recovery UX",
        "task": "Implement the VS Code status layer.",
        "status": "awaiting_claude_implementation",
        "cycle_count": 0,
        "max_cycles": 3,
        "last_verdict": None,
        "last_verdict_phase": None,
        "contract_version": "phase-3a-v2",
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": agent_loop.APPROVAL_MODE_REVIEW,
        "awaiting_human_for": None,
    }
    data.update(overrides)
    return data


class _StatusTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name).resolve()
        (self.repo_root / ".agent-loop").mkdir(parents=True)
        self.state_path = (
            self.repo_root / ".agent-loop" / "loop-state.json"
        )

    def _write_state(self, **overrides) -> dict:
        data = _baseline_state(**overrides)
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return data

    def _snapshot(self) -> dict:
        snap: dict = {}
        for path in self.repo_root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(self.repo_root).as_posix()
                snap[rel] = path.read_bytes()
        return snap


# ----- constants -----


class StatusConstantsTests(unittest.TestCase):

    def test_signal_version_is_phase_7c_v1(self) -> None:
        self.assertEqual(
            agent_loop.STATUS_SIGNAL_VERSION, "phase-7c-v1",
        )

    def test_recovery_hints_is_non_empty_dict(self) -> None:
        self.assertIsInstance(
            agent_loop.STATUS_RECOVERY_HINTS, dict,
        )
        self.assertGreater(
            len(agent_loop.STATUS_RECOVERY_HINTS), 0,
        )

    def test_recovery_hints_cover_every_strict_gate(self) -> None:
        # The strict-mode gates and the token-exhaustion halt are
        # the load-bearing recovery points; every one must have a
        # hint or the operator UX silently regresses on a halt.
        required = {
            agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            agent_loop.HALTED_PRE_FIX_PROMPT,
            agent_loop.HALTED_PRE_CODEX_REVIEW_NORMAL,
            agent_loop.HALTED_PRE_CODEX_REVIEW_FIX,
            agent_loop.HALTED_TOKEN_EXHAUSTION,
            "awaiting_claude_implementation",
            "phase_complete_awaiting_human_approval",
        }
        missing = required - set(agent_loop.STATUS_RECOVERY_HINTS)
        self.assertEqual(
            missing, set(),
            f"STATUS_RECOVERY_HINTS missing required recovery "
            f"points: {sorted(missing)}",
        )

    def test_recovery_fallback_is_non_empty_string(self) -> None:
        self.assertIsInstance(
            agent_loop.STATUS_RECOVERY_FALLBACK, str,
        )
        self.assertGreater(
            len(agent_loop.STATUS_RECOVERY_FALLBACK), 0,
        )


# ----- _status_recovery_hint -----


class StatusRecoveryHintTests(unittest.TestCase):

    def test_known_status_returns_mapped_hint(self) -> None:
        for status, hint in agent_loop.STATUS_RECOVERY_HINTS.items():
            self.assertEqual(
                agent_loop._status_recovery_hint(status), hint,
            )

    def test_unknown_status_returns_fallback(self) -> None:
        self.assertEqual(
            agent_loop._status_recovery_hint("totally_made_up"),
            agent_loop.STATUS_RECOVERY_FALLBACK,
        )

    def test_none_status_returns_no_status_hint(self) -> None:
        hint = agent_loop._status_recovery_hint(None)
        self.assertIn("no status set", hint)
        self.assertNotEqual(hint, agent_loop.STATUS_RECOVERY_FALLBACK)

    def test_empty_string_status_returns_no_status_hint(self) -> None:
        hint = agent_loop._status_recovery_hint("")
        self.assertIn("no status set", hint)


# ----- compute_status_summary -----


class ComputeStatusSummaryTests(_StatusTestCase):

    def test_missing_loop_state_returns_load_error_summary(self) -> None:
        # No state file planted.
        summary = agent_loop.compute_status_summary(self.repo_root)
        self.assertIsNone(summary["status"])
        self.assertIsNotNone(summary["load_error"])
        self.assertIn("halted_input_missing", summary["load_error"])
        self.assertIsNotNone(summary["recovery_hint"])

    def test_malformed_json_loop_state_returns_load_error_summary(
        self,
    ) -> None:
        self.state_path.write_text("not json", encoding="utf-8")
        summary = agent_loop.compute_status_summary(self.repo_root)
        self.assertIsNone(summary["status"])
        self.assertIsNotNone(summary["load_error"])
        self.assertIsNotNone(summary["recovery_hint"])

    def test_healthy_loop_state_surfaces_every_field(self) -> None:
        self._write_state(
            cycle_count=2, last_verdict="NEEDS_FIXES",
            awaiting_human_for=None,
        )
        summary = agent_loop.compute_status_summary(self.repo_root)
        self.assertEqual(
            summary["phase"], "Phase 7 - VS Code Polish",
        )
        self.assertEqual(
            summary["status"], "awaiting_claude_implementation",
        )
        self.assertEqual(summary["cycle_count"], 2)
        self.assertEqual(summary["max_cycles"], 3)
        self.assertEqual(summary["last_verdict"], "NEEDS_FIXES")
        self.assertIsNone(summary["load_error"])
        self.assertIsNotNone(summary["recovery_hint"])

    def test_recovery_hint_matches_status_for_known_status(self) -> None:
        self._write_state(status=agent_loop.HALTED_TOKEN_EXHAUSTION)
        summary = agent_loop.compute_status_summary(self.repo_root)
        self.assertEqual(
            summary["recovery_hint"],
            agent_loop.STATUS_RECOVERY_HINTS[
                agent_loop.HALTED_TOKEN_EXHAUSTION
            ],
        )

    def test_active_checkpoint_present_reported_true_when_on_disk(
        self,
    ) -> None:
        # Plant a checkpoint via the shipped writer so the active-
        # checkpoint detection routes through the real selector.
        self._write_state(
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
            ),
        )
        agent_loop.write_checkpoint_entry(
            self.repo_root,
            phase="Phase 7 - VS Code Polish",
            sub_phase="Phase 7C - Status, Reset, And Recovery UX",
            task="Implement the VS Code status layer.",
            cycle_count=0,
            approval_mode=agent_loop.APPROVAL_MODE_REVIEW,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
            ),
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            active_prompt_path=".agent-loop/claude-prompt.md",
            suspension_reason="token_exhaustion",
            continuation_budget=2,
            source_artifact_path=".agent-loop/loop-state.json",
        )
        summary = agent_loop.compute_status_summary(self.repo_root)
        self.assertTrue(summary["active_checkpoint_present"])

    def test_active_checkpoint_present_reported_false_when_absent(
        self,
    ) -> None:
        self._write_state()
        summary = agent_loop.compute_status_summary(self.repo_root)
        self.assertFalse(summary["active_checkpoint_present"])

    def test_compute_does_not_mutate_loop_state(self) -> None:
        self._write_state()
        before = self.state_path.read_bytes()
        agent_loop.compute_status_summary(self.repo_root)
        after = self.state_path.read_bytes()
        self.assertEqual(before, after)

    def test_compute_does_not_create_orchestrator_log(self) -> None:
        self._write_state()
        log_path = self.repo_root / ".agent-loop" / "orchestrator.log"
        self.assertFalse(log_path.exists())
        agent_loop.compute_status_summary(self.repo_root)
        self.assertFalse(log_path.exists())

    def test_compute_always_includes_signal_version(self) -> None:
        # On healthy state.
        self._write_state()
        s1 = agent_loop.compute_status_summary(self.repo_root)
        self.assertEqual(
            s1["status_signal_version"],
            agent_loop.STATUS_SIGNAL_VERSION,
        )
        # On missing state.
        self.state_path.unlink()
        s2 = agent_loop.compute_status_summary(self.repo_root)
        self.assertEqual(
            s2["status_signal_version"],
            agent_loop.STATUS_SIGNAL_VERSION,
        )


# ----- _render_status_summary -----


class RenderStatusSummaryTests(_StatusTestCase):

    def test_header_carries_signal_version(self) -> None:
        self._write_state()
        summary = agent_loop.compute_status_summary(self.repo_root)
        text = agent_loop._render_status_summary(summary)
        self.assertIn(
            agent_loop.STATUS_SIGNAL_VERSION, text,
        )
        self.assertIn("Phase 7C status", text)

    def test_load_error_surfaced_when_present(self) -> None:
        summary = agent_loop.compute_status_summary(self.repo_root)
        text = agent_loop._render_status_summary(summary)
        self.assertIn("Load error:", text)

    def test_load_error_not_surfaced_when_absent(self) -> None:
        self._write_state()
        summary = agent_loop.compute_status_summary(self.repo_root)
        text = agent_loop._render_status_summary(summary)
        self.assertNotIn("Load error:", text)

    def test_renders_every_row_label(self) -> None:
        self._write_state()
        summary = agent_loop.compute_status_summary(self.repo_root)
        text = agent_loop._render_status_summary(summary)
        for label in (
            "Phase:", "Sub-phase:", "Task:", "Status:",
            "Approval mode:", "Cycle:", "Last verdict:",
            "Last verdict phase:", "Awaiting human for:",
            "Active checkpoint:",
        ):
            self.assertIn(label, text)

    def test_trailing_recovery_hint_line(self) -> None:
        self._write_state()
        summary = agent_loop.compute_status_summary(self.repo_root)
        text = agent_loop._render_status_summary(summary)
        last = text.splitlines()[-1]
        self.assertTrue(last.startswith("Recovery hint:"))
        self.assertIn(
            summary["recovery_hint"], last,
        )

    def test_unset_fields_render_as_unset(self) -> None:
        summary = agent_loop.compute_status_summary(self.repo_root)
        text = agent_loop._render_status_summary(summary)
        self.assertIn("(unset)", text)


# ----- cmd_status via main(argv) -----


class CmdStatusTests(_StatusTestCase):

    def _run_main(self, argv) -> tuple:
        buf = io.StringIO()
        with mock.patch.object(
            agent_loop, "find_repo_root",
            return_value=self.repo_root,
        ):
            with redirect_stdout(buf):
                rc = agent_loop.main(argv)
        return rc, buf.getvalue()

    def test_cli_returns_zero_when_loop_state_missing(self) -> None:
        rc, out = self._run_main(["status"])
        self.assertEqual(rc, 0)
        self.assertIn(agent_loop.STATUS_SIGNAL_VERSION, out)
        self.assertIn("Load error:", out)
        self.assertIn("Recovery hint:", out)

    def test_cli_returns_zero_on_malformed_loop_state(self) -> None:
        self.state_path.write_text("not json", encoding="utf-8")
        rc, out = self._run_main(["status"])
        self.assertEqual(rc, 0)
        self.assertIn("Load error:", out)

    def test_cli_returns_zero_on_healthy_loop_state(self) -> None:
        self._write_state()
        rc, out = self._run_main(["status"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "Drive the next cycle", out,
        )

    def test_cli_does_not_mutate_loop_state(self) -> None:
        self._write_state()
        before = self.state_path.read_bytes()
        self._run_main(["status"])
        after = self.state_path.read_bytes()
        self.assertEqual(before, after)

    def test_cli_does_not_create_orchestrator_log(self) -> None:
        self._write_state()
        log_path = self.repo_root / ".agent-loop" / "orchestrator.log"
        self.assertFalse(log_path.exists())
        self._run_main(["status"])
        self.assertFalse(log_path.exists())

    def test_cli_routes_through_handlers_dispatch(self) -> None:
        self.assertIn("status", agent_loop.HANDLERS)
        self.assertIs(
            agent_loop.HANDLERS["status"], agent_loop.cmd_status,
        )


if __name__ == "__main__":
    unittest.main()
