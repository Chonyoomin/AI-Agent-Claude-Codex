"""Phase 10D - External Workspace Attach/Detach Runtime Initial Slice tests.

Exercises `attach_external_target(...)`, `detach_external_target(...)`,
`classify_pre_bootstrap_target_state(...)`, and the
`attach-external-target` / `detach-external-target` CLI subcommands.

The tests prove:
  - the controller-owned attach record at
    `.agent-loop/external-target.json` carries the documented
    Phase 10B schema (`attach_record_signal_version` = "phase-10b-v1",
    `attached_at`, `attached_by`, `target_path_canonical`,
    `target_path_raw`, `controller_path_canonical`,
    `controller_identity` with `repo_signature` / `orchestrator_version`
    / `contract_version`, `mode_selection` with
    `approval_mode` / `selected_at` / `selected_by`, `bootstrap_state`
    with `status` and the Phase 10C extension fields,
    `stale_attach_detection`, `audit` with `attach_log_line` and
    bounded `refusal_history`, and the
    `canonical_precedence_note` literal).
  - the attach runtime refuses fail-closed on every contract-listed
    refusal case (existing attach record, missing / over-bounded
    `attached_by`, unknown `approval_mode`, missing / empty target
    path, controller-self target, controller-nested target, target
    not a directory / not readable / not writable, and every
    pre-bootstrap target state other than `full_target` per the
    Phase 10C bootstrap-never-overwrites guarantee).
  - the pre-bootstrap classifier deterministically returns one of
    the four Phase 10C enumeration values
    (`empty_target` / `partial_target` / `full_target` /
    `malformed_target`) based on canonical-artifact presence and
    `loop-state.json` schema validity only.
  - the detach runtime refuses fail-closed on missing attach record,
    malformed JSON, unrecognized `attach_record_signal_version`,
    controller-mismatch, and missing / empty / over-bounded
    `detached_by`.
  - audit lines land in `.agent-loop/orchestrator.log` with the
    canonical `external target: attached ...` / `external target:
    detached ...` prefix; the attach record's `audit.attach_log_line`
    is byte-matched to the line appended to the log.
  - attach NEVER activates a target-side phase (the controller's
    loop-state is unchanged after attach).
  - the CLI surface is wired through `HANDLERS` and the argparse
    grammar carries the documented `--target-path` / `--attached-by`
    / `--approval-mode` (attach) and `--detached-by` (detach)
    required arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above
from agent_loop import HaltError  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"
ATTACH_RECORD_REL = ".agent-loop/external-target.json"


def _write_full_target(target_root: Path) -> None:
    """Populate the five canonical target-side artifacts the Phase
    10C contract names as the `full_target` set, with structurally
    valid contents the shipped Phase 3A validators accept.
    """
    (target_root / ".agent-loop").mkdir(parents=True, exist_ok=True)
    (target_root / "TASK.md").write_text(
        "# TASK.md\n\nTest target\n", encoding="utf-8",
    )
    (target_root / ".agent-loop" / "current-task.md").write_text(
        "# Current Task\n\nTest target task\n", encoding="utf-8",
    )
    (target_root / ".agent-loop" / "current-phase.md").write_text(
        "# Current Phase\n\nTest target phase\n",
        encoding="utf-8",
    )
    (target_root / ".agent-loop" / "phase-plan.md").write_text(
        "# Phase Plan\n\n## Active Phase\n\nTest\n",
        encoding="utf-8",
    )
    (target_root / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Test Phase",
            "sub_phase": "Test Sub",
            "task": "test task",
            "status": "awaiting_claude_implementation",
            "cycle_count": 0,
            "max_cycles": 3,
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


def _make_valid_attach_record(
    *,
    controller_canonical: str,
    target_canonical: str = "/tmp/some-target",
) -> dict:
    """Phase 10D fix-cycle: build a fully-populated, schema-valid
    Phase 10B attach record. Tests that exercise a SEMANTIC refusal
    (controller-mismatch, signal-version mismatch) use this helper +
    one targeted mutation so the schema-validator passes and the
    targeted refusal fires. Tests that exercise a SCHEMA refusal use
    this helper + drop or wrong-type the specific field under test.
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
            "attach_log_line": (
                "external target: attached signal_version="
                "phase-10b-v1 attached_by='alice' "
                "approval_mode='review' "
                "pre_bootstrap_target_state='full_target' "
                f"target_path_canonical={target_canonical!r} "
                "attach_record_path='.agent-loop/external-target.json'"
            ),
            "refusal_history": [],
        },
        "canonical_precedence_note": (
            "test canonical precedence note"
        ),
    }


def _make_controller(td: Path) -> Path:
    """Create a minimal controller repo root and plant a valid
    loop-state.json so the attach runtime can read the controller's
    contract_version.
    """
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("test\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10D - External Workspace Attach/Detach "
                "Runtime Initial Slice"
            ),
            "task": "phase-10d-test",
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


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ExternalTargetConstantsTests(unittest.TestCase):

    def test_attach_record_rel(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_ATTACH_RECORD_REL,
            ATTACH_RECORD_REL,
        )

    def test_attach_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_ATTACH_SIGNAL_VERSION,
            "phase-10b-v1",
        )

    def test_bootstrap_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_BOOTSTRAP_SIGNAL_VERSION,
            "phase-10c-v1",
        )

    def test_attached_by_max_length(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_ATTACHED_BY_MAX_LENGTH, 200,
        )

    def test_approval_modes_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_APPROVAL_MODES,
            frozenset({
                "review",
                "strict",
                "autonomous",
                "phase_9_autonomous_prd",
            }),
        )

    def test_bootstrap_statuses_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_BOOTSTRAP_STATUSES,
            frozenset({
                "target_canonical_set_present",
                "target_canonical_set_bootstrapped",
            }),
        )

    def test_pre_bootstrap_states_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_PRE_BOOTSTRAP_STATES,
            frozenset({
                "empty_target",
                "partial_target",
                "full_target",
                "malformed_target",
            }),
        )

    def test_canonical_artifact_relpaths(self) -> None:
        self.assertEqual(
            agent_loop.EXTERNAL_TARGET_CANONICAL_ARTIFACT_RELPATHS,
            (
                "TASK.md",
                ".agent-loop/current-task.md",
                ".agent-loop/current-phase.md",
                ".agent-loop/phase-plan.md",
                ".agent-loop/loop-state.json",
            ),
        )

    def test_handlers_wired(self) -> None:
        self.assertIn(
            "attach-external-target", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["attach-external-target"],
            agent_loop.cmd_attach_external_target,
        )
        self.assertIn(
            "detach-external-target", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["detach-external-target"],
            agent_loop.cmd_detach_external_target,
        )


# ---------------------------------------------------------------------------
# classify_pre_bootstrap_target_state
# ---------------------------------------------------------------------------
class ClassifyPreBootstrapTargetStateTests(unittest.TestCase):

    def test_empty_target(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            self.assertEqual(
                agent_loop.classify_pre_bootstrap_target_state(target),
                "empty_target",
            )

    def test_partial_target(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            (target / "TASK.md").write_text("test", encoding="utf-8")
            self.assertEqual(
                agent_loop.classify_pre_bootstrap_target_state(target),
                "partial_target",
            )

    def test_full_target(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            _write_full_target(target)
            self.assertEqual(
                agent_loop.classify_pre_bootstrap_target_state(target),
                "full_target",
            )

    def test_malformed_target_unparseable_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            _write_full_target(target)
            # Overwrite loop-state.json with garbage so the structural
            # validator rejects it.
            (target / ".agent-loop" / "loop-state.json").write_text(
                "not valid json", encoding="utf-8",
            )
            self.assertEqual(
                agent_loop.classify_pre_bootstrap_target_state(target),
                "malformed_target",
            )

    def test_malformed_target_missing_required_field(self) -> None:
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            _write_full_target(target)
            # Loop-state without a required field; the shipped
            # validate_loop_state will refuse.
            (target / ".agent-loop" / "loop-state.json").write_text(
                json.dumps({"phase": "x"}), encoding="utf-8",
            )
            self.assertEqual(
                agent_loop.classify_pre_bootstrap_target_state(target),
                "malformed_target",
            )


# ---------------------------------------------------------------------------
# attach_external_target - success path
# ---------------------------------------------------------------------------
class AttachExternalTargetSuccessTests(unittest.TestCase):

    def test_attach_writes_record_with_required_schema(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            log_path = controller / ".agent-loop" / "orchestrator.log"
            written = agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="review",
                log_path=log_path,
            )
            self.assertEqual(
                written.relative_to(controller).as_posix(),
                ATTACH_RECORD_REL,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            # Required Phase 10B top-level fields
            for field in (
                "attach_record_signal_version",
                "attached_at",
                "attached_by",
                "target_path_canonical",
                "target_path_raw",
                "controller_path_canonical",
                "controller_identity",
                "mode_selection",
                "bootstrap_state",
                "stale_attach_detection",
                "audit",
                "canonical_precedence_note",
            ):
                self.assertIn(field, payload)
            self.assertEqual(
                payload["attach_record_signal_version"],
                "phase-10b-v1",
            )
            self.assertEqual(payload["attached_by"], "alice")
            self.assertEqual(
                payload["target_path_canonical"],
                target.resolve().as_posix(),
            )
            self.assertEqual(payload["target_path_raw"], str(target))
            self.assertEqual(
                payload["controller_path_canonical"],
                controller.resolve().as_posix(),
            )
            # controller_identity sub-fields
            ci = payload["controller_identity"]
            self.assertEqual(
                ci["orchestrator_version"],
                agent_loop.ORCHESTRATOR_VERSION,
            )
            self.assertEqual(
                ci["contract_version"], CONTRACT_VERSION,
            )
            self.assertEqual(
                ci["repo_signature"],
                agent_loop._compute_external_target_repo_signature(
                    controller.resolve(),
                ),
            )
            # mode_selection sub-fields
            ms = payload["mode_selection"]
            self.assertEqual(ms["approval_mode"], "review")
            self.assertEqual(ms["selected_by"], "alice")
            self.assertEqual(ms["selected_at"], payload["attached_at"])
            # bootstrap_state sub-fields (no-bootstrap path)
            bs = payload["bootstrap_state"]
            self.assertEqual(
                bs["status"], "target_canonical_set_present",
            )
            self.assertIsNone(bs["bootstrapped_at"])
            self.assertIsNone(bs["bootstrapped_by"])
            self.assertIsNone(bs["bootstrap_signal_version"])
            self.assertEqual(
                bs["pre_bootstrap_target_state"], "full_target",
            )
            self.assertIsNone(bs["artifacts_written"])
            self.assertIsNone(bs["initial_loop_state_status"])
            self.assertIsNone(
                bs["initial_human_objective_excerpt"],
            )
            self.assertIsNone(bs["bootstrap_log_line"])
            # stale_attach_detection sub-fields
            sad = payload["stale_attach_detection"]
            self.assertEqual(
                sad["target_marker_files_at_attach"],
                list(
                    agent_loop.EXTERNAL_TARGET_CANONICAL_ARTIFACT_RELPATHS,
                ),
            )
            self.assertEqual(
                sad["target_path_canonical_at_attach"],
                target.resolve().as_posix(),
            )
            self.assertEqual(
                sad["controller_path_canonical_at_attach"],
                controller.resolve().as_posix(),
            )
            # audit sub-fields
            self.assertEqual(payload["audit"]["refusal_history"], [])
            self.assertIn(
                "external target: attached",
                payload["audit"]["attach_log_line"],
            )
            self.assertEqual(
                payload["canonical_precedence_note"],
                agent_loop.EXTERNAL_TARGET_CANONICAL_PRECEDENCE_NOTE,
            )

    def test_attach_log_line_byte_matches_audit_log(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            log_path = controller / ".agent-loop" / "orchestrator.log"
            written = agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="strict",
                log_path=log_path,
            )
            payload = json.loads(written.read_text(encoding="utf-8"))
            log_contents = log_path.read_text(encoding="utf-8")
            # The record's attach_log_line MUST appear byte-for-byte
            # in the audit log (the contract guarantees the two
            # sources agree).
            self.assertIn(
                payload["audit"]["attach_log_line"], log_contents,
            )
            # Must include the canonical prefix.
            self.assertIn(
                "external target: attached", log_contents,
            )
            # Must include the signal-version + approval-mode for
            # operator-facing reproducibility.
            self.assertIn("phase-10b-v1", log_contents)
            self.assertIn("'strict'", log_contents)

    def test_attach_does_not_mutate_controller_loop_state(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            state_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = state_path.read_text(encoding="utf-8")
            agent_loop.attach_external_target(
                controller,
                target_path=str(target),
                attached_by="alice",
                approval_mode="autonomous",
            )
            after = state_path.read_text(encoding="utf-8")
            self.assertEqual(
                before, after,
                "Phase 10D attach must NEVER mutate the controller's "
                "loop-state; activation goes through the shipped "
                "Phase 4C activator + APPROVED_FOR_ACTIVATION token",
            )

    def test_attach_atomic_write_leaves_no_tmp_file(self) -> None:
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
            # The atomic write uses temp + rename; no .tmp file
            # should remain on disk.
            al = controller / ".agent-loop"
            tmp_files = list(al.glob("external-target.json.tmp"))
            self.assertEqual(tmp_files, [])


# ---------------------------------------------------------------------------
# attach_external_target - refusal paths
# ---------------------------------------------------------------------------
class AttachExternalTargetRefusalTests(unittest.TestCase):

    def _attach(
        self, controller, **overrides,
    ):
        defaults = dict(
            target_path=str(controller.parent / "target"),
            attached_by="alice",
            approval_mode="review",
        )
        defaults.update(overrides)
        return agent_loop.attach_external_target(
            controller, **defaults,
        )

    def test_refuses_when_attach_record_already_exists(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            self._attach(controller, target_path=str(target))
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target_path=str(target))
            self.assertEqual(ctx.exception.status, "halted_input_missing")
            self.assertIn("already exists", ctx.exception.reason)

    def test_refuses_missing_attached_by(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            with self.assertRaises(HaltError) as ctx:
                self._attach(
                    controller,
                    target_path=str(target),
                    attached_by=None,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_refuses_empty_attached_by(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            with self.assertRaises(HaltError):
                self._attach(
                    controller,
                    target_path=str(target),
                    attached_by="   ",
                )

    def test_refuses_over_bounded_attached_by(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            with self.assertRaises(HaltError):
                self._attach(
                    controller,
                    target_path=str(target),
                    attached_by="x" * 201,
                )

    def test_refuses_unknown_approval_mode(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            with self.assertRaises(HaltError) as ctx:
                self._attach(
                    controller,
                    target_path=str(target),
                    approval_mode="bogus_mode",
                )
            self.assertIn(
                "EXTERNAL_TARGET_APPROVAL_MODES",
                ctx.exception.reason,
            )

    def test_refuses_target_path_same_as_controller(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            with self.assertRaises(HaltError) as ctx:
                self._attach(
                    controller,
                    target_path=str(controller),
                )
            self.assertIn("same as the controller", ctx.exception.reason)

    def test_refuses_target_path_nested_in_controller(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            nested = controller / "nested-target"
            nested.mkdir()
            with self.assertRaises(HaltError) as ctx:
                self._attach(
                    controller,
                    target_path=str(nested),
                )
            self.assertIn("nested inside", ctx.exception.reason)

    def test_refuses_target_path_not_a_directory(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            f = tdp / "file.txt"
            f.write_text("not a dir", encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target_path=str(f))
            self.assertIn("not a directory", ctx.exception.reason)

    def test_refuses_target_path_does_not_exist(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            with self.assertRaises(HaltError) as ctx:
                self._attach(
                    controller,
                    target_path=str(tdp / "nope"),
                )
            self.assertIn("does not exist", ctx.exception.reason)

    def test_refuses_empty_target_state(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            # No canonical artifacts: empty_target.
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target_path=str(target))
            self.assertIn("empty_target", ctx.exception.reason)
            self.assertIn("Phase 10E", ctx.exception.reason)

    def test_refuses_partial_target_state(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            (target / "TASK.md").write_text("partial", encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target_path=str(target))
            self.assertIn("partial_target", ctx.exception.reason)

    def test_refuses_malformed_target_state(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            # Break loop-state.json so the validator refuses.
            (target / ".agent-loop" / "loop-state.json").write_text(
                "bogus", encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target_path=str(target))
            self.assertIn("malformed_target", ctx.exception.reason)


# ---------------------------------------------------------------------------
# detach_external_target - success + refusal paths
# ---------------------------------------------------------------------------
class DetachExternalTargetTests(unittest.TestCase):

    def _attach_then(self, controller, target):
        _write_full_target(target)
        log_path = controller / ".agent-loop" / "orchestrator.log"
        agent_loop.attach_external_target(
            controller,
            target_path=str(target),
            attached_by="alice",
            approval_mode="review",
            log_path=log_path,
        )
        return log_path

    def test_detach_removes_attach_record_and_logs(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            log_path = self._attach_then(controller, target)
            attach_record = controller / ATTACH_RECORD_REL
            self.assertTrue(attach_record.exists())
            removed = agent_loop.detach_external_target(
                controller,
                detached_by="alice",
                log_path=log_path,
            )
            self.assertFalse(attach_record.exists())
            self.assertEqual(removed, attach_record)
            log_contents = log_path.read_text(encoding="utf-8")
            self.assertIn("external target: detached", log_contents)
            self.assertIn("'alice'", log_contents)
            self.assertIn("phase-10b-v1", log_contents)

    def test_detach_refuses_when_no_attach_record(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.detach_external_target(
                    controller, detached_by="alice",
                )
            self.assertIn(
                "no attach record on disk", ctx.exception.reason,
            )

    def test_detach_refuses_malformed_attach_record(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            attach_record = controller / ATTACH_RECORD_REL
            attach_record.parent.mkdir(parents=True, exist_ok=True)
            attach_record.write_text("not valid json", encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.detach_external_target(
                    controller, detached_by="alice",
                )
            self.assertIn("malformed JSON", ctx.exception.reason)

    def test_detach_refuses_unrecognized_signal_version(self) -> None:
        # Phase 10D fix-cycle: even with a fully-populated otherwise-
        # valid record, an unrecognized signal_version refuses
        # fail-closed BEFORE the schema check runs (so the operator
        # gets a clear contract-version-mismatch message rather than
        # a generic schema-missing-field message).
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            attach_record = controller / ATTACH_RECORD_REL
            attach_record.parent.mkdir(parents=True, exist_ok=True)
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            record["attach_record_signal_version"] = "future-v99"
            attach_record.write_text(
                json.dumps(record), encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.detach_external_target(
                    controller, detached_by="alice",
                )
            self.assertIn(
                "attach_record_signal_version", ctx.exception.reason,
            )

    def test_detach_refuses_controller_mismatch(self) -> None:
        # Phase 10D fix-cycle: a fully-populated record whose
        # `controller_path_canonical` does not match the running
        # controller fails the semantic mismatch check (which fires
        # AFTER the new schema validator passes).
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            attach_record = controller / ATTACH_RECORD_REL
            attach_record.parent.mkdir(parents=True, exist_ok=True)
            record = _make_valid_attach_record(
                controller_canonical="/some/other/path",
            )
            attach_record.write_text(
                json.dumps(record), encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.detach_external_target(
                    controller, detached_by="alice",
                )
            self.assertIn(
                "controller_path_canonical", ctx.exception.reason,
            )

    def test_detach_refuses_missing_detached_by(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.detach_external_target(
                    controller, detached_by=None,
                )
            self.assertEqual(ctx.exception.status, "halted_input_missing")

    def test_detach_refuses_empty_detached_by(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            with self.assertRaises(HaltError):
                agent_loop.detach_external_target(
                    controller, detached_by="   ",
                )


# ---------------------------------------------------------------------------
# Phase 10D fix-cycle: attach target-state refusals
# ---------------------------------------------------------------------------
class AttachTargetStateRefusalTests(unittest.TestCase):
    """Phase 10D fix-cycle: attach must refuse a `full_target` whose
    own `loop-state.json` either carries an unsupported
    `contract_version` or is in any `halted_*` status. The classifier
    intentionally permits a target with a different contract_version
    so a future Phase 10E bootstrap path can still classify; the
    attach runtime applies the stricter check AT ATTACH TIME so
    attaching never silently treats a halted or version-mismatched
    target as resumable.
    """

    def _attach(self, controller, target, **overrides):
        defaults = dict(
            target_path=str(target),
            attached_by="alice",
            approval_mode="review",
        )
        defaults.update(overrides)
        return agent_loop.attach_external_target(
            controller, **defaults,
        )

    def _set_target_loop_state(
        self, target: Path, **field_overrides,
    ) -> None:
        state_path = (
            target / ".agent-loop" / "loop-state.json"
        )
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data.update(field_overrides)
        state_path.write_text(
            json.dumps(data), encoding="utf-8",
        )

    def test_refuses_target_with_unsupported_contract_version(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            self._set_target_loop_state(
                target, contract_version="future-v99",
            )
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target)
            self.assertEqual(
                ctx.exception.status,
                "halted_contract_version_mismatch",
            )
            # No attach record should be written.
            self.assertFalse(
                (controller / ATTACH_RECORD_REL).exists(),
            )

    def test_refuses_target_with_missing_contract_version(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            self._set_target_loop_state(
                target, contract_version=None,
            )
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target)
            self.assertEqual(
                ctx.exception.status,
                "halted_contract_version_mismatch",
            )
            self.assertFalse(
                (controller / ATTACH_RECORD_REL).exists(),
            )

    def test_refuses_target_in_halted_state(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            self._set_target_loop_state(
                target, status="halted_input_missing",
            )
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "halted_input_missing", ctx.exception.reason,
            )
            self.assertIn(
                "halted state", ctx.exception.reason,
            )
            self.assertFalse(
                (controller / ATTACH_RECORD_REL).exists(),
            )

    def test_refuses_target_in_any_halted_variant(self) -> None:
        # Any `halted_*` status (the contract uses many variants:
        # `halted_review_parse_failed`, `halted_max_cycles_reached`,
        # `halted_failed_requires_human`, etc.) must refuse, not
        # just `halted_input_missing`.
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            target = tdp / "target"
            target.mkdir()
            _write_full_target(target)
            self._set_target_loop_state(
                target, status="halted_max_cycles_reached",
            )
            with self.assertRaises(HaltError) as ctx:
                self._attach(controller, target)
            self.assertIn(
                "halted_max_cycles_reached", ctx.exception.reason,
            )
            self.assertFalse(
                (controller / ATTACH_RECORD_REL).exists(),
            )


# ---------------------------------------------------------------------------
# Phase 10D fix-cycle: detach full-schema refusals
# ---------------------------------------------------------------------------
class DetachSchemaRefusalTests(unittest.TestCase):
    """Phase 10D fix-cycle: detach must refuse fail-closed on every
    malformed-but-JSON attach record. An underspecified record
    carrying only `attach_record_signal_version` and
    `controller_path_canonical` previously slipped through; the
    explicit schema check covers every required top-level field and
    every required sub-field inside the structured top-level objects.
    """

    def _plant(self, controller: Path, record: dict) -> None:
        attach_record = controller / ATTACH_RECORD_REL
        attach_record.parent.mkdir(parents=True, exist_ok=True)
        attach_record.write_text(
            json.dumps(record), encoding="utf-8",
        )

    def _detach_raises(self, controller: Path) -> HaltError:
        with self.assertRaises(HaltError) as ctx:
            agent_loop.detach_external_target(
                controller, detached_by="alice",
            )
        return ctx.exception

    def test_refuses_underspecified_record_with_only_two_fields(
        self,
    ) -> None:
        # The original review's reproducer: a record carrying only
        # `attach_record_signal_version` and
        # `controller_path_canonical` previously detached cleanly.
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            self._plant(controller, {
                "attach_record_signal_version": "phase-10b-v1",
                "controller_path_canonical": (
                    controller.resolve().as_posix()
                ),
            })
            exc = self._detach_raises(controller)
            self.assertEqual(exc.status, "halted_input_missing")
            self.assertIn("structurally invalid", exc.reason)
            # The detach refusal must NOT delete the malformed
            # record; the operator must inspect it manually.
            self.assertTrue(
                (controller / ATTACH_RECORD_REL).exists(),
            )

    def test_refuses_missing_attached_by(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["attached_by"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("attached_by", exc.reason)

    def test_refuses_non_string_attached_at(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            record["attached_at"] = 12345
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("attached_at", exc.reason)

    def test_refuses_missing_target_path_canonical(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["target_path_canonical"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("target_path_canonical", exc.reason)

    def test_refuses_missing_controller_identity(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["controller_identity"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("controller_identity", exc.reason)

    def test_refuses_wrong_typed_controller_identity(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            record["controller_identity"] = "should be a dict"
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("controller_identity", exc.reason)
            self.assertIn("not an object", exc.reason)

    def test_refuses_missing_controller_identity_subfield(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["controller_identity"]["repo_signature"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn(
                "controller_identity.repo_signature", exc.reason,
            )

    def test_refuses_missing_mode_selection(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["mode_selection"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("mode_selection", exc.reason)

    def test_refuses_missing_bootstrap_state_status(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["bootstrap_state"]["status"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("bootstrap_state.status", exc.reason)

    def test_refuses_missing_stale_attach_detection(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["stale_attach_detection"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("stale_attach_detection", exc.reason)

    def test_refuses_non_list_refusal_history(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            record["audit"]["refusal_history"] = "not a list"
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn(
                "audit.refusal_history", exc.reason,
            )
            self.assertIn("non-list", exc.reason)

    def test_refuses_missing_audit_attach_log_line(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["audit"]["attach_log_line"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn("audit.attach_log_line", exc.reason)

    def test_refuses_missing_canonical_precedence_note(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            del record["canonical_precedence_note"]
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn(
                "canonical_precedence_note", exc.reason,
            )

    def test_refuses_non_list_target_marker_files(self) -> None:
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            record["stale_attach_detection"][
                "target_marker_files_at_attach"
            ] = "should be a list"
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertIn(
                "stale_attach_detection.target_marker_files_at_attach",
                exc.reason,
            )

    def test_refuses_out_of_enumeration_approval_mode(self) -> None:
        # Phase 10D fix-cycle: a malformed record whose
        # `mode_selection.approval_mode` is outside the Phase 10B
        # closed enumeration refuses fail-closed AT SCHEMA TIME (not
        # only at the controller-mismatch check). Without this guard
        # an operator hand-edit or another controller could write
        # e.g. `approval_mode == "bogus_mode"` and the record would
        # silently detach.
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            record["mode_selection"]["approval_mode"] = "bogus_mode"
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertEqual(exc.status, "halted_input_missing")
            self.assertIn(
                "mode_selection.approval_mode", exc.reason,
            )
            self.assertIn(
                "EXTERNAL_TARGET_APPROVAL_MODES", exc.reason,
            )
            # The refusal must NOT delete the malformed record; the
            # operator must inspect it manually.
            self.assertTrue(
                (controller / ATTACH_RECORD_REL).exists(),
            )

    def test_refuses_out_of_enumeration_bootstrap_status(self) -> None:
        # Phase 10D fix-cycle: same guard for the
        # `bootstrap_state.status` closed enumeration. A malformed
        # record carrying a fabricated status string (e.g.
        # `"target_canonical_set_pending"`) is now rejected at
        # schema time.
        with TemporaryDirectory() as td:
            tdp = Path(td)
            controller = _make_controller(tdp / "controller")
            record = _make_valid_attach_record(
                controller_canonical=controller.resolve().as_posix(),
            )
            record["bootstrap_state"]["status"] = (
                "target_canonical_set_pending"
            )
            self._plant(controller, record)
            exc = self._detach_raises(controller)
            self.assertEqual(exc.status, "halted_input_missing")
            self.assertIn(
                "bootstrap_state.status", exc.reason,
            )
            self.assertIn(
                "EXTERNAL_TARGET_BOOTSTRAP_STATUSES", exc.reason,
            )
            self.assertTrue(
                (controller / ATTACH_RECORD_REL).exists(),
            )


# ---------------------------------------------------------------------------
# CLI argparse grammar
# ---------------------------------------------------------------------------
class AttachDetachCLISurfaceTests(unittest.TestCase):

    def test_argparse_grammar_attach(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "attach-external-target",
            "--target-path", "/tmp/x",
            "--attached-by", "alice",
            "--approval-mode", "review",
        ])
        self.assertEqual(args.cmd, "attach-external-target")
        self.assertEqual(args.target_path, "/tmp/x")
        self.assertEqual(args.attached_by, "alice")
        self.assertEqual(args.approval_mode, "review")

    def test_argparse_rejects_unknown_approval_mode(self) -> None:
        parser = agent_loop.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "attach-external-target",
                "--target-path", "/tmp/x",
                "--attached-by", "alice",
                "--approval-mode", "bogus",
            ])

    def test_argparse_requires_attach_args(self) -> None:
        parser = agent_loop.build_parser()
        with self.assertRaises(SystemExit):
            # missing --target-path
            parser.parse_args([
                "attach-external-target",
                "--attached-by", "alice",
                "--approval-mode", "review",
            ])

    def test_argparse_grammar_detach(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "detach-external-target",
            "--detached-by", "alice",
        ])
        self.assertEqual(args.cmd, "detach-external-target")
        self.assertEqual(args.detached_by, "alice")

    def test_argparse_requires_detached_by(self) -> None:
        parser = agent_loop.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["detach-external-target"])


if __name__ == "__main__":
    unittest.main()
