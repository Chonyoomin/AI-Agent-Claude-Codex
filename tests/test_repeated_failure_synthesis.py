"""Focused tests for the Phase 6L repeated-failure memory synthesis
slice.

Scope of this suite (Phase 6L, narrow):
- `synthesize_repeated_failures(repo_root, *, min_entries,
  max_source_entries, log_path)` reads the existing
  `failure`-category memory entries that match the active loop-state
  (phase, sub_phase) and writes a NEW append-mostly `failure` memory
  entry carrying a `synthesis_signal_version = "phase-6l-v1"` body
  marker plus the ordered list of source memory entry paths.
- The synthesis source set is restricted to entries that match the
  active (phase, sub_phase) and that do NOT themselves carry the 6L
  marker (no synthesis-of-syntheses).
- Refusal modes (all `halted_input_missing`): missing or malformed
  loop-state; unsupported `contract_version`
  (`halted_contract_version_mismatch`); fewer than `min_entries`
  matching source entries on disk; an existing 6L synthesis entry
  already on disk for the same (phase, sub_phase, source-set)
  identity; out-of-bound `min_entries` or `max_source_entries`
  (below 2, above the cap, non-int, bool); `max_source_entries <
  min_entries`.
- Bounded source-set: at most `max_source_entries` source entries
  feed a single synthesis; when more than the cap match, the newest
  entries (by `cycle_count`, `created_at`) are kept.
- Canonical-precedence preservation: synthesis never mutates
  `loop-state.json`, never mutates any source memory entry, and
  writes only under `.agent-loop/memory/failure/`.
- The `synthesize-repeated-failures` CLI subcommand routes through
  `main(argv)` HANDLERS dispatch and persists the new memory entry
  via the shipped Phase 6B `write_memory_entry` plumbing.

This slice does not implement arbitrary repo-file ingestion, raw
log / transcript ingestion, framework-backed runtime paths, or any
widening of Phase 5 autonomy.
"""

from __future__ import annotations

import json
import sys
import time
import unittest
import unittest.mock as mock
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


_ACTIVE_PHASE = "Phase 6 - Durable Memory and Optional Context Layer"
_ACTIVE_SUB_PHASE = (
    "Phase 6L - Repeated-Failure Memory Synthesis Initial Slice"
)
_ACTIVE_TASK = "Implement repeated-failure memory synthesis."


def _baseline_state(**overrides) -> dict:
    """Loop-state shape the synthesis reads. The status / verdict
    fields are not constrained by 6L (the synthesis can fire at any
    point in the cycle), but the contract version and required keys
    must validate.
    """
    data = {
        "phase": _ACTIVE_PHASE,
        "sub_phase": _ACTIVE_SUB_PHASE,
        "task": _ACTIVE_TASK,
        "status": "awaiting_claude_implementation",
        "cycle_count": 3,
        "max_cycles": 5,
        "last_verdict": None,
        "last_verdict_phase": None,
        "contract_version": "phase-3a-v2",
        "claude_version": "claude-opus-4-7",
        "codex_version": None,
        "orchestrator_version": "phase-3d-v0",
        "approval_mode": agent_loop.APPROVAL_MODE_REVIEW,
        "awaiting_human_for": None,
    }
    data.update(overrides)
    return data


class _SynthesisTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name).resolve()
        self.al = self.repo_root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        self.state_path = self.al / "loop-state.json"
        self.log_path = self.al / "orchestrator.log"
        self.memory_dir = self.repo_root / agent_loop.MEMORY_DIR_REL
        self.failure_dir = (
            self.memory_dir / agent_loop.MEMORY_CATEGORY_FAILURE
        )

    def _write_state(self, **overrides) -> dict:
        data = _baseline_state(**overrides)
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return data

    def _plant_failure_entry(
        self,
        *,
        phase: Optional[str] = None,
        sub_phase: Optional[str] = None,
        cycle_count: int = 1,
        body_extra: Optional[dict] = None,
        synthesis_marker: bool = False,
    ) -> Path:
        """Append-mostly: write one Phase 6B failure memory entry.
        Uses the shipped `write_memory_entry` so the on-disk
        envelope is structurally valid. Sleeps a microsecond between
        calls so the deterministic filename does not collide for
        same-second writes (matches the producer's hash-tail
        determinism)."""
        phase = phase if phase is not None else _ACTIVE_PHASE
        sub_phase = (
            sub_phase if sub_phase is not None else _ACTIVE_SUB_PHASE
        )
        body: dict = {
            "knowledge_type": "failure",
            "cycle_count": cycle_count,
            "failure": (
                f"phase {phase!r} sub_phase {sub_phase!r} cycle "
                f"{cycle_count} required fix cycle"
            ),
        }
        if synthesis_marker:
            body[agent_loop.REPEATED_FAILURE_BODY_MARKER_FIELD] = (
                agent_loop.REPEATED_FAILURE_SIGNAL_VERSION
            )
            body["source_memory_entries"] = []
        if body_extra:
            body.update(body_extra)
        path = agent_loop.write_memory_entry(
            self.repo_root,
            category=agent_loop.MEMORY_CATEGORY_FAILURE,
            phase=phase,
            sub_phase=sub_phase,
            cycle_count=cycle_count,
            source_artifact_path=".agent-loop/loop-state.json",
            body=json.dumps(body),
        )
        return path

    def _read_entry(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))


# ----- synthesize_repeated_failures: success shape -----


class SynthesizeSuccessShapeTests(_SynthesisTestCase):

    def test_writes_new_failure_entry_under_failure_dir(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        path = agent_loop.synthesize_repeated_failures(
            self.repo_root, log_path=self.log_path,
        )
        self.assertEqual(path.parent, self.failure_dir)
        self.assertTrue(path.is_file())

    def test_entry_body_carries_synthesis_signal_version(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        path = agent_loop.synthesize_repeated_failures(self.repo_root)
        envelope = self._read_entry(path)
        body = json.loads(envelope["body"])
        self.assertEqual(
            body[agent_loop.REPEATED_FAILURE_BODY_MARKER_FIELD],
            agent_loop.REPEATED_FAILURE_SIGNAL_VERSION,
        )

    def test_entry_body_records_source_memory_entries(self) -> None:
        self._write_state()
        a = self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        b = self._plant_failure_entry(cycle_count=2)
        path = agent_loop.synthesize_repeated_failures(self.repo_root)
        body = json.loads(self._read_entry(path)["body"])
        rel_a = a.relative_to(self.repo_root).as_posix()
        rel_b = b.relative_to(self.repo_root).as_posix()
        self.assertEqual(
            body["source_memory_entries"], [rel_a, rel_b],
        )
        self.assertEqual(body["source_count"], 2)
        self.assertEqual(body["source_cycle_counts"], [1, 2])

    def test_entry_body_records_phase_sub_phase_task_from_loop_state(
        self,
    ) -> None:
        self._write_state(cycle_count=5)
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        path = agent_loop.synthesize_repeated_failures(self.repo_root)
        body = json.loads(self._read_entry(path)["body"])
        self.assertEqual(body["phase"], _ACTIVE_PHASE)
        self.assertEqual(body["sub_phase"], _ACTIVE_SUB_PHASE)
        self.assertEqual(body["task"], _ACTIVE_TASK)
        self.assertEqual(body["cycle_count"], 5)
        self.assertEqual(body["knowledge_type"], "failure")

    def test_entry_body_carries_canonical_precedence_note(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        path = agent_loop.synthesize_repeated_failures(self.repo_root)
        body = json.loads(self._read_entry(path)["body"])
        self.assertEqual(
            body["canonical_precedence_note"],
            agent_loop.REPEATED_FAILURE_CANONICAL_PRECEDENCE_NOTE,
        )

    def test_entry_body_records_applied_bounds(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=3)
        path = agent_loop.synthesize_repeated_failures(
            self.repo_root, min_entries=3, max_source_entries=5,
        )
        body = json.loads(self._read_entry(path)["body"])
        self.assertEqual(body["min_entries_applied"], 3)
        self.assertEqual(body["max_source_entries_applied"], 5)

    def test_audit_log_line_lands_when_log_path_supplied(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        agent_loop.synthesize_repeated_failures(
            self.repo_root, log_path=self.log_path,
        )
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("repeated-failure synthesis:", log_text)
        self.assertIn("phase-6l-v1", log_text)

    def test_audit_log_byte_equivalent_when_log_path_omitted(
        self,
    ) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        before = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        agent_loop.synthesize_repeated_failures(self.repo_root)
        after = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        self.assertEqual(before, after)


# ----- synthesize_repeated_failures: bounds validation -----


class SynthesizeBoundsValidationTests(_SynthesisTestCase):

    def test_refuses_min_entries_below_two(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(
                self.repo_root, min_entries=1,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("min_entries", cm.exception.reason)

    def test_refuses_min_entries_above_cap(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.synthesize_repeated_failures(
                self.repo_root,
                min_entries=(
                    agent_loop.REPEATED_FAILURE_MAX_MIN_ENTRIES + 1
                ),
            )

    def test_refuses_min_entries_bool(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.synthesize_repeated_failures(
                self.repo_root, min_entries=True,
            )

    def test_refuses_min_entries_non_int(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.synthesize_repeated_failures(
                self.repo_root, min_entries="2",
            )

    def test_refuses_max_source_entries_below_two(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(
                self.repo_root, max_source_entries=1,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("max_source_entries", cm.exception.reason)

    def test_refuses_max_source_entries_above_cap(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.synthesize_repeated_failures(
                self.repo_root,
                max_source_entries=(
                    agent_loop.REPEATED_FAILURE_MAX_MAX_SOURCE_ENTRIES
                    + 1
                ),
            )

    def test_refuses_max_source_entries_bool(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.synthesize_repeated_failures(
                self.repo_root, max_source_entries=True,
            )

    def test_refuses_max_source_entries_below_min_entries(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=3)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=4)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(
                self.repo_root, min_entries=4, max_source_entries=3,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("max_source_entries", cm.exception.reason)
        self.assertIn("min_entries", cm.exception.reason)

    def test_caps_source_set_at_max_source_entries(self) -> None:
        # Plant 5 entries; cap to 3. The newest 3 (by cycle_count,
        # created_at) must be kept.
        self._write_state()
        for cc in range(1, 6):
            self._plant_failure_entry(cycle_count=cc)
            time.sleep(0.01)
        path = agent_loop.synthesize_repeated_failures(
            self.repo_root, max_source_entries=3,
        )
        body = json.loads(self._read_entry(path)["body"])
        self.assertEqual(body["source_count"], 3)
        self.assertEqual(body["source_cycle_counts"], [3, 4, 5])


# ----- synthesize_repeated_failures: source-set selection -----


class SynthesizeSourceSelectionTests(_SynthesisTestCase):

    def test_refuses_when_no_failure_entries_on_disk(self) -> None:
        self._write_state()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("only 0", cm.exception.reason)

    def test_refuses_when_below_default_min_entries(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("min_entries=2", cm.exception.reason)

    def test_refuses_when_below_custom_min_entries(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(
                self.repo_root, min_entries=3,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("min_entries=3", cm.exception.reason)

    def test_excludes_entries_from_different_phase(self) -> None:
        # Only 6 entries total: 2 match active phase, 4 are for a
        # different phase. With the default min_entries=2 the
        # synthesis succeeds on the matching pair only.
        self._write_state()
        for cc in range(1, 5):
            self._plant_failure_entry(
                cycle_count=cc, phase="Phase 99 - Different",
            )
            time.sleep(0.01)
        a = self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        b = self._plant_failure_entry(cycle_count=2)
        path = agent_loop.synthesize_repeated_failures(self.repo_root)
        body = json.loads(self._read_entry(path)["body"])
        self.assertEqual(body["source_count"], 2)
        rel_a = a.relative_to(self.repo_root).as_posix()
        rel_b = b.relative_to(self.repo_root).as_posix()
        self.assertEqual(
            body["source_memory_entries"], [rel_a, rel_b],
        )

    def test_excludes_entries_from_different_sub_phase(self) -> None:
        self._write_state()
        # Two for the active sub_phase, two for a different one.
        self._plant_failure_entry(
            cycle_count=1, sub_phase="Phase 6X - Different Sub-Phase",
        )
        time.sleep(0.01)
        self._plant_failure_entry(
            cycle_count=2, sub_phase="Phase 6X - Different Sub-Phase",
        )
        time.sleep(0.01)
        a = self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        b = self._plant_failure_entry(cycle_count=2)
        path = agent_loop.synthesize_repeated_failures(self.repo_root)
        body = json.loads(self._read_entry(path)["body"])
        self.assertEqual(body["source_count"], 2)
        rel_a = a.relative_to(self.repo_root).as_posix()
        rel_b = b.relative_to(self.repo_root).as_posix()
        self.assertEqual(
            body["source_memory_entries"], [rel_a, rel_b],
        )

    def test_excludes_prior_6l_synthesis_entries(self) -> None:
        # Plant two regular failure entries + one prior 6L synthesis
        # entry. The synthesis layer must stay flat: the prior 6L
        # entry is NOT a source for the new synthesis.
        self._write_state()
        a = self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        b = self._plant_failure_entry(cycle_count=2)
        time.sleep(0.01)
        self._plant_failure_entry(
            cycle_count=3, synthesis_marker=True,
        )
        path = agent_loop.synthesize_repeated_failures(self.repo_root)
        body = json.loads(self._read_entry(path)["body"])
        self.assertEqual(body["source_count"], 2)
        rel_a = a.relative_to(self.repo_root).as_posix()
        rel_b = b.relative_to(self.repo_root).as_posix()
        self.assertEqual(
            body["source_memory_entries"], [rel_a, rel_b],
        )

    def test_includes_6i_distillation_failure_entries(self) -> None:
        # A Phase 6I distillation failure entry carries a
        # `distillation_signal_version` body marker but NOT the 6L
        # marker. It IS a valid source for the 6L synthesis.
        self._write_state()
        a = self._plant_failure_entry(
            cycle_count=1,
            body_extra={
                agent_loop.DISTILLATION_BODY_MARKER_FIELD: (
                    agent_loop.DISTILLATION_SIGNAL_VERSION
                ),
            },
        )
        time.sleep(0.01)
        b = self._plant_failure_entry(cycle_count=2)
        path = agent_loop.synthesize_repeated_failures(self.repo_root)
        body = json.loads(self._read_entry(path)["body"])
        self.assertEqual(body["source_count"], 2)
        rel_a = a.relative_to(self.repo_root).as_posix()
        rel_b = b.relative_to(self.repo_root).as_posix()
        self.assertEqual(
            body["source_memory_entries"], [rel_a, rel_b],
        )


# ----- synthesize_repeated_failures: loop-state refusal -----


class SynthesizeLoopStateRefusalTests(_SynthesisTestCase):

    def test_refuses_when_loop_state_missing(self) -> None:
        # No state planted.
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")

    def test_refuses_on_unsupported_contract_version(self) -> None:
        self._write_state(contract_version="phase-9z-vX")
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(
            cm.exception.status, "halted_contract_version_mismatch",
        )

    def test_refuses_when_loop_state_missing_required_field(self) -> None:
        data = _baseline_state()
        del data["phase"]
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")


# ----- synthesize_repeated_failures: idempotency -----


class SynthesizeIdempotencyTests(_SynthesisTestCase):

    def test_refuses_repeat_call_with_identical_source_set(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        agent_loop.synthesize_repeated_failures(self.repo_root)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("source-set", cm.exception.reason)

    def test_succeeds_after_new_failure_entry_added(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        first = agent_loop.synthesize_repeated_failures(self.repo_root)
        # Add a fresh non-synthesis failure entry; the source-set
        # changes and a new synthesis is permitted.
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=3)
        second = agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())

    def test_refuses_when_existing_6l_entry_has_malformed_sources(
        self,
    ) -> None:
        # Plant a 6L-marked entry whose body has `source_memory_entries`
        # set to a non-list value. The idempotency probe must refuse
        # rather than silently skip it.
        self._write_state()
        a = self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        b = self._plant_failure_entry(cycle_count=2)
        time.sleep(0.01)
        # Manually craft a 6L-marked envelope with bad sources field.
        bad_body = json.dumps({
            agent_loop.REPEATED_FAILURE_BODY_MARKER_FIELD: (
                agent_loop.REPEATED_FAILURE_SIGNAL_VERSION
            ),
            "source_memory_entries": "not-a-list",
            "knowledge_type": "failure",
        })
        agent_loop.write_memory_entry(
            self.repo_root,
            category=agent_loop.MEMORY_CATEGORY_FAILURE,
            phase=_ACTIVE_PHASE,
            sub_phase=_ACTIVE_SUB_PHASE,
            cycle_count=99,
            source_artifact_path=".agent-loop/loop-state.json",
            body=bad_body,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("source_memory_entries", cm.exception.reason)
        # The two original sources are untouched.
        self.assertTrue(a.is_file())
        self.assertTrue(b.is_file())


# ----- synthesize_repeated_failures: canonical-precedence -----


class SynthesizeCanonicalPrecedenceTests(_SynthesisTestCase):

    def test_does_not_mutate_loop_state(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        before = self.state_path.read_bytes()
        agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_does_not_mutate_source_memory_entries(self) -> None:
        self._write_state()
        a = self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        b = self._plant_failure_entry(cycle_count=2)
        a_before = a.read_bytes()
        b_before = b.read_bytes()
        agent_loop.synthesize_repeated_failures(self.repo_root)
        self.assertEqual(a.read_bytes(), a_before)
        self.assertEqual(b.read_bytes(), b_before)

    def test_writes_only_under_failure_memory_dir(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        # Snapshot every file outside the failure dir before the
        # call.
        snapshot: dict = {}
        for p in self.repo_root.rglob("*"):
            if p.is_file():
                try:
                    p.relative_to(self.failure_dir)
                except ValueError:
                    snapshot[p] = p.read_bytes()
        agent_loop.synthesize_repeated_failures(self.repo_root)
        for p, before in snapshot.items():
            self.assertEqual(p.read_bytes(), before, f"mutated {p}")


# ----- cmd_synthesize_repeated_failures + main(argv) -----


class CmdSynthesizeRepeatedFailuresTests(_SynthesisTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_writes_synthesis_entry(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        rc = self._run_main(["synthesize-repeated-failures"])
        self.assertEqual(rc, 0)
        # Failure dir now contains 3 entries: 2 sources + 1 synthesis.
        entries = sorted(self.failure_dir.iterdir())
        self.assertEqual(len(entries), 3)

    def test_cli_honors_min_entries_override(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        rc = self._run_main([
            "synthesize-repeated-failures", "--min-entries", "3",
        ])
        # Only 2 matching sources; min=3 -> refuse via _halt -> rc=2.
        self.assertEqual(rc, 2)

    def test_cli_honors_max_source_entries_override(self) -> None:
        self._write_state()
        for cc in range(1, 6):
            self._plant_failure_entry(cycle_count=cc)
            time.sleep(0.01)
        rc = self._run_main([
            "synthesize-repeated-failures",
            "--max-source-entries", "3",
        ])
        self.assertEqual(rc, 0)
        # The newest synthesis entry records source_count == 3.
        # Pick the most-recently-written failure entry.
        entries = sorted(
            self.failure_dir.iterdir(),
            key=lambda p: p.stat().st_mtime,
        )
        body = json.loads(self._read_entry(entries[-1])["body"])
        self.assertEqual(body["source_count"], 3)

    def test_cli_refuses_on_insufficient_sources(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        rc = self._run_main(["synthesize-repeated-failures"])
        self.assertEqual(rc, 2)

    def test_cli_refuses_on_invalid_min_entries_flag(self) -> None:
        self._write_state()
        self._plant_failure_entry(cycle_count=1)
        time.sleep(0.01)
        self._plant_failure_entry(cycle_count=2)
        rc = self._run_main([
            "synthesize-repeated-failures", "--min-entries", "1",
        ])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
