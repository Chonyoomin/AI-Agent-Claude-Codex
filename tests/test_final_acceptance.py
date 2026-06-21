"""Phase 9G - Final Human Acceptance And Polish Gate tests.

Exercises `record_final_acceptance(...)`, `evaluate_final_acceptance(...)`,
and the `record-final-acceptance` / `evaluate-final-acceptance` CLI
subcommands. The Phase 9G gate is the load-bearing "but the human
still has to look at it before we call it done" boundary the Phase
9A autonomy contract requires; the shipped Phase 9B/9C/9D/9E/9F
surfaces can drive a PRD to the Codex-approved terminal but Phase 9G
refuses to let any caller treat the run as complete until explicit
human acceptance is recorded from canonical repo artifacts.

The tests prove:
  - the canonical acceptance artifact at
    `.agent-loop/final-acceptance.json` carries the documented
    schema (acceptance_signal_version, accepted_at, accepted_by,
    phase / sub_phase / task / cycle_count / last_verdict
    snapshot, optional notes, canonical_precedence_note)
  - the recorder refuses fail-closed unless the run has reached
    the Codex-approved terminal (status =
    phase_complete_awaiting_human_approval AND last_verdict =
    APPROVED_FOR_HUMAN_REVIEW)
  - the recorder refuses fail-closed on missing / empty / non-
    string / over-bounded `accepted_by`, on non-string /
    over-bounded `notes`, on output-boundary violations, and on
    an existing acceptance artifact (Phase 9G refuses silent
    re-acceptance)
  - the evaluator returns `not_ready` when the run has not
    reached the Codex-approved terminal, `awaiting_final_human_
    acceptance` when at the terminal but no artifact (or the
    artifact is corrupt / stale / mismatched), and
    `final_acceptance_recorded` when the artifact matches the
    current loop-state
  - the symmetric Phase 9 protected output sets all include the
    new `.agent-loop/final-acceptance.json` path so no other
    Phase 9 slice can overwrite it through its own output flag
  - the recorder writes the artifact first, then transitions
    only `loop-state.status` from
    `phase_complete_awaiting_human_approval` to
    `phase_complete_final_human_accepted` so the canonical state
    model itself reflects accepted completion; no other
    loop-state field is mutated. Recording remains a gate, not
    an activation: the shipped Phase 4C activator +
    APPROVED_FOR_ACTIVATION human approval remain the only path
    to the next phase. The artifact-first ordering means a
    `save_loop_state` failure after the artifact write leaves a
    torn state the evaluator detects rather than silently
    advancing.
"""
from __future__ import annotations

import argparse
import json
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

ACTIVE_PHASE = "Phase 9 - Fully Autonomous PRD-To-Product Mode"
ACTIVE_SUB_PHASE = "Phase 9G - Final Human Acceptance And Polish Gate"


def _make_repo(td: Path) -> Path:
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("test\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    return td


def _plant_loop_state(
    repo_root: Path,
    *,
    status: str = "phase_complete_awaiting_human_approval",
    last_verdict: object = "APPROVED_FOR_HUMAN_REVIEW",
    cycle_count: int = 3,
    max_cycles: int = 5,
    task: str = "final-acceptance-test",
    phase: str = ACTIVE_PHASE,
    sub_phase: str = ACTIVE_SUB_PHASE,
) -> Path:
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    state_path.write_text(json.dumps({
        "phase": phase,
        "sub_phase": sub_phase,
        "task": task,
        "status": status,
        "cycle_count": cycle_count,
        "max_cycles": max_cycles,
        "last_verdict": last_verdict,
        "last_verdict_phase": sub_phase,
        "contract_version": CONTRACT_VERSION,
        "claude_version": "claude-opus-4-7",
        "codex_version": "codex-stub",
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": "autonomous",
        "awaiting_human_for": None,
    }), encoding="utf-8")
    return state_path


class FinalAcceptanceConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_SIGNAL_VERSION, "phase-9g-v1",
        )

    def test_output_rel(self) -> None:
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_OUTPUT_REL,
            ".agent-loop/final-acceptance.json",
        )

    def test_required_terminal_status_and_verdict(self) -> None:
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_REQUIRED_TERMINAL_STATUS,
            "phase_complete_awaiting_human_approval",
        )
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_REQUIRED_LAST_VERDICT,
            "APPROVED_FOR_HUMAN_REVIEW",
        )

    def test_signal_vocabulary(self) -> None:
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_SIGNALS,
            frozenset({
                "not_ready",
                "awaiting_final_human_acceptance",
                "final_acceptance_recorded",
            }),
        )

    def test_bounded_field_caps(self) -> None:
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_MAX_ACCEPTED_BY_LENGTH, 200,
        )
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_MAX_NOTES_LENGTH, 8000,
        )

    def test_handlers_wired(self) -> None:
        self.assertIn(
            "record-final-acceptance", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["record-final-acceptance"],
            agent_loop.cmd_record_final_acceptance,
        )
        self.assertIn(
            "evaluate-final-acceptance", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["evaluate-final-acceptance"],
            agent_loop.cmd_evaluate_final_acceptance,
        )

    def test_protected_output_set_includes_siblings(self) -> None:
        protected = agent_loop.FINAL_ACCEPTANCE_PROTECTED_OUTPUT_PATHS
        for sibling in (
            ".agent-loop/prd-intake.json",
            ".agent-loop/prompt-handoff.json",
            ".agent-loop/review-fix-loop.json",
            ".agent-loop/long-run-continuation.json",
            ".agent-loop/capacity-retry-state.json",
        ):
            self.assertIn(sibling, protected)

    def test_protected_output_set_excludes_self_default(self) -> None:
        self.assertNotIn(
            ".agent-loop/final-acceptance.json",
            agent_loop.FINAL_ACCEPTANCE_PROTECTED_OUTPUT_PATHS,
        )

    def test_sibling_sets_protect_phase_9g_output(self) -> None:
        # Symmetric cross-slice output protection: every prior
        # Phase 9 protected set must include the new Phase 9G
        # final-acceptance path.
        for sibling_set in (
            agent_loop.PRD_INTAKE_PROTECTED_OUTPUT_PATHS,
            agent_loop.PROMPT_HANDOFF_PROTECTED_OUTPUT_PATHS,
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_PROTECTED_OUTPUT_PATHS,
            agent_loop.LONG_RUN_CONTINUATION_PROTECTED_OUTPUT_PATHS,
            agent_loop.CAPACITY_RETRY_PROTECTED_OUTPUT_PATHS,
        ):
            self.assertIn(
                ".agent-loop/final-acceptance.json", sibling_set,
            )


class RecordFinalAcceptanceTerminalGateTests(unittest.TestCase):

    def test_refuses_when_status_not_approved_terminal(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "Codex-approved terminal", str(ctx.exception),
            )

    def test_refuses_when_last_verdict_not_approved(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, last_verdict="NEEDS_FIXES")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "last_verdict", str(ctx.exception),
            )

    def test_refuses_when_loop_state_missing(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_accepts_at_codex_approved_terminal(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            written = agent_loop.record_final_acceptance(
                repo, accepted_by="operator", notes="ship it",
            )
            self.assertTrue(written.is_file())
            artifact = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                artifact["acceptance_signal_version"], "phase-9g-v1",
            )
            self.assertEqual(artifact["accepted_by"], "operator")
            self.assertEqual(artifact["notes"], "ship it")
            self.assertEqual(artifact["phase"], ACTIVE_PHASE)
            self.assertEqual(artifact["sub_phase"], ACTIVE_SUB_PHASE)
            self.assertEqual(artifact["task"], "final-acceptance-test")
            self.assertEqual(artifact["cycle_count"], 3)
            self.assertEqual(
                artifact["last_verdict"], "APPROVED_FOR_HUMAN_REVIEW",
            )
            self.assertIn(
                "Phase 4 planner",
                artifact["canonical_precedence_note"],
            )
            # Phase 9G fix-cycle: the acceptance gate now
            # transitions loop-state.status from the pre-acceptance
            # terminal to the canonical accepted terminal so the
            # canonical state model itself reflects accepted
            # completion. The transition is still a gate, not an
            # activation: no other loop-state field is mutated and
            # the next phase is not auto-activated (Phase 4C
            # activator + APPROVED_FOR_ACTIVATION remain the only
            # path).
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["status"], "phase_complete_final_human_accepted",
            )
            # Last_verdict and other fields are NOT mutated by the
            # gate; only the status reflects the acceptance.
            self.assertEqual(
                state["last_verdict"], "APPROVED_FOR_HUMAN_REVIEW",
            )
            self.assertEqual(state["cycle_count"], 3)
            self.assertEqual(state["phase"], ACTIVE_PHASE)
            self.assertEqual(state["sub_phase"], ACTIVE_SUB_PHASE)


class RecordFinalAcceptanceAcceptedByValidationTests(unittest.TestCase):

    def test_refuses_when_accepted_by_missing(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(repo)
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("accepted_by is required", str(ctx.exception))

    def test_refuses_when_accepted_by_empty_or_whitespace(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            for bad in ("", "   ", "\t\n"):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.record_final_acceptance(
                            repo, accepted_by=bad,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_refuses_when_accepted_by_non_string(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            for bad in (42, [], {}, True):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.record_final_acceptance(
                            repo, accepted_by=bad,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_refuses_when_accepted_by_too_long(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            too_long = "x" * (
                agent_loop.FINAL_ACCEPTANCE_MAX_ACCEPTED_BY_LENGTH + 1
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by=too_long,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_accepted_by_is_stripped(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            written = agent_loop.record_final_acceptance(
                repo, accepted_by="   operator-trimmed   ",
            )
            artifact = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                artifact["accepted_by"], "operator-trimmed",
            )


class RecordFinalAcceptanceNotesValidationTests(unittest.TestCase):

    def test_notes_optional_default_none(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            written = agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
            )
            artifact = json.loads(written.read_text(encoding="utf-8"))
            self.assertIsNone(artifact["notes"])

    def test_notes_refused_when_non_string(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            for bad in (42, [], {}, True):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.record_final_acceptance(
                            repo, accepted_by="operator", notes=bad,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_notes_refused_when_over_length(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            too_long = "x" * (
                agent_loop.FINAL_ACCEPTANCE_MAX_NOTES_LENGTH + 1
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator", notes=too_long,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )


class RecordFinalAcceptanceOutputBoundaryTests(unittest.TestCase):

    def test_refuses_outside_agent_loop(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator",
                    output_path=repo / "outside.json",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_overwriting_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator",
                    output_path=(
                        repo / ".agent-loop" / "loop-state.json"
                    ),
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_overwriting_capacity_retry_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator",
                    output_path=(
                        repo / ".agent-loop"
                        / "capacity-retry-state.json"
                    ),
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_memory_subtree(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator",
                    output_path=(
                        repo / ".agent-loop" / "memory" / "x.json"
                    ),
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_safe_override_succeeds(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            override = (
                repo / ".agent-loop" / "custom-acceptance.json"
            )
            written = agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
                output_path=override,
            )
            self.assertEqual(written, override)
            self.assertTrue(written.is_file())


class RecordFinalAcceptanceRefusesSilentReacceptanceTests(
    unittest.TestCase,
):

    def test_refuses_when_artifact_already_exists(self) -> None:
        # Phase 9G fix-cycle: after a successful record, BOTH
        # halves of the canonical accepted-state signal are set
        # (artifact on disk + loop-state.status bumped to
        # `phase_complete_final_human_accepted`). The second
        # `record_final_acceptance` call hits the new
        # status-already-accepted guard FIRST so the refusal
        # message names the canonical state-model condition;
        # the artifact-exists guard is reachable only when the
        # status guard has been manually reset (next test).
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            agent_loop.record_final_acceptance(
                repo, accepted_by="first-operator",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="second-operator",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "already 'phase_complete_final_human_accepted'",
                str(ctx.exception),
            )
            self.assertIn(
                "delete the acceptance artifact AND reset "
                "loop-state.status",
                str(ctx.exception),
            )

    def test_refuses_when_artifact_exists_but_status_reset(
        self,
    ) -> None:
        # Phase 9G fix-cycle: the artifact-already-exists guard
        # still fires when an operator manually resets only the
        # loop-state.status half of the canonical accepted
        # signal (leaving the artifact in place). The refusal
        # message names the existing artifact so the operator
        # sees both halves of the reset are required.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            agent_loop.record_final_acceptance(
                repo, accepted_by="first-operator",
            )
            # Manually reset only the loop-state half (artifact
            # remains on disk).
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["status"] = "phase_complete_awaiting_human_approval"
            state_path.write_text(
                json.dumps(state), encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="second-operator",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("already exists", str(ctx.exception))
            self.assertIn(
                "Delete the existing artifact",
                str(ctx.exception),
            )

    def test_explicit_delete_and_status_reset_allows_re_record(
        self,
    ) -> None:
        # Phase 9G fix-cycle: the full re-record flow now
        # requires resetting BOTH halves of the canonical
        # accepted-state signal: delete the artifact AND reset
        # loop-state.status back to the pre-acceptance terminal.
        # This is the fail-loud workflow the contract requires;
        # no `--force` flag is provided.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            written = agent_loop.record_final_acceptance(
                repo, accepted_by="first-operator",
            )
            # Reset both halves: delete artifact + reset status.
            written.unlink()
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["status"] = "phase_complete_awaiting_human_approval"
            state_path.write_text(
                json.dumps(state), encoding="utf-8",
            )
            agent_loop.record_final_acceptance(
                repo, accepted_by="second-operator",
                notes="re-recorded after polish",
            )
            artifact = json.loads(written.read_text(encoding="utf-8"))
            self.assertEqual(
                artifact["accepted_by"], "second-operator",
            )
            # Loop-state has been bumped back to accepted by the
            # re-record.
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["status"], "phase_complete_final_human_accepted",
            )


class RecordFinalAcceptanceAuditLogTests(unittest.TestCase):

    def test_audit_line_recorded(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            log_path = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.record_final_acceptance(
                repo, accepted_by="operator", notes="ok",
                log_path=log_path,
            )
            audit = log_path.read_text(encoding="utf-8")
            self.assertIn("final acceptance: recorded", audit)
            self.assertIn("phase-9g-v1", audit)
            self.assertIn("'operator'", audit)


class EvaluateFinalAcceptanceTests(unittest.TestCase):

    def test_not_ready_when_status_not_approved_terminal(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="claude_implementing")
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"], "not_ready",
            )
            self.assertFalse(result["acceptance_artifact_present"])
            self.assertFalse(
                result["acceptance_artifact_matches_loop_state"],
            )
            self.assertIsNone(result["accepted_by"])

    def test_not_ready_when_last_verdict_not_approved(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, last_verdict="NEEDS_FIXES")
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"], "not_ready",
            )

    def test_awaiting_when_terminal_but_no_artifact(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"],
                "awaiting_final_human_acceptance",
            )
            self.assertFalse(result["acceptance_artifact_present"])

    def test_recorded_when_artifact_matches_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
            )
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"],
                "final_acceptance_recorded",
            )
            self.assertTrue(result["acceptance_artifact_present"])
            self.assertTrue(
                result["acceptance_artifact_matches_loop_state"],
            )
            self.assertEqual(result["accepted_by"], "operator")

    def test_awaiting_when_artifact_corrupt(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            (repo / ".agent-loop" / "final-acceptance.json").write_text(
                "not json {", encoding="utf-8",
            )
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"],
                "awaiting_final_human_acceptance",
            )
            self.assertTrue(result["acceptance_artifact_present"])
            self.assertFalse(
                result["acceptance_artifact_matches_loop_state"],
            )

    def test_awaiting_when_artifact_mismatches_loop_state(self) -> None:
        # The artifact captured a snapshot of an EARLIER run; the
        # current loop-state has a different cycle_count. The
        # evaluator must report awaiting + does-not-match so the
        # stale acceptance does not silently validate the new run.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo, cycle_count=2)
            agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
            )
            # Bump the cycle_count out from under the artifact.
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["cycle_count"] = 5
            state_path.write_text(
                json.dumps(state), encoding="utf-8",
            )
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"],
                "awaiting_final_human_acceptance",
            )
            self.assertTrue(result["acceptance_artifact_present"])
            self.assertFalse(
                result["acceptance_artifact_matches_loop_state"],
            )
            self.assertEqual(result["accepted_by"], "operator")

    def test_evaluator_never_mutates_artifact(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            written = agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
            )
            before = written.read_text(encoding="utf-8")
            agent_loop.evaluate_final_acceptance(repo)
            agent_loop.evaluate_final_acceptance(repo)
            agent_loop.evaluate_final_acceptance(repo)
            after = written.read_text(encoding="utf-8")
            self.assertEqual(before, after)


class CanonicalAcceptedStateModelTests(unittest.TestCase):
    """Phase 9G fix-cycle: accepted completion is visible through
    the canonical state model (loop-state.status =
    `phase_complete_final_human_accepted`) AND the
    `.agent-loop/final-acceptance.json` artifact. Both halves must
    be set together for the `recorded` signal; a torn state is
    reported as `awaiting_final_human_acceptance` so the gate
    fails loud rather than silently advancing on a partial signal.
    """

    def test_new_accepted_status_constant_value(self) -> None:
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_ACCEPTED_STATUS,
            "phase_complete_final_human_accepted",
        )

    def test_valid_terminal_statuses_set_contains_both(self) -> None:
        self.assertEqual(
            agent_loop.FINAL_ACCEPTANCE_VALID_TERMINAL_STATUSES,
            frozenset({
                "phase_complete_awaiting_human_approval",
                "phase_complete_final_human_accepted",
            }),
        )

    def test_record_transitions_status_atomically(self) -> None:
        # The recording writes the artifact first, then transitions
        # loop-state.status. Both halves are present on disk after
        # a successful record.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            artifact_path = (
                repo / ".agent-loop" / "final-acceptance.json"
            )
            agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
            )
            # Both halves of the canonical accepted-state signal
            # are now on disk.
            self.assertTrue(artifact_path.exists())
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(
                state["status"],
                "phase_complete_final_human_accepted",
            )

    def test_record_refuses_when_status_already_accepted(self) -> None:
        # Re-recording on a run that already has loop-state at the
        # canonical accepted terminal is refused fail-closed with
        # a clear message naming both halves of the required reset.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(
                repo,
                status="phase_complete_final_human_accepted",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.record_final_acceptance(
                    repo, accepted_by="operator",
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "already 'phase_complete_final_human_accepted'",
                str(ctx.exception),
            )

    def test_evaluate_recorded_requires_status_bumped(self) -> None:
        # When the artifact matches but loop-state.status is
        # still at the pre-acceptance terminal (torn state), the
        # evaluator returns `awaiting_final_human_acceptance` so
        # the gate fails loud.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
            )
            # Manually reset only the loop-state half (artifact
            # remains on disk + matches).
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["status"] = "phase_complete_awaiting_human_approval"
            state_path.write_text(
                json.dumps(state), encoding="utf-8",
            )
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"],
                "awaiting_final_human_acceptance",
            )
            self.assertTrue(result["acceptance_artifact_present"])
            self.assertTrue(
                result["acceptance_artifact_matches_loop_state"],
            )
            self.assertIn("torn state", result["reason"])

    def test_evaluate_recorded_when_both_halves_present(self) -> None:
        # Both halves of the canonical accepted-state signal are
        # set: artifact present + matches + loop-state.status =
        # canonical accepted. The evaluator returns the
        # `recorded` signal.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
            )
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"],
                "final_acceptance_recorded",
            )

    def test_evaluate_treats_accepted_status_as_valid_terminal(
        self,
    ) -> None:
        # Phase 9G fix-cycle: the `not_ready` check accepts BOTH
        # the pre-acceptance terminal AND the canonical accepted
        # terminal as valid Codex-approved terminal states. A
        # loop-state at the accepted terminal but with the
        # artifact missing is reported as awaiting, not as
        # not_ready.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="phase_complete_final_human_accepted",
            )
            # No artifact written.
            result = agent_loop.evaluate_final_acceptance(repo)
            self.assertEqual(
                result["acceptance_signal"],
                "awaiting_final_human_acceptance",
            )

    def test_phase_9e_completion_recognizes_accepted_status(
        self,
    ) -> None:
        # The Phase 9E `evaluate_phase_completion(...)` was
        # extended to recognize the canonical accepted terminal
        # as a `completion_approved` signal so the long-run loop
        # terminates cleanly after a Phase 9G acceptance recording.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(
                repo,
                status="phase_complete_final_human_accepted",
            )
            result = agent_loop.evaluate_phase_completion(repo)
            self.assertEqual(
                result["completion_signal"],
                "completion_approved",
            )
            self.assertEqual(
                result["terminal_status"],
                "phase_complete_final_human_accepted",
            )

    def test_phase_9e_completion_still_recognizes_awaiting_status(
        self,
    ) -> None:
        # Regression guard: the pre-acceptance terminal still
        # produces a `completion_approved` signal so existing
        # Phase 9E callers stay byte-equivalent.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            result = agent_loop.evaluate_phase_completion(repo)
            self.assertEqual(
                result["completion_signal"],
                "completion_approved",
            )

    def test_audit_line_records_accepted_status(self) -> None:
        # The audit line now also records the new
        # `accepted_status` field so operators inspecting the
        # log see the canonical state-model transition.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            log_path = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.record_final_acceptance(
                repo, accepted_by="operator",
                log_path=log_path,
            )
            audit = log_path.read_text(encoding="utf-8")
            self.assertIn(
                "accepted_status="
                "'phase_complete_final_human_accepted'",
                audit,
            )


class FinalAcceptanceCliTests(unittest.TestCase):

    def setUp(self) -> None:
        self.td = TemporaryDirectory()
        self.repo = Path(self.td.name)
        _make_repo(self.repo)
        _plant_loop_state(self.repo)
        import os
        self._prev_cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self) -> None:
        import os
        os.chdir(self._prev_cwd)
        self.td.cleanup()

    def test_cli_record_writes_artifact(self) -> None:
        rc = agent_loop.main([
            "record-final-acceptance",
            "--accepted-by", "cli-operator",
            "--notes", "approved after manual polish",
        ])
        self.assertEqual(rc, 0)
        artifact_path = (
            self.repo / ".agent-loop" / "final-acceptance.json"
        )
        self.assertTrue(artifact_path.exists())
        artifact = json.loads(
            artifact_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(artifact["accepted_by"], "cli-operator")
        self.assertEqual(
            artifact["notes"], "approved after manual polish",
        )

    def test_cli_record_refuses_when_not_at_terminal(self) -> None:
        # Re-plant at non-approved terminal.
        _plant_loop_state(self.repo, status="claude_implementing")
        rc = agent_loop.main([
            "record-final-acceptance",
            "--accepted-by", "cli-operator",
        ])
        self.assertEqual(rc, 2)

    def test_cli_record_refuses_when_artifact_exists(self) -> None:
        agent_loop.main([
            "record-final-acceptance",
            "--accepted-by", "first",
        ])
        rc = agent_loop.main([
            "record-final-acceptance",
            "--accepted-by", "second",
        ])
        self.assertEqual(rc, 2)

    def test_cli_evaluate_reports_awaiting_signal(self) -> None:
        # No artifact yet -> awaiting.
        rc = agent_loop.main(["evaluate-final-acceptance"])
        self.assertEqual(rc, 0)

    def test_cli_evaluate_reports_recorded_signal(self) -> None:
        agent_loop.main([
            "record-final-acceptance",
            "--accepted-by", "operator",
        ])
        rc = agent_loop.main(["evaluate-final-acceptance"])
        self.assertEqual(rc, 0)

    def test_cli_evaluate_always_exits_0_even_without_loop_state(
        self,
    ) -> None:
        # Mirror the Phase 7C status-reporter contract: the
        # evaluator is read-only and never fails on a missing
        # loop-state; it prints a load_error line instead.
        (self.repo / ".agent-loop" / "loop-state.json").unlink()
        rc = agent_loop.main(["evaluate-final-acceptance"])
        self.assertEqual(rc, 0)

    def test_cli_record_refuses_output_outside_agent_loop(self) -> None:
        rc = agent_loop.main([
            "record-final-acceptance",
            "--accepted-by", "cli-operator",
            "--output", "../escape.json",
        ])
        self.assertEqual(rc, 2)


class FinalAcceptanceHelpTextTests(unittest.TestCase):

    def _help_text(self, subcmd: str) -> str:
        parser = agent_loop.build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for choice_action in action._choices_actions:
                    if choice_action.dest == subcmd:
                        return choice_action.help or ""
        self.fail(f"{subcmd} subparser help not found")
        return ""

    def test_record_help_describes_phase_9g_role(self) -> None:
        text = self._help_text("record-final-acceptance")
        self.assertIn("Phase 9G", text)
        self.assertIn("final human", text.lower())

    def test_record_help_documents_terminal_gate(self) -> None:
        text = self._help_text("record-final-acceptance")
        self.assertIn("phase_complete_awaiting_human_approval", text)
        self.assertIn("APPROVED_FOR_HUMAN_REVIEW", text)

    def test_record_help_names_artifact_path(self) -> None:
        text = self._help_text("record-final-acceptance")
        self.assertIn(".agent-loop/final-acceptance.json", text)

    def test_record_help_preserves_planner_activator_boundary(
        self,
    ) -> None:
        text = self._help_text("record-final-acceptance")
        self.assertIn("Phase 4C activator", text)
        self.assertIn("APPROVED_FOR_ACTIVATION", text)

    def test_evaluate_help_describes_phase_9g_role(self) -> None:
        text = self._help_text("evaluate-final-acceptance")
        self.assertIn("Phase 9G", text)
        self.assertIn("read-only", text)

    def test_evaluate_help_documents_signal_vocabulary(self) -> None:
        text = self._help_text("evaluate-final-acceptance")
        for signal in (
            "not_ready",
            "awaiting_final_human_acceptance",
            "final_acceptance_recorded",
        ):
            self.assertIn(signal, text)


if __name__ == "__main__":
    unittest.main()
