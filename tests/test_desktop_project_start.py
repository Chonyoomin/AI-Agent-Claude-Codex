"""Phase 10R - Desktop App PRD Intake And Project Start Flow tests.

Exercises:
  - module-level constants (signal version, precedence note,
    dimension id tuple, affordance id tuple)
  - the closed `_DESKTOP_PROJECT_START_AFFORDANCES` registry shape
  - per-affordance eligibility computation against loop-state.status
    AND attach-state AND active-phase-presence
  - canonical-mirror assembly (artifact presence + byte size; the
    Phase 10F target-attach inspector delegate; loop-state.json
    field passthrough)
  - `build_desktop_project_start_view(...)` shape + HaltError
    soft-failure semantics on both validator delegates
  - `render_desktop_project_start_text(...)` attribution
  - `build_desktop_project_start_controls(...)` widget descriptor
    shape
  - `cmd_view_desktop_project_start(...)` CLI handler wiring, the
    Phase-10L-mandated `--controller-root` REQUIRED refusal, the
    missing-controller-root-markers refusal, and the Phase 7C
    always-exit-0-on-report-content rule
  - integration into the shipped Phase 10M
    `assemble_desktop_app_view(...)` /
    `render_desktop_app_text(...)`
  - non-mutation invariants (no orchestrator.log write, no
    loop-state mutation, no `_halt` invocation, no subprocess
    spawn, no Phase 10I cap widening, no network socket open, no
    rewrite of any project-start canonical artifact)
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
    td: Path,
    status: str = "awaiting_claude_implementation",
    approval_mode: str = "review",
    phase: str = "Phase 10 - Future Product Features",
    sub_phase: str = (
        "Phase 10R - Desktop App PRD Intake And Project Start Flow"
    ),
    task: str = "phase-10r-test",
    max_cycles: int = 3,
    cycle_count: int = 1,
) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text(
        "# TASK.md\n## Human Objective\n\ntest task\n",
        encoding="utf-8",
    )
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": phase,
            "sub_phase": sub_phase,
            "task": task,
            "status": status,
            "cycle_count": cycle_count,
            "max_cycles": max_cycles,
            "last_verdict": None,
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
    return td


def _make_empty_loop_state_controller(td: Path) -> Path:
    """Controller with valid markers but loop-state.json missing
    the phase/sub_phase/task triple (e.g. a fresh checkout
    before the first activation). For `has_active_phase=False`
    coverage."""
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("t\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("t\n", encoding="utf-8")
    (td / "TASK.md").write_text("# t\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "",
            "sub_phase": "",
            "task": "",
            "status": "",
            "cycle_count": 0,
            "max_cycles": 0,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": None,
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": "review",
            "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )
    return td


def _write_attach_record(controller: Path) -> None:
    """Minimal Phase 10B-shaped attach record so
    `inspect_external_target_attach(...)` returns
    `attached=True`. The schema validity is irrelevant for the
    Phase 10R surface tests; we only need the `attached` field
    flipped on.
    """
    rec = {
        "attach_record_signal_version": "phase-10b-v1",
        "target_path": str(controller.parent / "target"),
        "approval_mode": "review",
        "attached_by": "tester",
        "attached_at_utc": "2025-01-01T00:00:00Z",
        "mode_selection": {"approval_mode": "review"},
    }
    (
        controller
        / agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL
    ).write_text(
        json.dumps(rec), encoding="utf-8",
    )


def _make_target_with_loop_state(
    td: Path,
    *,
    phase: str = "",
    sub_phase: str = "",
    task: str = "",
    status: str = "",
) -> Path:
    """Build a target project dir containing its own
    `.agent-loop/loop-state.json` so Phase 10R target-side state
    can be exercised."""
    td.mkdir(parents=True, exist_ok=True)
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": phase,
            "sub_phase": sub_phase,
            "task": task,
            "status": status,
            "cycle_count": 0,
            "max_cycles": 0,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": None,
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": "review",
            "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )
    return td


def _write_attach_record_with_target_path(
    controller: Path, target: Path,
) -> None:
    """Write an attach record carrying a parseable
    `target_path_canonical` field so the Phase 10F freshness probe
    yields a usable target path back through the Phase 10R
    project-start view."""
    rec = {
        "attach_record_signal_version": "phase-10b-v1",
        "target_path_canonical": target.resolve().as_posix(),
        "target_path": str(target),
        "approval_mode": "review",
        "attached_by": "tester",
        "attached_at_utc": "2025-01-01T00:00:00Z",
        "mode_selection": {"approval_mode": "review"},
    }
    (
        controller
        / agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL
    ).write_text(
        json.dumps(rec), encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_PROJECT_START_SIGNAL_VERSION,
            "phase-10r-v1",
        )

    def test_precedence_note_mentions_required_invariants(
        self,
    ) -> None:
        note = agent_loop.DESKTOP_PROJECT_START_PRECEDENCE_NOTE
        self.assertIn("Canonical artifacts on disk always win", note)
        self.assertIn("NEVER silently mutates", note)
        self.assertIn("NEVER auto-runs", note)
        self.assertIn("Phase 10I", note)
        self.assertIn("subprocess", note)
        self.assertIn("network socket", note)
        self.assertIn("hidden", note)

    def test_dimension_ids_cover_required_axes(self) -> None:
        ids = set(
            agent_loop.DESKTOP_PROJECT_START_DIMENSION_IDS
        )
        for required in (
            "target_attach", "task_md", "prd_intake",
            "proposed_phase", "claude_prompt", "current_task",
            "current_phase", "loop_state",
        ):
            self.assertIn(required, ids)

    def test_affordance_ids_cover_required_six(self) -> None:
        ids = set(
            agent_loop.DESKTOP_PROJECT_START_AFFORDANCE_IDS
        )
        for required in (
            "attach_or_select_target_project",
            "detach_target_project",
            "intake_prd",
            "bootstrap_prompt",
            "start_first_phase_via_plan_activate",
            "start_run",
        ):
            self.assertIn(required, ids)


# ---------------------------------------------------------------------------
# Affordance registry shape
# ---------------------------------------------------------------------------
class AffordanceRegistryShapeTests(unittest.TestCase):

    def test_registry_matches_id_tuple(self) -> None:
        registered_ids = tuple(
            spec["id"]
            for spec in (
                agent_loop._DESKTOP_PROJECT_START_AFFORDANCES
            )
        )
        self.assertEqual(
            registered_ids,
            agent_loop.DESKTOP_PROJECT_START_AFFORDANCE_IDS,
        )

    def test_every_spec_carries_steps_and_required_fields(
        self,
    ) -> None:
        required = {
            "id", "label", "steps", "dispatch_mode", "category",
            "eligibility_states", "requires_attached",
            "audit_note",
        }
        for spec in (
            agent_loop._DESKTOP_PROJECT_START_AFFORDANCES
        ):
            missing = required - set(spec.keys())
            self.assertEqual(
                missing, set(),
                f"affordance {spec.get('id')!r} missing fields "
                f"{missing!r}",
            )
            steps = spec["steps"]
            self.assertGreaterEqual(len(steps), 1)
            for step in steps:
                self.assertIn(
                    step["type"],
                    agent_loop.DESKTOP_RUN_PROFILE_STEP_TYPES,
                )

    def test_every_affordance_is_mutating_copy_paste(self) -> None:
        # Phase 10R ships ZERO library-callable controls. Every
        # affordance MUST be a copy-paste-only mutating command.
        for spec in (
            agent_loop._DESKTOP_PROJECT_START_AFFORDANCES
        ):
            self.assertEqual(spec["dispatch_mode"], "copy_paste")
            self.assertEqual(spec["category"], "mutating")

    def test_attach_affordance_uses_real_attach_parser_grammar(
        self,
    ) -> None:
        spec = next(
            s for s in (
                agent_loop._DESKTOP_PROJECT_START_AFFORDANCES
            )
            if s["id"] == "attach_or_select_target_project"
        )
        cli_steps = [
            step for step in spec["steps"]
            if step["type"] == "cli"
        ]
        self.assertEqual(len(cli_steps), 1)
        cmd = (
            cli_steps[0]["content"]
            .replace("<PATH>", "/tmp/target")
            .replace("<NAME>", "tester")
            .replace("<MODE>", "review")
        )
        argv = cmd.split()[2:]
        ns = agent_loop.build_parser().parse_args(argv)
        self.assertEqual(ns.cmd, "attach-external-target")
        self.assertEqual(ns.target_path, "/tmp/target")
        self.assertEqual(ns.attached_by, "tester")
        self.assertEqual(ns.approval_mode, "review")

    def test_detach_affordance_uses_real_detach_parser_grammar(
        self,
    ) -> None:
        spec = next(
            s for s in (
                agent_loop._DESKTOP_PROJECT_START_AFFORDANCES
            )
            if s["id"] == "detach_target_project"
        )
        cli_steps = [
            step for step in spec["steps"]
            if step["type"] == "cli"
        ]
        self.assertEqual(len(cli_steps), 1)
        cmd = (
            cli_steps[0]["content"]
            .replace("<NAME>", "tester")
        )
        argv = cmd.split()[2:]
        ns = agent_loop.build_parser().parse_args(argv)
        self.assertEqual(ns.cmd, "detach-external-target")
        self.assertEqual(ns.detached_by, "tester")

    def test_intake_prd_affordance_uses_real_intake_parser_grammar(
        self,
    ) -> None:
        spec = next(
            s for s in (
                agent_loop._DESKTOP_PROJECT_START_AFFORDANCES
            )
            if s["id"] == "intake_prd"
        )
        cli_steps = [
            step for step in spec["steps"]
            if step["type"] == "cli"
        ]
        self.assertEqual(len(cli_steps), 1)
        cmd = (
            cli_steps[0]["content"]
            .replace("<PATH>", "docs/prd.json")
        )
        argv = cmd.split()[2:]
        ns = agent_loop.build_parser().parse_args(argv)
        self.assertEqual(ns.cmd, "intake-prd")
        self.assertEqual(ns.input, "docs/prd.json")

    def test_attach_requires_not_attached_detach_requires_attached(
        self,
    ) -> None:
        specs_by_id = {
            spec["id"]: spec
            for spec in (
                agent_loop._DESKTOP_PROJECT_START_AFFORDANCES
            )
        }
        self.assertEqual(
            specs_by_id["attach_or_select_target_project"][
                "requires_attached"
            ],
            False,
        )
        self.assertEqual(
            specs_by_id["detach_target_project"][
                "requires_attached"
            ],
            True,
        )


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------
class EligibilityTests(unittest.TestCase):

    def _spec(self, affordance_id: str) -> dict:
        return next(
            s for s in (
                agent_loop._DESKTOP_PROJECT_START_AFFORDANCES
            )
            if s["id"] == affordance_id
        )

    def test_attach_eligible_when_not_attached(self) -> None:
        eligible, _ = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("attach_or_select_target_project"),
                status_value="awaiting_claude_implementation",
                attached=False,
                target_has_active_phase=True,
            )
        )
        self.assertTrue(eligible)

    def test_attach_ineligible_when_attached(self) -> None:
        eligible, reason = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("attach_or_select_target_project"),
                status_value="awaiting_claude_implementation",
                attached=True,
                target_has_active_phase=True,
            )
        )
        self.assertFalse(eligible)
        self.assertIn("already attached", reason)

    def test_detach_eligible_when_attached(self) -> None:
        eligible, _ = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("detach_target_project"),
                status_value="awaiting_claude_implementation",
                attached=True,
                target_has_active_phase=True,
            )
        )
        self.assertTrue(eligible)

    def test_detach_ineligible_when_not_attached(self) -> None:
        eligible, reason = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("detach_target_project"),
                status_value="awaiting_claude_implementation",
                attached=False,
                target_has_active_phase=True,
            )
        )
        self.assertFalse(eligible)
        self.assertIn("no external target", reason)

    def test_start_first_phase_ineligible_when_active_phase_present(
        self,
    ) -> None:
        eligible, reason = (
            agent_loop._desktop_project_start_eligibility(
                self._spec(
                    "start_first_phase_via_plan_activate",
                ),
                status_value="awaiting_claude_implementation",
                attached=False,
                target_has_active_phase=True,
            )
        )
        self.assertFalse(eligible)
        self.assertIn("active phase", reason)

    def test_start_first_phase_eligible_when_attached_and_target_fresh(
        self,
    ) -> None:
        eligible, _ = (
            agent_loop._desktop_project_start_eligibility(
                self._spec(
                    "start_first_phase_via_plan_activate",
                ),
                status_value=None,
                attached=True,
                target_has_active_phase=False,
            )
        )
        self.assertTrue(eligible)

    def test_start_first_phase_ineligible_when_no_target_attached(
        self,
    ) -> None:
        eligible, reason = (
            agent_loop._desktop_project_start_eligibility(
                self._spec(
                    "start_first_phase_via_plan_activate",
                ),
                status_value=None,
                attached=False,
                target_has_active_phase=False,
            )
        )
        self.assertFalse(eligible)
        self.assertIn(
            "no external target is currently attached", reason,
        )

    def test_first_phase_ignores_controller_active_phase(
        self,
    ) -> None:
        # Phase 10R fix cycle: the controller being mid-phase (e.g.
        # the controller's own loop-state carrying `Phase 10R`)
        # must NOT lock out a fresh attached target. The
        # `target_has_active_phase` input gates this affordance,
        # not anything controller-side.
        eligible, _ = (
            agent_loop._desktop_project_start_eligibility(
                self._spec(
                    "start_first_phase_via_plan_activate",
                ),
                status_value="awaiting_claude_implementation",
                attached=True,
                target_has_active_phase=False,
            )
        )
        self.assertTrue(eligible)

    def test_attach_ineligible_when_attach_record_refused(
        self,
    ) -> None:
        eligible, reason = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("attach_or_select_target_project"),
                status_value="awaiting_claude_implementation",
                attached=False,
                target_has_active_phase=False,
                attach_record_refused=True,
            )
        )
        self.assertFalse(eligible)
        self.assertIn(
            "unreadable or malformed JSON", reason,
        )

    def test_detach_ineligible_when_attach_record_refused(
        self,
    ) -> None:
        eligible, reason = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("detach_target_project"),
                status_value="awaiting_claude_implementation",
                attached=False,
                target_has_active_phase=False,
                attach_record_refused=True,
            )
        )
        self.assertFalse(eligible)
        self.assertIn(
            "unreadable or malformed JSON", reason,
        )

    def test_start_run_eligible_at_awaiting_claude(self) -> None:
        eligible, _ = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("start_run"),
                status_value="awaiting_claude_implementation",
                attached=False,
                target_has_active_phase=True,
            )
        )
        self.assertTrue(eligible)

    def test_start_run_ineligible_at_other_status(self) -> None:
        eligible, reason = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("start_run"),
                status_value=(
                    "phase_complete_awaiting_human_approval"
                ),
                attached=False,
                target_has_active_phase=True,
            )
        )
        self.assertFalse(eligible)
        self.assertIn("not in", reason)

    def test_intake_prd_always_operator_decision(self) -> None:
        eligible, reason = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("intake_prd"),
                status_value=None,
                attached=False,
                target_has_active_phase=False,
            )
        )
        self.assertTrue(eligible)
        self.assertIn("operator-decision", reason)

    def test_bootstrap_prompt_always_operator_decision(self) -> None:
        eligible, _ = (
            agent_loop._desktop_project_start_eligibility(
                self._spec("bootstrap_prompt"),
                status_value="awaiting_claude_implementation",
                attached=True,
                target_has_active_phase=True,
            )
        )
        self.assertTrue(eligible)


# ---------------------------------------------------------------------------
# Artifact-mirror helper
# ---------------------------------------------------------------------------
class ArtifactMirrorTests(unittest.TestCase):

    def test_present_artifact_reports_byte_size(self) -> None:
        with TemporaryDirectory() as td:
            p = Path(td) / "x.md"
            p.write_text("hello", encoding="utf-8")
            mirror = (
                agent_loop._desktop_project_start_artifact_mirror(
                    p, "x.md",
                )
            )
            self.assertTrue(mirror["present"])
            self.assertEqual(mirror["byte_size"], 5)
            self.assertIsNone(mirror["error"])
            self.assertEqual(mirror["rel"], "x.md")

    def test_absent_artifact_reports_present_false(self) -> None:
        with TemporaryDirectory() as td:
            p = Path(td) / "missing.md"
            mirror = (
                agent_loop._desktop_project_start_artifact_mirror(
                    p, "missing.md",
                )
            )
            self.assertFalse(mirror["present"])
            self.assertIsNone(mirror["byte_size"])
            self.assertIsNone(mirror["error"])


# ---------------------------------------------------------------------------
# build_desktop_project_start_view
# ---------------------------------------------------------------------------
class BuildProjectStartViewTests(unittest.TestCase):

    def test_view_shape(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            self.assertEqual(
                view["view_signal_version"], "phase-10r-v1",
            )
            self.assertEqual(
                view["controller_path_canonical"],
                controller.resolve().as_posix(),
            )
            for key in (
                "current_loop_state_status", "attached",
                "attach_record_refused",
                "has_active_phase",
                "controller_has_active_phase",
                "mirror", "affordances",
                "precedence_note",
            ):
                self.assertIn(key, view)
            self.assertIn(
                "target_loop_state", view["mirror"],
            )

    def test_unattached_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            self.assertFalse(view["attached"])
            attach = next(
                a for a in view["affordances"]
                if a["id"] == "attach_or_select_target_project"
            )
            detach = next(
                a for a in view["affordances"]
                if a["id"] == "detach_target_project"
            )
            self.assertTrue(attach["currently_eligible"])
            self.assertFalse(detach["currently_eligible"])

    def test_attached_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            _write_attach_record(controller)
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            self.assertTrue(view["attached"])
            attach = next(
                a for a in view["affordances"]
                if a["id"] == "attach_or_select_target_project"
            )
            detach = next(
                a for a in view["affordances"]
                if a["id"] == "detach_target_project"
            )
            self.assertFalse(attach["currently_eligible"])
            self.assertTrue(detach["currently_eligible"])

    def test_has_active_phase_true_when_target_loop_state_populated(
        self,
    ) -> None:
        # Phase 10R fix cycle: `has_active_phase` now reflects the
        # ATTACHED target's own loop-state, not the controller's.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            target = _make_target_with_loop_state(
                Path(td) / "target",
                phase="Phase 1 - target",
                sub_phase="Phase 1A - target",
                task="active-task",
                status="awaiting_claude_implementation",
            )
            _write_attach_record_with_target_path(
                controller, target,
            )
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            self.assertTrue(view["has_active_phase"])
            first_phase = next(
                a for a in view["affordances"]
                if a["id"]
                == "start_first_phase_via_plan_activate"
            )
            self.assertFalse(first_phase["currently_eligible"])

    def test_has_active_phase_false_when_target_loop_state_empty(
        self,
    ) -> None:
        # Phase 10R fix cycle: a fresh attached target with no
        # active phase makes the first-phase entry eligible even
        # when the CONTROLLER itself is mid-phase.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            target = _make_target_with_loop_state(
                Path(td) / "target",
            )
            _write_attach_record_with_target_path(
                controller, target,
            )
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            self.assertFalse(view["has_active_phase"])
            self.assertTrue(
                view["controller_has_active_phase"],
                "controller mirror should still reflect the "
                "controller's own active phase",
            )
            first_phase = next(
                a for a in view["affordances"]
                if a["id"]
                == "start_first_phase_via_plan_activate"
            )
            self.assertTrue(first_phase["currently_eligible"])

    def test_first_phase_eligible_with_fresh_target_despite_mid_phase_controller(
        self,
    ) -> None:
        # Phase 10R fix cycle (Codex Issue: active-phase gating
        # bug): the controller being mid-phase (e.g. on Phase 10R
        # itself) must NOT lock out the first-phase affordance
        # when the operator has just attached a fresh target.
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                phase="Phase 10 - Future Product Features",
                sub_phase="Phase 10R - active controller phase",
                task="phase-10r-active",
                status="awaiting_claude_implementation",
            )
            target = _make_target_with_loop_state(
                Path(td) / "target",
            )
            _write_attach_record_with_target_path(
                controller, target,
            )
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            self.assertTrue(view["controller_has_active_phase"])
            self.assertFalse(view["has_active_phase"])
            first_phase = next(
                a for a in view["affordances"]
                if a["id"]
                == "start_first_phase_via_plan_activate"
            )
            self.assertTrue(first_phase["currently_eligible"])

    def test_first_phase_ineligible_when_no_target_attached(
        self,
    ) -> None:
        # Without a target the first-phase entry has no project to
        # activate against; it must surface as ineligible.
        with TemporaryDirectory() as td:
            controller = _make_empty_loop_state_controller(
                Path(td) / "c",
            )
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            self.assertFalse(view["attached"])
            first_phase = next(
                a for a in view["affordances"]
                if a["id"]
                == "start_first_phase_via_plan_activate"
            )
            self.assertFalse(first_phase["currently_eligible"])

    def test_attach_record_refused_when_inspector_halts_with_record_on_disk(
        self,
    ) -> None:
        # Phase 10R fix cycle (Codex Issue: attach-state routing
        # bug): when the attach record file is on disk but the
        # inspector refuses fail-closed, the view must record
        # `attach_record_refused=True` AND BOTH the attach and
        # detach affordances must surface as ineligible (the
        # canonical attach refuses because the record already
        # exists; the canonical detach refuses because the record
        # is unreadable).
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (
                controller
                / agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL
            ).write_text(
                "{not-json-this-is-garbage}",
                encoding="utf-8",
            )
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            self.assertTrue(view["attach_record_refused"])
            attach = next(
                a for a in view["affordances"]
                if a["id"] == "attach_or_select_target_project"
            )
            detach = next(
                a for a in view["affordances"]
                if a["id"] == "detach_target_project"
            )
            self.assertFalse(attach["currently_eligible"])
            self.assertFalse(detach["currently_eligible"])
            self.assertIn(
                "unreadable or malformed JSON",
                attach["eligibility_reason"],
            )
            self.assertIn(
                "unreadable or malformed JSON",
                detach["eligibility_reason"],
            )

    def test_attach_record_refused_false_when_inspector_halts_with_no_record(
        self,
    ) -> None:
        # If the inspector raises HaltError for some other reason
        # (no attach record file on disk), `attach_record_refused`
        # must stay False - the canonical attach is then eligible
        # (no record to refuse) and the operator should not see
        # the malformed-record refusal message.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "inspect_external_target_attach",
                side_effect=agent_loop.HaltError(
                    "halted_input_missing",
                    "synthetic non-record halt",
                ),
            ):
                view = (
                    agent_loop
                    .build_desktop_project_start_view(controller)
                )
            self.assertFalse(view["attach_record_refused"])
            attach = next(
                a for a in view["affordances"]
                if a["id"] == "attach_or_select_target_project"
            )
            self.assertTrue(attach["currently_eligible"])

    def test_target_loop_state_mirror_present_when_attached(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            target = _make_target_with_loop_state(
                Path(td) / "target",
                phase="Phase 1 - target",
                sub_phase="Phase 1A - target",
                task="active-task",
                status="awaiting_codex_review",
            )
            _write_attach_record_with_target_path(
                controller, target,
            )
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            tls = view["mirror"]["target_loop_state"]
            self.assertEqual(
                tls["path"], target.resolve().as_posix(),
            )
            self.assertEqual(
                tls["status"], "awaiting_codex_review",
            )
            self.assertTrue(tls["has_active_phase"])
            self.assertIsNone(tls["error"])

    def test_target_loop_state_mirror_records_error_on_missing_state(
        self,
    ) -> None:
        # Target dir exists but has no `.agent-loop/loop-state.json`
        # -> target-side load_loop_state raises HaltError, the view
        # soft-fails the error into the mirror, and the operator
        # still sees a usable view.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            target = Path(td) / "target"
            target.mkdir()
            _write_attach_record_with_target_path(
                controller, target,
            )
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            tls = view["mirror"]["target_loop_state"]
            self.assertEqual(
                tls["path"], target.resolve().as_posix(),
            )
            self.assertIsNotNone(tls["error"])
            self.assertFalse(tls["has_active_phase"])

    def test_loop_state_halt_soft_fails(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "load_loop_state",
                side_effect=agent_loop.HaltError(
                    "halted_input_missing", "loop-state halt",
                ),
            ):
                view = (
                    agent_loop
                    .build_desktop_project_start_view(controller)
                )
            self.assertIsNone(view["current_loop_state_status"])
            self.assertFalse(view["has_active_phase"])
            self.assertIsNone(
                view["mirror"]["loop_state"]["phase"],
            )

    def test_target_inspector_halt_soft_fails(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "inspect_external_target_attach",
                side_effect=agent_loop.HaltError(
                    "halted_input_missing", "target halt",
                ),
            ):
                view = (
                    agent_loop
                    .build_desktop_project_start_view(controller)
                )
            self.assertFalse(view["attached"])
            self.assertEqual(
                view["mirror"]["target_attach"]["error"],
                "target halt",
            )

    def test_artifact_mirror_byte_sizes_propagate(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            (
                controller / ".agent-loop" / "claude-prompt.md"
            ).write_text("prompt", encoding="utf-8")
            view = (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )
            cp = view["mirror"]["claude_prompt"]
            self.assertTrue(cp["present"])
            self.assertEqual(cp["byte_size"], 6)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
class RenderProjectStartTextTests(unittest.TestCase):

    def _view(self) -> dict:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            return (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )

    def test_header_signal_version(self) -> None:
        lines = agent_loop.render_desktop_project_start_text(
            self._view(),
        )
        self.assertTrue(any(
            "[desktop-project-start] view" in line
            and "phase-10r-v1" in line
            for line in lines
        ))

    def test_renders_canonical_mirror_for_every_artifact(
        self,
    ) -> None:
        text = "\n".join(
            agent_loop.render_desktop_project_start_text(
                self._view(),
            )
        )
        for fragment in (
            "[canonical mirror] target_attach",
            "[refused] attach_record_refused",
            "[canonical mirror] loop_state",
            "[canonical mirror] target_loop_state",
            "[advisory] has_active_phase",
            "[advisory] controller_has_active_phase",
            "[canonical mirror] task_md",
            "[canonical mirror] prd_intake",
            "[canonical mirror] proposed_phase",
            "[canonical mirror] claude_prompt",
            "[canonical mirror] current_task",
            "[canonical mirror] current_phase",
        ):
            self.assertIn(fragment, text)

    def test_renders_typed_steps_with_tags(self) -> None:
        text = "\n".join(
            agent_loop.render_desktop_project_start_text(
                self._view(),
            )
        )
        self.assertIn(
            "1. [cli] python scripts/agent_loop.py plan", text,
        )
        self.assertIn("[manual-edit]", text)
        self.assertIn("intake-prd", text)
        self.assertIn(
            "steps (1 step):", text,
        )
        self.assertIn(
            "steps (3 steps; copy-paste each in order):", text,
        )

    def test_affordance_and_ineligible_tags(self) -> None:
        text = "\n".join(
            agent_loop.render_desktop_project_start_text(
                self._view(),
            )
        )
        self.assertIn("[affordance]", text)
        self.assertIn("[ineligible]", text)

    def test_precedence_note_is_last_line(self) -> None:
        lines = agent_loop.render_desktop_project_start_text(
            self._view(),
        )
        self.assertTrue(
            lines[-1].startswith("precedence_note:"),
        )


# ---------------------------------------------------------------------------
# Controls (Tk widget descriptors)
# ---------------------------------------------------------------------------
class BuildProjectStartControlsTests(unittest.TestCase):

    def _view(self) -> dict:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            return (
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            )

    def test_controls_match_affordance_id_tuple(self) -> None:
        controls = (
            agent_loop.build_desktop_project_start_controls(
                self._view(),
            )
        )
        self.assertEqual(
            tuple(c["id"] for c in controls),
            agent_loop.DESKTOP_PROJECT_START_AFFORDANCE_IDS,
        )

    def test_each_control_carries_required_widget_fields(
        self,
    ) -> None:
        required = {
            "id", "label", "enabled", "eligibility_reason",
            "clipboard_payload", "audit_note", "dispatch_mode",
            "category", "requires_attached",
        }
        for control in (
            agent_loop.build_desktop_project_start_controls(
                self._view(),
            )
        ):
            missing = required - set(control.keys())
            self.assertEqual(missing, set())

    def test_clipboard_payload_per_line_tagged(self) -> None:
        for control in (
            agent_loop.build_desktop_project_start_controls(
                self._view(),
            )
        ):
            for line in (
                control["clipboard_payload"].splitlines()
            ):
                self.assertTrue(
                    line.startswith("[cli]")
                    or line.startswith("[manual-edit]"),
                    f"payload line {line!r} missing step tag",
                )

    def test_enabled_mirrors_currently_eligible(self) -> None:
        view = self._view()
        eligibility_by_id = {
            a["id"]: a["currently_eligible"]
            for a in view["affordances"]
        }
        for control in (
            agent_loop.build_desktop_project_start_controls(view)
        ):
            self.assertEqual(
                control["enabled"],
                bool(eligibility_by_id[control["id"]]),
            )

    def test_empty_input_returns_empty_controls(self) -> None:
        self.assertEqual(
            agent_loop.build_desktop_project_start_controls(
                {"affordances": []},
            ),
            [],
        )
        self.assertEqual(
            agent_loop.build_desktop_project_start_controls({}),
            [],
        )


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdViewDesktopProjectStartTests(unittest.TestCase):

    def test_omitted_controller_root_refuses(self) -> None:
        args = argparse.Namespace(
            cmd="view-desktop-project-start",
            controller_root=None,
        )
        err = io.StringIO()
        with redirect_stderr(err):
            rc = agent_loop.cmd_view_desktop_project_start(args)
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", err.getvalue())
        self.assertIn("--controller-root", err.getvalue())

    def test_invalid_controller_root_refuses_with_markers(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            args = argparse.Namespace(
                cmd="view-desktop-project-start",
                controller_root=str(Path(td)),
            )
            err = io.StringIO()
            with redirect_stderr(err):
                rc = (
                    agent_loop.cmd_view_desktop_project_start(
                        args,
                    )
                )
            self.assertEqual(rc, 2)
            self.assertIn("REFUSED", err.getvalue())
            self.assertIn("AGENTS.md", err.getvalue())

    def test_valid_controller_root_exits_zero_and_prints_view(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-project-start",
                controller_root=str(controller),
            )
            out = io.StringIO()
            with redirect_stdout(out):
                rc = (
                    agent_loop.cmd_view_desktop_project_start(
                        args,
                    )
                )
            self.assertEqual(rc, 0)
            self.assertIn(
                "[desktop-project-start] view", out.getvalue(),
            )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-project-start",
            agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS[
                "view-desktop-project-start"
            ],
            agent_loop.cmd_view_desktop_project_start,
        )

    def test_parser_accepts_subcommand(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-project-start",
            "--controller-root", "/tmp/nope",
        ])
        self.assertEqual(
            args.cmd, "view-desktop-project-start",
        )
        self.assertEqual(args.controller_root, "/tmp/nope")


# ---------------------------------------------------------------------------
# Integration into the Phase 10M desktop app view
# ---------------------------------------------------------------------------
class DesktopAppViewIncludesProjectStartTests(unittest.TestCase):

    def test_assemble_includes_project_start_view_key(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            self.assertIn("project_start_view", view)
            ps = view["project_start_view"]
            self.assertIsInstance(ps, dict)
            self.assertEqual(
                ps["view_signal_version"],
                agent_loop.DESKTOP_PROJECT_START_SIGNAL_VERSION,
            )

    def test_assemble_delegates_to_build_project_start_view(
        self,
    ) -> None:
        sentinel = {
            "view_signal_version": "phase-10r-v1",
            "_sentinel": "project_start",
            "controller_path_canonical": "/tmp/c",
            "current_loop_state_status": None,
            "attached": False,
            "attach_record_refused": False,
            "has_active_phase": False,
            "controller_has_active_phase": False,
            "mirror": {
                "target_attach": {
                    "attached": False, "schema_valid": False,
                    "summary": "", "error": None,
                },
                "loop_state": {
                    "phase": None, "sub_phase": None,
                    "task": None, "status": None,
                    "approval_mode": None,
                    "has_active_phase": False,
                },
                "target_loop_state": {
                    "path": None, "status": None,
                    "has_active_phase": False, "error": None,
                },
                "task_md": {
                    "rel": "TASK.md", "present": False,
                    "byte_size": None, "error": None,
                },
                "prd_intake": {
                    "rel": ".agent-loop/prd-intake.json",
                    "present": False, "byte_size": None,
                    "error": None,
                },
                "proposed_phase": {
                    "rel": ".agent-loop/proposed-phase.md",
                    "present": False, "byte_size": None,
                    "error": None,
                },
                "claude_prompt": {
                    "rel": ".agent-loop/claude-prompt.md",
                    "present": False, "byte_size": None,
                    "error": None,
                },
                "current_task": {
                    "rel": ".agent-loop/current-task.md",
                    "present": False, "byte_size": None,
                    "error": None,
                },
                "current_phase": {
                    "rel": ".agent-loop/current-phase.md",
                    "present": False, "byte_size": None,
                    "error": None,
                },
            },
            "affordances": [],
            "precedence_note": "x",
        }
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop, "build_desktop_project_start_view",
                return_value=sentinel,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIs(view["project_start_view"], sentinel)

    def test_halt_does_not_break_other_sub_views(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")

            def _raise_halt(_root, *args, **kwargs):
                raise agent_loop.HaltError(
                    "halted_input_missing",
                    "project start halt",
                )

            with mock.patch.object(
                agent_loop, "build_desktop_project_start_view",
                side_effect=_raise_halt,
            ):
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
            self.assertIsNone(
                view["project_start_view"]["view"],
            )
            self.assertIn(
                "project start halt",
                view["project_start_view"]["error"],
            )
            for key in (
                "status_view", "controls_view",
                "dashboard_view", "setup_view",
                "run_profiles_view",
            ):
                self.assertIn(
                    "view_signal_version", view[key],
                )

    def test_render_includes_project_start_phase_10r_label(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
            output = "\n".join(lines)
            self.assertIn("Project Start (Phase 10R)", output)
            self.assertIn(
                "[desktop-project-start] view "
                "(signal_version='phase-10r-v1')",
                output,
            )


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_build_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.build_desktop_project_start_view(controller)
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_build_does_not_write_orchestrator_log(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            self.assertFalse(log_path.exists())
            agent_loop.build_desktop_project_start_view(controller)
            self.assertFalse(log_path.exists())

    def test_build_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            calls = []

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return -1

            with mock.patch.object(agent_loop, "_halt", _record):
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            self.assertEqual(calls, [])

    def test_build_does_not_create_project_start_artifacts(
        self,
    ) -> None:
        # No write to runtime-config / external-target /
        # proposed-phase / claude-prompt / current-task /
        # current-phase / TASK.md.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            for rel in (
                ".agent-loop/runtime-config.json",
                agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL,
                agent_loop.PROPOSAL_PATH_REL,
                ".agent-loop/claude-prompt.md",
                ".agent-loop/current-task.md",
                ".agent-loop/current-phase.md",
                ".agent-loop/prd-intake.json",
            ):
                self.assertFalse(
                    (controller / rel).exists(),
                    f"{rel} exists pre-build; test setup leaked",
                )
            before_task = (
                controller / "TASK.md"
            ).read_text(encoding="utf-8")
            agent_loop.build_desktop_project_start_view(controller)
            for rel in (
                ".agent-loop/runtime-config.json",
                agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL,
                agent_loop.PROPOSAL_PATH_REL,
                ".agent-loop/claude-prompt.md",
                ".agent-loop/current-task.md",
                ".agent-loop/current-phase.md",
                ".agent-loop/prd-intake.json",
            ):
                self.assertFalse(
                    (controller / rel).exists(),
                    f"{rel} created by "
                    f"build_desktop_project_start_view",
                )
            after_task = (
                controller / "TASK.md"
            ).read_text(encoding="utf-8")
            self.assertEqual(before_task, after_task)

    def test_cli_does_not_spawn_subprocess(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                cmd="view-desktop-project-start",
                controller_root=str(controller),
            )
            spawn_calls = []

            def _record(*args, **kwargs):
                spawn_calls.append((args, kwargs))
                raise RuntimeError(
                    "Phase 10L contract violation: project "
                    "start surface must NOT spawn a subprocess"
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
                    "subprocess.check_output",
                    side_effect=_record,
                ),
                mock.patch("os.system", side_effect=_record),
            ]
            for p in patches:
                p.start()
            try:
                with redirect_stdout(io.StringIO()):
                    rc = (
                        agent_loop
                        .cmd_view_desktop_project_start(args)
                    )
            finally:
                for p in patches:
                    p.stop()
            self.assertEqual(rc, 0)
            self.assertEqual(spawn_calls, [])

    def test_does_not_widen_phase_10i_library_callable_cap(
        self,
    ) -> None:
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
            "Phase 10R MUST NOT widen the Phase 10I library-"
            "callable control surface beyond the three shipped "
            "controls",
        )

    def test_build_does_not_open_a_network_socket(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            import socket
            calls = []
            real_socket = socket.socket

            def _record(*args, **kwargs):
                calls.append((args, kwargs))
                return real_socket(*args, **kwargs)

            with mock.patch.object(
                socket, "socket", side_effect=_record,
            ):
                agent_loop.build_desktop_project_start_view(
                    controller,
                )
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
