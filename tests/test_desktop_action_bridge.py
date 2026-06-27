"""Phase 10N - Desktop App Action Bridge Initial Slice tests.

Exercises:
  - module-level constants (signal version, precedence note,
    affordance id tuple)
  - the closed `_DESKTOP_ACTION_BRIDGE_AFFORDANCES` registry shape
  - per-affordance eligibility computation against loop-state.status
  - `build_desktop_action_bridge_view(...)` shape + soft-failure
    semantics on missing / malformed loop-state
  - `render_desktop_action_bridge_text(...)` attribution
  - `cmd_view_desktop_actions(...)` CLI handler wiring, the
    Phase-10L-mandated `--controller-root` REQUIRED refusal, and
    the missing-controller-root-markers refusal
  - non-mutation invariants required by the Phase 10L contract
    (no orchestrator.log write, no loop-state mutation, no `_halt`
    invocation, no subprocess spawn, no widening of the Phase 10I
    three-control library-callable cap)
"""
from __future__ import annotations

import argparse
import io
import json
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
    td: Path, status: str = "awaiting_claude_implementation",
) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("# TASK.md\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10N - Desktop App Action Bridge Initial Slice"
            ),
            "task": "phase-10n-test",
            "status": status,
            "cycle_count": 1,
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
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_ACTION_BRIDGE_SIGNAL_VERSION,
            "phase-10n-v1",
        )

    def test_affordance_ids_match_contract_four(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_ACTION_BRIDGE_AFFORDANCE_IDS,
            ("attach", "inspect", "run", "resume"),
        )

    def test_precedence_note_pins_phase_10l_contract(self) -> None:
        note = agent_loop.DESKTOP_ACTION_BRIDGE_PRECEDENCE_NOTE
        for fragment in (
            "Canonical artifacts on disk always win",
            "NEVER silently spawns",
            "NEVER auto-fills",
            "NEVER widens the Phase 10I library-callable",
            "Ineligible affordances",
        ):
            self.assertIn(fragment, note)


# ---------------------------------------------------------------------------
# Affordance registry shape
# ---------------------------------------------------------------------------
class AffordanceRegistryShapeTests(unittest.TestCase):

    def test_registry_has_exactly_four_entries(self) -> None:
        self.assertEqual(
            len(agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES), 4,
        )

    def test_registry_ids_match_closed_tuple(self) -> None:
        ids = tuple(
            spec["id"]
            for spec in agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
        )
        self.assertEqual(
            ids,
            agent_loop.DESKTOP_ACTION_BRIDGE_AFFORDANCE_IDS,
        )

    def test_every_entry_has_required_fields(self) -> None:
        required = {
            "id", "label", "command", "dispatch_mode", "category",
            "delegated_library_function",
            "delegated_phase_10i_control_id",
            "eligibility_states", "audit_note",
        }
        for spec in agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES:
            self.assertEqual(
                set(spec.keys()), required,
                f"affordance {spec.get('id')!r} has wrong field set",
            )

    def test_mutating_affordances_are_copy_paste_only(self) -> None:
        # Phase 10L bridge contract: every mutating affordance MUST
        # carry `dispatch_mode="copy_paste"`. A mutating affordance
        # that claimed `library_call` would widen the Phase 10I cap.
        for spec in agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES:
            if spec["category"] == "mutating":
                self.assertEqual(
                    spec["dispatch_mode"], "copy_paste",
                    f"mutating affordance {spec['id']!r} declares "
                    f"dispatch_mode={spec['dispatch_mode']!r}; "
                    f"Phase 10L contract requires copy_paste for "
                    f"every mutating affordance",
                )

    def test_library_call_delegates_to_phase_10i_registry(
        self,
    ) -> None:
        # The only acceptable library_call delegations are the
        # three Phase 10I-pinned control ids. Phase 10N MUST NOT
        # widen the cap.
        phase_10i_library_call_ids = {
            spec["id"]
            for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if spec["dispatch_mode"] == "library_call"
        }
        for spec in agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES:
            if spec["dispatch_mode"] == "library_call":
                self.assertIn(
                    spec["delegated_phase_10i_control_id"],
                    phase_10i_library_call_ids,
                    f"action-bridge affordance {spec['id']!r} "
                    f"delegates to "
                    f"{spec['delegated_phase_10i_control_id']!r} "
                    f"which is NOT a Phase 10I library-callable "
                    f"control; this would widen the Phase 10I "
                    f"three-control cap",
                )

    def test_no_command_auto_fills_operator_identity(self) -> None:
        # The Phase 10L contract forbids the desktop shell from
        # auto-filling any `--*-by` operator-identity argument. The
        # affordance commands MUST use placeholder text (`<NAME>` /
        # `<PATH>`) rather than actual identity values.
        forbidden_placeholders = (
            "$USER", "$LOGNAME", "$(whoami)", "${USER}",
        )
        for spec in agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES:
            for token in forbidden_placeholders:
                self.assertNotIn(
                    token, spec["command"],
                    f"affordance {spec['id']!r} command contains "
                    f"forbidden identity-auto-fill token {token!r}",
                )

    def test_attach_command_uses_placeholder_identity(self) -> None:
        # Targeted: the attach affordance specifically must surface
        # `<PATH>`, `<NAME>`, and `<MODE>` as placeholder text. The
        # shipped attach-external-target parser requires all three
        # arguments (--target-path, --attached-by, --approval-mode);
        # an operator copy-pasting the affordance command must see
        # placeholders for each so no identity / mode value is
        # silently auto-filled by the desktop shell.
        attach = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "attach"
        )
        self.assertIn("<PATH>", attach["command"])
        self.assertIn("<NAME>", attach["command"])
        self.assertIn("<MODE>", attach["command"])

    def test_attach_command_matches_shipped_parser_contract(
        self,
    ) -> None:
        # The shipped `attach-external-target` parser requires
        # exactly --target-path / --attached-by / --approval-mode
        # (Phase 10B / Phase 10D contract). A prior cycle rendered
        # `--target-root` which does not exist on the shipped
        # parser and omitted the required `--approval-mode`,
        # producing a command that argparse rejects at run time.
        # Pin the affordance command against the real parser so
        # this divergence cannot silently re-appear.
        attach = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "attach"
        )
        self.assertIn("--target-path", attach["command"])
        self.assertIn("--attached-by", attach["command"])
        self.assertIn("--approval-mode", attach["command"])
        # Negative: the prior misnamed flag must be absent.
        self.assertNotIn(
            "--target-root", attach["command"],
            "attach affordance must NOT render the obsolete "
            "`--target-root` flag; the shipped parser uses "
            "`--target-path`",
        )

    def test_attach_command_parses_against_shipped_parser(
        self,
    ) -> None:
        # End-to-end: feed the affordance command (with placeholder
        # values resolved to concrete-looking strings) into the
        # actual `build_parser()` and confirm the shipped argparse
        # surface accepts it without error. This catches any
        # divergence between the affordance template and the real
        # CLI grammar, including the previously-shipped --target-
        # root / missing --approval-mode pair.
        attach = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "attach"
        )
        # Tokenize the command and skip the leading
        # `python scripts/agent_loop.py` prefix; substitute
        # placeholder tokens with concrete values that the parser
        # will accept (--approval-mode is choice-constrained).
        tokens = attach["command"].split()
        self.assertEqual(tokens[:3], [
            "python", "scripts/agent_loop.py",
        ] + tokens[2:3])
        cli_tokens = tokens[2:]
        substituted = []
        for tok in cli_tokens:
            if tok == "<PATH>":
                substituted.append("/tmp/example-target")
            elif tok == "<NAME>":
                substituted.append("test-operator")
            elif tok == "<MODE>":
                # Choose any valid mode from the closed
                # enumeration; argparse will accept it.
                substituted.append("review")
            else:
                substituted.append(tok)
        parser = agent_loop.build_parser()
        args = parser.parse_args(substituted)
        self.assertEqual(args.cmd, "attach-external-target")
        self.assertEqual(args.target_path, "/tmp/example-target")
        self.assertEqual(args.attached_by, "test-operator")
        self.assertEqual(args.approval_mode, "review")
        self.assertIn("<NAME>", attach["command"])


# ---------------------------------------------------------------------------
# Eligibility computation
# ---------------------------------------------------------------------------
class EligibilityTests(unittest.TestCase):

    def test_always_eligible_affordance_when_status_none(
        self,
    ) -> None:
        # `attach` and `inspect` carry eligibility_states=None;
        # they remain operator-decision regardless of loop-state.
        attach = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "attach"
        )
        eligible, reason = agent_loop._desktop_action_eligibility(
            attach, None,
        )
        self.assertTrue(eligible)
        self.assertIn("operator-decision", reason)

    def test_gated_affordance_refused_when_status_none(self) -> None:
        run = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "run"
        )
        eligible, reason = agent_loop._desktop_action_eligibility(
            run, None,
        )
        self.assertFalse(eligible)
        self.assertIn("unavailable", reason)

    def test_run_eligible_when_status_matches(self) -> None:
        run = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "run"
        )
        eligible, reason = agent_loop._desktop_action_eligibility(
            run, "awaiting_claude_implementation",
        )
        self.assertTrue(eligible)
        self.assertIn("matches", reason)

    def test_run_refused_when_status_mismatches(self) -> None:
        run = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "run"
        )
        eligible, reason = agent_loop._desktop_action_eligibility(
            run, "halted_awaiting_human_pre_codex_review_normal",
        )
        self.assertFalse(eligible)
        self.assertIn(
            "is not in the affordance's eligible set", reason,
        )

    def test_resume_eligible_for_each_strict_gate_halt(self) -> None:
        resume = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "resume"
        )
        for halt in (
            agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            agent_loop.HALTED_PRE_FIX_PROMPT,
            agent_loop.HALTED_PRE_CODEX_REVIEW_NORMAL,
            agent_loop.HALTED_PRE_CODEX_REVIEW_FIX,
        ):
            eligible, _ = agent_loop._desktop_action_eligibility(
                resume, halt,
            )
            self.assertTrue(
                eligible,
                f"resume should be eligible at halt {halt!r}",
            )

    def test_resume_refused_when_idle(self) -> None:
        resume = next(
            spec for spec in (
                agent_loop._DESKTOP_ACTION_BRIDGE_AFFORDANCES
            )
            if spec["id"] == "resume"
        )
        eligible, _ = agent_loop._desktop_action_eligibility(
            resume, "awaiting_claude_implementation",
        )
        self.assertFalse(eligible)


# ---------------------------------------------------------------------------
# build_desktop_action_bridge_view
# ---------------------------------------------------------------------------
class BuildActionBridgeViewTests(unittest.TestCase):

    def test_view_shape(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_action_bridge_view(
                controller,
            )
            self.assertEqual(
                view["view_signal_version"], "phase-10n-v1",
            )
            self.assertEqual(
                view["controller_path_canonical"],
                controller.resolve().as_posix(),
            )
            self.assertEqual(
                view["current_loop_state_status"],
                "awaiting_claude_implementation",
            )
            ids = [a["id"] for a in view["affordances"]]
            self.assertEqual(
                ids, list(
                    agent_loop.DESKTOP_ACTION_BRIDGE_AFFORDANCE_IDS,
                ),
            )

    def test_view_run_eligible_idle(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_action_bridge_view(
                controller,
            )
            run_desc = next(
                a for a in view["affordances"] if a["id"] == "run"
            )
            self.assertTrue(run_desc["currently_eligible"])
            resume_desc = next(
                a for a in view["affordances"]
                if a["id"] == "resume"
            )
            self.assertFalse(resume_desc["currently_eligible"])

    def test_view_resume_eligible_at_strict_gate(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status=agent_loop.HALTED_PRE_CODEX_REVIEW_NORMAL,
            )
            view = agent_loop.build_desktop_action_bridge_view(
                controller,
            )
            resume_desc = next(
                a for a in view["affordances"]
                if a["id"] == "resume"
            )
            self.assertTrue(resume_desc["currently_eligible"])
            run_desc = next(
                a for a in view["affordances"] if a["id"] == "run"
            )
            self.assertFalse(run_desc["currently_eligible"])

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / ".agent-loop").mkdir()
            view = agent_loop.build_desktop_action_bridge_view(
                controller,
            )
            self.assertIsNone(
                view["current_loop_state_status"],
            )
            # attach + inspect remain operator-decision; run +
            # resume refuse fail-closed.
            statuses = {
                a["id"]: a["currently_eligible"]
                for a in view["affordances"]
            }
            self.assertTrue(statuses["attach"])
            self.assertTrue(statuses["inspect"])
            self.assertFalse(statuses["run"])
            self.assertFalse(statuses["resume"])


# ---------------------------------------------------------------------------
# render_desktop_action_bridge_text
# ---------------------------------------------------------------------------
class RenderActionBridgeTextTests(unittest.TestCase):

    def test_render_includes_signal_version_and_all_affordances(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_action_bridge_view(
                controller,
            )
            lines = (
                agent_loop.render_desktop_action_bridge_text(view)
            )
            output = "\n".join(lines)
            self.assertIn(
                "signal_version='phase-10n-v1'", output,
            )
            for action_id in (
                "attach", "inspect", "run", "resume",
            ):
                self.assertIn(f"id={action_id!r}", output)

    def test_render_tags_ineligible_affordances(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_action_bridge_view(
                controller,
            )
            lines = (
                agent_loop.render_desktop_action_bridge_text(view)
            )
            output = "\n".join(lines)
            self.assertIn("[ineligible] id='resume'", output)
            self.assertIn("[affordance] id='run'", output)

    def test_render_includes_attribution_tags(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.build_desktop_action_bridge_view(
                controller,
            )
            lines = (
                agent_loop.render_desktop_action_bridge_text(view)
            )
            output = "\n".join(lines)
            self.assertIn("[canonical mirror]", output)
            self.assertIn("[advisory]", output)
            self.assertIn("audit_note:", output)


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopActionsTests(unittest.TestCase):

    def _run(
        self,
        controller_root_arg,
    ) -> tuple:
        args = argparse.Namespace(
            cmd="view-desktop-actions",
            controller_root=controller_root_arg,
        )
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = agent_loop.cmd_view_desktop_actions(args)
        return rc, out.getvalue(), err.getvalue()

    def test_handler_wired(self) -> None:
        self.assertIn(
            "view-desktop-actions", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["view-desktop-actions"],
            agent_loop.cmd_view_desktop_actions,
        )

    def test_argparse_grammar(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-actions",
            "--controller-root", "/tmp/c",
        ])
        self.assertEqual(args.cmd, "view-desktop-actions")
        self.assertEqual(args.controller_root, "/tmp/c")

    def test_exits_zero_with_rendered_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            rc, out, err = self._run(str(controller))
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")
            self.assertIn("signal_version='phase-10n-v1'", out)

    def test_omitted_controller_root_refuses_explicitly(
        self,
    ) -> None:
        # Phase 10L Controller-Root Selection Flow: --controller-
        # root is REQUIRED. Match the same explicit-refusal pattern
        # the Phase 10M launch-desktop-app handler enforces.
        rc, out, err = self._run(None)
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn(
            "[desktop-action-bridge] REFUSED:", err,
        )
        self.assertIn("--controller-root is required", err)
        for fragment in (
            "Phase 10L",
            "Controller-Root Selection Flow",
            "MUST NOT silently pick a default root",
        ):
            self.assertIn(fragment, err)

    def test_omitted_controller_root_does_not_call_find_repo_root(
        self,
    ) -> None:
        calls = []

        def _record(*args, **kwargs):
            calls.append((args, kwargs))
            return Path(".")

        args = argparse.Namespace(
            cmd="view-desktop-actions", controller_root=None,
        )
        with mock.patch.object(
            agent_loop, "find_repo_root", _record,
        ):
            with redirect_stdout(io.StringIO()):
                with redirect_stderr(io.StringIO()):
                    rc = agent_loop.cmd_view_desktop_actions(args)
        self.assertEqual(rc, 2)
        self.assertEqual(
            calls, [],
            "cmd_view_desktop_actions called find_repo_root() "
            "when --controller-root was omitted; Phase 10L "
            "Controller-Root Selection Flow forbids any "
            "auto-discovered fallback",
        )

    def test_missing_controller_root_markers_refuses(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            rc, out, err = self._run(str(controller))
            self.assertEqual(rc, 2)
            self.assertEqual(out, "")
            self.assertIn(
                "[desktop-action-bridge] REFUSED:", err,
            )
            self.assertIn("AGENTS.md", err)
            self.assertIn("CLAUDE.md", err)
            self.assertIn("TASK.md", err)


# ---------------------------------------------------------------------------
# Non-mutation invariants (Phase 10L contract)
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_build_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.build_desktop_action_bridge_view(controller)
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_build_does_not_write_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            self.assertFalse(log_path.exists())
            agent_loop.build_desktop_action_bridge_view(controller)
            self.assertFalse(
                log_path.exists(),
                "build_desktop_action_bridge_view must NOT create "
                "`.agent-loop/orchestrator.log` (Phase 10L "
                "contract)",
            )

    def test_build_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            calls = []

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return -1

            with mock.patch.object(agent_loop, "_halt", _record):
                agent_loop.build_desktop_action_bridge_view(
                    controller,
                )
            self.assertEqual(
                calls, [],
                "build_desktop_action_bridge_view called "
                "_halt(...); Phase 10L contract forbids invoking "
                "_halt from the desktop action bridge path",
            )

    def test_cli_does_not_spawn_subprocess(self) -> None:
        # The Phase 10L contract forbids the desktop shell from
        # silently spawning a mutating subprocess on the operator's
        # behalf. Patch every plausible subprocess entry point and
        # assert zero calls during a render.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-actions",
                controller_root=str(controller),
            )
            spawn_calls = []

            def _record(*args, **kwargs):
                spawn_calls.append((args, kwargs))
                raise RuntimeError(
                    "Phase 10L contract violation: action bridge "
                    "must NOT spawn a subprocess"
                )

            patches = [
                mock.patch(
                    "subprocess.Popen", side_effect=_record,
                ),
                mock.patch(
                    "subprocess.run", side_effect=_record,
                ),
                mock.patch(
                    "subprocess.call", side_effect=_record,
                ),
                mock.patch(
                    "subprocess.check_call", side_effect=_record,
                ),
                mock.patch(
                    "subprocess.check_output", side_effect=_record,
                ),
                mock.patch("os.system", side_effect=_record),
            ]
            for p in patches:
                p.start()
            try:
                with redirect_stdout(io.StringIO()):
                    rc = agent_loop.cmd_view_desktop_actions(args)
            finally:
                for p in patches:
                    p.stop()
            self.assertEqual(rc, 0)
            self.assertEqual(
                spawn_calls, [],
                "cmd_view_desktop_actions spawned a subprocess; "
                "Phase 10L contract forbids silent CLI dispatch",
            )

    def test_does_not_widen_phase_10i_library_callable_cap(
        self,
    ) -> None:
        # Anchor the Phase 10I three-control cap exactly.
        library_call_ids = {
            spec["id"]
            for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if spec["dispatch_mode"] == "library_call"
        }
        self.assertEqual(
            library_call_ids,
            {
                "view-external-status",
                "view-external-controls",
                "inspect-external-target",
            },
            "Phase 10N MUST NOT widen the Phase 10I library-"
            "callable control surface beyond the three shipped "
            "controls",
        )

    def test_cli_does_not_mutate_controller_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            before_state = state_path.read_text(encoding="utf-8")
            log_exists_before = log_path.exists()
            args = argparse.Namespace(
                cmd="view-desktop-actions",
                controller_root=str(controller),
            )
            with redirect_stdout(io.StringIO()):
                agent_loop.cmd_view_desktop_actions(args)
            self.assertEqual(
                before_state,
                state_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                log_exists_before, log_path.exists(),
            )


if __name__ == "__main__":
    unittest.main()
