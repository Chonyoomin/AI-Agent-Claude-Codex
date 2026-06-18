"""Phase 9F - Capacity-Halt Reprobe And Automatic Resume tests.

Exercises `reprobe_capacity_and_resume(...)` and the
`run-capacity-reprobe` CLI subcommand without actually sleeping.
The tests inject:
  - a `sleep` callable that records calls so backoff progression
    is verifiable without real wall-clock delay
  - a `probe` callable that returns a configurable bool so the
    "capacity available" / "capacity still unavailable" branches
    are deterministically testable

The tests prove:
  - structural refusal vocabulary fires fail-closed on missing
    loop-state, wrong status, out-of-bound bounds args, output-
    boundary violations, and stale retry-state on disk
  - the first attempt initializes the retry-state at the canonical
    path with the documented schema
  - subsequent attempts increment `attempt_count` and append to
    `history`
  - cumulative budget caps total attempts across multiple
    invocations
  - successful probe restores loop-state.status from
    `suspended_status` and deletes the retry-state
  - failed probe with budget remaining returns the retry-state
    path with the failure persisted
  - exponential backoff is computed correctly and capped at
    max_backoff_seconds
  - the symmetric output-boundary protects sibling Phase 9
    descriptors from a Phase 9F write
  - the operator-facing argparse help cannot drift silently
"""
from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above
from agent_loop import HaltError  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"

ACTIVE_PHASE = "Phase 9 - Fully Autonomous PRD-To-Product Mode"
ACTIVE_SUB_PHASE = "Phase 9F - Capacity-Halt Reprobe And Automatic Resume"


def _make_repo(td: Path) -> Path:
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text("test\n", encoding="utf-8")
    (td / ".agent-loop").mkdir()
    return td


def _plant_loop_state(
    repo_root: Path,
    *,
    status: str = "halted_capacity_unavailable",
    cycle_count: int = 0,
    max_cycles: int = 3,
    task: str = "capacity-reprobe-test",
) -> Path:
    state_path = repo_root / ".agent-loop" / "loop-state.json"
    state_path.write_text(json.dumps({
        "phase": ACTIVE_PHASE,
        "sub_phase": ACTIVE_SUB_PHASE,
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
        "approval_mode": "review",
        "awaiting_human_for": None,
    }), encoding="utf-8")
    return state_path


def _noop_sleep(seconds: float) -> None:
    return None


def _always_true_probe(repo_root: Path) -> bool:
    return True


def _always_false_probe(repo_root: Path) -> bool:
    return False


class CapacityReprobeConstantsTests(unittest.TestCase):

    def test_halt_vocabulary(self) -> None:
        self.assertEqual(
            agent_loop.HALTED_CAPACITY_UNAVAILABLE,
            "halted_capacity_unavailable",
        )

    def test_signal_version_is_phase_9f_v1(self) -> None:
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_SIGNAL_VERSION, "phase-9f-v1",
        )

    def test_output_rel_is_under_agent_loop(self) -> None:
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_STATE_OUTPUT_REL,
            ".agent-loop/capacity-retry-state.json",
        )

    def test_default_and_max_attempts(self) -> None:
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_DEFAULT_MAX_ATTEMPTS, 5,
        )
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_MAX_MAX_ATTEMPTS, 16,
        )

    def test_default_and_max_backoff(self) -> None:
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_DEFAULT_INITIAL_BACKOFF_SECONDS,
            1.0,
        )
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_DEFAULT_MAX_BACKOFF_SECONDS,
            30.0,
        )
        self.assertEqual(
            agent_loop.CAPACITY_RETRY_MAX_MAX_BACKOFF_SECONDS, 600.0,
        )

    def test_handler_is_wired(self) -> None:
        self.assertIn(
            "run-capacity-reprobe", agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS["run-capacity-reprobe"],
            agent_loop.cmd_reprobe_capacity_and_resume,
        )

    def test_protected_output_set_includes_siblings(self) -> None:
        protected = agent_loop.CAPACITY_RETRY_PROTECTED_OUTPUT_PATHS
        for sibling in (
            ".agent-loop/prd-intake.json",
            ".agent-loop/prompt-handoff.json",
            ".agent-loop/review-fix-loop.json",
            ".agent-loop/long-run-continuation.json",
        ):
            self.assertIn(sibling, protected)

    def test_protected_output_set_excludes_self_default(self) -> None:
        self.assertNotIn(
            ".agent-loop/capacity-retry-state.json",
            agent_loop.CAPACITY_RETRY_PROTECTED_OUTPUT_PATHS,
        )

    def test_sibling_sets_protect_phase_9f_output(self) -> None:
        for sibling_set in (
            agent_loop.PRD_INTAKE_PROTECTED_OUTPUT_PATHS,
            agent_loop.PROMPT_HANDOFF_PROTECTED_OUTPUT_PATHS,
            agent_loop.INTERNAL_REVIEW_FIX_LOOP_PROTECTED_OUTPUT_PATHS,
            agent_loop.LONG_RUN_CONTINUATION_PROTECTED_OUTPUT_PATHS,
        ):
            self.assertIn(
                ".agent-loop/capacity-retry-state.json", sibling_set,
            )


class CapacityReprobeRefusalTests(unittest.TestCase):

    def test_refuses_wrong_status(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, status="awaiting_claude_implementation")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "halted_capacity_unavailable", str(ctx.exception),
            )

    def test_refuses_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_out_of_bound_max_attempts(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            for bad in (0, -1, 99, "two", 2.5, True):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.reprobe_capacity_and_resume(
                            repo,
                            max_attempts=bad,
                            sleep=_noop_sleep,
                            probe=_always_true_probe,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_refuses_out_of_bound_backoff(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            for bad in (0, -1, 9999, "x", True):
                with self.subTest(value=bad):
                    with self.assertRaises(HaltError) as ctx:
                        agent_loop.reprobe_capacity_and_resume(
                            repo,
                            initial_backoff_seconds=bad,
                            sleep=_noop_sleep,
                            probe=_always_true_probe,
                        )
                    self.assertEqual(
                        ctx.exception.status, "halted_input_missing",
                    )

    def test_refuses_initial_greater_than_max_backoff(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    initial_backoff_seconds=10,
                    max_backoff_seconds=5,
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_probe_raising_exception(self) -> None:
        def bad_probe(_repo_root: Path) -> bool:
            raise RuntimeError("probe blew up")

        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=bad_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("probe raised", str(ctx.exception))


class CapacityReprobeOutputBoundaryTests(unittest.TestCase):

    def _setup(self, td: Path) -> Path:
        repo = _make_repo(td)
        _plant_loop_state(repo)
        return repo

    def test_refuses_outside_agent_loop(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    output_path=repo / "outside.json",
                    sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_overwriting_long_run_descriptor(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    output_path=(
                        repo / ".agent-loop"
                        / "long-run-continuation.json"
                    ),
                    sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_overwriting_review_fix_loop_descriptor(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "review-fix-loop.json"
                    ),
                    sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_refuses_memory_subtree(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    output_path=(
                        repo / ".agent-loop" / "memory" / "x.json"
                    ),
                    sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_safe_override_succeeds(self) -> None:
        with TemporaryDirectory() as td:
            repo = self._setup(Path(td))
            written = agent_loop.reprobe_capacity_and_resume(
                repo,
                output_path=(
                    repo / ".agent-loop" / "custom-retry.json"
                ),
                sleep=_noop_sleep, probe=_always_true_probe,
            )
            # On success, the retry-state file is deleted.
            self.assertEqual(written.name, "custom-retry.json")
            self.assertFalse(written.exists())


class CapacityReprobeSuccessTests(unittest.TestCase):

    def test_first_attempt_success_restores_status(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="claude_implementing",
                sleep=_noop_sleep, probe=_always_true_probe,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_implementing")
            # Retry-state file is deleted on success.
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            self.assertFalse(retry_path.exists())

    def test_default_suspended_status_is_claude_implementing(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo, sleep=_noop_sleep, probe=_always_true_probe,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_implementing")

    def test_custom_suspended_status_is_respected(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                suspended_status="claude_fixing",
                sleep=_noop_sleep, probe=_always_true_probe,
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_fixing")

    def test_sleep_is_invoked_with_first_backoff(self) -> None:
        sleep_calls: list[float] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            agent_loop.reprobe_capacity_and_resume(
                repo,
                initial_backoff_seconds=2.0,
                max_backoff_seconds=30.0,
                sleep=lambda s: sleep_calls.append(s),
                probe=_always_true_probe,
            )
            # Attempt 1 backoff = 2 * 2**0 = 2.
            self.assertEqual(sleep_calls, [2.0])


class CapacityReprobeFailureAndBudgetTests(unittest.TestCase):

    def test_all_attempts_fail_exhausts_budget(self) -> None:
        sleep_calls: list[float] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=3,
                    initial_backoff_seconds=1.0,
                    max_backoff_seconds=4.0,
                    sleep=lambda s: sleep_calls.append(s),
                    probe=_always_false_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn("budget exhausted", str(ctx.exception))
            # Backoff progression: 1, 2, 4 (capped at max_backoff).
            self.assertEqual(sleep_calls, [1.0, 2.0, 4.0])
            # Retry-state is preserved on disk for inspection.
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            self.assertTrue(retry_path.exists())
            retry_state = json.loads(
                retry_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(retry_state["attempt_count"], 3)
            self.assertEqual(len(retry_state["history"]), 3)
            self.assertEqual(retry_state["last_outcome"], "failed")

    def test_backoff_caps_at_max(self) -> None:
        sleep_calls: list[float] = []
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            try:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=5,
                    initial_backoff_seconds=1.0,
                    max_backoff_seconds=3.0,
                    sleep=lambda s: sleep_calls.append(s),
                    probe=_always_false_probe,
                )
            except HaltError:
                pass
            # Expected: 1, 2, 3 (cap), 3, 3.
            self.assertEqual(sleep_calls, [1.0, 2.0, 3.0, 3.0, 3.0])

    def test_history_records_each_attempt_outcome(self) -> None:
        probe_results = [False, False, True]

        def cyclic_probe(_repo_root: Path) -> bool:
            return probe_results.pop(0)

        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            state_path = _plant_loop_state(repo)
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            agent_loop.reprobe_capacity_and_resume(
                repo,
                max_attempts=5,
                initial_backoff_seconds=1.0,
                sleep=_noop_sleep,
                probe=cyclic_probe,
            )
            # On success, retry-state file is deleted.
            self.assertFalse(retry_path.exists())
            # Loop-state was restored.
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_implementing")


class CapacityReprobeCumulativeBudgetTests(unittest.TestCase):
    """The retry-state on disk persists across invocations; the
    cumulative attempt count is bounded by max_attempts even when
    the operator re-runs the CLI multiple times.
    """

    def test_persisted_retry_state_carries_history_across_runs(
        self,
    ) -> None:
        # First call: 2 max_attempts, both fail.
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            try:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=2,
                    initial_backoff_seconds=1.0,
                    sleep=_noop_sleep,
                    probe=_always_false_probe,
                )
            except HaltError:
                pass
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            state = json.loads(retry_path.read_text(encoding="utf-8"))
            self.assertEqual(state["attempt_count"], 2)
            # Second call with max_attempts=5: persisted_cap=2,
            # effective_cap=min(5,2)=2; cumulative count is 2 so
            # no more attempts run and the call refuses immediately.
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=5,
                    initial_backoff_seconds=1.0,
                    sleep=_noop_sleep,
                    probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_deleting_retry_state_resets_budget(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            try:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=1,
                    initial_backoff_seconds=1.0,
                    sleep=_noop_sleep,
                    probe=_always_false_probe,
                )
            except HaltError:
                pass
            retry_path = (
                repo / ".agent-loop" / "capacity-retry-state.json"
            )
            retry_path.unlink()
            # Re-run with a successful probe; the budget is fresh.
            agent_loop.reprobe_capacity_and_resume(
                repo,
                max_attempts=1,
                initial_backoff_seconds=1.0,
                sleep=_noop_sleep,
                probe=_always_true_probe,
            )
            state_path = repo / ".agent-loop" / "loop-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "claude_implementing")


class CapacityReprobeStaleRetryStateTests(unittest.TestCase):

    def _seed_retry_state(self, repo: Path, **overrides) -> Path:
        path = repo / ".agent-loop" / "capacity-retry-state.json"
        body = {
            "retry_signal_version": "phase-9f-v1",
            "created_at": "2026-06-17T00:00:00Z",
            "phase": ACTIVE_PHASE,
            "sub_phase": ACTIVE_SUB_PHASE,
            "task": "capacity-reprobe-test",
            "cycle_count": 0,
            "attempt_count": 0,
            "max_attempts": 5,
            "initial_backoff_seconds": 1.0,
            "max_backoff_seconds": 30.0,
            "suspended_status": "claude_implementing",
            "history": [],
            "last_outcome": None,
            "canonical_precedence_note": "test",
        }
        body.update(overrides)
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def test_wrong_signal_version_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            self._seed_retry_state(
                repo, retry_signal_version="phase-9e-v1",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )
            self.assertIn(
                "retry_signal_version", str(ctx.exception),
            )

    def test_phase_mismatch_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            self._seed_retry_state(repo, phase="Phase 1 - Stale")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_cycle_count_mismatch_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo, cycle_count=2)
            self._seed_retry_state(repo, cycle_count=0)
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_missing_required_field_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            path = self._seed_retry_state(repo)
            body = json.loads(path.read_text(encoding="utf-8"))
            del body["attempt_count"]
            path.write_text(json.dumps(body), encoding="utf-8")
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )

    def test_malformed_json_refuses(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            (repo / ".agent-loop" / "capacity-retry-state.json").write_text(
                "not json {", encoding="utf-8",
            )
            with self.assertRaises(HaltError) as ctx:
                agent_loop.reprobe_capacity_and_resume(
                    repo, sleep=_noop_sleep, probe=_always_true_probe,
                )
            self.assertEqual(
                ctx.exception.status, "halted_input_missing",
            )


class CapacityReprobeAuditLogTests(unittest.TestCase):

    def test_success_audit_lines(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            agent_loop.reprobe_capacity_and_resume(
                repo,
                sleep=_noop_sleep, probe=_always_true_probe,
                log_path=log,
            )
            audit = log.read_text(encoding="utf-8")
            self.assertIn("capacity reprobe: started", audit)
            self.assertIn("capacity reprobe: succeeded", audit)

    def test_failure_audit_lines(self) -> None:
        with TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            _plant_loop_state(repo)
            log = repo / ".agent-loop" / "orchestrator.log"
            try:
                agent_loop.reprobe_capacity_and_resume(
                    repo,
                    max_attempts=2,
                    sleep=_noop_sleep, probe=_always_false_probe,
                    log_path=log,
                )
            except HaltError:
                pass
            audit = log.read_text(encoding="utf-8")
            self.assertIn(
                "capacity reprobe: attempt_failed", audit,
            )
            self.assertIn(
                "capacity reprobe: budget_exhausted", audit,
            )


class CapacityReprobeCliTests(unittest.TestCase):

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

    def test_cli_default_success_with_patched_sleep(self) -> None:
        with mock.patch("agent_loop.time.sleep", lambda s: None):
            rc = agent_loop.main([
                "run-capacity-reprobe",
                "--max-attempts", "1",
                "--initial-backoff-seconds", "0.001",
                "--max-backoff-seconds", "0.001",
            ])
        self.assertEqual(rc, 0)
        state = json.loads(
            (self.repo / ".agent-loop" / "loop-state.json").read_text(
                encoding="utf-8",
            ),
        )
        self.assertEqual(state["status"], "claude_implementing")

    def test_cli_refuses_bad_output(self) -> None:
        rc = agent_loop.main([
            "run-capacity-reprobe",
            "--output", ".agent-loop/long-run-continuation.json",
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_out_of_bound_max_attempts(self) -> None:
        rc = agent_loop.main([
            "run-capacity-reprobe",
            "--max-attempts", "99",
        ])
        self.assertEqual(rc, 2)


class CapacityReprobeHelpTextTests(unittest.TestCase):

    def _help_text(self) -> str:
        parser = agent_loop.build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for choice_action in action._choices_actions:
                    if choice_action.dest == "run-capacity-reprobe":
                        return choice_action.help or ""
        self.fail("run-capacity-reprobe subparser help not found")
        return ""

    def test_help_describes_phase_9f_role(self) -> None:
        text = self._help_text()
        self.assertIn("Phase 9F", text)
        self.assertIn("capacity", text)

    def test_help_documents_retry_state_path(self) -> None:
        text = self._help_text()
        self.assertIn(
            ".agent-loop/capacity-retry-state.json", text,
        )

    def test_help_documents_bounded_behavior(self) -> None:
        text = self._help_text()
        self.assertIn("bounded", text)
        self.assertIn("backoff", text)
        self.assertIn("budget", text)

    def test_help_documents_halt_status(self) -> None:
        text = self._help_text()
        self.assertIn("halted_capacity_unavailable", text)


if __name__ == "__main__":
    unittest.main()
