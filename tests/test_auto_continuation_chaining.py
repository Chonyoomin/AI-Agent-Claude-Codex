"""Focused tests for the Phase 6G automatic continuation chaining slice.

Scope of this suite (Phase 6G, narrow):
- `run_auto_continue(...)` performs up to `AUTO_CONTINUE_MAX_HOPS`
  hops of the shipped Phase 6F single-hop
  `run_token_exhaustion_resume(...)` while loop-state.json status
  re-enters `HALTED_TOKEN_EXHAUSTION` between hops.
- A hop's success criterion is the dispatched continuation's rc; the
  chain's continue/stop criterion is the persisted loop-state status
  after the hop.
- Refusal handling: the initial "status is not the token-exhaustion
  halt" check uses the recovery-preserving stderr+log+exit-2 pattern
  (NOT `_halt`) so a strict-gate halt on disk is preserved if the
  operator runs `auto-continue` by mistake. Per-hop refusals come
  from the underlying Phase 6F single-hop primitive (budget exhausted,
  unsupported saved stage, malformed checkpoint, cycle-identity
  mismatch); those refusals already preserve the saved halt.
- A defense-in-depth `AUTO_CONTINUE_MAX_HOPS` bound caps chain depth
  independently of per-checkpoint `continuation_budget`. Hitting the
  cap refuses fail-closed and leaves the halt intact.
- The new `auto-continue` CLI subcommand routes through the standard
  `HANDLERS` dispatch in `main(argv)` so the operator runtime path is
  real, not a library helper.
- Canonical-precedence preservation: a successful chain does NOT
  advance `cycle_count`, does NOT progress the phase, does NOT widen
  autonomy, does NOT bypass any Phase 5 human gate; a refused chain
  does not mutate any on-disk checkpoint bytes; a `cmd_resume`
  invocation on `HALTED_TOKEN_EXHAUSTION` still dispatches the
  single-hop resume unchanged (the chain is OPT-IN through the
  dedicated `auto-continue` subcommand, not an automatic widening of
  the resume path).

This slice does not implement phase-boundary memory distillation,
repeated-failure memory synthesis, broader optional context-file
loading, or any widening of Phase 5 autonomy.
"""

from __future__ import annotations

import argparse
import json
import sys
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


_ACTIVE_PHASE = "Phase 6 - Durable Memory and Optional Context Layer"
_ACTIVE_SUB_PHASE = (
    "Phase 6G - Automatic Continuation Chaining Initial Slice"
)
_ACTIVE_TASK = "Implement automatic continuation chaining."
_PRE_SUSPENSION_STATUS = "awaiting_codex_review"
_PRE_SUSPENSION_AWAITING_HUMAN_FOR = None


def _baseline_loop_state(**overrides) -> dict:
    """Loop-state at a typical mid-cycle moment where a token-exhaustion
    chain might originate (Codex review awaited, no halt in effect)."""
    data = {
        "phase": _ACTIVE_PHASE,
        "sub_phase": _ACTIVE_SUB_PHASE,
        "task": _ACTIVE_TASK,
        "status": _PRE_SUSPENSION_STATUS,
        "cycle_count": 1,
        "max_cycles": 3,
        "last_verdict": None,
        "last_verdict_phase": None,
        "contract_version": "phase-3a-v2",
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": agent_loop.APPROVAL_MODE_REVIEW,
        "awaiting_human_for": _PRE_SUSPENSION_AWAITING_HUMAN_FOR,
    }
    data.update(overrides)
    return data


class _AutoContinueTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.al = self.repo_root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        self.state_path = self.al / "loop-state.json"
        self.log_path = self.al / "orchestrator.log"
        self.memory_dir = self.repo_root / agent_loop.MEMORY_DIR_REL
        self.checkpoint_dir = (
            self.memory_dir / agent_loop.MEMORY_CATEGORY_CHECKPOINT
        )

    def _write_state(self, **overrides) -> dict:
        data = _baseline_loop_state(**overrides)
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return data

    def _state_on_disk(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _record(self, **overrides) -> Path:
        kwargs = dict(active_prompt_path=".agent-loop/claude-prompt.md")
        kwargs.update(overrides)
        return agent_loop.record_token_exhaustion(self.repo_root, **kwargs)

    def _set_status_to_token_halt(self) -> None:
        """Force loop-state into the token-exhaustion halt without going
        through `record_token_exhaustion` (e.g. for simulating that a
        dispatched continuation re-entered the halt)."""
        data = self._state_on_disk()
        data["status"] = agent_loop.HALTED_TOKEN_EXHAUSTION
        data["awaiting_human_for"] = (
            agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
        )
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )

    def _make_reentering_dispatch(self, hops_to_reenter: int):
        """Build a side_effect callable for
        `_run_normal_cycle_codex_review_step` that simulates the
        dispatched continuation recording a FRESH token-exhaustion
        event on the first `hops_to_reenter` calls and then completing
        cleanly on the next call.

        On a re-entering call: writes a NEW checkpoint with a budget
        that varies by call number (so the deterministic on-disk
        filename `{YYYYMMDDTHHMMSSZ}-{sha256_short(body)[:8]}.json`
        does not collide when several writes land in the same wall-
        clock second) and transitions loop-state to
        HALTED_TOKEN_EXHAUSTION. Returns 0 so the resume layer treats
        the hop as a successful dispatch; the chain decision is then
        made on the post-hop loop-state status.

        On a clean call: leaves loop-state at whatever the dispatch
        prelude wrote (typically `evidence_capture`) and returns 0 so
        the chain naturally terminates."""
        call_state = {"count": 0}

        def _side_effect(repo_root_arg, data_arg, log_arg) -> int:
            call_state["count"] += 1
            if call_state["count"] <= hops_to_reenter:
                # Simulate a fresh exhaustion event during the
                # continuation. Use the orchestrator's own writer so
                # the on-disk checkpoint and loop-state mirror what a
                # real adapter would produce.
                state_path = (
                    repo_root_arg / ".agent-loop" / "loop-state.json"
                )
                cur = json.loads(state_path.read_text(encoding="utf-8"))
                cur["status"] = _PRE_SUSPENSION_STATUS
                cur["awaiting_human_for"] = (
                    _PRE_SUSPENSION_AWAITING_HUMAN_FOR
                )
                state_path.write_text(
                    json.dumps(cur, indent=2) + "\n", encoding="utf-8",
                )
                # Vary the budget per call so the body-hash component
                # of the filename differs even when multiple writes
                # land in the same wall-clock second. The Phase 6D
                # writer enforces non-negative; an offset large enough
                # to stay positive across the deepest chain we
                # exercise.
                agent_loop.record_token_exhaustion(
                    repo_root_arg,
                    active_prompt_path=".agent-loop/claude-prompt.md",
                    continuation_budget=1000 + 1000 * call_state["count"],
                )
            return 0

        return _side_effect, call_state


# ----- run_auto_continue: single-hop natural termination -----


class RunAutoContinueSingleHopTests(_AutoContinueTestCase):

    def test_chain_terminates_after_one_hop_when_continuation_clears_halt(
        self,
    ) -> None:
        self._write_state()
        self._record(continuation_budget=2)
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=0,
        ) as continuation:
            rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 0)
        continuation.assert_called_once()
        # Loop-state cleared the token-exhaustion halt (the dispatch
        # left the transitional `evidence_capture` in place, since the
        # mocked continuation did not write a fresh halt back).
        after = self._state_on_disk()
        self.assertEqual(after["status"], "evidence_capture")
        # Exactly one budget unit consumed: the budget=2 starting
        # checkpoint produced a budget=1 superseding checkpoint.
        paths = agent_loop.list_checkpoint_entries(self.repo_root)
        self.assertEqual(len(paths), 2)
        newest = max(paths, key=lambda p: (p.stat().st_mtime_ns, p.name))
        self.assertEqual(
            agent_loop.read_checkpoint_entry(newest)["continuation_budget"],
            1,
        )
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("auto-continue chain start:", log_text)
        self.assertIn("auto-continue chain completed after 1 hop", log_text)


# ----- run_auto_continue: multi-hop chained continuation -----


class RunAutoContinueMultiHopTests(_AutoContinueTestCase):

    def test_chain_walks_multiple_hops_when_continuation_reenters_halt(
        self,
    ) -> None:
        # Two hops chained: the dispatched continuation simulates a
        # fresh exhaustion event on the first call (so the chain
        # advances to hop 2) and then clears cleanly on the second.
        self._write_state()
        self._record(continuation_budget=2)
        side_effect, call_state = self._make_reentering_dispatch(
            hops_to_reenter=1,
        )
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            side_effect=side_effect,
        ):
            rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 0)
        self.assertEqual(call_state["count"], 2)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("auto-continue chain hop 1 begin", log_text)
        self.assertIn("auto-continue chain hop 2 begin", log_text)
        self.assertIn("auto-continue chain completed after 2 hop", log_text)

    def test_chain_terminates_when_continuation_clears_halt_mid_chain(
        self,
    ) -> None:
        # budget=3 initial; the dispatched continuation re-enters only
        # ONCE so the chain should terminate after hop 2 (not consume
        # all the budget).
        self._write_state()
        self._record(continuation_budget=3)
        side_effect, call_state = self._make_reentering_dispatch(
            hops_to_reenter=1,
        )
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            side_effect=side_effect,
        ):
            rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 0)
        self.assertEqual(call_state["count"], 2)


# ----- run_auto_continue: refusal modes -----


class RunAutoContinueRefusalTests(_AutoContinueTestCase):

    def test_chain_refuses_when_status_is_not_token_exhaustion_halt(
        self,
    ) -> None:
        # Plant a clean non-halt loop-state. Auto-continue must refuse
        # using the recovery-preserving pattern (NOT `_halt`) so it
        # does not clobber an unrelated halt.
        self._write_state()
        rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 2)
        # No halt was written - the loop-state still carries the
        # original non-halt status.
        after = self._state_on_disk()
        self.assertEqual(after["status"], _PRE_SUSPENSION_STATUS)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("auto-continue refused:", log_text)
        self.assertIn(
            "reserved for token-exhaustion chaining", log_text,
        )

    def test_chain_refusal_preserves_strict_gate_halt(self) -> None:
        # If the operator runs auto-continue while paused at a Phase
        # 5C strict-gate halt, the recovery-preserving refusal must
        # leave the strict-gate state intact (no clobbering).
        self._write_state(
            status=agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT
            ),
            approval_mode=agent_loop.APPROVAL_MODE_STRICT,
        )
        rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        # The strict-gate halt is byte-equivalent to what we wrote -
        # auto-continue did NOT route through `_halt` (which would have
        # rewritten status to halted_input_missing).
        self.assertEqual(after["status"], agent_loop.HALTED_PRE_CLAUDE_PROMPT)
        self.assertEqual(
            after["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT,
        )
        self.assertEqual(
            after["approval_mode"], agent_loop.APPROVAL_MODE_STRICT,
        )

    def test_chain_refuses_on_exhausted_budget(self) -> None:
        # budget=0 on the active checkpoint: the FIRST hop refuses
        # (delegated to run_token_exhaustion_resume's existing
        # exhausted-budget refusal) and the chain stops.
        self._write_state()
        self._record(continuation_budget=0)
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=0,
        ) as continuation:
            rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 2)
        continuation.assert_not_called()
        # The saved HALTED_TOKEN_EXHAUSTION halt is preserved (the
        # underlying recovery-preserving 6F refusal).
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("continuation_budget=0", log_text)
        self.assertIn("exhausted", log_text)

    def test_chain_refuses_on_unsupported_saved_stage(self) -> None:
        # `claude_implementing` is a real mid-cycle status but NOT in
        # `TOKEN_EXHAUSTION_SUPPORTED_RESUME_STATUSES`. The underlying
        # Phase 6F single-hop refuses; auto-continue propagates rc=2
        # and leaves the saved halt intact.
        self._write_state(status="claude_implementing")
        self._record()
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=0,
        ) as continuation:
            rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 2)
        continuation.assert_not_called()
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("supported interrupted-stage set", log_text)

    def test_chain_refuses_on_malformed_checkpoint(self) -> None:
        # Plant the halt by hand but write a malformed checkpoint that
        # is missing every required body field. The underlying 6F
        # single-hop refuses; auto-continue propagates the refusal.
        self._write_state(
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
            ),
        )
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "signal_version": agent_loop.MEMORY_SIGNAL_VERSION,
            "category": agent_loop.MEMORY_CATEGORY_CHECKPOINT,
            "phase": _ACTIVE_PHASE,
            "sub_phase": _ACTIVE_SUB_PHASE,
            "cycle_count": 1,
            "source_artifact_path": ".agent-loop/loop-state.json",
            "created_at": "2030-01-01T00:00:00Z",
            "supersedes": None,
            "body": json.dumps({}),
        }
        (self.checkpoint_dir / "20300101T000000Z-deadbeef.json").write_text(
            json.dumps(entry), encoding="utf-8",
        )
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=0,
        ) as continuation:
            rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 2)
        continuation.assert_not_called()
        after = self._state_on_disk()
        self.assertEqual(after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION)

    def test_chain_propagates_non_token_halt_from_dispatched_continuation(
        self,
    ) -> None:
        # If the dispatched continuation halts with a non-zero rc but
        # does NOT re-enter HALTED_TOKEN_EXHAUSTION, the chain must
        # propagate the rc unchanged (e.g. evidence refusal, FAILED
        # verdict, max_cycles).
        self._write_state()
        self._record(continuation_budget=2)
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=2,
        ) as continuation:
            rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 2)
        continuation.assert_called_once()


# ----- run_auto_continue: defense-in-depth max-hops cap -----


class RunAutoContinueMaxHopsCapTests(_AutoContinueTestCase):

    def test_chain_hits_max_hops_cap_and_refuses(self) -> None:
        # Build a re-entering dispatch that ALWAYS records a fresh
        # exhaustion event with the default budget. The chain would
        # otherwise run forever; the AUTO_CONTINUE_MAX_HOPS cap must
        # fire instead, refuse fail-closed, and leave the saved halt
        # intact.
        self._write_state()
        self._record(continuation_budget=10)
        # Re-enter on every call within the test (hops_to_reenter
        # equal to the cap so the chain hits the cap before naturally
        # terminating).
        side_effect, call_state = self._make_reentering_dispatch(
            hops_to_reenter=agent_loop.AUTO_CONTINUE_MAX_HOPS + 5,
        )
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            side_effect=side_effect,
        ):
            rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 2)
        # Exactly MAX_HOPS hops were performed before the cap fired.
        self.assertEqual(
            call_state["count"], agent_loop.AUTO_CONTINUE_MAX_HOPS,
        )
        # The token-exhaustion halt is preserved on disk (the cap
        # uses the recovery-preserving refusal pattern).
        after = self._state_on_disk()
        self.assertEqual(
            after["status"], agent_loop.HALTED_TOKEN_EXHAUSTION,
        )
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            f"chain reached the AUTO_CONTINUE_MAX_HOPS="
            f"{agent_loop.AUTO_CONTINUE_MAX_HOPS}",
            log_text,
        )


# ----- cmd_auto_continue + main(argv) routing -----


class CmdAutoContinueRoutingTests(_AutoContinueTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_subcommand_dispatches_to_run_auto_continue(self) -> None:
        self._write_state()
        self._record()
        with mock.patch.object(
            agent_loop, "run_auto_continue", return_value=33,
        ) as ac:
            rc = self._run_main(["auto-continue"])
        self.assertEqual(rc, 33)
        ac.assert_called_once_with(self.repo_root)

    def test_cli_subcommand_records_chain_audit_log_end_to_end(
        self,
    ) -> None:
        # End-to-end through main(argv): the subcommand really invokes
        # the chain and the audit log lands on disk. The dispatched
        # continuation is mocked to a clean single-hop completion.
        self._write_state()
        self._record(continuation_budget=2)
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=0,
        ):
            rc = self._run_main(["auto-continue"])
        self.assertEqual(rc, 0)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("auto-continue chain start:", log_text)

    def test_cmd_resume_does_not_dispatch_chain_on_token_exhaustion_halt(
        self,
    ) -> None:
        # The chain is OPT-IN through the `auto-continue` subcommand.
        # Phase 5C / 6E / 6F resume semantics are unchanged: a
        # HALTED_TOKEN_EXHAUSTION halt still routes to the single-hop
        # `run_token_exhaustion_resume`, NOT to `run_auto_continue`.
        self._write_state(
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
            ),
        )
        with mock.patch.object(
            agent_loop, "run_token_exhaustion_resume", return_value=11,
        ) as single_hop, mock.patch.object(
            agent_loop, "run_auto_continue", return_value=22,
        ) as chain:
            rc = self._run_main(["resume"])
        self.assertEqual(rc, 11)
        single_hop.assert_called_once_with(self.repo_root)
        chain.assert_not_called()


# ----- canonical-precedence preservation -----


class CanonicalPrecedencePreservationTests(_AutoContinueTestCase):

    def test_successful_chain_does_not_advance_cycle_count(self) -> None:
        self._write_state(cycle_count=2)
        self._record()
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=0,
        ):
            agent_loop.run_auto_continue(self.repo_root)
        after = self._state_on_disk()
        self.assertEqual(after["cycle_count"], 2)

    def test_successful_chain_preserves_phase_identity(self) -> None:
        self._write_state()
        self._record()
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=0,
        ):
            agent_loop.run_auto_continue(self.repo_root)
        after = self._state_on_disk()
        self.assertEqual(after["phase"], _ACTIVE_PHASE)
        self.assertEqual(after["sub_phase"], _ACTIVE_SUB_PHASE)
        self.assertEqual(after["task"], _ACTIVE_TASK)
        self.assertEqual(
            after["approval_mode"], agent_loop.APPROVAL_MODE_REVIEW,
        )

    def test_refused_chain_does_not_mutate_checkpoint_files(self) -> None:
        # The initial-status refusal path does not touch checkpoints
        # at all; this proves the on-disk checkpoint bytes are
        # byte-equivalent across the refusal.
        self._write_state()
        path = self._record()
        before = path.read_bytes()
        # Plant a non-halt status so auto-continue refuses on the
        # initial check.
        data = self._state_on_disk()
        data["status"] = "evidence_capture"
        data["awaiting_human_for"] = None
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        rc = agent_loop.run_auto_continue(self.repo_root)
        self.assertEqual(rc, 2)
        self.assertEqual(path.read_bytes(), before)

    def test_chain_does_not_widen_phase_5_autonomy(self) -> None:
        # A successful chain does NOT change approval_mode, does NOT
        # bypass any Phase 5 gate, and does NOT advance phase / sub_phase.
        # The dispatched continuation operates within the same Phase 5
        # semantics it would under a manual resume.
        self._write_state(approval_mode=agent_loop.APPROVAL_MODE_REVIEW)
        self._record()
        with mock.patch.object(
            agent_loop, "_run_normal_cycle_codex_review_step",
            return_value=0,
        ):
            agent_loop.run_auto_continue(self.repo_root)
        after = self._state_on_disk()
        # approval_mode preserved exactly.
        self.assertEqual(
            after["approval_mode"], agent_loop.APPROVAL_MODE_REVIEW,
        )
        # No autonomous-bypass note from the chain itself (the chain
        # never logs autonomous-mode bypasses; it just sits on top of
        # the single-hop primitive).
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertNotIn("autonomous mode:", log_text)


if __name__ == "__main__":
    unittest.main()
