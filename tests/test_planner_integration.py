"""Focused tests for the Phase 4D planner-orchestrator integration in
`scripts/agent_loop.py`.

Scope:
- After a terminal `APPROVED_FOR_HUMAN_REVIEW` verdict is persisted, the
  orchestrator invokes the standalone planner exactly once through
  `_invoke_post_approval_planner` (called from `_handle_verdict_loop`).
- A normal planner refusal return code must NOT convert the
  already-approved orchestrator result into a halt: `_handle_verdict_loop`
  still returns 0.
- An unexpected exception raised by planner code must be caught and
  logged as a `note:` line to `.agent-loop/orchestrator.log`; it must
  NOT crash or halt the already-approved cycle: `_handle_verdict_loop`
  still returns 0.
- The integration path performs NO activation-owned writes: TASK.md,
  .agent-loop/current-task.md, .agent-loop/current-phase.md,
  .agent-loop/phase-plan.md stay byte-identical, and loop-state.json's
  `phase` / `sub_phase` / `task` are unchanged (the orchestrator's own
  terminal `status` update is expected and is not an activation write).

The tests drive `_handle_verdict_loop` directly with the
`APPROVED_FOR_HUMAN_REVIEW` verdict, which is the seam that persists the
terminal status, fires the post-approval planner hook, and returns the
orchestrator exit code. The synthetic repository is built by reusing
`test_planner._Repo`, whose default state is a planner-success setup
(fresh evidence, a dispatchable active sub-phase, closed prior
sub-phases for dependency resolution).
"""

from __future__ import annotations

import json
import os
import sys
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))

import agent_loop  # noqa: E402 - sys.path is set above
import test_planner  # noqa: E402 - reuse the planner-success _Repo builder


# Activation-owned files the integration path must never write. loop-state.json
# is handled separately because the orchestrator legitimately updates its
# `status` field on a terminal verdict; the integration must not change its
# `phase` / `sub_phase` / `task` (which would be an activation write).
_ACTIVATION_OWNED_MARKDOWN = (
    "TASK.md",
    ".agent-loop/current-task.md",
    ".agent-loop/current-phase.md",
    ".agent-loop/phase-plan.md",
)


class _IntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = test_planner._Repo(Path(self._tmp.name))
        self.state_path = self.repo.root / ".agent-loop" / "loop-state.json"
        self.log_path = self.repo.root / ".agent-loop" / "orchestrator.log"

    def _data(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _approve(self) -> int:
        """Drive the APPROVED_FOR_HUMAN_REVIEW branch of the verdict loop,
        which persists the terminal status and fires the post-approval
        planner hook. Returns the orchestrator exit code."""
        return agent_loop._handle_verdict_loop(
            self.state_path,
            self._data(),
            "APPROVED_FOR_HUMAN_REVIEW",
            self.repo.root,
            self.log_path,
        )

    def _orchestrator_log(self) -> str:
        return self.log_path.read_text(encoding="utf-8") if self.log_path.is_file() else ""


class SuccessfulIntegrationTests(_IntegrationTestCase):

    def test_returns_zero_and_logs_planner_invocation(self) -> None:
        rc = self._approve()
        self.assertEqual(rc, 0)
        log = self._orchestrator_log()
        self.assertIn("post-approval planner invoked", log)
        self.assertIn("planner_exit_code=0", log)

    def test_real_planner_writes_proposed_phase_within_boundary(self) -> None:
        rc = self._approve()
        self.assertEqual(rc, 0)
        # The real planner (active sub-phase dispatches to a concrete
        # proposal) writes its proposal artifact.
        self.assertTrue(
            (self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists(),
            "post-approval planner should refresh proposed-phase.md on success",
        )

    def test_terminal_status_persisted(self) -> None:
        self._approve()
        state = self._data()
        self.assertEqual(state["status"], "phase_complete_awaiting_human_approval")
        self.assertEqual(state["last_verdict"], "APPROVED_FOR_HUMAN_REVIEW")


class RefusalIntegrationTests(_IntegrationTestCase):

    def test_planner_refusal_does_not_halt_orchestrator(self) -> None:
        # Deterministically simulate a planner refusal return code.
        with mock.patch.object(agent_loop, "run_planner", return_value=2):
            rc = self._approve()
        self.assertEqual(rc, 0, "a planner refusal must not change the terminal 0")
        log = self._orchestrator_log()
        self.assertIn("post-approval planner invoked", log)
        self.assertIn("planner_exit_code=2", log)

    def test_real_stale_evidence_refusal_does_not_halt(self) -> None:
        # Make evidence stale relative to the summary/review mtime so the
        # REAL planner refuses with stale_evidence; the orchestrator must
        # still return 0.
        self.repo.with_evidence_age(seconds_after_summary=-300)
        rc = self._approve()
        self.assertEqual(rc, 0)
        # The planner refused, so no proposal was written, but the
        # orchestrator outcome is unchanged.
        log = self._orchestrator_log()
        self.assertIn("post-approval planner invoked", log)
        self.assertIn("planner_exit_code=2", log)


class ExceptionIntegrationTests(_IntegrationTestCase):

    def test_unexpected_planner_exception_is_contained(self) -> None:
        def _boom(_repo_root):
            raise RuntimeError("simulated unexpected planner crash")

        with mock.patch.object(agent_loop, "run_planner", side_effect=_boom):
            rc = self._approve()
        self.assertEqual(
            rc, 0,
            "an unexpected planner exception must not halt the approved cycle",
        )
        log = self._orchestrator_log()
        self.assertIn("post-approval planner raised an unexpected exception", log)
        self.assertIn("RuntimeError", log)
        self.assertIn("simulated unexpected planner crash", log)

    def test_exception_path_still_persists_terminal_status(self) -> None:
        def _boom(_repo_root):
            raise ValueError("kaboom")

        with mock.patch.object(agent_loop, "run_planner", side_effect=_boom):
            self._approve()
        state = self._data()
        self.assertEqual(state["status"], "phase_complete_awaiting_human_approval")
        self.assertEqual(state["last_verdict"], "APPROVED_FOR_HUMAN_REVIEW")


class NoActivationWriteTests(_IntegrationTestCase):

    def _snapshot_markdown(self) -> dict:
        # Record bytes for files that exist and None for files that do
        # not. A correct integration leaves existing files byte-identical
        # AND never creates a missing activation-owned file, so comparing
        # the before/after maps (including the None entries) proves both.
        snap: dict = {}
        for rel in _ACTIVATION_OWNED_MARKDOWN:
            p = self.repo.root / rel
            snap[rel] = p.read_bytes() if p.is_file() else None
        return snap

    def test_integration_performs_no_activation_writes_on_success(self) -> None:
        before_md = self._snapshot_markdown()
        before_state = self._data()
        rc = self._approve()
        self.assertEqual(rc, 0)
        after_md = self._snapshot_markdown()
        for rel in _ACTIVATION_OWNED_MARKDOWN:
            self.assertEqual(
                before_md[rel], after_md[rel],
                f"integration path must not write activation-owned file {rel}",
            )
        # loop-state.json: phase / sub_phase / task must be unchanged by
        # the integration (those are activation writes); only the
        # orchestrator's own runtime `status` / verdict fields move.
        after_state = self._data()
        for field in ("phase", "sub_phase", "task"):
            self.assertEqual(
                before_state[field], after_state[field],
                f"integration path must not perform the activation write to "
                f"loop-state.json field {field!r}",
            )

    def test_integration_performs_no_activation_writes_on_refusal(self) -> None:
        before_md = self._snapshot_markdown()
        before_state = self._data()
        with mock.patch.object(agent_loop, "run_planner", return_value=2):
            rc = self._approve()
        self.assertEqual(rc, 0)
        after_md = self._snapshot_markdown()
        for rel in _ACTIVATION_OWNED_MARKDOWN:
            self.assertEqual(before_md[rel], after_md[rel])
        after_state = self._data()
        for field in ("phase", "sub_phase", "task"):
            self.assertEqual(before_state[field], after_state[field])


if __name__ == "__main__":
    unittest.main(verbosity=2)
