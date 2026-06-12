"""Focused tests for the Phase 6I phase-boundary memory distillation
slice.

Scope of this suite (Phase 6I, narrow):
- `distill_phase_boundary_memory(repo_root, ...)` writes append-mostly
  durable memory entries in the three named Phase 6A categories
  (`summary`, `decision`, and conditionally `failure`) at an APPROVED
  phase boundary, sourced from canonical loop-state plus bounded
  excerpts of `.agent-loop/claude-summary.md` and
  `.agent-loop/codex-review.md`.
- Each written entry carries an explicit `distillation_signal_version`
  body marker plus a `source_artifacts` list pointing at the canonical
  source paths so later retrieval can trace where the distilled
  knowledge came from.
- Refusal modes (all `halted_input_missing` unless noted): missing /
  malformed `loop-state.json`, unsupported `contract_version`
  (`halted_contract_version_mismatch`), status not
  `phase_complete_awaiting_human_approval`, `last_verdict` not
  `APPROVED_FOR_HUMAN_REVIEW`, missing or malformed source artifacts
  (`halted_summary_malformed` / `halted_review_*` from the existing
  validators), on-disk codex-review verdict disagreeing with
  loop-state `last_verdict`, an unreadable source artifact, an
  already-distilled-marker entry on disk for this exact
  (phase, sub_phase, cycle_count), out-of-bound
  `excerpt_byte_limit`.
- Bounded excerpts: each source artifact is included up to
  `excerpt_byte_limit` bytes (default
  `DISTILLATION_DEFAULT_EXCERPT_BYTE_LIMIT`, capped at
  `DISTILLATION_MAX_EXCERPT_BYTE_LIMIT`) with explicit truncation
  flagging.
- Canonical-precedence preservation: distillation never mutates
  `loop-state.json`, never modifies canonical task / phase artifacts,
  and writes only to `.agent-loop/memory/<category>/`. A re-run is
  refused fail-closed rather than silently producing a duplicate.
- The `distill-phase-boundary-memory` CLI subcommand routes through
  `main(argv)` HANDLERS dispatch end-to-end.

This slice does not implement broader optional context-file loading,
does not parse internal markdown structure of the source artifacts,
and does not widen Phase 5 autonomy or bypass any human gate.
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
    "Phase 6I - Phase-Boundary Memory Distillation Initial Slice"
)
_ACTIVE_TASK = "Implement phase-boundary memory distillation."


def _baseline_boundary_state(**overrides) -> dict:
    """Loop-state at a typical APPROVED phase boundary."""
    data = {
        "phase": _ACTIVE_PHASE,
        "sub_phase": _ACTIVE_SUB_PHASE,
        "task": _ACTIVE_TASK,
        "status": agent_loop.DISTILLATION_ELIGIBLE_STATUS,
        "cycle_count": 1,
        "max_cycles": 3,
        "last_verdict": agent_loop.DISTILLATION_ELIGIBLE_VERDICT,
        "last_verdict_phase": _ACTIVE_SUB_PHASE,
        "contract_version": "phase-3a-v2",
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": agent_loop.APPROVAL_MODE_REVIEW,
        "awaiting_human_for": "phase_complete_awaiting_human_approval",
    }
    data.update(overrides)
    return data


_VALID_CLAUDE_SUMMARY = """# Claude Implementation Summary

## Phase
Phase 6I - Phase-Boundary Memory Distillation Initial Slice

## Task
Implement phase-boundary memory distillation.

## Files changed
- scripts/agent_loop.py: distillation block added.

## What was implemented
- distillation function

## What was not implemented
- broader optional context loading

## Tests added or changed
- tests/test_phase_boundary_distillation.py

## Validation run
- python -m pytest tests/test_phase_boundary_distillation.py -q

## Assumptions
- None

## Risk areas
- None identified
"""


_VALID_CODEX_REVIEW = """# Codex Review

## Verdict
APPROVED_FOR_HUMAN_REVIEW

## Review summary
The implementation looks correct.

## Claude summary accuracy
Accurate

## Scope control
In scope

## Validation result
Passed

## Issues found
None
"""


class _DistillationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.al = self.repo_root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        self.state_path = self.al / "loop-state.json"
        self.log_path = self.al / "orchestrator.log"
        self.claude_summary_path = self.al / "claude-summary.md"
        self.codex_review_path = self.al / "codex-review.md"
        self.memory_dir = self.repo_root / agent_loop.MEMORY_DIR_REL
        self.summary_dir = (
            self.memory_dir / agent_loop.MEMORY_CATEGORY_SUMMARY
        )
        self.decision_dir = (
            self.memory_dir / agent_loop.MEMORY_CATEGORY_DECISION
        )
        self.failure_dir = (
            self.memory_dir / agent_loop.MEMORY_CATEGORY_FAILURE
        )

    def _write_state(self, **overrides) -> dict:
        data = _baseline_boundary_state(**overrides)
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return data

    def _state_on_disk(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _plant_sources(
        self,
        claude_summary: str = _VALID_CLAUDE_SUMMARY,
        codex_review: str = _VALID_CODEX_REVIEW,
    ) -> None:
        self.claude_summary_path.write_text(claude_summary, encoding="utf-8")
        self.codex_review_path.write_text(codex_review, encoding="utf-8")

    def _setup_boundary(self, **state_overrides) -> dict:
        data = self._write_state(**state_overrides)
        self._plant_sources()
        return data

    def _read_entry(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))


# ----- distill_phase_boundary_memory: success shape -----


class DistillationSuccessShapeTests(_DistillationTestCase):

    def test_first_cycle_writes_summary_and_decision_entries(self) -> None:
        # cycle_count == 1: no fix cycles were required, so the
        # conditional `failure` entry is NOT written. Exactly two
        # entries land on disk.
        self._setup_boundary(cycle_count=1)
        written = agent_loop.distill_phase_boundary_memory(
            self.repo_root, log_path=self.log_path,
        )
        self.assertEqual(len(written), 2)
        self.assertEqual(written[0].parent, self.summary_dir)
        self.assertEqual(written[1].parent, self.decision_dir)
        # No failure entry directory was created.
        self.assertFalse(self.failure_dir.exists())

    def test_multi_cycle_writes_summary_decision_and_failure_entries(
        self,
    ) -> None:
        # cycle_count > 1: at least one fix cycle was required before
        # APPROVED, so the failure entry codifies the retry lesson.
        self._setup_boundary(cycle_count=3)
        written = agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(len(written), 3)
        self.assertEqual(written[0].parent, self.summary_dir)
        self.assertEqual(written[1].parent, self.decision_dir)
        self.assertEqual(written[2].parent, self.failure_dir)

    def test_each_entry_body_carries_distillation_signal_version(
        self,
    ) -> None:
        self._setup_boundary(cycle_count=3)
        written = agent_loop.distill_phase_boundary_memory(self.repo_root)
        for path in written:
            envelope = self._read_entry(path)
            body = json.loads(envelope["body"])
            self.assertEqual(
                body[agent_loop.DISTILLATION_BODY_MARKER_FIELD],
                agent_loop.DISTILLATION_SIGNAL_VERSION,
            )

    def test_each_entry_body_records_source_artifact_references(
        self,
    ) -> None:
        # Per the Phase 6I contract, every distilled entry must point
        # at the canonical source artifacts so later retrieval can
        # trace provenance.
        self._setup_boundary()
        written = agent_loop.distill_phase_boundary_memory(self.repo_root)
        expected = list(agent_loop.DISTILLATION_SOURCE_ARTIFACTS)
        for path in written:
            body = json.loads(self._read_entry(path)["body"])
            self.assertEqual(body["source_artifacts"], expected)
            # Both bounded excerpt blocks are present on every entry.
            self.assertIn("claude_summary_excerpt", body)
            self.assertIn("codex_review_excerpt", body)

    def test_summary_decision_failure_carry_different_knowledge_types(
        self,
    ) -> None:
        self._setup_boundary(cycle_count=2)
        written = agent_loop.distill_phase_boundary_memory(self.repo_root)
        types = [
            json.loads(self._read_entry(p)["body"])["knowledge_type"]
            for p in written
        ]
        self.assertEqual(types, ["summary", "decision", "failure"])

    def test_audit_log_records_the_distillation(self) -> None:
        self._setup_boundary(cycle_count=2)
        agent_loop.distill_phase_boundary_memory(
            self.repo_root, log_path=self.log_path,
        )
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("phase-boundary distillation:", log_text)
        self.assertIn(
            f"signal_version='{agent_loop.DISTILLATION_SIGNAL_VERSION}'",
            log_text,
        )
        self.assertIn("entries_written=3", log_text)


# ----- distill_phase_boundary_memory: bounded excerpts -----


class DistillationBoundedExcerptsTests(_DistillationTestCase):

    def test_excerpt_bytes_bounded_and_truncation_flag_set(self) -> None:
        # Plant a very large claude-summary so the default excerpt
        # cap triggers truncation. The valid claude-summary requires
        # header order; we add bulk to a section body, not break the
        # header sequence.
        large_body = (
            _VALID_CLAUDE_SUMMARY.replace(
                "- distillation function",
                "- distillation function\n" + ("Y" * 8000),
            )
        )
        self._write_state(cycle_count=1)
        self._plant_sources(claude_summary=large_body)
        written = agent_loop.distill_phase_boundary_memory(
            self.repo_root, excerpt_byte_limit=2000,
        )
        body = json.loads(self._read_entry(written[0])["body"])
        ex = body["claude_summary_excerpt"]
        self.assertEqual(ex["excerpt_byte_size"], 2000)
        self.assertTrue(ex["truncated"])
        self.assertGreater(ex["byte_size_on_disk"], 2000)
        self.assertEqual(body["excerpt_byte_limit_applied"], 2000)

    def test_under_budget_excerpt_not_marked_truncated(self) -> None:
        self._setup_boundary(cycle_count=1)
        written = agent_loop.distill_phase_boundary_memory(
            self.repo_root, excerpt_byte_limit=8192,
        )
        body = json.loads(self._read_entry(written[0])["body"])
        ex = body["claude_summary_excerpt"]
        self.assertFalse(ex["truncated"])

    def test_refuses_on_excerpt_byte_limit_zero(self) -> None:
        self._setup_boundary()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(
                self.repo_root, excerpt_byte_limit=0,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("excerpt_byte_limit", cm.exception.reason)

    def test_refuses_on_excerpt_byte_limit_negative(self) -> None:
        self._setup_boundary()
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.distill_phase_boundary_memory(
                self.repo_root, excerpt_byte_limit=-1,
            )

    def test_refuses_on_excerpt_byte_limit_above_safety_cap(self) -> None:
        self._setup_boundary()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(
                self.repo_root,
                excerpt_byte_limit=(
                    agent_loop.DISTILLATION_MAX_EXCERPT_BYTE_LIMIT + 1
                ),
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn(
            "DISTILLATION_MAX_EXCERPT_BYTE_LIMIT",
            cm.exception.reason,
        )

    def test_refuses_on_excerpt_byte_limit_bool(self) -> None:
        self._setup_boundary()
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.distill_phase_boundary_memory(
                self.repo_root, excerpt_byte_limit=True,
            )


# ----- distill_phase_boundary_memory: refusal modes -----


class DistillationRefusalTests(_DistillationTestCase):

    def test_refuses_when_status_is_not_phase_boundary(self) -> None:
        self._write_state(status="awaiting_claude_implementation")
        self._plant_sources()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("status", cm.exception.reason)

    def test_refuses_when_last_verdict_is_not_approved(self) -> None:
        self._write_state(last_verdict="NEEDS_FIXES")
        self._plant_sources()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("last_verdict", cm.exception.reason)

    def test_refuses_when_loop_state_missing(self) -> None:
        # No loop-state.json on disk.
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.distill_phase_boundary_memory(self.repo_root)

    def test_refuses_on_unsupported_contract_version(self) -> None:
        self._write_state(contract_version="phase-9z-from-the-future")
        self._plant_sources()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(
            cm.exception.status, "halted_contract_version_mismatch",
        )

    def test_refuses_when_claude_summary_missing(self) -> None:
        self._write_state()
        # Plant only codex-review; claude-summary is absent.
        self.codex_review_path.write_text(
            _VALID_CODEX_REVIEW, encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        # validate_claude_summary raises halted_summary_malformed for a
        # missing/empty file by virtue of its header-order check.
        self.assertIn(cm.exception.status, (
            "halted_summary_malformed", "halted_input_missing",
        ))

    def test_refuses_when_codex_review_missing(self) -> None:
        self._write_state()
        self.claude_summary_path.write_text(
            _VALID_CLAUDE_SUMMARY, encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        # The codex-review validator surfaces a parse failure when the
        # file is missing/empty.
        self.assertIn(cm.exception.status, (
            "halted_review_malformed",
            "halted_review_parse_failed",
            "halted_input_missing",
        ))

    def test_refuses_when_review_verdict_disagrees_with_loop_state(
        self,
    ) -> None:
        # loop-state says APPROVED, but on-disk review says
        # NEEDS_FIXES. Defense-in-depth refusal.
        contradictory_review = _VALID_CODEX_REVIEW.replace(
            "APPROVED_FOR_HUMAN_REVIEW", "NEEDS_FIXES",
        )
        self._write_state()
        self._plant_sources(codex_review=contradictory_review)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("contradict", cm.exception.reason)

    def test_refuses_when_claude_summary_phase_header_disagrees(
        self,
    ) -> None:
        # The summary's ## Phase body references a DIFFERENT phase
        # than loop-state, which the existing
        # validate_claude_summary refuses with
        # halted_summary_malformed.
        bad_summary = _VALID_CLAUDE_SUMMARY.replace(
            "Phase 6I - Phase-Boundary Memory Distillation Initial Slice",
            "Phase 5A - Approval Modes Contract",
        )
        self._write_state()
        self._plant_sources(claude_summary=bad_summary)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_summary_malformed")

    def test_refuses_idempotently_on_second_call(self) -> None:
        # First call succeeds; second call against the same
        # (phase, sub_phase, cycle_count) refuses because the
        # idempotency marker is already on disk.
        self._setup_boundary(cycle_count=1)
        agent_loop.distill_phase_boundary_memory(self.repo_root)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("already exists", cm.exception.reason)

    def test_refuses_when_source_artifact_is_unreadable(self) -> None:
        self._setup_boundary()
        real_read_bytes = Path.read_bytes
        target = self.claude_summary_path

        def _side_effect(self_path: Path, *args, **kwargs):
            if self_path.resolve() == target.resolve():
                raise OSError("simulated read failure")
            return real_read_bytes(self_path, *args, **kwargs)

        with mock.patch.object(Path, "read_bytes", _side_effect):
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("unreadable", cm.exception.reason)


# ----- distill_phase_boundary_memory: canonical-precedence -----


class DistillationCanonicalPrecedenceTests(_DistillationTestCase):

    def test_distillation_does_not_mutate_loop_state(self) -> None:
        self._setup_boundary(cycle_count=2)
        before = self.state_path.read_bytes()
        agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_distillation_does_not_mutate_source_artifacts(self) -> None:
        self._setup_boundary(cycle_count=2)
        before_summary = self.claude_summary_path.read_bytes()
        before_review = self.codex_review_path.read_bytes()
        agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(self.claude_summary_path.read_bytes(), before_summary)
        self.assertEqual(self.codex_review_path.read_bytes(), before_review)

    def test_distillation_only_writes_under_memory_dir(self) -> None:
        # Snapshot every file BELOW repo_root before the call (except
        # the memory dir which is the target). After the call, no
        # other file may have changed bytes.
        self._setup_boundary(cycle_count=2)
        snapshot: dict = {}
        for p in self.repo_root.rglob("*"):
            if p.is_file() and self.memory_dir not in p.parents:
                snapshot[p] = p.read_bytes()
        agent_loop.distill_phase_boundary_memory(self.repo_root)
        for p, bytes_before in snapshot.items():
            self.assertEqual(
                p.read_bytes(), bytes_before,
                f"non-memory file mutated by distillation: {p}",
            )

    def test_idempotency_refusal_does_not_partially_extend_memory(
        self,
    ) -> None:
        # The first call writes 3 entries (cycle_count=2 -> failure
        # entry included). The second call refuses; the memory
        # directory must still contain exactly the original 3 entries.
        self._setup_boundary(cycle_count=2)
        first = agent_loop.distill_phase_boundary_memory(self.repo_root)
        self.assertEqual(len(first), 3)
        before_count = sum(
            1 for _ in self.memory_dir.rglob("*.json")
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.distill_phase_boundary_memory(self.repo_root)
        after_count = sum(
            1 for _ in self.memory_dir.rglob("*.json")
        )
        self.assertEqual(before_count, after_count)


# ----- cmd_distill_phase_boundary_memory + main(argv) -----


class CmdDistillationTests(_DistillationTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_subcommand_writes_entries_end_to_end(self) -> None:
        self._setup_boundary(cycle_count=2)
        rc = self._run_main(["distill-phase-boundary-memory"])
        self.assertEqual(rc, 0)
        # Three entries written (summary + decision + failure).
        self.assertTrue(self.summary_dir.is_dir())
        self.assertTrue(self.decision_dir.is_dir())
        self.assertTrue(self.failure_dir.is_dir())
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("phase-boundary distillation:", log_text)

    def test_cli_subcommand_honors_excerpt_limit_override(self) -> None:
        self._setup_boundary(cycle_count=1)
        rc = self._run_main([
            "distill-phase-boundary-memory",
            "--excerpt-byte-limit", "1024",
        ])
        self.assertEqual(rc, 0)
        # Find the summary entry and check the limit was applied.
        summary_files = list(self.summary_dir.glob("*.json"))
        self.assertEqual(len(summary_files), 1)
        body = json.loads(
            json.loads(
                summary_files[0].read_text(encoding="utf-8"),
            )["body"],
        )
        self.assertEqual(body["excerpt_byte_limit_applied"], 1024)

    def test_cli_subcommand_refuses_on_ineligible_status(self) -> None:
        # Non-boundary loop-state. The CLI handler routes the HaltError
        # through _halt; loop-state.json gets the structural failure
        # vocabulary.
        self._write_state(status="awaiting_claude_implementation")
        self._plant_sources()
        rc = self._run_main(["distill-phase-boundary-memory"])
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        self.assertEqual(after["status"], "halted_input_missing")
        # No memory entries were written.
        self.assertFalse(self.summary_dir.exists())

    def test_cli_subcommand_refuses_on_invalid_limit_flag(self) -> None:
        self._setup_boundary()
        rc = self._run_main([
            "distill-phase-boundary-memory",
            "--excerpt-byte-limit", "0",
        ])
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        self.assertEqual(after["status"], "halted_input_missing")
        self.assertFalse(self.summary_dir.exists())


if __name__ == "__main__":
    unittest.main()
