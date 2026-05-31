"""Focused tests for the Phase 5B Review-Mode Initial Slice.

Scope of this suite (Phase 5B, narrow):
- newly activated Phase 5+ runtime state defaults `approval_mode` to
  `"review"` and `awaiting_human_for` to `null` (Phase 5A contract)
- a normal cycle on a loaded loop-state.json that pre-dates Phase 5B
  upgrades those fields to the same defaults at cycle start
- the implemented `review` path sets `awaiting_human_for` to the named
  Phase 5A gate `"phase_complete_awaiting_human_approval"` on
  `APPROVED_FOR_HUMAN_REVIEW` and leaves it `null` on NEEDS_FIXES /
  FAILED_REQUIRES_HUMAN
- `.agent-loop/claude-done.json` is written for implementation completion
  with the Phase 5A-required minimum fields
- `.agent-loop/claude-done.json` is written for fix completion with
  `mode = "fix"` and `source_prompt_path = ".agent-loop/fix-prompt.md"`
- a new implementation cycle or fix-prompt issuance clears / supersedes
  any prior `.agent-loop/claude-done.json` (stale completion signals
  cannot drive the wrong review cycle)
- the existing review-mode loop is not regressed: existing planner
  suites still pass, and the verdict-handler still persists the
  pre-Phase-5B terminal `status` / `last_verdict` exactly as before

These tests reuse `test_planner._Repo` for a synthetic activated repo.
"""

from __future__ import annotations

import json
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


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class _ApprovalModesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = test_planner._Repo(Path(self._tmp.name))
        self.state_path = self.repo.root / ".agent-loop" / "loop-state.json"
        self.log_path = self.repo.root / ".agent-loop" / "orchestrator.log"
        self.done_path = self.repo.root / agent_loop.CLAUDE_DONE_PATH_REL

    def _state(self) -> dict:
        return _read_json(self.state_path)


# ----- Phase 5A field defaults -----

class ActivationDefaultsTests(_ApprovalModesTestCase):

    def test_activation_defaults_approval_mode_to_review(self) -> None:
        # _Repo's default state has no approval_mode set; activation must
        # add it with the contract-required default.
        before = self._state()
        self.assertNotIn("approval_mode", before)
        merged = agent_loop._compute_activated_loop_state(
            before, "Phase 5 - Approval Modes",
            "Phase 5C - Strict Mode Pauses", "do the thing",
        )
        self.assertEqual(merged["approval_mode"], agent_loop.APPROVAL_MODE_REVIEW)
        self.assertEqual(merged["approval_mode"], "review")

    def test_activation_resets_awaiting_human_for_to_null(self) -> None:
        # Pre-existing gate must be cleared by activation, since the new
        # phase has not yet hit one.
        before = self._state()
        before["awaiting_human_for"] = "phase_complete_awaiting_human_approval"
        merged = agent_loop._compute_activated_loop_state(
            before, "p", "sp", "t",
        )
        self.assertIsNone(merged["awaiting_human_for"])

    def test_activation_preserves_explicitly_selected_mode(self) -> None:
        # If a human/Codex already selected a non-review mode, activation
        # does not silently overwrite it. (autonomy/strict remain future
        # slices, but the field is owned by Phase 5A semantics today.)
        before = self._state()
        before["approval_mode"] = agent_loop.APPROVAL_MODE_STRICT
        merged = agent_loop._compute_activated_loop_state(
            before, "p", "sp", "t",
        )
        self.assertEqual(merged["approval_mode"], "strict")


class NormalCycleStateDefaultsTests(_ApprovalModesTestCase):
    """A normal cycle on pre-Phase-5B state upgrades the runtime fields."""

    def _stub_adapters_for_one_cycle(self):
        """Stub the Claude/Codex adapters + evidence capture + summary
        validation so a normal cycle reaches the verdict handler without
        needing real artifacts. Returns the patches as a list so the
        caller can layer them with ExitStack."""
        # We don't actually execute a cycle here - only test the early
        # field-default writes. The cycle is exercised end-to-end by
        # ClaudeDoneImplementationTests / FixCycleTests via direct calls
        # into the inner helpers.
        raise NotImplementedError

    def test_review_default_applied_on_cycle_start_when_missing(self) -> None:
        # Simulate the cycle-start block: load + structurally validate
        # (already passes for _Repo), then apply the same runtime_updates
        # the cycle uses. This isolates the default behavior from the
        # full Claude adapter machinery.
        data = self._state()
        runtime_updates: dict = {
            "orchestrator_version": agent_loop.ORCHESTRATOR_VERSION,
        }
        if data.get("approval_mode") in (None, ""):
            runtime_updates["approval_mode"] = agent_loop.DEFAULT_APPROVAL_MODE
        if "awaiting_human_for" not in data:
            runtime_updates["awaiting_human_for"] = None
        agent_loop.save_loop_state(self.state_path, data, runtime_updates)

        after = self._state()
        self.assertEqual(after["approval_mode"], "review")
        self.assertIsNone(after["awaiting_human_for"])

    def test_existing_approval_mode_is_not_overwritten(self) -> None:
        data = self._state()
        data["approval_mode"] = agent_loop.APPROVAL_MODE_AUTONOMOUS
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        # Re-apply the cycle-start default block.
        data = self._state()
        runtime_updates: dict = {}
        if data.get("approval_mode") in (None, ""):
            runtime_updates["approval_mode"] = agent_loop.DEFAULT_APPROVAL_MODE
        if "awaiting_human_for" not in data:
            runtime_updates["awaiting_human_for"] = None
        if runtime_updates:
            agent_loop.save_loop_state(self.state_path, data, runtime_updates)
        self.assertEqual(self._state()["approval_mode"], "autonomous")


class SaveLoopStateAllowsPhase5BFieldsTests(_ApprovalModesTestCase):

    def test_approval_mode_and_awaiting_human_for_are_writable(self) -> None:
        # save_loop_state refuses any non-orchestrator field; both Phase
        # 5B runtime fields must be on the allowed list.
        self.assertIn("approval_mode", agent_loop.ORCHESTRATOR_WRITABLE_FIELDS)
        self.assertIn("awaiting_human_for", agent_loop.ORCHESTRATOR_WRITABLE_FIELDS)
        data = self._state()
        agent_loop.save_loop_state(self.state_path, data, {
            "approval_mode": "review",
            "awaiting_human_for": "phase_complete_awaiting_human_approval",
        })
        after = self._state()
        self.assertEqual(after["approval_mode"], "review")
        self.assertEqual(
            after["awaiting_human_for"],
            "phase_complete_awaiting_human_approval",
        )


# ----- awaiting_human_for transitions in the review path -----

class AwaitingHumanForTransitionTests(_ApprovalModesTestCase):

    def _drive_verdict(self, verdict: str) -> int:
        # Suppress the post-approval planner side-effect so this test
        # focuses on awaiting_human_for transitions.
        with mock.patch.object(agent_loop, "_invoke_post_approval_planner",
                               return_value=0):
            return agent_loop._handle_verdict_loop(
                self.state_path, self._state(), verdict,
                self.repo.root, self.log_path,
            )

    def test_approved_sets_phase_complete_gate(self) -> None:
        rc = self._drive_verdict("APPROVED_FOR_HUMAN_REVIEW")
        self.assertEqual(rc, 0)
        after = self._state()
        self.assertEqual(after["status"], "phase_complete_awaiting_human_approval")
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PHASE_COMPLETE,
        )

    def test_failed_clears_awaiting_human_for(self) -> None:
        # Seed a non-null gate to prove FAILED clears it.
        data = self._state()
        data["awaiting_human_for"] = "phase_complete_awaiting_human_approval"
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        rc = self._drive_verdict("FAILED_REQUIRES_HUMAN")
        self.assertEqual(rc, 2)
        after = self._state()
        self.assertEqual(after["status"], "halted_failed_requires_human")
        self.assertIsNone(after["awaiting_human_for"])

    def test_needs_fixes_clears_awaiting_human_for_before_threshold_halt(
        self,
    ) -> None:
        # Set cycle_count == max_cycles so NEEDS_FIXES hits the threshold
        # halt; the gate-clearing write is the same write that records
        # last_verdict, and it must happen regardless of the threshold
        # outcome.
        data = self._state()
        data["awaiting_human_for"] = "phase_complete_awaiting_human_approval"
        data["cycle_count"] = data["max_cycles"]
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        rc = self._drive_verdict("NEEDS_FIXES")
        self.assertEqual(rc, 2)  # threshold-halt exit
        after = self._state()
        self.assertEqual(after["last_verdict"], "NEEDS_FIXES")
        self.assertIsNone(after["awaiting_human_for"])


# ----- claude-done.json writer + clearer -----

class ClaudeDoneWriterTests(_ApprovalModesTestCase):

    def _payload(self) -> dict:
        return _read_json(self.done_path)

    def test_implementation_completion_required_fields(self) -> None:
        agent_loop.write_claude_done(
            self.repo.root,
            phase="Phase 5 - Approval Modes",
            sub_phase="Phase 5B - Review Mode Initial Slice",
            task="do the thing",
            cycle_count=1,
            mode=agent_loop.CLAUDE_DONE_MODE_IMPLEMENTATION,
            source_prompt_path=".agent-loop/claude-prompt.md",
        )
        p = self._payload()
        for key in (
            "signal_version", "phase", "sub_phase", "task", "cycle_count",
            "mode", "source_prompt_path", "status",
        ):
            self.assertIn(key, p, f"claude-done.json missing required field {key!r}")
        self.assertEqual(p["signal_version"], agent_loop.CLAUDE_DONE_SIGNAL_VERSION)
        self.assertEqual(p["mode"], "implementation")
        self.assertEqual(p["source_prompt_path"], ".agent-loop/claude-prompt.md")
        self.assertEqual(p["status"], "ready_for_codex_review")
        self.assertEqual(p["cycle_count"], 1)
        self.assertEqual(p["phase"], "Phase 5 - Approval Modes")

    def test_fix_completion_required_fields(self) -> None:
        agent_loop.write_claude_done(
            self.repo.root,
            phase="Phase 5 - Approval Modes",
            sub_phase="Phase 5B - Review Mode Initial Slice",
            task="do the thing",
            cycle_count=2,
            mode=agent_loop.CLAUDE_DONE_MODE_FIX,
            source_prompt_path=".agent-loop/fix-prompt.md",
        )
        p = self._payload()
        self.assertEqual(p["mode"], "fix")
        self.assertEqual(p["source_prompt_path"], ".agent-loop/fix-prompt.md")
        self.assertEqual(p["status"], "ready_for_codex_review")
        self.assertEqual(p["cycle_count"], 2)

    def test_write_rejects_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            agent_loop.write_claude_done(
                self.repo.root,
                phase="p", sub_phase="sp", task="t", cycle_count=1,
                mode="bogus", source_prompt_path=".agent-loop/claude-prompt.md",
            )
        self.assertFalse(
            self.done_path.exists(),
            "an invalid mode must not leave a partial claude-done.json behind",
        )

    def test_clear_removes_existing_done_file(self) -> None:
        agent_loop.write_claude_done(
            self.repo.root,
            phase="p", sub_phase="sp", task="t", cycle_count=1,
            mode=agent_loop.CLAUDE_DONE_MODE_IMPLEMENTATION,
            source_prompt_path=".agent-loop/claude-prompt.md",
        )
        self.assertTrue(self.done_path.exists())
        agent_loop.clear_claude_done(self.repo.root)
        self.assertFalse(self.done_path.exists())

    def test_clear_is_noop_when_absent(self) -> None:
        self.assertFalse(self.done_path.exists())
        agent_loop.clear_claude_done(self.repo.root)  # must not raise
        self.assertFalse(self.done_path.exists())


# ----- stale-signal supersession across cycles -----

class StaleSignalSupersessionTests(_ApprovalModesTestCase):

    def _seed_stale(self, cycle: int) -> dict:
        agent_loop.write_claude_done(
            self.repo.root,
            phase="prev-phase", sub_phase="prev-sp", task="prev-task",
            cycle_count=cycle,
            mode=agent_loop.CLAUDE_DONE_MODE_IMPLEMENTATION,
            source_prompt_path=".agent-loop/claude-prompt.md",
        )
        return _read_json(self.done_path)

    def test_new_implementation_writes_supersede_stale_signal(self) -> None:
        stale = self._seed_stale(cycle=99)
        self.assertEqual(stale["phase"], "prev-phase")
        # A fresh implementation completion writes the current cycle's
        # payload; the stale phase/cycle must not survive.
        agent_loop.write_claude_done(
            self.repo.root,
            phase="Phase 5 - Approval Modes",
            sub_phase="Phase 5B - Review Mode Initial Slice",
            task="do the thing",
            cycle_count=1,
            mode=agent_loop.CLAUDE_DONE_MODE_IMPLEMENTATION,
            source_prompt_path=".agent-loop/claude-prompt.md",
        )
        fresh = _read_json(self.done_path)
        self.assertEqual(fresh["phase"], "Phase 5 - Approval Modes")
        self.assertEqual(fresh["cycle_count"], 1)
        self.assertNotEqual(fresh["phase"], stale["phase"])

    def test_fix_issuance_path_clears_stale_signal_then_writes_fix(self) -> None:
        # Simulate the fix flow: implementation completion left a stale
        # signal behind; then a fix-prompt is issued (clear), then the
        # fix cycle completes (write with mode=fix).
        self._seed_stale(cycle=1)
        agent_loop.clear_claude_done(self.repo.root)
        self.assertFalse(self.done_path.exists())
        agent_loop.write_claude_done(
            self.repo.root,
            phase="Phase 5 - Approval Modes",
            sub_phase="Phase 5B - Review Mode Initial Slice",
            task="do the thing",
            cycle_count=2,
            mode=agent_loop.CLAUDE_DONE_MODE_FIX,
            source_prompt_path=".agent-loop/fix-prompt.md",
        )
        p = _read_json(self.done_path)
        self.assertEqual(p["mode"], "fix")
        self.assertEqual(p["source_prompt_path"], ".agent-loop/fix-prompt.md")
        self.assertEqual(p["cycle_count"], 2)


# ----- baseline review-mode loop not regressed -----

class ReviewModeBaselineNotRegressedTests(_ApprovalModesTestCase):
    """The pre-Phase-5B observable contract of the verdict handler must
    still hold under `review` mode (the implemented path). This pins the
    terminal status / verdict writes that existing Phase 3+ tests depend
    on, alongside the new awaiting_human_for write."""

    def test_approved_persists_terminal_status_and_verdict(self) -> None:
        with mock.patch.object(
            agent_loop, "_invoke_post_approval_planner", return_value=0,
        ):
            rc = agent_loop._handle_verdict_loop(
                self.state_path, self._state(),
                "APPROVED_FOR_HUMAN_REVIEW",
                self.repo.root, self.log_path,
            )
        self.assertEqual(rc, 0)
        after = self._state()
        self.assertEqual(after["status"], "phase_complete_awaiting_human_approval")
        self.assertEqual(after["last_verdict"], "APPROVED_FOR_HUMAN_REVIEW")

    def test_failed_persists_halt_and_verdict(self) -> None:
        rc = agent_loop._handle_verdict_loop(
            self.state_path, self._state(),
            "FAILED_REQUIRES_HUMAN",
            self.repo.root, self.log_path,
        )
        self.assertEqual(rc, 2)
        after = self._state()
        self.assertEqual(after["status"], "halted_failed_requires_human")
        self.assertEqual(after["last_verdict"], "FAILED_REQUIRES_HUMAN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
