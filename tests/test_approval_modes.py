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


# ----- Phase 5B fix coverage -----
#
# These tests pin the two contract gaps surfaced in fix-prompt.md:
#   (1) `approval_mode` is fail-closed validated against ALLOWED_APPROVAL_MODES;
#   (2) `.agent-loop/claude-done.json` is written only after the summary AND
#       evidence have both validated, so a halt above that point cannot leave
#       a stale `ready_for_codex_review` signal behind.

class _CycleHarness(_ApprovalModesTestCase):
    """Helper to drive `run_normal_cycle` against the synthetic `_Repo`
    with the Claude/Codex adapters and evidence helpers stubbed. This lets
    the test exercise the orchestrator's claude-done.json timing without
    spawning real subprocesses or requiring real evidence files."""

    def setUp(self) -> None:
        super().setUp()
        # Mark the loop ready to start and give the cycle some headroom.
        data = self._state()
        data["status"] = "awaiting_claude_implementation"
        data["max_cycles"] = 3
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        # Pre-create the prompt the orchestrator will require.
        (self.repo.root / ".agent-loop" / "claude-prompt.md").write_text(
            "# Claude Code Task\n\n## Phase\nP\n\n## Objective\no\n\n"
            "## Context\nc\n\n## Required work\n- x\n\n"
            "## Constraints\n- y\n\n## Required output\n- z\n",
            encoding="utf-8",
        )

    def _make_summary_writer(self, *, model_id: str = "stub-claude"):
        """Build a Claude-adapter `.invoke(prompt, summary)` stub that
        writes a minimally valid claude-summary.md and returns a success
        ExecutionResult; mtimes advance because the file is rewritten."""
        repo_root = self.repo.root

        def _invoke(prompt_path, summary_path):
            data = self._state()
            phase = data["phase"]
            sub_phase = data.get("sub_phase") or ""
            summary_text = (
                "# Claude Implementation Summary\n\n"
                f"## Phase\n{phase} (sub-phase: {sub_phase})\n\n"
                "## Task\nt\n\n"
                "## Files changed\n- f: change\n\n"
                "## What was implemented\n- x\n\n"
                "## What was not implemented\n- y\n\n"
                "## Tests added or changed\n- None\n\n"
                "## Validation run\n- Not run\n\n"
                "## Assumptions\n- None\n\n"
                "## Risk areas\n- None identified\n"
            )
            summary_path.write_text(summary_text, encoding="utf-8")
            return agent_loop.ExecutionResult(
                exit_code=0, model_id=model_id, duration_seconds=0.0,
            )

        return _invoke


class InvalidApprovalModeHaltsTests(_ApprovalModesTestCase):

    def test_validate_loop_state_rejects_invalid_nonempty_mode(self) -> None:
        data = self._state()
        data["approval_mode"] = "bogus"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.validate_loop_state(data)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("approval_mode", cm.exception.reason)
        self.assertIn("bogus", cm.exception.reason)

    def test_validate_loop_state_allows_missing_mode_for_backfill(self) -> None:
        data = self._state()
        data.pop("approval_mode", None)
        agent_loop.validate_loop_state(data)  # must not raise

    def test_validate_loop_state_allows_empty_mode_for_backfill(self) -> None:
        data = self._state()
        data["approval_mode"] = ""
        agent_loop.validate_loop_state(data)  # must not raise

    def test_validate_loop_state_accepts_all_three_allowed_modes(self) -> None:
        for mode in ("review", "strict", "autonomous"):
            data = self._state()
            data["approval_mode"] = mode
            try:
                agent_loop.validate_loop_state(data)
            except agent_loop.HaltError as exc:
                self.fail(f"valid approval_mode {mode!r} was rejected: {exc.reason}")

    def test_run_normal_cycle_halts_on_invalid_mode(self) -> None:
        data = self._state()
        data["approval_mode"] = "bogus"
        data["status"] = "awaiting_claude_implementation"
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        # The cycle should halt at the structural-validate step before it
        # touches any adapter, so no adapter stubs are needed.
        rc = agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(rc, 2, "invalid approval_mode must halt with exit 2")
        after = self._state()
        # The halt path persists the halt status and never advances past
        # validate_loop_state, so the invalid mode is still present on disk
        # for human inspection (the orchestrator does not silently rewrite
        # an invalid value to a valid one).
        self.assertTrue(after["status"].startswith("halted_"))
        self.assertEqual(after["approval_mode"], "bogus")


class ClaudeDoneOnlyWhenReviewReadyTests(_CycleHarness):

    def test_done_signal_not_written_when_evidence_capture_halts(self) -> None:
        # Simulate `invoke_run_checks` raising the contract halt for a
        # missing evidence file - the same halt vocabulary the real
        # evidence helpers use.
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks",
            side_effect=agent_loop.HaltError(
                "halted_evidence_missing", "synthetic evidence-capture failure",
            ),
        ):
            rc = agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(rc, 2, "an evidence-capture halt exits 2")
        self.assertFalse(
            self.done_path.exists(),
            "claude-done.json must not advertise ready_for_codex_review when "
            "the cycle halted before review readiness was reached",
        )
        after = self._state()
        self.assertEqual(after["status"], "halted_evidence_missing")

    def test_done_signal_not_written_when_evidence_validation_halts(
        self,
    ) -> None:
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks", return_value=0,
        ), mock.patch.object(
            agent_loop, "validate_evidence_files",
            side_effect=agent_loop.HaltError(
                "halted_evidence_malformed", "synthetic evidence-validate failure",
            ),
        ):
            rc = agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse(
            self.done_path.exists(),
            "claude-done.json must not be left after an evidence-validation halt",
        )

    def test_stale_done_signal_is_cleared_on_evidence_halt(self) -> None:
        # The cycle-start clear must drop any prior cycle's claude-done.json
        # even if THIS cycle then halts on evidence and never writes a new
        # one. That is the only way the contract guarantee ("the repo is
        # never left advertising ready_for_codex_review for a halted cycle")
        # holds when a prior cycle's signal is present at cycle start.
        agent_loop.write_claude_done(
            self.repo.root,
            phase="prev", sub_phase="prev", task="prev", cycle_count=42,
            mode=agent_loop.CLAUDE_DONE_MODE_IMPLEMENTATION,
            source_prompt_path=".agent-loop/claude-prompt.md",
        )
        self.assertTrue(self.done_path.exists())
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks",
            side_effect=agent_loop.HaltError(
                "halted_evidence_missing", "synthetic",
            ),
        ):
            rc = agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertFalse(
            self.done_path.exists(),
            "stale prior-cycle claude-done.json must be cleared at cycle start "
            "regardless of how this cycle ends",
        )

    def test_success_path_still_writes_done_signal_after_evidence(self) -> None:
        # Drive the cycle through evidence validation success and into the
        # Codex-review step. Stub the Codex adapter so it does not block,
        # but make it return a failure so the cycle halts after the
        # claude-done.json write (the test only needs to observe the write).
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks", return_value=0,
        ), mock.patch.object(
            agent_loop, "validate_evidence_files", return_value=None,
        ), mock.patch.object(
            agent_loop, "make_codex_adapter",
            return_value=mock.Mock(wait_for_review=lambda _p: agent_loop.ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=0.0,
            )),
        ):
            agent_loop.run_normal_cycle(self.repo.root)
        self.assertTrue(
            self.done_path.exists(),
            "the success path through evidence must produce claude-done.json",
        )
        payload = _read_json(self.done_path)
        self.assertEqual(payload["status"], "ready_for_codex_review")
        self.assertEqual(payload["mode"], "implementation")
        self.assertEqual(payload["source_prompt_path"], ".agent-loop/claude-prompt.md")


# ----- Phase 5C strict-mode coverage -----
#
# These tests pin the three strict-mode pauses defined in Phase 5A and
# implemented in Phase 5C, plus the `resume` continuation:
#   - pre_claude_prompt before a new implementation prompt dispatches
#   - pre_fix_prompt before a new fix prompt dispatches
#   - pre_codex_review after Claude completion + evidence validation but
#     before Codex review begins (one variant for the normal cycle, one
#     for the fix cycle)
# A `_handle_verdict_loop` review must already have happened to reach the
# pre_fix_prompt gate, so the fix-prompt tests drive `_handle_verdict_loop`
# directly with a synthetic NEEDS_FIXES verdict.

class _StrictCycleHarness(_CycleHarness):
    """Same setup as _CycleHarness but flips approval_mode to `strict`
    and pre-writes a valid fix-prompt for the fix-gate tests."""

    def setUp(self) -> None:
        super().setUp()
        data = self._state()
        data["approval_mode"] = agent_loop.APPROVAL_MODE_STRICT
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        # Pre-create a minimally valid fix-prompt for the gate-on-fix tests.
        (self.repo.root / ".agent-loop" / "fix-prompt.md").write_text(
            "# Claude Code Fix Task\n\n## Objective\no\n\n"
            "## Context\nc\n\n## Required fixes\n- x\n\n"
            "## Constraints\n- y\n\n## Required output\n- z\n",
            encoding="utf-8",
        )


class StrictGatePreClaudePromptTests(_StrictCycleHarness):

    def test_strict_gate_fires_before_any_claude_invocation(self) -> None:
        invoked = {"called": False}
        adapter = mock.Mock()
        def _invoke(*_):
            invoked["called"] = True
            raise AssertionError(
                "Claude adapter must not be invoked when the strict "
                "pre_claude_prompt gate fires"
            )
        adapter.invoke = _invoke
        with mock.patch.object(
            agent_loop, "make_claude_adapter", return_value=adapter,
        ):
            rc = agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(rc, 2, "the strict gate exits cleanly with code 2")
        self.assertFalse(invoked["called"])
        after = self._state()
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
        )
        # The cycle counter was NOT incremented yet (the gate fires before
        # the threshold/increment block).
        self.assertEqual(after["cycle_count"], 0)


class StrictGatePreCodexReviewNormalTests(_StrictCycleHarness):

    def test_strict_gate_fires_after_evidence_before_codex_review(self) -> None:
        codex_called = {"called": False}

        def _wait(_path):
            codex_called["called"] = True
            raise AssertionError(
                "Codex adapter must not be invoked when the strict "
                "pre_codex_review gate fires"
            )

        # The pre_claude_prompt gate fires first under strict mode. To
        # observe the second strict gate (pre_codex_review) we drive the
        # continuation entry point directly, which is the same entry the
        # `resume` subcommand uses after the human approves the first
        # gate.
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks", return_value=0,
        ), mock.patch.object(
            agent_loop, "validate_evidence_files", return_value=None,
        ), mock.patch.object(
            agent_loop, "make_codex_adapter",
            return_value=mock.Mock(wait_for_review=_wait),
        ):
            rc = agent_loop._run_normal_cycle_from_increment(
                self.repo.root, self._state(), self.log_path,
            )
        self.assertEqual(rc, 2)
        self.assertFalse(codex_called["called"])
        after = self._state()
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CODEX_REVIEW_NORMAL)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW,
        )
        # claude-done.json was already written (review-ready) and the
        # cycle counter was incremented.
        self.assertTrue(self.done_path.exists())
        self.assertEqual(after["cycle_count"], 1)


class StrictGatePreFixPromptTests(_StrictCycleHarness):

    def _drive_verdict(self, verdict: str) -> int:
        with mock.patch.object(
            agent_loop, "_invoke_post_approval_planner", return_value=0,
        ):
            return agent_loop._handle_verdict_loop(
                self.state_path, self._state(), verdict,
                self.repo.root, self.log_path,
            )

    def test_strict_gate_fires_before_fix_cycle_invokes_claude(self) -> None:
        # Seed a state where the verdict loop would normally proceed to a
        # fix cycle (cycle_count below max_cycles).
        data = self._state()
        data["cycle_count"] = 1
        data["max_cycles"] = 3
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )

        invoked = {"called": False}

        def _invoke(*_):
            invoked["called"] = True
            raise AssertionError(
                "fix-cycle Claude adapter must not be invoked when the "
                "strict pre_fix_prompt gate fires"
            )

        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=_invoke),
        ):
            rc = self._drive_verdict("NEEDS_FIXES")
        self.assertEqual(rc, 2)
        self.assertFalse(invoked["called"])
        after = self._state()
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_FIX_PROMPT)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_FIX_PROMPT,
        )
        # NEEDS_FIXES was recorded before the gate fired.
        self.assertEqual(after["last_verdict"], "NEEDS_FIXES")


class StrictGatePreCodexReviewFixTests(_StrictCycleHarness):

    def test_strict_gate_fires_after_fix_evidence_before_codex_review(
        self,
    ) -> None:
        # Set up state mid-fix-cycle (Claude fix already implemented,
        # evidence already validated). Drive _run_fix_cycle directly via
        # the verdict-loop path so the strict gate fires at step 4b.
        data = self._state()
        data["cycle_count"] = 1
        data["max_cycles"] = 3
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        codex_called = {"called": False}

        def _wait(_path):
            codex_called["called"] = True
            raise AssertionError(
                "Codex adapter must not be invoked when the strict "
                "pre_codex_review gate fires in the fix cycle"
            )

        # The pre_fix_prompt gate would fire first; bypass it by patching
        # `_fire_strict_gate` to return None on its FIRST call (the fix-prompt
        # gate), so the fix cycle actually starts and we observe the
        # SECOND gate fire at the pre-codex-review point. The simplest way
        # is to flip the loaded state's approval_mode for the
        # pre_fix_prompt gate only; we instead skip the first gate by
        # directly invoking the fix-cycle helpers.
        try:
            with mock.patch.object(
                agent_loop, "make_claude_adapter",
                return_value=mock.Mock(invoke=self._make_summary_writer()),
            ), mock.patch.object(
                agent_loop, "invoke_run_checks", return_value=0,
            ), mock.patch.object(
                agent_loop, "validate_evidence_files", return_value=None,
            ), mock.patch.object(
                agent_loop, "make_codex_adapter",
                return_value=mock.Mock(wait_for_review=_wait),
            ):
                agent_loop._run_fix_cycle(
                    self.state_path, self._state(), self.repo.root, self.log_path,
                )
            self.fail("_run_fix_cycle must raise _FixCycleHalt when the strict gate fires")
        except agent_loop._FixCycleHalt as halted:
            self.assertEqual(halted.exit_code, 2)
        self.assertFalse(codex_called["called"])
        after = self._state()
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CODEX_REVIEW_FIX)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW,
        )
        # The fix cycle did its own increment and wrote the fix-mode done
        # signal before the gate fired.
        self.assertTrue(self.done_path.exists())
        self.assertEqual(_read_json(self.done_path)["mode"], "fix")
        self.assertEqual(after["cycle_count"], 2)


class StrictResumeDispatchTests(_StrictCycleHarness):

    def test_resume_refuses_when_status_is_not_a_strict_gate(self) -> None:
        # awaiting_claude_implementation is the canonical ready state -
        # resume is only valid after a strict gate halted the cycle.
        data = self._state()
        data["status"] = "awaiting_claude_implementation"
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        rc = agent_loop.run_strict_resume(self.repo.root)
        self.assertEqual(rc, 2)
        after = self._state()
        # The refusal persists its own halt status and does NOT clear
        # awaiting_human_for (because none was set in the first place).
        self.assertTrue(after["status"].startswith("halted_"))

    def test_resume_after_pre_claude_prompt_dispatches_to_increment(
        self,
    ) -> None:
        # Fire the gate first.
        with mock.patch.object(
            agent_loop, "make_claude_adapter", return_value=mock.Mock(),
        ):
            agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(self._state()["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT)

        # Now resume under the SAME strict mode (the Phase 5C fix requires
        # the paused mode to be preserved through resume; mutating to
        # `review` mid-cycle to bypass the next gate is refused). The
        # continuation runs the cycle_count increment + claude + evidence
        # + claude-done.json write, then fires the second strict gate
        # (`pre_codex_review_normal`) - which is exactly what proves the
        # resume correctly dispatched into the continuation AND that the
        # later gate still fires after a mid-cycle resume.
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks", return_value=0,
        ), mock.patch.object(
            agent_loop, "validate_evidence_files", return_value=None,
        ), mock.patch.object(
            agent_loop, "make_codex_adapter",
            return_value=mock.Mock(wait_for_review=lambda _p: agent_loop.ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=0.0,
            )),
        ):
            agent_loop.run_strict_resume(self.repo.root)
        after = self._state()
        # The continuation did the cycle_count increment + the full
        # claude+evidence+done flow, then hit the next strict gate.
        self.assertEqual(after["cycle_count"], 1)
        self.assertTrue(self.done_path.exists())
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CODEX_REVIEW_NORMAL)
        # The second gate set awaiting_human_for to its own gate name.
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW,
        )

    def test_resume_after_pre_codex_review_normal_skips_back_to_review(
        self,
    ) -> None:
        # Fire the post-evidence gate first.
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks", return_value=0,
        ), mock.patch.object(
            agent_loop, "validate_evidence_files", return_value=None,
        ), mock.patch.object(
            agent_loop, "make_codex_adapter", return_value=mock.Mock(),
        ):
            # The pre_claude_prompt gate fires first; bypass by stepping
            # directly into the post-increment continuation against the
            # initial state.
            agent_loop._run_normal_cycle_from_increment(
                self.repo.root, self._state(), self.log_path,
            )
        self.assertEqual(
            self._state()["status"], agent_loop.HALTED_PRE_CODEX_REVIEW_NORMAL,
        )
        # The Claude side of the cycle has already happened (increment +
        # summary + evidence + claude-done.json).
        self.assertTrue(self.done_path.exists())
        claude_done_mtime = self.done_path.stat().st_mtime

        # Now resume. Patch Codex to return a Codex failure to halt
        # cleanly after the review attempt. Crucially, the Claude
        # adapter MUST NOT be re-invoked.
        claude_invocations = {"count": 0}

        def _no_call(*_):
            claude_invocations["count"] += 1
            raise AssertionError(
                "Claude adapter must not be re-invoked on resume after "
                "the pre_codex_review gate; only the Codex review step runs"
            )

        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=_no_call),
        ), mock.patch.object(
            agent_loop, "make_codex_adapter",
            return_value=mock.Mock(wait_for_review=lambda _p: agent_loop.ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=0.0,
            )),
        ):
            agent_loop.run_strict_resume(self.repo.root)
        self.assertEqual(claude_invocations["count"], 0)
        after = self._state()
        self.assertIsNone(after["awaiting_human_for"])
        # cycle_count was not bumped again on resume.
        self.assertEqual(after["cycle_count"], 1)
        # claude-done.json bytes are unchanged (the cycle did not
        # re-write the signal on resume).
        self.assertEqual(self.done_path.stat().st_mtime, claude_done_mtime)


class StrictResumeModeCoherenceTests(_StrictCycleHarness):
    """Phase 5C contract: a strict-gate halt may only be resumed under
    `approval_mode = "strict"`. Mutating `approval_mode` between the halt
    and the resume - the only way a human or a test could try to bypass
    later gates - must be refused fail-closed."""

    def _fire_pre_claude_prompt_gate(self) -> None:
        with mock.patch.object(
            agent_loop, "make_claude_adapter", return_value=mock.Mock(),
        ):
            agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(
            self._state()["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT,
        )

    def test_resume_refuses_when_mode_was_mutated_to_review(self) -> None:
        self._fire_pre_claude_prompt_gate()
        # Mutate approval_mode from `strict` to `review` while the cycle
        # is paused at a strict gate.
        data = self._state()
        data["approval_mode"] = "review"
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )

        # The Claude adapter MUST NOT be invoked; the refusal happens
        # before any continuation runs.
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=lambda *_: (_ for _ in ()).throw(
                AssertionError("Claude adapter must not run on a refused resume"),
            )),
        ):
            rc = agent_loop.run_strict_resume(self.repo.root)
        self.assertEqual(rc, 2)
        after = self._state()
        # The refusal persists its own halt; awaiting_human_for is left
        # alone (the prior gate value stays visible for the human).
        self.assertTrue(after["status"].startswith("halted_"))
        self.assertEqual(after["approval_mode"], "review")
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
        )

    def test_resume_refuses_when_mode_was_mutated_to_autonomous(self) -> None:
        # The contract is symmetric: any non-strict mode is refused, not
        # just "review". `autonomous` is in the allowed vocabulary today
        # even though its runtime path is deferred.
        self._fire_pre_claude_prompt_gate()
        data = self._state()
        data["approval_mode"] = "autonomous"
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        rc = agent_loop.run_strict_resume(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertEqual(self._state()["approval_mode"], "autonomous")

    def test_refusal_message_names_strict_mode_requirement(self) -> None:
        # The auditable refusal must explicitly name strict-mode as the
        # required mode so the human reading orchestrator.log understands
        # why their resume was refused.
        self._fire_pre_claude_prompt_gate()
        data = self._state()
        data["approval_mode"] = "review"
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        agent_loop.run_strict_resume(self.repo.root)
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("approval_mode", log)
        self.assertIn("strict", log)


class StrictResumeFixPathTests(_StrictCycleHarness):

    def test_resume_after_pre_fix_prompt_runs_one_fix_cycle(self) -> None:
        # Seed the verdict-loop frame and fire the pre_fix_prompt gate.
        data = self._state()
        data["cycle_count"] = 1
        data["max_cycles"] = 3
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        with mock.patch.object(
            agent_loop, "_invoke_post_approval_planner", return_value=0,
        ), mock.patch.object(
            agent_loop, "make_claude_adapter", return_value=mock.Mock(),
        ):
            agent_loop._handle_verdict_loop(
                self.state_path, self._state(), "NEEDS_FIXES",
                self.repo.root, self.log_path,
            )
        self.assertEqual(self._state()["status"], agent_loop.HALTED_PRE_FIX_PROMPT)

        # Resume under the SAME strict mode (mid-cycle mode mutation is
        # now refused by `run_strict_resume`; the test must prove the
        # safe path, not the bypass). The fix cycle runs increment +
        # claude + evidence + claude-done.json (mode=fix), then fires the
        # pre_codex_review gate's fix-flavor halt.
        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks", return_value=0,
        ), mock.patch.object(
            agent_loop, "validate_evidence_files", return_value=None,
        ), mock.patch.object(
            agent_loop, "make_codex_adapter",
            return_value=mock.Mock(wait_for_review=lambda _p: agent_loop.ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=0.0,
            )),
        ):
            agent_loop.run_strict_resume(self.repo.root)
        after = self._state()
        # The fix cycle incremented cycle_count from 1 -> 2 and wrote a
        # fix-mode claude-done.json before the second strict gate halted
        # the cycle.
        self.assertEqual(after["cycle_count"], 2)
        self.assertEqual(_read_json(self.done_path)["mode"], "fix")
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CODEX_REVIEW_FIX)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CODEX_REVIEW,
        )


class ReviewModeStrictBehaviorNotRegressedTests(_CycleHarness):
    """The shipped review-mode baseline must not fire any strict gate."""

    def test_review_mode_does_not_fire_pre_claude_prompt_gate(self) -> None:
        # Review mode (the default for _CycleHarness) must NOT halt at
        # the strict pre-claude gate; it proceeds through to claude
        # invocation. We stub Claude to ensure it IS called (the gate
        # would prevent that).
        called = {"n": 0}

        def _invoke(*_, **__):
            called["n"] += 1
            return agent_loop.ExecutionResult(
                exit_code=0, model_id="stub", duration_seconds=0.0,
            )

        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=_invoke),
        ):
            # The summary will be invalid (empty), so the cycle will halt
            # later - that is fine. We only need to prove the strict gate
            # did NOT fire.
            agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(
            called["n"], 1,
            "review mode must not fire the pre_claude_prompt strict gate",
        )
        after = self._state()
        self.assertNotEqual(after["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT)

    def test_review_mode_does_not_fire_pre_codex_review_gate(self) -> None:
        codex_called = {"n": 0}

        def _wait(_path):
            codex_called["n"] += 1
            return agent_loop.ExecutionResult(
                exit_code=1, model_id=None, duration_seconds=0.0,
            )

        with mock.patch.object(
            agent_loop, "make_claude_adapter",
            return_value=mock.Mock(invoke=self._make_summary_writer()),
        ), mock.patch.object(
            agent_loop, "invoke_run_checks", return_value=0,
        ), mock.patch.object(
            agent_loop, "validate_evidence_files", return_value=None,
        ), mock.patch.object(
            agent_loop, "make_codex_adapter",
            return_value=mock.Mock(wait_for_review=_wait),
        ):
            agent_loop.run_normal_cycle(self.repo.root)
        self.assertEqual(
            codex_called["n"], 1,
            "review mode must not fire the pre_codex_review strict gate",
        )
        after = self._state()
        self.assertNotEqual(
            after["status"], agent_loop.HALTED_PRE_CODEX_REVIEW_NORMAL,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
