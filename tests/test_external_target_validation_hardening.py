"""Phase 10F - External Target Validation And Refusal Hardening tests.

Exercises:
  - the Phase 10F internal-coherence extensions to
    `_validate_external_target_attach_record_schema(...)`:
    `mode_selection.selected_by == attached_by`,
    `mode_selection.selected_at == attached_at`,
    `stale_attach_detection.target_path_canonical_at_attach ==
    target_path_canonical`, the matching controller-path equality,
    and the bootstrap_state extension-field null-vs-non-null
    coherence (present-branch requires every extension field null;
    bootstrapped-branch requires every extension field non-null and
    each pinned value matches the Phase 10C contract).
  - the new freshness probe
    `probe_external_target_attach_freshness(controller_root) -> dict`
    detecting target_path drift / missing target dir / missing
    marker files / controller_path drift.
  - the new throwing assertion
    `assert_external_target_attach_fresh(controller_root) -> None`
    raising `HaltError("halted_external_target_stale_attach", ...)`
    on drift and `HaltError("halted_input_missing", ...)` when no
    attach record exists.
  - the aggregator inspector
    `inspect_external_target_attach(controller_root) -> dict`
    reporting attached / schema_valid / schema_violations /
    freshness in a single structured report.
  - the new `inspect-external-target` CLI subcommand (Phase 7C
    reporter pattern: always exits 0; prints the report; never
    mutates).
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402
from agent_loop import HaltError  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"
ATTACH_RECORD_REL = ".agent-loop/external-target.json"


def _make_controller(td: Path) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("test\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10F - External Target Validation And "
                "Refusal Hardening"
            ),
            "task": "phase-10f-test",
            "status": "awaiting_claude_implementation",
            "cycle_count": 0,
            "max_cycles": 3,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": "claude-opus-4-7",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": "review",
            "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )
    return td


def _write_full_target(target_root: Path) -> None:
    (target_root / ".agent-loop").mkdir(parents=True, exist_ok=True)
    (target_root / "TASK.md").write_text("# T\n", encoding="utf-8")
    (target_root / ".agent-loop" / "current-task.md").write_text(
        "# Current Task\n", encoding="utf-8",
    )
    (target_root / ".agent-loop" / "current-phase.md").write_text(
        "# Current Phase\n", encoding="utf-8",
    )
    (target_root / ".agent-loop" / "phase-plan.md").write_text(
        "# Phase Plan\n\n## Active Phase\nT\n", encoding="utf-8",
    )
    (target_root / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "X", "sub_phase": "Y", "task": "z",
            "status": "awaiting_claude_implementation",
            "cycle_count": 0, "max_cycles": 3,
            "last_verdict": None, "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": None, "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": "review", "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )


def _make_valid_present_record(
    *,
    controller_canonical: str,
    target_canonical: str = "/tmp/some-target",
) -> dict:
    """Fully-populated, schema-valid Phase 10B attach record on the
    no-bootstrap `target_canonical_set_present` branch.
    """
    return {
        "attach_record_signal_version": "phase-10b-v1",
        "attached_at": "2026-06-21T17:42:08Z",
        "attached_by": "alice",
        "target_path_canonical": target_canonical,
        "target_path_raw": target_canonical,
        "controller_path_canonical": controller_canonical,
        "controller_identity": {
            "repo_signature": "0" * 64,
            "orchestrator_version": "phase-3d-v0",
            "contract_version": CONTRACT_VERSION,
        },
        "mode_selection": {
            "approval_mode": "review",
            "selected_at": "2026-06-21T17:42:08Z",
            "selected_by": "alice",
        },
        "bootstrap_state": {
            "status": "target_canonical_set_present",
            "bootstrapped_at": None,
            "bootstrapped_by": None,
            "bootstrap_signal_version": None,
            "pre_bootstrap_target_state": "full_target",
            "artifacts_written": None,
            "initial_loop_state_status": None,
            "initial_human_objective_excerpt": None,
            "bootstrap_log_line": None,
        },
        "stale_attach_detection": {
            "target_marker_files_at_attach": [
                "TASK.md",
                ".agent-loop/current-task.md",
                ".agent-loop/current-phase.md",
                ".agent-loop/phase-plan.md",
                ".agent-loop/loop-state.json",
            ],
            "target_path_canonical_at_attach": target_canonical,
            "controller_path_canonical_at_attach": controller_canonical,
        },
        "audit": {
            "attach_log_line": "external target: attached ...",
            "refusal_history": [],
        },
        "canonical_precedence_note": "test precedence note",
    }


def _make_valid_bootstrapped_record(
    *,
    controller_canonical: str,
    target_canonical: str = "/tmp/some-target",
) -> dict:
    """Fully-populated, schema-valid Phase 10B attach record on the
    `target_canonical_set_bootstrapped` branch with the Phase 10C
    extension fields populated.
    """
    record = _make_valid_present_record(
        controller_canonical=controller_canonical,
        target_canonical=target_canonical,
    )
    record["bootstrap_state"] = {
        "status": "target_canonical_set_bootstrapped",
        "bootstrapped_at": "2026-06-21T17:42:08Z",
        "bootstrapped_by": "alice",
        "bootstrap_signal_version": "phase-10c-v1",
        "pre_bootstrap_target_state": "empty_target",
        "artifacts_written": [
            ".agent-loop/current-phase.md",
            ".agent-loop/current-task.md",
            ".agent-loop/loop-state.json",
            ".agent-loop/phase-plan.md",
            "TASK.md",
        ],
        "initial_loop_state_status": "awaiting_first_activation",
        "initial_human_objective_excerpt": "Build the thing.",
        "bootstrap_log_line": (
            "external target: bootstrapped ..."
        ),
    }
    return record


# ---------------------------------------------------------------------------
# Schema validator: Phase 10F internal-coherence checks
# ---------------------------------------------------------------------------
class SchemaCoherenceChecksTests(unittest.TestCase):

    def _validate(self, record: dict) -> None:
        agent_loop._validate_external_target_attach_record_schema(
            record,
        )

    def test_accepts_baseline_present_record(self) -> None:
        record = _make_valid_present_record(
            controller_canonical="/c",
        )
        # No raise.
        self._validate(record)

    def test_accepts_baseline_bootstrapped_record(self) -> None:
        record = _make_valid_bootstrapped_record(
            controller_canonical="/c",
        )
        self._validate(record)

    def test_refuses_mode_selection_selected_by_mismatch(self) -> None:
        record = _make_valid_present_record(
            controller_canonical="/c",
        )
        record["mode_selection"]["selected_by"] = "bob"
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertEqual(ctx.exception.status, "halted_input_missing")
        self.assertIn(
            "mode_selection.selected_by", ctx.exception.reason,
        )
        self.assertIn("does not match", ctx.exception.reason)

    def test_refuses_mode_selection_selected_at_mismatch(self) -> None:
        record = _make_valid_present_record(
            controller_canonical="/c",
        )
        record["mode_selection"]["selected_at"] = (
            "2099-01-01T00:00:00Z"
        )
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertIn(
            "mode_selection.selected_at", ctx.exception.reason,
        )

    def test_refuses_target_path_snapshot_mismatch(self) -> None:
        record = _make_valid_present_record(
            controller_canonical="/c",
        )
        record["stale_attach_detection"][
            "target_path_canonical_at_attach"
        ] = "/different/path"
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertIn(
            "target_path_canonical_at_attach", ctx.exception.reason,
        )

    def test_refuses_controller_path_snapshot_mismatch(self) -> None:
        record = _make_valid_present_record(
            controller_canonical="/c",
        )
        record["stale_attach_detection"][
            "controller_path_canonical_at_attach"
        ] = "/different/path"
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertIn(
            "controller_path_canonical_at_attach",
            ctx.exception.reason,
        )

    def test_refuses_present_branch_with_nonnull_extension_field(
        self,
    ) -> None:
        record = _make_valid_present_record(
            controller_canonical="/c",
        )
        # status='present' MUST carry null for every Phase 10C
        # extension field; setting bootstrapped_by to non-null is a
        # contradiction.
        record["bootstrap_state"]["bootstrapped_by"] = "alice"
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertIn(
            "target_canonical_set_present", ctx.exception.reason,
        )
        self.assertIn("bootstrapped_by", ctx.exception.reason)

    def test_refuses_bootstrapped_branch_with_null_extension_field(
        self,
    ) -> None:
        record = _make_valid_bootstrapped_record(
            controller_canonical="/c",
        )
        record["bootstrap_state"]["artifacts_written"] = None
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertIn(
            "target_canonical_set_bootstrapped", ctx.exception.reason,
        )
        self.assertIn("artifacts_written", ctx.exception.reason)

    def test_refuses_bootstrapped_branch_with_wrong_signal_version(
        self,
    ) -> None:
        record = _make_valid_bootstrapped_record(
            controller_canonical="/c",
        )
        record["bootstrap_state"]["bootstrap_signal_version"] = (
            "phase-10c-v99"
        )
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertIn(
            "bootstrap_signal_version", ctx.exception.reason,
        )

    def test_refuses_bootstrapped_branch_with_wrong_pre_state(
        self,
    ) -> None:
        record = _make_valid_bootstrapped_record(
            controller_canonical="/c",
        )
        record["bootstrap_state"]["pre_bootstrap_target_state"] = (
            "full_target"
        )
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertIn(
            "pre_bootstrap_target_state", ctx.exception.reason,
        )

    def test_refuses_bootstrapped_branch_with_wrong_initial_status(
        self,
    ) -> None:
        record = _make_valid_bootstrapped_record(
            controller_canonical="/c",
        )
        record["bootstrap_state"]["initial_loop_state_status"] = (
            "awaiting_claude_implementation"
        )
        with self.assertRaises(HaltError) as ctx:
            self._validate(record)
        self.assertIn(
            "initial_loop_state_status", ctx.exception.reason,
        )


# ---------------------------------------------------------------------------
# Freshness probe
# ---------------------------------------------------------------------------
class FreshnessProbeTests(unittest.TestCase):

    def test_reports_not_attached_when_no_record(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            report = (
                agent_loop.probe_external_target_attach_freshness(
                    controller,
                )
            )
            self.assertFalse(report["attached"])
            self.assertFalse(report["is_fresh"])
            self.assertIn(
                "no attach record on disk", report["reasons"][0],
            )
            self.assertEqual(
                report["freshness_signal_version"], "phase-10f-v1",
            )

    def test_reports_fresh_for_intact_attach(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            report = (
                agent_loop.probe_external_target_attach_freshness(
                    controller,
                )
            )
            self.assertTrue(report["attached"])
            self.assertTrue(report["is_fresh"])
            self.assertEqual(report["reasons"], [])
            self.assertEqual(
                report["missing_target_marker_files"], [],
            )

    def test_reports_drift_when_target_removed(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            # Remove the entire target directory after attach.
            import shutil
            shutil.rmtree(target)
            report = (
                agent_loop.probe_external_target_attach_freshness(
                    controller,
                )
            )
            self.assertTrue(report["attached"])
            self.assertFalse(report["is_fresh"])
            joined = " ".join(report["reasons"])
            self.assertIn("no longer exists on disk", joined)

    def test_reports_drift_when_marker_files_removed(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            # Delete some marker files but keep the target dir.
            (target / "TASK.md").unlink()
            (target / ".agent-loop" / "loop-state.json").unlink()
            report = (
                agent_loop.probe_external_target_attach_freshness(
                    controller,
                )
            )
            self.assertFalse(report["is_fresh"])
            self.assertIn(
                "TASK.md", report["missing_target_marker_files"],
            )
            self.assertIn(
                ".agent-loop/loop-state.json",
                report["missing_target_marker_files"],
            )

    def test_reports_drift_when_controller_root_changes(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            # Hand-edit the attach record to claim a different
            # controller path; the probe must observe the drift
            # against the running controller root.
            record_path = controller / ATTACH_RECORD_REL
            record = json.loads(
                record_path.read_text(encoding="utf-8"),
            )
            record["controller_path_canonical"] = (
                "/elsewhere/controller"
            )
            record_path.write_text(
                json.dumps(record), encoding="utf-8",
            )
            report = (
                agent_loop.probe_external_target_attach_freshness(
                    controller,
                )
            )
            self.assertFalse(report["is_fresh"])
            joined = " ".join(report["reasons"])
            self.assertIn(
                "controller_path_canonical drift", joined,
            )

    def test_raises_on_unreadable_attach_record(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            record_path = controller / ATTACH_RECORD_REL
            record_path.parent.mkdir(parents=True, exist_ok=True)
            record_path.write_text("not valid json", encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.probe_external_target_attach_freshness(
                    controller,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )


# ---------------------------------------------------------------------------
# Throwing freshness assertion
# ---------------------------------------------------------------------------
class FreshnessAssertionTests(unittest.TestCase):

    def test_raises_input_missing_when_not_attached(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.assert_external_target_attach_fresh(
                    controller,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "not currently attached", ctx.exception.reason,
            )

    def test_does_not_raise_when_fresh(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            agent_loop.assert_external_target_attach_fresh(controller)

    def test_raises_stale_attach_on_drift(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            (target / "TASK.md").unlink()
            with self.assertRaises(HaltError) as ctx:
                agent_loop.assert_external_target_attach_fresh(
                    controller,
                )
            self.assertEqual(
                ctx.exception.status,
                "halted_external_target_stale_attach",
            )
            self.assertIn(
                "have drifted", ctx.exception.reason,
            )

    def test_halt_status_constant_registered(self) -> None:
        self.assertEqual(
            agent_loop.HALTED_EXTERNAL_TARGET_STALE_ATTACH,
            "halted_external_target_stale_attach",
        )


# ---------------------------------------------------------------------------
# Aggregator inspector
# ---------------------------------------------------------------------------
class InspectorAggregatorTests(unittest.TestCase):

    def test_reports_not_attached_when_no_record(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            report = agent_loop.inspect_external_target_attach(
                controller,
            )
            self.assertFalse(report["attached"])
            self.assertEqual(
                report["inspection_signal_version"],
                "phase-10f-v1",
            )
            self.assertIn("not attached", report["summary"])

    def test_reports_fresh_and_schema_valid(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            report = agent_loop.inspect_external_target_attach(
                controller,
            )
            self.assertTrue(report["attached"])
            self.assertTrue(report["schema_valid"])
            self.assertEqual(report["schema_violations"], [])
            self.assertTrue(report["freshness"]["is_fresh"])
            self.assertIn("schema-valid and fresh", report["summary"])

    def test_reports_schema_violation_on_inconsistent_record(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_present_record(
                controller_canonical=(
                    controller.resolve().as_posix()
                ),
            )
            # Internal inconsistency: selected_by != attached_by.
            record["mode_selection"]["selected_by"] = "bob"
            attach_record = controller / ATTACH_RECORD_REL
            attach_record.parent.mkdir(parents=True, exist_ok=True)
            attach_record.write_text(
                json.dumps(record), encoding="utf-8",
            )
            report = agent_loop.inspect_external_target_attach(
                controller,
            )
            self.assertTrue(report["attached"])
            self.assertFalse(report["schema_valid"])
            self.assertTrue(report["schema_violations"])
            self.assertIn(
                "mode_selection.selected_by",
                report["schema_violations"][0],
            )
            self.assertIn(
                "FAILS schema validation", report["summary"],
            )

    def test_reports_stale_freshness_with_valid_schema(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            (target / "TASK.md").unlink()
            report = agent_loop.inspect_external_target_attach(
                controller,
            )
            self.assertTrue(report["schema_valid"])
            self.assertFalse(report["freshness"]["is_fresh"])
            self.assertIn("STALE on disk", report["summary"])

    def test_raises_on_unreadable_record(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            attach_record = controller / ATTACH_RECORD_REL
            attach_record.parent.mkdir(parents=True, exist_ok=True)
            attach_record.write_text("not valid", encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.inspect_external_target_attach(controller)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )


# ---------------------------------------------------------------------------
# CLI: inspect-external-target
# ---------------------------------------------------------------------------
class CmdInspectExternalTargetTests(unittest.TestCase):

    def _run(self, controller: Path) -> tuple:
        args = argparse.Namespace(cmd="inspect-external-target")
        buf = io.StringIO()
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=controller,
        ):
            with redirect_stdout(buf):
                rc = agent_loop.cmd_inspect_external_target(args)
        return rc, buf.getvalue()

    def test_handler_wired(self) -> None:
        self.assertIn(
            "inspect-external-target", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["inspect-external-target"],
            agent_loop.cmd_inspect_external_target,
        )

    def test_argparse_grammar(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args(["inspect-external-target"])
        self.assertEqual(args.cmd, "inspect-external-target")

    def test_exits_zero_when_not_attached(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            rc, output = self._run(controller)
            self.assertEqual(rc, 0)
            self.assertIn("attached: False", output)
            self.assertIn("not attached", output)

    def test_exits_zero_when_fresh_and_valid(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            rc, output = self._run(controller)
            self.assertEqual(rc, 0)
            self.assertIn("schema_valid: True", output)
            self.assertIn("freshness.is_fresh: True", output)
            self.assertIn("schema-valid and fresh", output)

    def test_exits_zero_and_reports_stale_drift(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            import shutil
            shutil.rmtree(target)
            rc, output = self._run(controller)
            self.assertEqual(rc, 0, "inspector must always exit 0")
            self.assertIn("freshness.is_fresh: False", output)
            self.assertIn("STALE on disk", output)

    def test_inspector_does_not_mutate_attach_record(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            record_path = controller / ATTACH_RECORD_REL
            before = record_path.read_text(encoding="utf-8")
            log_path = controller / ".agent-loop" / "orchestrator.log"
            log_before = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else ""
            )
            self._run(controller)
            after = record_path.read_text(encoding="utf-8")
            log_after = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else ""
            )
            self.assertEqual(
                before, after,
                "inspector MUST NOT mutate the attach record",
            )
            self.assertEqual(
                log_before, log_after,
                "inspector MUST NOT write to orchestrator.log",
            )


# ---------------------------------------------------------------------------
# CLI: verify-external-target - the production runtime path that calls
# the throwing freshness assertion and halts fail-closed on drift.
# ---------------------------------------------------------------------------
class CmdVerifyExternalTargetTests(unittest.TestCase):
    """Phase 10F fix-cycle: proves the production runtime path
    `verify-external-target` halts fail-closed with
    `halted_external_target_stale_attach` persisted in loop-state.json
    on stale attach state, with `halted_input_missing` on missing
    attach record, and exits 0 only on a verifiably fresh attach.
    These tests exercise the shipped CLI surface, not just the
    underlying helper function.
    """

    def _run(self, controller: Path) -> tuple:
        args = argparse.Namespace(cmd="verify-external-target")
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        from contextlib import redirect_stderr
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=controller,
        ):
            with redirect_stdout(buf_out), redirect_stderr(buf_err):
                rc = agent_loop.cmd_verify_external_target(args)
        return rc, buf_out.getvalue(), buf_err.getvalue()

    def _read_controller_state(self, controller: Path) -> dict:
        return json.loads(
            (controller / ".agent-loop" / "loop-state.json")
            .read_text(encoding="utf-8"),
        )

    def test_handler_wired(self) -> None:
        self.assertIn(
            "verify-external-target", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["verify-external-target"],
            agent_loop.cmd_verify_external_target,
        )

    def test_argparse_grammar(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args(["verify-external-target"])
        self.assertEqual(args.cmd, "verify-external-target")

    def test_exits_zero_on_fresh_attach(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            rc, out, err = self._run(controller)
            self.assertEqual(rc, 0)
            self.assertIn(
                "external target attach is fresh", out,
            )
            # Controller loop-state remains at the pre-verify
            # status; verify must NOT mutate it on success.
            state = self._read_controller_state(controller)
            self.assertEqual(
                state["status"], "awaiting_claude_implementation",
            )

    def test_halts_fail_closed_with_stale_attach_status(self) -> None:
        # The load-bearing fix-cycle proof: the production CLI path
        # MUST persist `halted_external_target_stale_attach` into
        # loop-state.json on observed drift.
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            # Delete marker files to introduce drift.
            (target / "TASK.md").unlink()
            (target / ".agent-loop" / "loop-state.json").unlink()
            rc, out, err = self._run(controller)
            self.assertEqual(
                rc, 2,
                "verify-external-target must exit 2 on stale drift",
            )
            state = self._read_controller_state(controller)
            self.assertEqual(
                state["status"],
                "halted_external_target_stale_attach",
                "loop-state.status must be persisted to the new "
                "halt status on stale drift",
            )
            self.assertIn(
                "halted_external_target_stale_attach", err,
            )
            # Attach record is NOT removed by the verify halt; the
            # operator must explicitly detach to clean up.
            self.assertTrue(
                (controller / ATTACH_RECORD_REL).exists(),
            )
            # Orchestrator log received the HALT note.
            log_contents = (
                controller / ".agent-loop" / "orchestrator.log"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "HALT halted_external_target_stale_attach",
                log_contents,
            )

    def test_halts_fail_closed_when_target_dir_removed(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
            )
            import shutil
            shutil.rmtree(target)
            rc, out, err = self._run(controller)
            self.assertEqual(rc, 2)
            state = self._read_controller_state(controller)
            self.assertEqual(
                state["status"],
                "halted_external_target_stale_attach",
            )

    def test_halts_with_input_missing_when_no_attach_record(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            rc, out, err = self._run(controller)
            self.assertEqual(
                rc, 2,
                "verify-external-target must exit 2 when no attach "
                "record exists (operator-correctable refusal)",
            )
            state = self._read_controller_state(controller)
            self.assertEqual(
                state["status"], "halted_input_missing",
            )
            self.assertIn(
                "not currently attached", err,
            )


if __name__ == "__main__":
    unittest.main()
