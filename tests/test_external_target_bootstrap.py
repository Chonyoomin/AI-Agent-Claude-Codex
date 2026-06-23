"""Phase 10E - External Workspace Bootstrap Runtime Initial Slice tests.

Exercises `bootstrap_external_target(...)`, the `--bootstrap` opt-in
path through `attach_external_target(...)`, and the new
`halted_external_target_bootstrap_*` halt-status family.

The tests prove:
  - the bootstrap runtime writes exactly the five canonical
    target-side artifacts under the Phase 10C contract
    (`TASK.md`, `.agent-loop/current-task.md`,
    `.agent-loop/current-phase.md`, `.agent-loop/phase-plan.md`,
    `.agent-loop/loop-state.json`) with the pinned initial contents
    and never touches any other path
  - the target's `loop-state.json` carries
    `status = "awaiting_first_activation"`, `phase = null`,
    `sub_phase = null`, `task = null`, `cycle_count = 0`,
    `max_cycles = 3`, `contract_version` =
    controller_contract_version, `orchestrator_version` =
    running ORCHESTRATOR_VERSION, `approval_mode` =
    operator-supplied attach approval_mode, all other fields = null
  - the attach record's `bootstrap_state` sub-object carries
    `status = "target_canonical_set_bootstrapped"`,
    `bootstrap_signal_version = "phase-10c-v1"`,
    `pre_bootstrap_target_state = "empty_target"`, the sorted list
    of five artifacts_written paths, `initial_loop_state_status =
    "awaiting_first_activation"`, the human-objective excerpt
    (capped at 200 chars), and the `bootstrap_log_line` byte-for-byte
    matched to the line written to `.agent-loop/orchestrator.log`
  - bootstrap refuses fail-closed on every Phase 10C-listed refusal
    case (missing / empty / over-bounded `bootstrapped_by` /
    `human_objective` / `project_intent`,
    `bootstrapped_by != attached_by`,
    `pre_bootstrap_state != empty_target`, atomicity failure with
    rollback)
  - bootstrap NEVER overwrites an existing canonical artifact on
    `partial_target` / `malformed_target` / `full_target`, even on
    operator opt-in
  - attach `--bootstrap` flag dispatches the bootstrap branch only
    when the pre-bootstrap target state is `empty_target`; passing
    `--bootstrap` against `full_target` is a no-op (attach proceeds
    on the no-bootstrap path)
  - attach without `--bootstrap` against `empty_target` refuses
    fail-closed with a forward-pointer to the bootstrap flag
  - bootstrap NEVER activates a target-side phase; the bootstrapped
    target sits at `awaiting_first_activation` until the shipped
    Phase 4C activator runs against it
  - the CLI surface accepts the new `--bootstrap`,
    `--bootstrapped-by`, `--human-objective`, `--project-intent`
    arguments alongside the shipped Phase 10D arguments
"""
from __future__ import annotations

import json
import os
import sys
import unittest
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
                "Phase 10E - External Workspace Bootstrap "
                "Runtime Initial Slice"
            ),
            "task": "phase-10e-test",
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


# ---------------------------------------------------------------------------
# Constants + halt-status registration
# ---------------------------------------------------------------------------
class BootstrapConstantsTests(unittest.TestCase):

    def test_awaiting_first_activation_status(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_BOOTSTRAP_AWAITING_FIRST_ACTIVATION_STATUS,
            "awaiting_first_activation",
        )

    def test_human_objective_excerpt_max_length(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_BOOTSTRAP_HUMAN_OBJECTIVE_EXCERPT_MAX_LENGTH,
            200,
        )

    def test_halt_status_constants(self) -> None:
        self.assertEqual(
            agent_loop.HALTED_EXTERNAL_TARGET_BOOTSTRAP_INPUT_MISSING,
            "halted_external_target_bootstrap_input_missing",
        )
        self.assertEqual(
            agent_loop.HALTED_EXTERNAL_TARGET_BOOTSTRAP_ATOMICITY_FAILURE,
            "halted_external_target_bootstrap_atomicity_failure",
        )

    def test_halt_status_frozenset(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_BOOTSTRAP_HALT_STATUSES,
            frozenset({
                "halted_external_target_bootstrap_input_missing",
                "halted_external_target_bootstrap_atomicity_failure",
            }),
        )

    def test_initial_max_cycles_matches_phase3a_default(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_BOOTSTRAP_INITIAL_MAX_CYCLES, 3,
        )


# ---------------------------------------------------------------------------
# bootstrap_external_target - success path (library function)
# ---------------------------------------------------------------------------
class BootstrapSuccessTests(unittest.TestCase):

    def _bootstrap(self, target_root: Path, **overrides):
        defaults = dict(
            bootstrapped_by="alice",
            attached_by="alice",
            approval_mode="review",
            human_objective="Build the thing.",
            project_intent="Reach the thing.",
            controller_contract_version=CONTRACT_VERSION,
            controller_orchestrator_version=(
                agent_loop.ORCHESTRATOR_VERSION
            ),
        )
        defaults.update(overrides)
        return agent_loop.bootstrap_external_target(
            target_root, **defaults,
        )

    def test_writes_exactly_the_five_canonical_artifacts(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            result = self._bootstrap(target)
            self.assertEqual(
                result["status"], "target_canonical_set_bootstrapped",
            )
            self.assertEqual(
                result["artifacts_written"],
                sorted([
                    "TASK.md",
                    ".agent-loop/current-task.md",
                    ".agent-loop/current-phase.md",
                    ".agent-loop/phase-plan.md",
                    ".agent-loop/loop-state.json",
                ]),
            )
            for rel in result["artifacts_written"]:
                self.assertTrue(
                    (target / rel).exists(),
                    f"bootstrap did not write {rel}",
                )

    def test_initial_loop_state_matches_phase10c_pin(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            self._bootstrap(target, approval_mode="strict")
            loop_state = json.loads(
                (target / ".agent-loop" / "loop-state.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(
                loop_state["status"], "awaiting_first_activation",
            )
            self.assertIsNone(loop_state["phase"])
            self.assertIsNone(loop_state["sub_phase"])
            self.assertIsNone(loop_state["task"])
            self.assertEqual(loop_state["cycle_count"], 0)
            self.assertEqual(loop_state["max_cycles"], 3)
            self.assertIsNone(loop_state["last_verdict"])
            self.assertIsNone(loop_state["last_verdict_phase"])
            self.assertEqual(
                loop_state["contract_version"], CONTRACT_VERSION,
            )
            self.assertEqual(
                loop_state["orchestrator_version"],
                agent_loop.ORCHESTRATOR_VERSION,
            )
            self.assertEqual(loop_state["approval_mode"], "strict")
            self.assertIsNone(loop_state["claude_version"])
            self.assertIsNone(loop_state["codex_version"])
            self.assertIsNone(loop_state["awaiting_human_for"])

    def test_task_md_carries_operator_supplied_objective_and_intent(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            self._bootstrap(
                target,
                human_objective="Compose the symphony.",
                project_intent="Concert by autumn.",
            )
            body = (target / "TASK.md").read_text(encoding="utf-8")
            self.assertIn("## Human Objective", body)
            self.assertIn("Compose the symphony.", body)
            self.assertIn("## Project Intent", body)
            self.assertIn("Concert by autumn.", body)
            # Every other section MUST carry the explicit
            # `(to be set by first Phase 4C activation)` placeholder.
            for header in (
                "## Active Phase",
                "## Active Sub-Phase",
                "## Phase Status",
                "## Active Task",
                "## Phase Outcome Required Now",
                "## Next-Phase Gate",
                "## Out Of Scope For Current Phase",
            ):
                self.assertIn(header, body)
            self.assertIn(
                "(to be set by first Phase 4C activation)", body,
            )

    def test_bootstrap_state_payload_carries_phase10c_fields(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            result = self._bootstrap(
                target,
                human_objective="A" * 250,
            )
            self.assertEqual(
                result["bootstrap_signal_version"], "phase-10c-v1",
            )
            self.assertEqual(
                result["pre_bootstrap_target_state"], "empty_target",
            )
            self.assertEqual(
                result["initial_loop_state_status"],
                "awaiting_first_activation",
            )
            # Excerpt capped at 200 chars per the Phase 10C contract.
            self.assertEqual(
                len(result["initial_human_objective_excerpt"]), 200,
            )
            self.assertEqual(
                result["initial_human_objective_excerpt"], "A" * 200,
            )
            self.assertIn(
                "external target: bootstrapped",
                result["bootstrap_log_line"],
            )
            self.assertIn(
                "phase-10c-v1", result["bootstrap_log_line"],
            )

    def test_creates_agent_loop_directory_when_absent(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            self.assertFalse((target / ".agent-loop").exists())
            self._bootstrap(target)
            self.assertTrue((target / ".agent-loop").is_dir())

    def test_does_not_write_outside_canonical_set(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            self._bootstrap(target)
            # Bootstrap MUST NOT write any of these protected paths.
            forbidden = (
                ".agent-loop/orchestrator.log",
                ".agent-loop/claude-prompt.md",
                ".agent-loop/claude-summary.md",
                ".agent-loop/codex-review.md",
                ".agent-loop/fix-prompt.md",
                ".agent-loop/external-target.json",
                ".agent-loop/memory",
                "AGENTS.md",
                "CLAUDE.md",
                "ROADMAP.md",
                "README.md",
                ".gitignore",
            )
            for rel in forbidden:
                self.assertFalse(
                    (target / rel).exists(),
                    f"bootstrap unexpectedly wrote {rel}",
                )


# ---------------------------------------------------------------------------
# bootstrap_external_target - refusal paths (library function)
# ---------------------------------------------------------------------------
class BootstrapRefusalTests(unittest.TestCase):

    def _bootstrap(self, target_root: Path, **overrides):
        defaults = dict(
            bootstrapped_by="alice",
            attached_by="alice",
            approval_mode="review",
            human_objective="Build.",
            project_intent="Intent.",
            controller_contract_version=CONTRACT_VERSION,
            controller_orchestrator_version=(
                agent_loop.ORCHESTRATOR_VERSION
            ),
        )
        defaults.update(overrides)
        return agent_loop.bootstrap_external_target(
            target_root, **defaults,
        )

    def test_refuses_missing_bootstrapped_by(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            with self.assertRaises(HaltError) as ctx:
                self._bootstrap(target, bootstrapped_by=None)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_empty_bootstrapped_by(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            with self.assertRaises(HaltError):
                self._bootstrap(target, bootstrapped_by="   ")

    def test_refuses_over_bounded_bootstrapped_by(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            with self.assertRaises(HaltError):
                self._bootstrap(target, bootstrapped_by="x" * 201)

    def test_refuses_identity_mismatch(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            with self.assertRaises(HaltError) as ctx:
                self._bootstrap(
                    target,
                    bootstrapped_by="alice",
                    attached_by="bob",
                )
            self.assertEqual(
                ctx.exception.status,
                "halted_external_target_bootstrap_input_missing",
            )
            self.assertIn(
                "does not match", ctx.exception.reason,
            )

    def test_refuses_missing_human_objective(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            with self.assertRaises(HaltError) as ctx:
                self._bootstrap(target, human_objective=None)
            self.assertEqual(
                ctx.exception.status,
                "halted_external_target_bootstrap_input_missing",
            )
            self.assertIn(
                "human_objective", ctx.exception.reason,
            )

    def test_refuses_empty_human_objective(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            with self.assertRaises(HaltError):
                self._bootstrap(target, human_objective="   ")

    def test_refuses_missing_project_intent(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            with self.assertRaises(HaltError) as ctx:
                self._bootstrap(target, project_intent=None)
            self.assertIn(
                "project_intent", ctx.exception.reason,
            )

    def test_refuses_invalid_approval_mode(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            with self.assertRaises(HaltError):
                self._bootstrap(target, approval_mode="bogus_mode")

    def test_refuses_when_pre_state_is_partial(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            # Plant one canonical artifact -> partial_target.
            (target / "TASK.md").write_text(
                "partial", encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                self._bootstrap(target)
            self.assertEqual(
                ctx.exception.status,
                "halted_external_target_bootstrap_input_missing",
            )
            self.assertIn(
                "partial_target", ctx.exception.reason,
            )
            # Bootstrap-never-overwrites: the pre-existing artifact
            # MUST remain.
            self.assertEqual(
                (target / "TASK.md").read_text(encoding="utf-8"),
                "partial",
            )

    def test_refuses_when_pre_state_is_full(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            _write_full_target(target)
            with self.assertRaises(HaltError) as ctx:
                self._bootstrap(target)
            self.assertIn(
                "full_target", ctx.exception.reason,
            )

    def test_refuses_when_pre_state_is_malformed(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            _write_full_target(target)
            (target / ".agent-loop" / "loop-state.json").write_text(
                "not valid json", encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                self._bootstrap(target)
            self.assertIn(
                "malformed_target", ctx.exception.reason,
            )

    def test_rolls_back_on_atomic_write_failure(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()

            real_replace = os.replace
            call_state = {"count": 0}

            def flaky_replace(src, dst):
                call_state["count"] += 1
                # Fail on the third os.replace call so two artifacts
                # have already landed on disk before the failure.
                if call_state["count"] == 3:
                    raise OSError("simulated rename failure")
                return real_replace(src, dst)

            with mock.patch.object(
                agent_loop.os, "replace", side_effect=flaky_replace,
            ):
                with self.assertRaises(HaltError) as ctx:
                    self._bootstrap(target)
            self.assertEqual(
                ctx.exception.status,
                "halted_external_target_bootstrap_atomicity_failure",
            )
            # Rollback: none of the five canonical artifacts may
            # remain on disk after the failure.
            for rel in (
                "TASK.md",
                ".agent-loop/current-task.md",
                ".agent-loop/current-phase.md",
                ".agent-loop/phase-plan.md",
                ".agent-loop/loop-state.json",
            ):
                self.assertFalse(
                    (target / rel).exists(),
                    f"rollback did not remove {rel}",
                )
            # No leftover .tmp companion files.
            tmp_remainders = list(target.rglob("*.tmp"))
            self.assertEqual(tmp_remainders, [])


# ---------------------------------------------------------------------------
# attach_external_target with --bootstrap opt-in
# ---------------------------------------------------------------------------
class AttachBootstrapIntegrationTests(unittest.TestCase):

    def _attach(self, controller, target, log_path=None, **overrides):
        defaults = dict(
            target_path=str(target),
            attached_by="alice",
            approval_mode="review",
            log_path=log_path,
        )
        defaults.update(overrides)
        return agent_loop.attach_external_target(
            controller, **defaults,
        )

    def test_attach_with_bootstrap_dispatches_bootstrap_runtime(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            log_path = controller / ".agent-loop" / "orchestrator.log"
            self._attach(
                controller, target, log_path=log_path,
                bootstrap=True,
                bootstrapped_by="alice",
                human_objective="Goal.",
                project_intent="Intent.",
            )
            attach_record = controller / ATTACH_RECORD_REL
            payload = json.loads(
                attach_record.read_text(encoding="utf-8"),
            )
            bs = payload["bootstrap_state"]
            self.assertEqual(
                bs["status"], "target_canonical_set_bootstrapped",
            )
            self.assertEqual(
                bs["bootstrap_signal_version"], "phase-10c-v1",
            )
            self.assertEqual(
                bs["pre_bootstrap_target_state"], "empty_target",
            )
            self.assertEqual(
                bs["initial_loop_state_status"],
                "awaiting_first_activation",
            )
            self.assertEqual(bs["bootstrapped_by"], "alice")
            self.assertIsNotNone(bs["bootstrapped_at"])
            self.assertEqual(
                bs["artifacts_written"],
                sorted([
                    "TASK.md",
                    ".agent-loop/current-task.md",
                    ".agent-loop/current-phase.md",
                    ".agent-loop/phase-plan.md",
                    ".agent-loop/loop-state.json",
                ]),
            )
            # Both audit lines land in the log; the
            # `bootstrap_log_line` matches the log byte-for-byte.
            log_contents = log_path.read_text(encoding="utf-8")
            self.assertIn(
                bs["bootstrap_log_line"], log_contents,
            )
            self.assertIn(
                "external target: bootstrapped", log_contents,
            )
            self.assertIn(
                "external target: attached", log_contents,
            )

    def test_target_loop_state_at_awaiting_first_activation(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            self._attach(
                controller, target,
                bootstrap=True,
                bootstrapped_by="alice",
                human_objective="Goal.",
                project_intent="Intent.",
                approval_mode="autonomous",
            )
            target_loop_state = json.loads(
                (target / ".agent-loop" / "loop-state.json")
                .read_text(encoding="utf-8")
            )
            self.assertEqual(
                target_loop_state["status"],
                "awaiting_first_activation",
            )
            self.assertEqual(
                target_loop_state["approval_mode"], "autonomous",
            )

    def test_bootstrap_does_not_mutate_controller_loop_state(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            controller_state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = controller_state_path.read_text(encoding="utf-8")
            self._attach(
                controller, target,
                bootstrap=True,
                bootstrapped_by="alice",
                human_objective="Goal.",
                project_intent="Intent.",
            )
            after = controller_state_path.read_text(encoding="utf-8")
            self.assertEqual(
                before, after,
                "bootstrap+attach must NEVER mutate the controller's "
                "loop-state",
            )

    def test_bootstrap_on_full_target_is_a_noop(self) -> None:
        # The Phase 10C contract: a --bootstrap flag against a
        # `full_target` is honored as a no-op (attach proceeds on
        # the no-bootstrap path).
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            self._attach(
                controller, target,
                bootstrap=True,
                bootstrapped_by="alice",
                human_objective="ignored",
                project_intent="ignored",
            )
            attach_record = controller / ATTACH_RECORD_REL
            payload = json.loads(
                attach_record.read_text(encoding="utf-8"),
            )
            bs = payload["bootstrap_state"]
            self.assertEqual(
                bs["status"], "target_canonical_set_present",
            )
            self.assertIsNone(bs["bootstrapped_at"])
            self.assertIsNone(bs["bootstrapped_by"])
            self.assertIsNone(bs["bootstrap_signal_version"])

    def test_bootstrap_on_partial_target_refuses_without_overwrite(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            (target / "TASK.md").write_text(
                "preexisting", encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                self._attach(
                    controller, target,
                    bootstrap=True,
                    bootstrapped_by="alice",
                    human_objective="Goal.",
                    project_intent="Intent.",
                )
            self.assertIn(
                "partial_target", ctx.exception.reason,
            )
            self.assertFalse(
                (controller / ATTACH_RECORD_REL).exists(),
                "attach record MUST NOT be written on refused "
                "bootstrap",
            )
            # The pre-existing artifact MUST remain unchanged.
            self.assertEqual(
                (target / "TASK.md").read_text(encoding="utf-8"),
                "preexisting",
            )

    def test_bootstrap_on_malformed_target_refuses(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            (target / ".agent-loop" / "loop-state.json").write_text(
                "broken", encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                self._attach(
                    controller, target,
                    bootstrap=True,
                    bootstrapped_by="alice",
                    human_objective="Goal.",
                    project_intent="Intent.",
                )
            self.assertIn(
                "malformed_target", ctx.exception.reason,
            )
            self.assertFalse(
                (controller / ATTACH_RECORD_REL).exists(),
            )

    def test_attach_without_bootstrap_against_empty_refuses(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target)
            self.assertIn("empty_target", ctx.exception.reason)
            self.assertIn("--bootstrap", ctx.exception.reason)

    def test_bootstrap_with_identity_mismatch_refuses(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            with self.assertRaises(HaltError) as ctx:
                self._attach(
                    controller, target,
                    attached_by="alice",
                    bootstrap=True,
                    bootstrapped_by="bob",
                    human_objective="Goal.",
                    project_intent="Intent.",
                )
            self.assertEqual(
                ctx.exception.status,
                "halted_external_target_bootstrap_input_missing",
            )
            self.assertFalse(
                (controller / ATTACH_RECORD_REL).exists(),
            )

    def test_bootstrap_failure_leaves_no_attach_record(self) -> None:
        # If the bootstrap runtime refuses, no attach record may be
        # written. The bootstrap call runs BEFORE the attach-record
        # write so a refusal is observable as "no controller-side
        # state changed".
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            with self.assertRaises(HaltError):
                self._attach(
                    controller, target,
                    bootstrap=True,
                    bootstrapped_by="alice",
                    human_objective=None,  # refusal: missing input
                    project_intent="Intent.",
                )
            self.assertFalse(
                (controller / ATTACH_RECORD_REL).exists(),
            )


# ---------------------------------------------------------------------------
# CLI argparse grammar - new bootstrap flags
# ---------------------------------------------------------------------------
class BootstrapCLISurfaceTests(unittest.TestCase):

    def test_argparse_accepts_bootstrap_flags(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "attach-external-target",
            "--target-path", "/tmp/x",
            "--attached-by", "alice",
            "--approval-mode", "review",
            "--bootstrap",
            "--bootstrapped-by", "alice",
            "--human-objective", "Goal.",
            "--project-intent", "Intent.",
        ])
        self.assertEqual(args.cmd, "attach-external-target")
        self.assertTrue(args.bootstrap)
        self.assertEqual(args.bootstrapped_by, "alice")
        self.assertEqual(args.human_objective, "Goal.")
        self.assertEqual(args.project_intent, "Intent.")

    def test_argparse_bootstrap_defaults_off(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "attach-external-target",
            "--target-path", "/tmp/x",
            "--attached-by", "alice",
            "--approval-mode", "review",
        ])
        self.assertFalse(args.bootstrap)
        self.assertIsNone(args.bootstrapped_by)
        self.assertIsNone(args.human_objective)
        self.assertIsNone(args.project_intent)


if __name__ == "__main__":
    unittest.main()
