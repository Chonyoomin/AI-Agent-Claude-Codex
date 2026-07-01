"""Phase 10X - Autonomous Run Console And Completion Ledger tests.

Exercises:
  - module-level constants (signal version, precedence note,
    closed enumerations)
  - pure activity-state / cycle-state / fix-cycle-state helpers
  - phase-plan header parser (bounded by
    RUN_CONSOLE_PHASE_PLAN_HEADER_CAP)
  - completion-ledger derivation from active phase / sub-phase
  - `build_desktop_run_console_view(...)` shape + canonical
    mirrors + activity/cycle/fix-cycle derivation + soft-fail
    on missing loop-state / phase-plan
  - renderer per-line attribution
  - `build_desktop_run_console_controls(...)` widget shape (3
    copy-paste inspection buttons; ZERO library-callable)
  - `cmd_view_desktop_run_console(...)` CLI handler + Phase 7C
    exit-0 pattern
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no Phase 10I library-callable cap widening,
    no persisted run-console cache)
"""
from __future__ import annotations

import argparse
import io
import json
import socket
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"


def _make_controller(
    td: Path,
    status: str = "awaiting_claude_implementation",
    approval_mode: str = "review",
    cycle_count: int = 0,
    max_cycles: int = 3,
    last_verdict=None,
    active_phase: str = "Phase 10 - Future Product Features",
    active_sub_phase: str = (
        "Phase 10X - Autonomous Run Console And Completion Ledger"
    ),
    phase_plan_text=None,
) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("agents\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("claude\n", encoding="utf-8")
    (td / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
    (td / "README.md").write_text("readme\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": active_phase,
            "sub_phase": active_sub_phase,
            "task": "phase-10x-test",
            "status": status,
            "cycle_count": cycle_count,
            "max_cycles": max_cycles,
            "last_verdict": last_verdict,
            "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": "claude-opus-4-7",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": approval_mode,
            "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )
    if phase_plan_text is None:
        phase_plan_text = (
            "## Phase 10V - RAG Source Selection Contract\n"
            "\n"
            "Complete.\n"
            "\n"
            "## Phase 10W - RAG Local Index And Retrieval "
            "Controls\n"
            "\n"
            "Complete.\n"
            "\n"
            "## Phase 10X - Autonomous Run Console And "
            "Completion Ledger\n"
            "\n"
            "Active.\n"
            "\n"
            "## Phase 10Y - Deferred Slice\n"
            "\n"
            "Deferred.\n"
        )
    (td / ".agent-loop" / "phase-plan.md").write_text(
        phase_plan_text, encoding="utf-8",
    )
    (td / ".agent-loop" / "current-phase.md").write_text(
        f"# Current Phase\n\n{active_phase} "
        f"(sub-phase: {active_sub_phase})\n",
        encoding="utf-8",
    )
    (td / ".agent-loop" / "current-task.md").write_text(
        "# Current Task\n\nphase-10x-test\n",
        encoding="utf-8",
    )
    return td


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_RUN_CONSOLE_SIGNAL_VERSION,
            "phase-10x-v1",
        )

    def test_precedence_note_pins_phase_10x_contract(self) -> None:
        note = agent_loop.DESKTOP_RUN_CONSOLE_PRECEDENCE_NOTE
        for needle in (
            "Phase 10X",
            "VISIBILITY-ONLY",
            "Phase 10I",
            "NEVER mutates any canonical artifact",
            "NEVER spawns a subprocess",
            "NEVER opens a network socket",
            "NEVER auto-resumes",
            "NEVER auto-activates",
            "loop-state.json",
            "phase-plan.md",
        ):
            self.assertIn(needle, note, needle)

    def test_activity_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RUN_CONSOLE_ACTIVITY_STATES,
            (
                "running",
                "awaiting_review",
                "awaiting_fix",
                "awaiting_human",
                "phase_complete",
                "halted_recoverable",
                "halted_requires_human",
                "unknown",
            ),
        )

    def test_cycle_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RUN_CONSOLE_CYCLE_STATES,
            (
                "within_budget",
                "at_last_cycle",
                "over_budget",
                "unknown",
            ),
        )

    def test_completion_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RUN_CONSOLE_COMPLETION_STATES,
            ("pending", "in_progress", "complete", "unknown"),
        )

    def test_fix_cycle_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RUN_CONSOLE_FIX_CYCLE_STATES,
            ("not_in_fix_cycle", "in_fix_cycle", "unknown"),
        )

    def test_refusal_reasons_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RUN_CONSOLE_REFUSAL_REASONS,
            (
                "controller_root_invalid",
                "loop_state_unreadable",
                "phase_plan_unreadable",
            ),
        )

    def test_phase_plan_header_cap_is_bounded(self) -> None:
        # A future runtime slice MAY widen this cap only by
        # explicitly editing this constant AND this test.
        self.assertEqual(
            agent_loop.RUN_CONSOLE_PHASE_PLAN_HEADER_CAP, 200,
        )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
class ActivityStateTests(unittest.TestCase):

    def _derive(self, status):
        return agent_loop._run_console_derive_activity_state(status)

    def test_none_returns_unknown(self) -> None:
        self.assertEqual(self._derive(None), "unknown")

    def test_empty_returns_unknown(self) -> None:
        self.assertEqual(self._derive(""), "unknown")

    def test_non_string_returns_unknown(self) -> None:
        self.assertEqual(self._derive(42), "unknown")

    def test_running_family_maps_to_running(self) -> None:
        for status in (
            "claude_implementing",
            "claude_fixing",
            "evidence_capture",
        ):
            self.assertEqual(self._derive(status), "running", status)

    def test_review_maps_to_awaiting_review(self) -> None:
        self.assertEqual(
            self._derive("awaiting_codex_review"),
            "awaiting_review",
        )

    def test_awaiting_claude_maps_to_awaiting_fix(self) -> None:
        self.assertEqual(
            self._derive("awaiting_claude_implementation"),
            "awaiting_fix",
        )

    def test_phase_complete_maps(self) -> None:
        self.assertEqual(
            self._derive("phase_complete_awaiting_human_approval"),
            "phase_complete",
        )

    def test_terminal_halt_maps_to_halted_requires_human(
        self,
    ) -> None:
        for status in (
            "halted_failed_requires_human",
            "halted_max_cycles_reached",
        ):
            self.assertEqual(
                self._derive(status),
                "halted_requires_human",
                status,
            )

    def test_strict_gate_halts_map_to_awaiting_human(self) -> None:
        for status in (
            "halted_awaiting_human_pre_claude_prompt",
            "halted_awaiting_human_pre_fix_prompt",
            "halted_awaiting_human_pre_codex_review_normal",
            "halted_awaiting_human_pre_codex_review_fix",
        ):
            self.assertEqual(
                self._derive(status),
                "awaiting_human",
                status,
            )

    def test_other_halts_map_to_halted_recoverable(self) -> None:
        for status in (
            "halted_human_stop",
            "halted_input_missing",
            "halted_review_malformed",
        ):
            self.assertEqual(
                self._derive(status),
                "halted_recoverable",
                status,
            )


class CycleStateTests(unittest.TestCase):

    def _derive(self, cc, mc):
        return agent_loop._run_console_derive_cycle_state(cc, mc)

    def test_none_returns_unknown(self) -> None:
        self.assertEqual(self._derive(None, 3), "unknown")
        self.assertEqual(self._derive(1, None), "unknown")

    def test_max_cycles_zero_returns_unknown(self) -> None:
        self.assertEqual(self._derive(0, 0), "unknown")

    def test_negative_cycle_returns_unknown(self) -> None:
        self.assertEqual(self._derive(-1, 3), "unknown")

    def test_within_budget(self) -> None:
        self.assertEqual(self._derive(0, 3), "within_budget")
        self.assertEqual(self._derive(1, 3), "within_budget")

    def test_at_last_cycle(self) -> None:
        self.assertEqual(self._derive(2, 3), "at_last_cycle")

    def test_over_budget(self) -> None:
        self.assertEqual(self._derive(3, 3), "over_budget")
        self.assertEqual(self._derive(4, 3), "over_budget")


class FixCycleStateTests(unittest.TestCase):

    def _derive(self, status, last_verdict):
        return agent_loop._run_console_derive_fix_cycle_state(
            status, last_verdict,
        )

    def test_none_status_returns_unknown(self) -> None:
        self.assertEqual(self._derive(None, "NEEDS_FIXES"), "unknown")

    def test_no_verdict_returns_not_in_fix_cycle(self) -> None:
        self.assertEqual(
            self._derive("awaiting_claude_implementation", None),
            "not_in_fix_cycle",
        )

    def test_needs_fixes_with_awaiting_claude(self) -> None:
        self.assertEqual(
            self._derive(
                "awaiting_claude_implementation", "NEEDS_FIXES",
            ),
            "in_fix_cycle",
        )

    def test_needs_fixes_with_claude_fixing(self) -> None:
        self.assertEqual(
            self._derive("claude_fixing", "NEEDS_FIXES"),
            "in_fix_cycle",
        )

    def test_approved_verdict_returns_not_in_fix_cycle(self) -> None:
        self.assertEqual(
            self._derive(
                "awaiting_claude_implementation",
                "APPROVED_FOR_HUMAN_REVIEW",
            ),
            "not_in_fix_cycle",
        )


# ---------------------------------------------------------------------------
# Phase-plan header parser
# ---------------------------------------------------------------------------
class ParsePhasePlanHeadersTests(unittest.TestCase):

    def test_parses_simple_headers(self) -> None:
        text = (
            "# Phase Plan\n"
            "\n"
            "## Phase 10V - RAG Source Selection\n"
            "\n"
            "body\n"
            "\n"
            "## Phase 10W - RAG Local Index\n"
        )
        entries = agent_loop._run_console_parse_phase_plan_headers(
            text,
        )
        self.assertEqual(
            [e["phase_id"] for e in entries],
            ["Phase 10V", "Phase 10W"],
        )
        self.assertEqual(
            entries[0]["title"], "RAG Source Selection",
        )

    def test_ignores_deeper_headers(self) -> None:
        text = (
            "## Phase 10X - Title\n"
            "\n"
            "### Objective\n"
            "\n"
            "body\n"
        )
        entries = agent_loop._run_console_parse_phase_plan_headers(
            text,
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["phase_id"], "Phase 10X")

    def test_supports_fix_phase_prefix(self) -> None:
        text = (
            "## Fix Phase A - Automatic Local Claude Invocation\n"
        )
        entries = agent_loop._run_console_parse_phase_plan_headers(
            text,
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["phase_id"], "Fix Phase A")

    def test_cap_bounds_header_count(self) -> None:
        chunks = [
            f"## Phase {i}A - Test\n"
            for i in range(300)
        ]
        entries = agent_loop._run_console_parse_phase_plan_headers(
            "".join(chunks),
        )
        self.assertLessEqual(
            len(entries),
            agent_loop.RUN_CONSOLE_PHASE_PLAN_HEADER_CAP,
        )

    def test_empty_text_returns_empty_list(self) -> None:
        self.assertEqual(
            agent_loop._run_console_parse_phase_plan_headers(""),
            [],
        )


# ---------------------------------------------------------------------------
# Completion ledger derivation
# ---------------------------------------------------------------------------
class CompletionLedgerTests(unittest.TestCase):

    def _ledger(
        self, headers, active_phase=None, active_sub_phase=None,
        activity_state="awaiting_fix",
    ):
        return agent_loop._run_console_derive_completion_ledger(
            headers,
            active_phase_id=active_phase,
            active_sub_phase_id=active_sub_phase,
            activity_state=activity_state,
        )

    def test_active_sub_phase_marks_prior_complete_and_later_pending(
        self,
    ) -> None:
        headers = [
            {"phase_id": "Phase 10V", "title": "V"},
            {"phase_id": "Phase 10W", "title": "W"},
            {"phase_id": "Phase 10X", "title": "X"},
            {"phase_id": "Phase 10Y", "title": "Y"},
        ]
        ledger = self._ledger(
            headers, active_sub_phase="Phase 10X",
        )
        states = [e["completion_state"] for e in ledger]
        self.assertEqual(
            states, ["complete", "complete", "in_progress", "pending"],
        )

    def test_phase_complete_activity_marks_active_complete(
        self,
    ) -> None:
        headers = [
            {"phase_id": "Phase 10W", "title": "W"},
            {"phase_id": "Phase 10X", "title": "X"},
            {"phase_id": "Phase 10Y", "title": "Y"},
        ]
        ledger = self._ledger(
            headers, active_sub_phase="Phase 10X",
            activity_state="phase_complete",
        )
        self.assertEqual(
            ledger[1]["completion_state"], "complete",
        )

    def test_no_active_match_marks_everything_unknown(self) -> None:
        headers = [
            {"phase_id": "Phase 10W", "title": "W"},
            {"phase_id": "Phase 10Y", "title": "Y"},
        ]
        ledger = self._ledger(
            headers, active_sub_phase="Phase 10X",
        )
        for e in ledger:
            self.assertEqual(e["completion_state"], "unknown")

    def test_progress_snapshot(self) -> None:
        ledger = [
            {"phase_id": "A", "title": "a", "completion_state": "complete"},
            {"phase_id": "B", "title": "b", "completion_state": "complete"},
            {"phase_id": "C", "title": "c", "completion_state": "in_progress"},
            {"phase_id": "D", "title": "d", "completion_state": "pending"},
            {"phase_id": "E", "title": "e", "completion_state": "unknown"},
        ]
        snap = agent_loop._run_console_completion_progress(ledger)
        self.assertEqual(snap["total_phases"], 5)
        self.assertEqual(snap["complete_count"], 2)
        self.assertEqual(snap["in_progress_count"], 1)
        self.assertEqual(snap["pending_count"], 1)
        self.assertEqual(snap["unknown_count"], 1)


# ---------------------------------------------------------------------------
# build_desktop_run_console_view
# ---------------------------------------------------------------------------
class BuildRunConsoleViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "loop_state_readable",
            "phase_plan_readable",
            "active_phase_id",
            "active_sub_phase_id",
            "active_task_summary",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "activity_state",
            "cycle_count",
            "max_cycles",
            "cycle_state",
            "last_verdict",
            "last_verdict_phase",
            "fix_cycle_state",
            "current_phase_md_mirror",
            "current_task_md_mirror",
            "phase_plan_header_cap",
            "phase_plan_headers",
            "completion_ledger",
            "completion_progress",
            "activity_states",
            "cycle_states",
            "completion_states",
            "fix_cycle_states",
            "refusal_reasons",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10x-v1",
        )

    def test_activity_state_reflects_loop_state_status(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status="awaiting_codex_review",
            )
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
        self.assertEqual(view["activity_state"], "awaiting_review")

    def test_cycle_state_derived_from_canonical_counts(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                cycle_count=2, max_cycles=3,
            )
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
        self.assertEqual(view["cycle_state"], "at_last_cycle")

    def test_fix_cycle_state_reflects_last_verdict(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status="awaiting_claude_implementation",
                last_verdict="NEEDS_FIXES",
            )
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
        self.assertEqual(view["fix_cycle_state"], "in_fix_cycle")

    def test_completion_ledger_marks_active_sub_phase_in_progress(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
        by_id = {
            e["phase_id"]: e["completion_state"]
            for e in view["completion_ledger"]
        }
        self.assertEqual(by_id.get("Phase 10W"), "complete")
        self.assertEqual(by_id.get("Phase 10X"), "in_progress")
        self.assertEqual(by_id.get("Phase 10Y"), "pending")

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / "AGENTS.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "CLAUDE.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "TASK.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "README.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / ".agent-loop").mkdir()
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
        self.assertFalse(view["loop_state_readable"])
        self.assertFalse(view["phase_plan_readable"])
        self.assertIsNone(view["current_loop_state_status"])
        self.assertEqual(view["activity_state"], "unknown")

    def test_view_soft_fails_on_missing_phase_plan(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (controller / ".agent-loop" / "phase-plan.md").unlink()
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
        self.assertFalse(view["phase_plan_readable"])
        self.assertEqual(view["completion_ledger"], [])


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RunConsoleRendererTests(unittest.TestCase):

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
        output = "\n".join(
            agent_loop.render_desktop_run_console_text(view),
        )
        for tag in (
            "phase-10x-v1",
            "[canonical mirror]",
            "[advisory]",
            "[run-console]",
            "[completion-ledger]",
            "[cycle]",
            "[fix-cycle]",
        ):
            self.assertIn(tag, output, tag)


# ---------------------------------------------------------------------------
# build_desktop_run_console_controls
# ---------------------------------------------------------------------------
class RunConsoleControlsBuilderTests(unittest.TestCase):

    def test_controls_three_copy_paste_buttons(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_run_console_controls(view)
            )
        self.assertEqual(len(controls), 3)
        ids = [c["id"] for c in controls]
        self.assertEqual(
            ids,
            [
                "run_console_copy_status",
                "run_console_copy_inspect_artifacts",
                "run_console_copy_check_state",
            ],
        )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(
                control["category"], "run_console_visibility",
            )
            self.assertTrue(control["enabled"])
            self.assertTrue(
                control["clipboard_payload"].startswith(
                    "python scripts/agent_loop.py "
                ),
            )

    def test_controls_clipboard_payloads_are_shipped_subcommands(
        self,
    ) -> None:
        # Every clipboard payload MUST resolve to a real
        # `agent_loop.HANDLERS` entry; the run console MUST NOT
        # advertise a non-existent CLI subcommand.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_run_console_controls(view)
            )
        for control in controls:
            payload = control["clipboard_payload"]
            # Grammar: `python scripts/agent_loop.py <sub>`
            sub = payload.split()[2]
            self.assertIn(sub, agent_loop.HANDLERS, sub)


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopRunConsoleTests(unittest.TestCase):

    def _args(self, **kwargs):
        defaults = {"controller_root": None}
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_refuses_missing_controller_root(self) -> None:
        buf_err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(buf_err):
            rc = agent_loop.cmd_view_desktop_run_console(
                self._args(),
            )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-run-console] REFUSED",
            buf_err.getvalue(),
        )

    def test_refuses_invalid_controller_root(self) -> None:
        with TemporaryDirectory() as td:
            # Missing required markers: no AGENTS.md / CLAUDE.md /
            # TASK.md / .agent-loop/ -- the Phase 10L guard refuses.
            buf_err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(
                buf_err,
            ):
                rc = agent_loop.cmd_view_desktop_run_console(
                    self._args(controller_root=str(td)),
                )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_phase_7c_exits_zero_on_valid_root(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = agent_loop.cmd_view_desktop_run_console(
                    self._args(controller_root=str(controller)),
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-run-console]", buf_out.getvalue(),
        )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-run-console", agent_loop.HANDLERS,
        )

    def test_parser_accepts_subcommand(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-run-console",
            "--controller-root", ".",
        ])
        self.assertEqual(args.cmd, "view-desktop-run-console")


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_run_console_view_key(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("run_console_view", view)
        rc = view["run_console_view"]
        self.assertIsInstance(rc, dict)
        self.assertEqual(rc["view_signal_version"], "phase-10x-v1")

    def test_render_includes_phase_10x_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== Run Console (Phase 10X) ===", output,
        )
        self.assertIn("phase-10x-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                agent_loop.build_desktop_run_console_view(
                    controller,
                )
        p.assert_not_called()

    def test_view_does_not_spawn_subprocess(self) -> None:
        import subprocess
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            patches = [
                mock.patch.object(subprocess, "run"),
                mock.patch.object(subprocess, "Popen"),
                mock.patch.object(subprocess, "call"),
                mock.patch.object(subprocess, "check_call"),
                mock.patch.object(subprocess, "check_output"),
                mock.patch("os.system"),
            ]
            mocks = [p.start() for p in patches]
            try:
                agent_loop.build_desktop_run_console_view(
                    controller,
                )
            finally:
                for p in patches:
                    p.stop()
        for m in mocks:
            m.assert_not_called()

    def test_view_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(agent_loop, "_halt") as h:
                agent_loop.build_desktop_run_console_view(
                    controller,
                )
        h.assert_not_called()

    def test_view_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            agent_loop.build_desktop_run_console_view(controller)
            after = ls.read_bytes()
        self.assertEqual(before, after)

    def test_view_does_not_append_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_run_console_view(controller)
        self.assertFalse(log_path.exists())

    def test_view_does_not_persist_run_console_cache(self) -> None:
        # Snapshot the controller-root directory listing before /
        # after so a future edit that writes a cache trips the
        # regression.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            before_root = sorted(
                p.name for p in controller.iterdir()
            )
            before_dot = sorted(
                p.name for p in (controller / ".agent-loop").iterdir()
            )
            agent_loop.build_desktop_run_console_view(controller)
            after_root = sorted(
                p.name for p in controller.iterdir()
            )
            after_dot = sorted(
                p.name for p in (controller / ".agent-loop").iterdir()
            )
        self.assertEqual(before_root, after_root)
        self.assertEqual(before_dot, after_dot)

    def test_phase_10i_library_callable_cap_not_widened(
        self,
    ) -> None:
        # The Phase 10I contract caps library-callable controls
        # at three: `view-external-status`, `view-external-controls`,
        # `inspect-external-target`. The Phase 10X run-console
        # slice MUST NOT widen that cap. Each of the run-console's
        # widget descriptors is `dispatch_mode="copy_paste"`, NOT
        # `dispatch_mode="library_call"`, so no new library-
        # callable control is introduced.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_run_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_run_console_controls(view)
            )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
                control["id"],
            )
        # Anchor the Phase 10I registry itself: exactly three
        # library-callable entries.
        library_callable = [
            c for c in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if c.get("dispatch_mode") == "library_call"
        ]
        self.assertEqual(
            {c["id"] for c in library_callable},
            {
                "view-external-status",
                "view-external-controls",
                "inspect-external-target",
            },
        )


if __name__ == "__main__":
    unittest.main()
