"""Phase 10H - Minimal External UI Read-Only Status Surface tests.

Exercises:
  - `build_external_ui_status_view(controller_root) -> dict`
  - `cmd_view_external_status(args)` CLI handler
  - the `view-external-status` argparse subparser + HANDLERS wiring

The tests prove the read-only UI surface satisfies the approved
Phase 10G contract:
  - reads ONLY the approved canonical controller-side artifacts
    (`.agent-loop/loop-state.json`, `TASK.md`, the Codex-owned
    planning artifacts) plus the approved target-side artifacts
    (`.agent-loop/loop-state.json`, `TASK.md`, etc.) only when
    attach is present AND fresh
  - distinguishes canonical mirrors (each tagged with its source
    artifact) from advisory derived state (each tagged
    `[advisory]`) in the rendered output
  - renders CLI-only mutating operations as copy-paste-only text
    cards (never executes them; the cards include the shipped
    subcommand names with `<placeholder>` operator-supplied
    fields)
  - never mutates any canonical artifact, never writes to
    orchestrator.log, never advances loop-state
  - surfaces refusal / staleness state advisorily from the Phase
    10F inspector report (does NOT itself raise on stale)
  - hard failures (unreadable attach record JSON, non-dict
    top-level) propagate via `HaltError -> _halt` matching the
    inspect-external-target behavior
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
    (td / "TASK.md").write_text(
        "# TASK.md\n\n## Human Objective\n\nBuild it.\n",
        encoding="utf-8",
    )
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "current-task.md").write_text(
        "# Current Task\n\nphase-10h-test\n", encoding="utf-8",
    )
    (td / ".agent-loop" / "current-phase.md").write_text(
        "# Current Phase\n\nPhase 10H\n", encoding="utf-8",
    )
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10H - Minimal External UI Read-Only "
                "Status Surface"
            ),
            "task": "phase-10h-test",
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
    (target_root / "TASK.md").write_text(
        "# TASK.md\n\nTarget task body\n", encoding="utf-8",
    )
    (target_root / ".agent-loop" / "current-task.md").write_text(
        "# Current Task\n\nTarget current task\n",
        encoding="utf-8",
    )
    (target_root / ".agent-loop" / "current-phase.md").write_text(
        "# Current Phase\n\nTarget current phase\n",
        encoding="utf-8",
    )
    (target_root / ".agent-loop" / "phase-plan.md").write_text(
        "# Phase Plan\n\n## Active Phase\n\nTarget\n",
        encoding="utf-8",
    )
    (target_root / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "TARGET_PHASE", "sub_phase": "TARGET_SUB",
            "task": "target task",
            "status": "awaiting_claude_implementation",
            "cycle_count": 2, "max_cycles": 3,
            "last_verdict": None, "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": None, "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": "strict",
            "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ViewConstantsTests(unittest.TestCase):

    def test_view_signal_version_constant(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_UI_VIEW_SIGNAL_VERSION,
            "phase-10h-v1",
        )

    def test_canonical_precedence_note_pins_phase_10g_rule(
        self,
    ) -> None:
        note = agent_loop.EXTERNAL_UI_CANONICAL_PRECEDENCE_NOTE
        self.assertIn("Canonical artifacts on disk always win", note)
        self.assertIn(
            "CLI-only operations are rendered as copyable", note,
        )
        self.assertIn("UI never executes them", note)


# ---------------------------------------------------------------------------
# build_external_ui_status_view: success paths
# ---------------------------------------------------------------------------
class ViewModelBuildTests(unittest.TestCase):

    def test_controller_only_no_attach_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            view = agent_loop.build_external_ui_status_view(
                controller,
            )
            self.assertEqual(
                view["view_signal_version"], "phase-10h-v1",
            )
            self.assertEqual(
                view["controller"]["controller_path_canonical"],
                controller.resolve().as_posix(),
            )
            cls = view["controller"]["loop_state"]
            self.assertTrue(cls["present"])
            self.assertIsNone(cls["error"])
            self.assertEqual(
                cls["mirror"]["phase"],
                "Phase 10 - Future Product Features",
            )
            self.assertEqual(
                cls["mirror"]["status"],
                "awaiting_claude_implementation",
            )
            self.assertEqual(
                cls["mirror"]["approval_mode"], "review",
            )
            self.assertTrue(view["controller"]["task_md"]["present"])
            self.assertFalse(view["attach"]["attached"])
            self.assertFalse(view["target"]["rendered"])
            self.assertEqual(
                view["target"]["reason"], "not attached",
            )
            self.assertEqual(
                view["advisory_status_label"],
                "in-flight (awaiting_claude_implementation)",
            )

    def test_attached_and_fresh_renders_target_view(self) -> None:
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
            view = agent_loop.build_external_ui_status_view(
                controller,
            )
            self.assertTrue(view["attach"]["attached"])
            self.assertTrue(view["attach"]["schema_valid"])
            self.assertTrue(view["attach"]["freshness"]["is_fresh"])
            self.assertTrue(view["target"]["rendered"])
            self.assertEqual(
                view["target"]["reason"], "rendered",
            )
            self.assertEqual(
                view["target"]["target_path_canonical"],
                target.resolve().as_posix(),
            )
            target_ls = view["target"]["loop_state"]
            self.assertEqual(
                target_ls["mirror"]["phase"], "TARGET_PHASE",
            )
            self.assertEqual(
                target_ls["mirror"]["sub_phase"], "TARGET_SUB",
            )
            self.assertEqual(
                target_ls["mirror"]["cycle_count"], 2,
            )
            self.assertEqual(
                target_ls["mirror"]["approval_mode"], "strict",
            )
            # Advisory label is derived from the TARGET status when
            # attached + fresh + target loop-state present.
            self.assertEqual(
                view["advisory_status_label"],
                "in-flight (awaiting_claude_implementation)",
            )
            self.assertTrue(view["target"]["task_md"]["present"])
            self.assertTrue(
                view["target"]["current_task_md"]["present"],
            )
            self.assertTrue(
                view["target"]["current_phase_md"]["present"],
            )

    def test_stale_attach_renders_advisory_note_without_target(
        self,
    ) -> None:
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
            # Remove a marker file to introduce drift.
            (target / "TASK.md").unlink()
            view = agent_loop.build_external_ui_status_view(
                controller,
            )
            self.assertTrue(view["attach"]["attached"])
            self.assertFalse(view["attach"]["freshness"]["is_fresh"])
            self.assertFalse(view["target"]["rendered"])
            self.assertIn(
                "STALE on disk", view["target"]["reason"],
            )
            self.assertTrue(view["advisory_notes"])
            joined = " ".join(view["advisory_notes"])
            self.assertIn("STALE", joined)
            self.assertIn("verify-external-target", joined)
            self.assertIn("detach-external-target", joined)

    def test_advisory_status_label_for_halted_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            # Mutate controller loop-state to a halted status.
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            data = json.loads(
                state_path.read_text(encoding="utf-8"),
            )
            data["status"] = "halted_input_missing"
            state_path.write_text(
                json.dumps(data), encoding="utf-8",
            )
            view = agent_loop.build_external_ui_status_view(
                controller,
            )
            self.assertEqual(
                view["advisory_status_label"],
                "halted (halted_input_missing)",
            )

    def test_advisory_status_label_for_phase_complete(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            data = json.loads(
                state_path.read_text(encoding="utf-8"),
            )
            data["status"] = "phase_complete_awaiting_human_approval"
            state_path.write_text(
                json.dumps(data), encoding="utf-8",
            )
            view = agent_loop.build_external_ui_status_view(
                controller,
            )
            self.assertIn(
                "phase complete", view["advisory_status_label"],
            )

    def test_advisory_status_label_for_awaiting_first_activation(
        self,
    ) -> None:
        # The Phase 10E bootstrap status. Use it directly via the
        # private helper since the public view requires a valid
        # loop-state schema.
        label = agent_loop._ui_advisory_status_label(
            agent_loop.EXTERNAL_TARGET_BOOTSTRAP_AWAITING_FIRST_ACTIVATION_STATUS,
        )
        self.assertIn(
            "awaiting first Phase 4C activation", label,
        )


# ---------------------------------------------------------------------------
# CLI-only operations cards
# ---------------------------------------------------------------------------
class CliOnlyOperationsCardsTests(unittest.TestCase):
    """The view model MUST surface every shipped mutating operation
    as a copy-paste card; the UI MUST NOT execute them. This guards
    the Phase 10G contract requirement that the UI is read-only.
    """

    def setUp(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            self.view = agent_loop.build_external_ui_status_view(
                controller,
            )

    def test_view_includes_cli_only_operation_cards(self) -> None:
        ops = self.view["cli_only_operations"]
        self.assertIsInstance(ops, list)
        self.assertGreater(len(ops), 0)
        for op in ops:
            self.assertIn("label", op)
            self.assertIn("command", op)
            self.assertIn("category", op)
            # Every command MUST be a copy-pasteable shipped CLI
            # invocation; the UI MUST NOT promise to execute.
            self.assertTrue(
                op["command"].startswith(
                    "python scripts/agent_loop.py "
                ),
                f"CLI-only card {op['label']!r} does not use the "
                f"shipped CLI invocation prefix",
            )

    def test_cards_cover_required_mutating_operations(self) -> None:
        commands = [
            op["command"] for op in self.view["cli_only_operations"]
        ]
        joined = " | ".join(commands)
        # Every mutating operation the Phase 10G contract enumerates
        # as CLI-only MUST appear in the rendered cards.
        for shipped in (
            "attach-external-target",
            "detach-external-target",
            "verify-external-target",
            "plan",
            "activate",
            "run",
            "resume",
            "auto-continue",
            "run-long-run-continuation",
            "run-capacity-reprobe",
            "record-final-acceptance",
        ):
            self.assertIn(
                shipped, joined,
                f"CLI-only operation card list does not surface "
                f"shipped subcommand {shipped!r}",
            )

    def test_cards_cover_required_read_only_reporters(self) -> None:
        # The Phase 10G contract pins five read-only reporters that
        # the UI MAY render via the library function but MUST NOT
        # dispatch as a subprocess; the rendered card list MUST
        # surface every one of them so the operator sees the full
        # CLI-only boundary, not a curated subset.
        commands = [
            op["command"] for op in self.view["cli_only_operations"]
        ]
        joined = " | ".join(commands)
        for shipped in (
            "inspect-external-target",
            "inspect-artifacts",
            "status",
            "evaluate-final-acceptance",
            "validate-artifacts",
            "check-state",
        ):
            self.assertIn(
                shipped, joined,
                f"CLI-only operation card list does not surface "
                f"shipped read-only reporter {shipped!r}",
            )

    def test_cards_classify_mutating_vs_read_only_correctly(
        self,
    ) -> None:
        # Each card declares a category; the Phase 10G contract
        # separates mutating commands (write canonical artifacts /
        # persist halt status) from read-only reporters. The UI MUST
        # preserve this distinction so the rendered output mirrors
        # the contract's structure.
        mutating_required = {
            "attach-external-target",
            "detach-external-target",
            "verify-external-target",
            "plan",
            "activate",
            "run",
            "resume",
            "auto-continue",
            "run-long-run-continuation",
            "run-capacity-reprobe",
            "record-final-acceptance",
        }
        read_only_required = {
            "inspect-external-target",
            "inspect-artifacts",
            "status",
            "evaluate-final-acceptance",
            "validate-artifacts",
            "check-state",
        }
        for op in self.view["cli_only_operations"]:
            self.assertIn(
                op["category"], ("mutating", "read_only"),
                f"Card {op['label']!r} has unrecognized category "
                f"{op['category']!r}",
            )
            for token in mutating_required:
                if f" {token} " in op["command"] + " " or (
                    op["command"].endswith(" " + token)
                ):
                    self.assertEqual(
                        op["category"], "mutating",
                        f"Card for {token!r} must be category="
                        f"mutating per Phase 10G; got "
                        f"{op['category']!r}",
                    )
            for token in read_only_required:
                if f" {token} " in op["command"] + " " or (
                    op["command"].endswith(" " + token)
                ):
                    self.assertEqual(
                        op["category"], "read_only",
                        f"Card for {token!r} must be category="
                        f"read_only per Phase 10G; got "
                        f"{op['category']!r}",
                    )

    def test_mutating_cards_carry_placeholders_not_real_values(
        self,
    ) -> None:
        # Operator-identity fields MUST NOT be auto-filled; the
        # cards carry <PLACEHOLDER> tokens.
        for op in self.view["cli_only_operations"]:
            if "--attached-by" in op["command"]:
                self.assertIn(
                    "<NAME>", op["command"],
                    "attach card must carry a <NAME> placeholder "
                    "instead of auto-filling operator identity",
                )
            if "--accepted-by" in op["command"]:
                self.assertIn("<NAME>", op["command"])
            if "--detached-by" in op["command"]:
                self.assertIn("<NAME>", op["command"])


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_build_does_not_mutate_controller_loop_state(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.build_external_ui_status_view(controller)
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_view_build_does_not_write_to_orchestrator_log(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            log_before = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else ""
            )
            agent_loop.build_external_ui_status_view(controller)
            log_after = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else ""
            )
            self.assertEqual(log_before, log_after)

    def test_view_build_does_not_mutate_attach_record(self) -> None:
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
            agent_loop.build_external_ui_status_view(controller)
            after = record_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_view_build_does_not_mutate_target_loop_state(
        self,
    ) -> None:
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
            target_state = (
                target / ".agent-loop" / "loop-state.json"
            )
            before = target_state.read_text(encoding="utf-8")
            agent_loop.build_external_ui_status_view(controller)
            after = target_state.read_text(encoding="utf-8")
            self.assertEqual(before, after)


# ---------------------------------------------------------------------------
# Hard failure propagation
# ---------------------------------------------------------------------------
class HardFailurePropagationTests(unittest.TestCase):

    def test_unreadable_attach_record_propagates_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            attach_record = controller / ATTACH_RECORD_REL
            attach_record.parent.mkdir(parents=True, exist_ok=True)
            attach_record.write_text("not valid", encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.build_external_ui_status_view(controller)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )


# ---------------------------------------------------------------------------
# Render helper output
# ---------------------------------------------------------------------------
class RenderViewLinesTests(unittest.TestCase):

    def test_rendered_lines_attribute_canonical_mirrors(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            view = agent_loop.build_external_ui_status_view(
                controller,
            )
            lines = agent_loop._ui_render_view_lines(view)
            joined = "\n".join(lines)
            # Every canonical-mirror line must carry an attribution.
            self.assertIn("canonical mirror", joined)
            # Advisory lines must be tagged explicitly.
            self.assertIn("[advisory]", joined)
            # The CLI-only operations list must NOT promise
            # execution.
            self.assertIn(
                "the UI does NOT execute these", joined,
            )
            # The Phase 10G precedence reminder must be rendered.
            self.assertIn(
                "Canonical artifacts on disk always win", joined,
            )


# ---------------------------------------------------------------------------
# CLI: view-external-status
# ---------------------------------------------------------------------------
class CmdViewExternalStatusTests(unittest.TestCase):

    def _run(self, controller: Path) -> tuple:
        args = argparse.Namespace(cmd="view-external-status")
        buf = io.StringIO()
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=controller,
        ):
            with redirect_stdout(buf):
                rc = agent_loop.cmd_view_external_status(args)
        return rc, buf.getvalue()

    def test_handler_wired(self) -> None:
        self.assertIn(
            "view-external-status", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["view-external-status"],
            agent_loop.cmd_view_external_status,
        )

    def test_argparse_grammar(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args(["view-external-status"])
        self.assertEqual(args.cmd, "view-external-status")

    def test_exits_zero_with_controller_only_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            rc, output = self._run(controller)
            self.assertEqual(rc, 0)
            self.assertIn(
                "signal_version='phase-10h-v1'", output,
            )
            self.assertIn(
                "controller.loop_state (canonical mirror", output,
            )
            self.assertIn(
                "target.rendered: False", output,
            )
            self.assertIn("[advisory]", output)
            self.assertIn(
                "cli_only_operations (advisory; copy-paste only",
                output,
            )

    def test_exits_zero_with_attached_view(self) -> None:
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
            self.assertIn("target.rendered: True", output)
            self.assertIn(
                "target.loop_state (canonical mirror", output,
            )
            self.assertIn("TARGET_PHASE", output)

    def test_exits_zero_with_stale_attach_view(self) -> None:
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
            rc, output = self._run(controller)
            # Reporter pattern: stale state is REPORT content, not a
            # halt. The CLI MUST exit 0.
            self.assertEqual(
                rc, 0,
                "view-external-status must exit 0 on stale state "
                "(Phase 7C reporter pattern)",
            )
            self.assertIn("attach.freshness.is_fresh", output)
            self.assertIn("False", output)
            self.assertIn("STALE", output)

    def test_cli_does_not_mutate_controller_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            log_before = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else ""
            )
            self._run(controller)
            self.assertEqual(
                before, state_path.read_text(encoding="utf-8"),
            )
            log_after = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else ""
            )
            self.assertEqual(log_before, log_after)

    def test_unreadable_attach_record_halts_via_halt_path(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            attach_record = controller / ATTACH_RECORD_REL
            attach_record.parent.mkdir(parents=True, exist_ok=True)
            attach_record.write_text("not valid", encoding="utf-8")
            args = argparse.Namespace(cmd="view-external-status")
            buf = io.StringIO()
            with mock.patch.object(
                agent_loop, "find_repo_root", return_value=controller,
            ):
                with redirect_stdout(buf):
                    rc = agent_loop.cmd_view_external_status(args)
            # Hard failure: matches inspect-external-target's halt
            # behavior. Exit code 2 + persisted halt status.
            self.assertEqual(rc, 2)
            state = json.loads(
                (controller / ".agent-loop" / "loop-state.json")
                .read_text(encoding="utf-8"),
            )
            self.assertEqual(
                state["status"], "halted_input_missing",
            )


if __name__ == "__main__":
    unittest.main()
