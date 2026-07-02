"""Phase 10Y - Capacity Recovery And Resume Console tests.

Exercises:
  - module-level constants (signal version, precedence note,
    closed enumerations, checkpoint mirror cap)
  - pure capacity-halt / checkpoint-state / resume-policy /
    retry-state helpers
  - bounded checkpoint directory read
  - `build_desktop_resume_console_view(...)` shape + canonical
    mirrors + capacity-halt / checkpoint / resume-policy / retry
    derivation + soft-fail on missing loop-state
  - renderer per-line attribution
  - `build_desktop_resume_console_controls(...)` widget shape
    (three copy-paste buttons; enabled bits gated by the live
    capacity-halt state)
  - `cmd_view_desktop_resume_console(...)` CLI handler + Phase 7C
    exit-0 pattern
  - integration into `assemble_desktop_app_view(...)` +
    `render_desktop_app_text(...)`
  - non-mutation invariants (no socket, no subprocess, no
    orchestrator.log append, no loop-state mutation, no
    `_halt(...)`, no Phase 10I library-callable cap widening,
    no persisted resume-console cache)
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
    awaiting_human_for=None,
    checkpoint_files=None,
) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("agents\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("claude\n", encoding="utf-8")
    (td / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
    (td / "README.md").write_text("readme\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10Y - Capacity Recovery And Resume Console"
            ),
            "task": "phase-10y-test",
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
            "awaiting_human_for": awaiting_human_for,
        }),
        encoding="utf-8",
    )
    if checkpoint_files:
        ckpt_dir = td / ".agent-loop" / "memory" / "checkpoint"
        ckpt_dir.mkdir(parents=True)
        for name in checkpoint_files:
            (ckpt_dir / name).write_text(
                "{}\n", encoding="utf-8",
            )
    return td


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_RESUME_CONSOLE_SIGNAL_VERSION,
            "phase-10y-v1",
        )

    def test_precedence_note_pins_phase_10y_contract(self) -> None:
        note = agent_loop.DESKTOP_RESUME_CONSOLE_PRECEDENCE_NOTE
        for needle in (
            "Phase 10Y",
            "VISIBILITY-ONLY",
            "Phase 10I",
            "NEVER mutates any canonical artifact",
            "NEVER spawns a subprocess",
            "NEVER opens a network socket",
            "NEVER refreshes a token",
            "NEVER polls a token",
            "loop-state.json",
            "checkpoint",
        ):
            self.assertIn(needle, note, needle)

    def test_capacity_halt_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RESUME_CONSOLE_CAPACITY_HALT_STATES,
            (
                "not_halted",
                "awaiting_token_exhaustion_continuation",
                "halted_capacity_recoverable",
                "halted_capacity_terminal",
                "unknown",
            ),
        )

    def test_checkpoint_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RESUME_CONSOLE_CHECKPOINT_STATES,
            ("not_present", "present", "present_multiple", "unknown"),
        )

    def test_resume_policy_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RESUME_CONSOLE_RESUME_POLICY_STATES,
            (
                "manual_resume_only",
                "bounded_auto_continue_available",
                "autonomous_bounded",
                "unknown",
            ),
        )

    def test_retry_states_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RESUME_CONSOLE_RETRY_STATES,
            (
                "not_in_retry",
                "within_retry_budget",
                "at_max_cycles",
                "unknown",
            ),
        )

    def test_refusal_reasons_closed_enum(self) -> None:
        self.assertEqual(
            agent_loop.RESUME_CONSOLE_REFUSAL_REASONS,
            (
                "controller_root_invalid",
                "loop_state_unreadable",
                "checkpoint_dir_unreadable",
            ),
        )

    def test_checkpoint_mirror_cap_is_bounded(self) -> None:
        self.assertEqual(
            agent_loop.RESUME_CONSOLE_CHECKPOINT_MIRROR_CAP, 25,
        )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
class CapacityHaltStateTests(unittest.TestCase):

    def _derive(self, status):
        return (
            agent_loop._resume_console_derive_capacity_halt_state(
                status,
            )
        )

    def test_none_returns_unknown(self) -> None:
        self.assertEqual(self._derive(None), "unknown")

    def test_empty_returns_unknown(self) -> None:
        self.assertEqual(self._derive(""), "unknown")

    def test_token_exhaustion_maps_to_awaiting_continuation(
        self,
    ) -> None:
        self.assertEqual(
            self._derive(agent_loop.HALTED_TOKEN_EXHAUSTION),
            "awaiting_token_exhaustion_continuation",
        )

    def test_terminal_halts_map_to_terminal(self) -> None:
        for status in (
            "halted_failed_requires_human",
            "halted_max_cycles_reached",
        ):
            self.assertEqual(
                self._derive(status),
                "halted_capacity_terminal",
                status,
            )

    def test_other_halts_map_to_recoverable(self) -> None:
        for status in (
            "halted_input_missing",
            "halted_review_malformed",
            "halted_human_stop",
            "halted_awaiting_human_pre_claude_prompt",
        ):
            self.assertEqual(
                self._derive(status),
                "halted_capacity_recoverable",
                status,
            )

    def test_non_halted_maps_to_not_halted(self) -> None:
        for status in (
            "awaiting_claude_implementation",
            "awaiting_codex_review",
            "claude_implementing",
            "phase_complete_awaiting_human_approval",
        ):
            self.assertEqual(
                self._derive(status), "not_halted", status,
            )


class CheckpointStateTests(unittest.TestCase):

    def _derive(self, names):
        return (
            agent_loop._resume_console_derive_checkpoint_state(
                names,
            )
        )

    def test_empty_returns_not_present(self) -> None:
        self.assertEqual(self._derive([]), "not_present")

    def test_single_returns_present(self) -> None:
        self.assertEqual(self._derive(["ckpt.json"]), "present")

    def test_multiple_returns_present_multiple(self) -> None:
        self.assertEqual(
            self._derive(["a.json", "b.json"]),
            "present_multiple",
        )


class ReadCheckpointNamesTests(unittest.TestCase):

    def test_missing_dir_returns_empty_readable(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            names, readable = (
                agent_loop._resume_console_read_checkpoint_names(
                    controller,
                )
            )
        self.assertEqual(names, [])
        self.assertTrue(readable)

    def test_present_dir_returns_sorted_names(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                checkpoint_files=(
                    "b-ckpt.json", "a-ckpt.json", "c-ckpt.json",
                ),
            )
            names, readable = (
                agent_loop._resume_console_read_checkpoint_names(
                    controller,
                )
            )
        self.assertTrue(readable)
        self.assertEqual(
            names,
            ["a-ckpt.json", "b-ckpt.json", "c-ckpt.json"],
        )

    def test_cap_bounds_returned_names(self) -> None:
        many = [f"{i:04d}-ckpt.json" for i in range(30)]
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c", checkpoint_files=many,
            )
            names, readable = (
                agent_loop._resume_console_read_checkpoint_names(
                    controller,
                )
            )
        self.assertTrue(readable)
        self.assertLessEqual(
            len(names),
            agent_loop.RESUME_CONSOLE_CHECKPOINT_MIRROR_CAP,
        )


class ResumePolicyStateTests(unittest.TestCase):

    def _derive(self, mode, halt_state):
        return (
            agent_loop._resume_console_derive_resume_policy_state(
                mode, halt_state,
            )
        )

    def test_token_exhaustion_maps_to_auto_continue(self) -> None:
        for mode in ("review", "strict", "autonomous"):
            self.assertEqual(
                self._derive(
                    mode,
                    "awaiting_token_exhaustion_continuation",
                ),
                "bounded_auto_continue_available",
                mode,
            )

    def test_autonomous_mode_maps_to_autonomous_bounded(self) -> None:
        self.assertEqual(
            self._derive("autonomous", "not_halted"),
            "autonomous_bounded",
        )

    def test_review_and_strict_map_to_manual_only(self) -> None:
        for mode in ("review", "strict"):
            self.assertEqual(
                self._derive(mode, "not_halted"),
                "manual_resume_only",
                mode,
            )

    def test_unknown_mode_maps_to_unknown(self) -> None:
        self.assertEqual(
            self._derive(None, "not_halted"), "unknown",
        )
        self.assertEqual(
            self._derive("bogus", "not_halted"), "unknown",
        )


class RetryStateTests(unittest.TestCase):

    def _derive(self, cc, mc):
        return agent_loop._resume_console_derive_retry_state(cc, mc)

    def test_none_returns_unknown(self) -> None:
        self.assertEqual(self._derive(None, 3), "unknown")
        self.assertEqual(self._derive(1, None), "unknown")

    def test_negative_or_zero_max_cycles_returns_unknown(
        self,
    ) -> None:
        self.assertEqual(self._derive(0, 0), "unknown")
        self.assertEqual(self._derive(-1, 3), "unknown")

    def test_zero_returns_not_in_retry(self) -> None:
        self.assertEqual(self._derive(0, 3), "not_in_retry")

    def test_within_budget_returns_within_retry_budget(self) -> None:
        self.assertEqual(
            self._derive(1, 3), "within_retry_budget",
        )
        self.assertEqual(
            self._derive(2, 3), "within_retry_budget",
        )

    def test_at_max_returns_at_max_cycles(self) -> None:
        self.assertEqual(self._derive(3, 3), "at_max_cycles")
        self.assertEqual(self._derive(4, 3), "at_max_cycles")


# ---------------------------------------------------------------------------
# build_desktop_resume_console_view
# ---------------------------------------------------------------------------
class BuildResumeConsoleViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "loop_state_readable",
            "checkpoint_dir_readable",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "cycle_count",
            "max_cycles",
            "awaiting_human_for",
            "capacity_halt_state",
            "checkpoint_state",
            "checkpoint_count",
            "checkpoint_names",
            "checkpoint_mirror_cap",
            "resume_policy_state",
            "retry_state",
            "recovery_hint",
            "capacity_halt_states",
            "checkpoint_states",
            "resume_policy_states",
            "retry_states",
            "refusal_reasons",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10y-v1",
        )

    def test_capacity_halt_reflects_token_exhaustion(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        self.assertEqual(
            view["capacity_halt_state"],
            "awaiting_token_exhaustion_continuation",
        )
        # Resume policy MUST flip to bounded auto-continue
        # available so the shipped Phase 6G runtime is
        # discoverable.
        self.assertEqual(
            view["resume_policy_state"],
            "bounded_auto_continue_available",
        )

    def test_terminal_halt_maps_to_capacity_terminal(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status="halted_max_cycles_reached",
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        self.assertEqual(
            view["capacity_halt_state"],
            "halted_capacity_terminal",
        )

    def test_checkpoint_present_reflected_in_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                checkpoint_files=("20260701-abc.json",),
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        self.assertEqual(view["checkpoint_state"], "present")
        self.assertEqual(view["checkpoint_count"], 1)
        self.assertIn(
            "20260701-abc.json", view["checkpoint_names"],
        )

    def test_multiple_checkpoints_reflected_in_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                checkpoint_files=("a.json", "b.json"),
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        self.assertEqual(
            view["checkpoint_state"], "present_multiple",
        )

    def test_at_max_cycles_retry_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                cycle_count=3, max_cycles=3,
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        self.assertEqual(view["retry_state"], "at_max_cycles")

    def test_autonomous_mode_reflects_bounded(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c", approval_mode="autonomous",
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        self.assertEqual(
            view["resume_policy_state"], "autonomous_bounded",
        )

    def test_recovery_hint_mirrors_status_recovery_map(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        # The recovery hint MUST come from the shipped
        # `STATUS_RECOVERY_HINTS` map so the resume console does
        # not invent its own recovery advice.
        self.assertEqual(
            view["recovery_hint"],
            agent_loop.STATUS_RECOVERY_HINTS[
                agent_loop.HALTED_TOKEN_EXHAUSTION
            ],
        )

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            for name in ("AGENTS.md", "CLAUDE.md", "TASK.md",
                         "README.md"):
                (controller / name).write_text(
                    "x", encoding="utf-8",
                )
            (controller / ".agent-loop").mkdir()
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        self.assertFalse(view["loop_state_readable"])
        self.assertIsNone(view["current_loop_state_status"])
        self.assertEqual(view["capacity_halt_state"], "unknown")


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class ResumeConsoleRendererTests(unittest.TestCase):

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status=agent_loop.HALTED_TOKEN_EXHAUSTION,
                checkpoint_files=("20260701-abc.json",),
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
        output = "\n".join(
            agent_loop.render_desktop_resume_console_text(view),
        )
        for tag in (
            "phase-10y-v1",
            "[canonical mirror]",
            "[advisory]",
            "[resume-console]",
            "[capacity-halt]",
            "[checkpoint]",
            "[resume-policy]",
            "[retry]",
        ):
            self.assertIn(tag, output, tag)


# ---------------------------------------------------------------------------
# build_desktop_resume_console_controls
# ---------------------------------------------------------------------------
class ResumeConsoleControlsBuilderTests(unittest.TestCase):

    def test_controls_three_copy_paste_buttons(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_resume_console_controls(
                    view,
                )
            )
        self.assertEqual(len(controls), 3)
        ids = [c["id"] for c in controls]
        self.assertEqual(
            ids,
            [
                "resume_console_copy_resume",
                "resume_console_copy_auto_continue",
                "resume_console_copy_check_state",
            ],
        )
        for control in controls:
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(
                control["category"], "resume_console_recovery",
            )
            self.assertTrue(
                control["clipboard_payload"].startswith(
                    "python scripts/agent_loop.py ",
                ),
            )

    def test_resume_disabled_when_not_halted(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_resume_console_controls(
                    view,
                )
            )
        resume = next(
            c for c in controls
            if c["id"] == "resume_console_copy_resume"
        )
        self.assertFalse(resume["enabled"])
        auto = next(
            c for c in controls
            if c["id"] == "resume_console_copy_auto_continue"
        )
        self.assertFalse(auto["enabled"])
        # `check-state` is always enabled because it's a pure
        # reporter.
        check = next(
            c for c in controls
            if c["id"] == "resume_console_copy_check_state"
        )
        self.assertTrue(check["enabled"])

    def test_resume_enabled_on_token_exhaustion(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_resume_console_controls(
                    view,
                )
            )
        resume = next(
            c for c in controls
            if c["id"] == "resume_console_copy_resume"
        )
        self.assertTrue(resume["enabled"])
        auto = next(
            c for c in controls
            if c["id"] == "resume_console_copy_auto_continue"
        )
        self.assertTrue(auto["enabled"])

    def test_auto_continue_disabled_on_non_token_halt(self) -> None:
        # A non-token halt (e.g. `halted_input_missing`) supports
        # `resume` but NOT `auto-continue` per the shipped Phase
        # 6G contract; the console MUST NOT advertise the
        # unrunnable path as enabled.
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c", status="halted_input_missing",
            )
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_resume_console_controls(
                    view,
                )
            )
        resume = next(
            c for c in controls
            if c["id"] == "resume_console_copy_resume"
        )
        self.assertTrue(resume["enabled"])
        auto = next(
            c for c in controls
            if c["id"] == "resume_console_copy_auto_continue"
        )
        self.assertFalse(auto["enabled"])

    def test_resume_disabled_when_capacity_halt_unknown(self) -> None:
        # Fix-cycle regression: `capacity_halt_state == "unknown"`
        # is produced when `build_desktop_resume_console_view(...)`
        # soft-fails an unreadable / malformed `loop-state.json`.
        # The Phase 10Y contract says `resume` is enabled only
        # when a CONFIRMED halt is in flight, so `unknown` MUST
        # fail closed: the operator cannot be invited to paste a
        # `resume` invocation when the surface cannot confirm a
        # halt exists.
        view = {"capacity_halt_state": "unknown"}
        controls = (
            agent_loop.build_desktop_resume_console_controls(view)
        )
        resume = next(
            c for c in controls
            if c["id"] == "resume_console_copy_resume"
        )
        auto = next(
            c for c in controls
            if c["id"] == "resume_console_copy_auto_continue"
        )
        check = next(
            c for c in controls
            if c["id"] == "resume_console_copy_check_state"
        )
        self.assertFalse(resume["enabled"])
        self.assertFalse(auto["enabled"])
        # `check-state` remains enabled because it is a pure
        # Phase 7C reporter (safe even when loop-state is
        # unreadable).
        self.assertTrue(check["enabled"])

    def test_resume_disabled_end_to_end_when_loop_state_unreadable(
        self,
    ) -> None:
        # Fix-cycle regression, end-to-end: point the resume
        # console at a controller root whose `.agent-loop/loop-
        # state.json` cannot be loaded (missing). The view builder
        # MUST soft-fail to `loop_state_readable=False` +
        # `capacity_halt_state="unknown"`, and the paired controls
        # builder MUST disable both `resume` and `auto-continue`.
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            for name in (
                "AGENTS.md", "CLAUDE.md", "TASK.md", "README.md",
            ):
                (controller / name).write_text(
                    "x", encoding="utf-8",
                )
            (controller / ".agent-loop").mkdir()
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_resume_console_controls(
                    view,
                )
            )
        self.assertFalse(view["loop_state_readable"])
        self.assertEqual(view["capacity_halt_state"], "unknown")
        by_id = {c["id"]: c for c in controls}
        self.assertFalse(
            by_id["resume_console_copy_resume"]["enabled"],
        )
        self.assertFalse(
            by_id[
                "resume_console_copy_auto_continue"
            ]["enabled"],
        )
        self.assertTrue(
            by_id["resume_console_copy_check_state"]["enabled"],
        )

    def test_resume_enabled_on_every_confirmed_halt_state(
        self,
    ) -> None:
        # Positive lock-in: for each closed CONFIRMED-halt member
        # (`awaiting_token_exhaustion_continuation`,
        # `halted_capacity_recoverable`,
        # `halted_capacity_terminal`), the `resume` button MUST be
        # enabled. This anchors the closed vocabulary so a future
        # helper edit that regresses the allowlist trips a red
        # test.
        for halt_state in (
            "awaiting_token_exhaustion_continuation",
            "halted_capacity_recoverable",
            "halted_capacity_terminal",
        ):
            with self.subTest(halt_state=halt_state):
                view = {"capacity_halt_state": halt_state}
                controls = (
                    agent_loop.build_desktop_resume_console_controls(
                        view,
                    )
                )
                resume = next(
                    c for c in controls
                    if c["id"] == "resume_console_copy_resume"
                )
                self.assertTrue(resume["enabled"], halt_state)

    def test_confirmed_halt_states_closed_allowlist(self) -> None:
        # Anchor the fix-cycle constant: the allowlist MUST be a
        # strict subset of the closed capacity-halt vocabulary and
        # MUST NOT include `not_halted` or `unknown` (both must
        # fail closed).
        allowlist = (
            agent_loop._RESUME_CONSOLE_CONFIRMED_HALT_STATES
        )
        self.assertEqual(
            allowlist,
            frozenset({
                "awaiting_token_exhaustion_continuation",
                "halted_capacity_recoverable",
                "halted_capacity_terminal",
            }),
        )
        self.assertTrue(
            allowlist.issubset(
                set(
                    agent_loop.RESUME_CONSOLE_CAPACITY_HALT_STATES,
                ),
            ),
        )
        self.assertNotIn("not_halted", allowlist)
        self.assertNotIn("unknown", allowlist)

    def test_controls_clipboard_payloads_are_shipped_subcommands(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_resume_console_controls(
                    view,
                )
            )
        for control in controls:
            payload = control["clipboard_payload"]
            sub = payload.split()[2]
            self.assertIn(sub, agent_loop.HANDLERS, sub)


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopResumeConsoleTests(unittest.TestCase):

    def _args(self, **kwargs):
        defaults = {"controller_root": None}
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_refuses_missing_controller_root(self) -> None:
        buf_err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(buf_err):
            rc = agent_loop.cmd_view_desktop_resume_console(
                self._args(),
            )
        self.assertEqual(rc, 2)
        self.assertIn(
            "[desktop-resume-console] REFUSED",
            buf_err.getvalue(),
        )

    def test_refuses_invalid_controller_root(self) -> None:
        with TemporaryDirectory() as td:
            buf_err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(
                buf_err,
            ):
                rc = agent_loop.cmd_view_desktop_resume_console(
                    self._args(controller_root=str(td)),
                )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())

    def test_phase_7c_exits_zero_on_valid_root(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            buf_out = io.StringIO()
            with redirect_stdout(buf_out):
                rc = agent_loop.cmd_view_desktop_resume_console(
                    self._args(controller_root=str(controller)),
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-resume-console]", buf_out.getvalue(),
        )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-resume-console", agent_loop.HANDLERS,
        )

    def test_parser_accepts_subcommand(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-resume-console",
            "--controller-root", ".",
        ])
        self.assertEqual(
            args.cmd, "view-desktop-resume-console",
        )


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_resume_console_view_key(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("resume_console_view", view)
        rc = view["resume_console_view"]
        self.assertIsInstance(rc, dict)
        self.assertEqual(rc["view_signal_version"], "phase-10y-v1")

    def test_render_includes_phase_10y_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== Capacity Recovery Console (Phase 10Y) ===", output,
        )
        self.assertIn("phase-10y-v1", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_does_not_open_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(socket, "socket") as p:
                agent_loop.build_desktop_resume_console_view(
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
                agent_loop.build_desktop_resume_console_view(
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
                agent_loop.build_desktop_resume_console_view(
                    controller,
                )
        h.assert_not_called()

    def test_view_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls = controller / ".agent-loop" / "loop-state.json"
            before = ls.read_bytes()
            agent_loop.build_desktop_resume_console_view(
                controller,
            )
            after = ls.read_bytes()
        self.assertEqual(before, after)

    def test_view_does_not_append_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_resume_console_view(controller)
        self.assertFalse(log_path.exists())

    def test_view_does_not_persist_resume_console_cache(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            before_root = sorted(
                p.name for p in controller.iterdir()
            )
            before_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
            agent_loop.build_desktop_resume_console_view(controller)
            after_root = sorted(
                p.name for p in controller.iterdir()
            )
            after_dot = sorted(
                p.name
                for p in (controller / ".agent-loop").iterdir()
            )
        self.assertEqual(before_root, after_root)
        self.assertEqual(before_dot, after_dot)

    def test_phase_10i_library_callable_cap_not_widened(
        self,
    ) -> None:
        # The Phase 10Y resume console MUST NOT introduce any new
        # library-callable control. Every descriptor is
        # `dispatch_mode='copy_paste'`.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_resume_console_view(
                controller,
            )
            controls = (
                agent_loop.build_desktop_resume_console_controls(
                    view,
                )
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
