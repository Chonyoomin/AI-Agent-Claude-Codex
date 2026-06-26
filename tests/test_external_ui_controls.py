"""Phase 10I - Minimal External UI Run/Resume Controls tests.

Exercises:
  - `_EXTERNAL_UI_CONTROL_REGISTRY` shape + closed-enumeration
    invariants (every mutating entry is `copy_paste`; every
    `library_call` entry names a wired delegation function)
  - `build_external_ui_control_view(controller_root) -> dict`
    eligibility-aware view shape
  - `invoke_external_ui_control(controller_root, control_id) -> dict`
    refuses fail-closed for unknown ids and for mutating /
    copy-paste-only ids; succeeds for the three wired library-call
    delegation entries; writes a single audit line
  - `view-external-controls` and `invoke-external-control` CLI
    handlers (argparse wiring, HANDLERS entries, exit codes,
    non-mutation invariants where applicable)

All tests are self-contained, run against a `TemporaryDirectory`
controller layout, and never mutate any real on-disk state.
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
from agent_loop import (  # noqa: E402
    ExternalUiControlRefusal,
    HaltError,
)


CONTRACT_VERSION = "phase-3a-v2"


def _make_controller(td: Path, status: str = "awaiting_claude_implementation") -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text(
        "# TASK.md\n\n## Human Objective\n\nBuild it.\n",
        encoding="utf-8",
    )
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "current-task.md").write_text(
        "# Current Task\n\nphase-10i-test\n", encoding="utf-8",
    )
    (td / ".agent-loop" / "current-phase.md").write_text(
        "# Current Phase\n\nPhase 10I\n", encoding="utf-8",
    )
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10I - Minimal External UI Run/Resume Controls"
            ),
            "task": "phase-10i-test",
            "status": status,
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


# ---------------------------------------------------------------------------
# Constants + registry shape
# ---------------------------------------------------------------------------
class ConstantsAndRegistryTests(unittest.TestCase):

    def test_view_signal_version_constant(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_UI_CONTROL_VIEW_SIGNAL_VERSION,
            "phase-10i-v1",
        )

    def test_delegation_note_pins_phase_10g_boundary(self) -> None:
        note = agent_loop.EXTERNAL_UI_CONTROL_DELEGATION_NOTE
        self.assertIn("Phase 10G CLI-only boundary", note)
        self.assertIn("MUST", note)
        self.assertIn("dispatch_mode", note)

    def test_registry_is_nonempty_and_well_formed(self) -> None:
        registry = agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
        self.assertGreater(len(registry), 0)
        for spec in registry:
            for required in (
                "id", "label", "command", "dispatch_mode",
                "category", "delegated_library_function",
                "eligibility_states",
            ):
                self.assertIn(required, spec)
            self.assertIn(
                spec["dispatch_mode"],
                ("library_call", "copy_paste"),
            )
            self.assertIn(spec["category"], ("read_only", "mutating"))

    def test_mutating_entries_are_always_copy_paste(self) -> None:
        for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY:
            if spec["category"] == "mutating":
                self.assertEqual(
                    spec["dispatch_mode"], "copy_paste",
                    f"control {spec['id']!r} is mutating but its "
                    f"dispatch_mode is {spec['dispatch_mode']!r}; "
                    f"Phase 10G CLI-only boundary requires "
                    f"copy_paste for mutating controls",
                )
                self.assertIsNone(
                    spec["delegated_library_function"],
                    f"control {spec['id']!r} is mutating but names a "
                    f"delegated_library_function",
                )

    def test_library_call_entries_name_wired_functions(self) -> None:
        wired = {
            "build_external_ui_status_view",
            "build_external_ui_control_view",
            "inspect_external_target_attach",
        }
        for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY:
            if spec["dispatch_mode"] == "library_call":
                self.assertIn(
                    spec["delegated_library_function"], wired,
                    f"control {spec['id']!r} is library_call but "
                    f"names function "
                    f"{spec['delegated_library_function']!r} which "
                    f"is not wired in invoke_external_ui_control",
                )

    def test_registry_ids_are_unique(self) -> None:
        ids = [
            c["id"] for c in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
        ]
        self.assertEqual(
            len(ids), len(set(ids)),
            "duplicate control id in _EXTERNAL_UI_CONTROL_REGISTRY",
        )

    def test_registry_covers_run_resume_inspect(self) -> None:
        ids = {
            c["id"]
            for c in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
        }
        # The Phase 10I prompt explicitly names "run/resume/inspect"
        # as the bounded control set; every one of those names MUST
        # appear in the rendered registry.
        for required in ("run", "resume", "inspect-external-target"):
            self.assertIn(
                required, ids,
                f"Phase 10I registry does not surface required "
                f"control id {required!r}",
            )


# ---------------------------------------------------------------------------
# build_external_ui_control_view
# ---------------------------------------------------------------------------
class ViewModelBuildTests(unittest.TestCase):

    def test_view_shape_with_awaiting_implementation_status(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            view = agent_loop.build_external_ui_control_view(
                controller,
            )
            self.assertEqual(
                view["view_signal_version"], "phase-10i-v1",
            )
            self.assertEqual(
                view["controller_path_canonical"],
                controller.resolve().as_posix(),
            )
            self.assertEqual(
                view["current_loop_state_status"],
                "awaiting_claude_implementation",
            )
            self.assertEqual(
                len(view["controls"]),
                len(agent_loop._EXTERNAL_UI_CONTROL_REGISTRY),
            )
            self.assertIn(
                "Phase 10G CLI-only boundary",
                view["delegation_note"],
            )

    def test_run_is_eligible_from_awaiting_implementation(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            view = agent_loop.build_external_ui_control_view(
                controller,
            )
            run = next(c for c in view["controls"] if c["id"] == "run")
            self.assertTrue(run["currently_eligible"])
            self.assertEqual(run["category"], "mutating")
            self.assertEqual(run["dispatch_mode"], "copy_paste")

    def test_resume_is_not_eligible_from_awaiting_implementation(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            view = agent_loop.build_external_ui_control_view(
                controller,
            )
            resume = next(
                c for c in view["controls"] if c["id"] == "resume"
            )
            self.assertFalse(resume["currently_eligible"])
            self.assertIn(
                "not in the control's eligible set",
                resume["eligibility_reason"],
            )

    def test_resume_eligible_when_strict_gate_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "controller",
                status=agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            )
            view = agent_loop.build_external_ui_control_view(
                controller,
            )
            resume = next(
                c for c in view["controls"] if c["id"] == "resume"
            )
            self.assertTrue(resume["currently_eligible"])

    def test_view_handles_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "controller"
            controller.mkdir()
            view = agent_loop.build_external_ui_control_view(
                controller,
            )
            self.assertIsNone(view["current_loop_state_status"])
            # always-sensible controls remain eligible
            for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY:
                if spec["eligibility_states"] is None:
                    descriptor = next(
                        c for c in view["controls"]
                        if c["id"] == spec["id"]
                    )
                    self.assertTrue(descriptor["currently_eligible"])
                else:
                    descriptor = next(
                        c for c in view["controls"]
                        if c["id"] == spec["id"]
                    )
                    self.assertFalse(descriptor["currently_eligible"])
                    self.assertIn(
                        "unavailable",
                        descriptor["eligibility_reason"],
                    )


# ---------------------------------------------------------------------------
# invoke_external_ui_control
# ---------------------------------------------------------------------------
class InvokeLibraryDelegationTests(unittest.TestCase):

    def test_unknown_control_id_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            with self.assertRaises(ExternalUiControlRefusal) as ctx:
                agent_loop.invoke_external_ui_control(
                    controller, "no-such-control-xyzzy",
                )
            self.assertIn(
                "unknown external UI control id",
                ctx.exception.reason,
            )

    def test_refusal_is_not_a_HaltError(self) -> None:
        # Phase 10G UI contract: the UI MUST NOT call mutating /
        # throwing helpers such as `_halt(...)`, and refusals MUST
        # NOT produce a canonical halt record. Surfacing refusals as
        # `HaltError` would risk a caller routing them through
        # `_halt(...)`; the dedicated `ExternalUiControlRefusal`
        # subclass keeps the two refusal vocabularies separate.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            with self.assertRaises(ExternalUiControlRefusal) as ctx:
                agent_loop.invoke_external_ui_control(
                    controller, "run",
                )
            self.assertNotIsInstance(ctx.exception, HaltError)

    def test_mutating_control_refused_fail_closed(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            with self.assertRaises(ExternalUiControlRefusal) as ctx:
                agent_loop.invoke_external_ui_control(
                    controller, "run",
                )
            # Refusal message MUST carry the Phase 10G boundary
            # vocabulary AND the copy-paste invocation so the
            # operator sees both why they were refused and how to
            # run the command manually.
            self.assertIn(
                "Phase 10G CLI-only boundary", ctx.exception.reason,
            )
            self.assertIn(
                "python scripts/agent_loop.py run",
                ctx.exception.reason,
            )

    def test_copy_paste_readonly_control_refused(self) -> None:
        # `status` is read_only but copy_paste (no library entry
        # point in this slice); the UI MUST NOT dispatch a CLI
        # subprocess to execute it either.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            with self.assertRaises(ExternalUiControlRefusal) as ctx:
                agent_loop.invoke_external_ui_control(
                    controller, "status",
                )
            self.assertIn(
                "dispatch_mode='copy_paste'", ctx.exception.reason,
            )

    def test_view_external_status_library_delegation_succeeds(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            outcome = agent_loop.invoke_external_ui_control(
                controller, "view-external-status",
            )
            self.assertTrue(outcome["invoked"])
            self.assertEqual(
                outcome["control_id"], "view-external-status",
            )
            self.assertEqual(
                outcome["delegated_library_function"],
                "build_external_ui_status_view",
            )
            self.assertIsInstance(outcome["result"], dict)
            self.assertEqual(
                outcome["result"]["view_signal_version"],
                "phase-10h-v1",
            )

    def test_view_external_controls_library_delegation_succeeds(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            outcome = agent_loop.invoke_external_ui_control(
                controller, "view-external-controls",
            )
            self.assertEqual(
                outcome["delegated_library_function"],
                "build_external_ui_control_view",
            )
            self.assertEqual(
                outcome["result"]["view_signal_version"],
                "phase-10i-v1",
            )

    def test_inspect_external_target_library_delegation_succeeds(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            outcome = agent_loop.invoke_external_ui_control(
                controller, "inspect-external-target",
            )
            self.assertEqual(
                outcome["delegated_library_function"],
                "inspect_external_target_attach",
            )
            self.assertIsInstance(outcome["result"], dict)
            self.assertIn("attached", outcome["result"])

    def test_successful_delegation_does_not_write_orchestrator_log(
        self,
    ) -> None:
        # Phase 10G UI contract: the UI MUST NOT write any canonical
        # artifact it reads. `orchestrator.log` is a canonical
        # artifact; a successful library-call delegation MUST NOT
        # append a UI-side audit line to it.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            before = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else None
            )
            agent_loop.invoke_external_ui_control(
                controller, "view-external-controls",
            )
            after_exists = log_path.exists()
            after = (
                log_path.read_text(encoding="utf-8")
                if after_exists else None
            )
            if before is None:
                self.assertFalse(
                    after_exists,
                    "successful library-call delegation must NOT "
                    "create `.agent-loop/orchestrator.log` from "
                    "scratch (Phase 10G UI contract)",
                )
            else:
                self.assertEqual(
                    before, after,
                    "successful library-call delegation must NOT "
                    "append to `.agent-loop/orchestrator.log` "
                    "(Phase 10G UI contract)",
                )

    def test_refusal_does_not_write_audit_line(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            before = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else None
            )
            with self.assertRaises(ExternalUiControlRefusal):
                agent_loop.invoke_external_ui_control(
                    controller, "run",
                )
            after_exists = log_path.exists()
            after = (
                log_path.read_text(encoding="utf-8")
                if after_exists else None
            )
            if before is None:
                self.assertFalse(after_exists)
            else:
                self.assertEqual(before, after)

    def test_refusal_does_not_mutate_loop_state(self) -> None:
        # The contract violation Codex flagged: a refused UI
        # invocation MUST NOT persist `halted_input_missing` (or
        # any other halt status) into `.agent-loop/loop-state.json`.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            with self.assertRaises(ExternalUiControlRefusal):
                agent_loop.invoke_external_ui_control(
                    controller, "run",
                )
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(
                before, after,
                "refused library-call delegation must NOT mutate "
                "`.agent-loop/loop-state.json` (Phase 10G UI "
                "contract)",
            )


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_view_build_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.build_external_ui_control_view(controller)
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
            agent_loop.build_external_ui_control_view(controller)
            log_after = (
                log_path.read_text(encoding="utf-8")
                if log_path.exists() else ""
            )
            self.assertEqual(log_before, log_after)

    def test_library_delegation_does_not_mutate_loop_state(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.invoke_external_ui_control(
                controller, "view-external-controls",
            )
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)


# ---------------------------------------------------------------------------
# CLI: view-external-controls
# ---------------------------------------------------------------------------
class CmdViewExternalControlsTests(unittest.TestCase):

    def _run(self, controller: Path) -> tuple:
        args = argparse.Namespace(cmd="view-external-controls")
        buf = io.StringIO()
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=controller,
        ):
            with redirect_stdout(buf):
                rc = agent_loop.cmd_view_external_controls(args)
        return rc, buf.getvalue()

    def test_handler_wired(self) -> None:
        self.assertIn(
            "view-external-controls", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["view-external-controls"],
            agent_loop.cmd_view_external_controls,
        )

    def test_argparse_grammar(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args(["view-external-controls"])
        self.assertEqual(args.cmd, "view-external-controls")

    def test_exits_zero_with_controls_rendered(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            rc, output = self._run(controller)
            self.assertEqual(rc, 0)
            self.assertIn(
                "signal_version='phase-10i-v1'", output,
            )
            self.assertIn("library-call", output)
            self.assertIn("copy-paste-only", output)
            self.assertIn("ELIGIBLE", output)
            self.assertIn("delegation_note:", output)


# ---------------------------------------------------------------------------
# CLI: invoke-external-control
# ---------------------------------------------------------------------------
class CmdInvokeExternalControlTests(unittest.TestCase):

    def _run(
        self, controller: Path, control_id: str,
    ) -> tuple:
        args = argparse.Namespace(
            cmd="invoke-external-control", control=control_id,
        )
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=controller,
        ):
            with redirect_stdout(stdout_buf):
                with mock.patch.object(
                    agent_loop.sys, "stderr", stderr_buf,
                ):
                    rc = agent_loop.cmd_invoke_external_control(args)
        return rc, stdout_buf.getvalue(), stderr_buf.getvalue()

    def test_handler_wired(self) -> None:
        self.assertIn(
            "invoke-external-control", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["invoke-external-control"],
            agent_loop.cmd_invoke_external_control,
        )

    def test_argparse_grammar_requires_control_flag(self) -> None:
        parser = agent_loop.build_parser()
        # --control is required; parsing without it should exit 2
        # (argparse error).
        with self.assertRaises(SystemExit):
            parser.parse_args(["invoke-external-control"])
        args = parser.parse_args([
            "invoke-external-control",
            "--control", "view-external-controls",
        ])
        self.assertEqual(args.cmd, "invoke-external-control")
        self.assertEqual(args.control, "view-external-controls")

    def test_cli_exits_zero_for_library_call_control(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            rc, stdout, _ = self._run(
                controller, "view-external-controls",
            )
            self.assertEqual(rc, 0)
            self.assertIn("[external-ui]", stdout)
            self.assertIn(
                "control delegated", stdout,
            )
            self.assertIn("view-external-controls", stdout)
            self.assertIn(
                "build_external_ui_control_view", stdout,
            )
            self.assertIn("result keys (top-level)", stdout)

    def test_cli_success_does_not_write_orchestrator_log(self) -> None:
        # Phase 10G UI contract: the UI MUST NOT write any canonical
        # artifact it reads. The CLI handler's success path also
        # must not produce a canonical audit line, even though it
        # prints to stdout.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            log_exists_before = log_path.exists()
            self._run(controller, "view-external-controls")
            self.assertEqual(
                log_path.exists(), log_exists_before,
                "successful invoke-external-control must NOT create "
                "or append to `.agent-loop/orchestrator.log`",
            )

    def test_cli_success_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            self._run(controller, "view-external-controls")
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_cli_refuses_mutating_control_with_nonzero_exit(
        self,
    ) -> None:
        # Refusal contract: exit code 2 + stderr REFUSED message;
        # NO canonical halt status persisted, NO orchestrator.log
        # write.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            state_before = state_path.read_text(encoding="utf-8")
            log_before_exists = log_path.exists()
            rc, stdout, stderr = self._run(controller, "run")
            self.assertEqual(rc, 2)
            # Stderr carries the user-visible refusal message with
            # the Phase 10G boundary vocabulary AND the copy-paste
            # invocation.
            self.assertIn("[external-ui] REFUSED", stderr)
            self.assertIn(
                "Phase 10G CLI-only boundary", stderr,
            )
            self.assertIn(
                "python scripts/agent_loop.py run", stderr,
            )
            # Loop-state is unchanged.
            state_after = state_path.read_text(encoding="utf-8")
            self.assertEqual(state_before, state_after)
            self.assertNotIn(
                "halted_input_missing", state_after,
                "refused invoke-external-control MUST NOT persist "
                "`halted_input_missing` (or any halt status) into "
                "`.agent-loop/loop-state.json` per the Phase 10G "
                "UI contract",
            )
            # No new orchestrator.log written.
            self.assertEqual(
                log_path.exists(), log_before_exists,
                "refused invoke-external-control MUST NOT create "
                "`.agent-loop/orchestrator.log`",
            )

    def test_cli_refuses_unknown_control_with_nonzero_exit(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "controller")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            state_before = state_path.read_text(encoding="utf-8")
            rc, _, stderr = self._run(controller, "no-such-control")
            self.assertEqual(rc, 2)
            self.assertIn("[external-ui] REFUSED", stderr)
            self.assertIn(
                "unknown external UI control id", stderr,
            )
            state_after = state_path.read_text(encoding="utf-8")
            self.assertEqual(state_before, state_after)
            self.assertNotIn(
                "halted_input_missing", state_after,
            )


if __name__ == "__main__":
    unittest.main()
