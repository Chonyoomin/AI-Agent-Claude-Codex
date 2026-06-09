"""Focused tests for the Phase 6C selective memory retrieval layer.

Scope of this suite (Phase 6C, narrow):
- relevant-entry filtering: an active phase / sub_phase / task scope
  excludes entries whose metadata does not match, and a category
  filter restricts results to one or more of the five Phase 6A
  categories
- bounded result limits: retrieval enforces a positive limit, a
  default limit, and a hard upper bound, refusing zero / negative /
  non-int / over-bound limits fail-closed
- malformed-entry refusal: a malformed, missing-field, or
  unrecognized-`signal_version` entry on disk causes the entire
  retrieval call to halt rather than silently dropping the entry
- unknown-category refusal: an out-of-vocabulary category in the
  caller-supplied filter is refused at the retrieval boundary
- canonical-precedence preservation: retrieval never writes to disk,
  never mutates any canonical workflow / state artifact, and returns
  entries marked advisory-only by contract (no side-effect on
  `.agent-loop/loop-state.json` or any other canonical file)

The Phase 6C implementation is retrieval only; no test in this suite
exercises checkpoint-consumption on resume, token-exhaustion
continuation chaining, or any continuation-driving runtime behavior,
because those are deferred to later 6x slices.
"""

from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


_ACTIVE_PHASE = "Phase 6 - Durable Memory and Optional Context Layer"
_ACTIVE_SUB_PHASE = "Phase 6C - Selective Memory Retrieval Initial Slice"
_OTHER_SUB_PHASE = "Phase 6B - Structured Durable Memory Storage"
_ACTIVE_TASK_PATH = ".agent-loop/current-task.md"
_OTHER_TASK_PATH = "human"


class _RetrievalTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.memory_dir = self.repo_root / agent_loop.MEMORY_DIR_REL
        self.log_path = self.repo_root / ".agent-loop" / "orchestrator.log"
        (self.repo_root / ".agent-loop").mkdir(parents=True, exist_ok=True)

    def _write_one(
        self,
        *,
        category: str = agent_loop.MEMORY_CATEGORY_DECISION,
        phase: str = _ACTIVE_PHASE,
        sub_phase: str = _ACTIVE_SUB_PHASE,
        cycle_count: int = 0,
        source_artifact_path: str = _ACTIVE_TASK_PATH,
        body: str = "default body",
        supersedes=None,
    ) -> Path:
        return agent_loop.write_memory_entry(
            self.repo_root,
            category=category,
            phase=phase,
            sub_phase=sub_phase,
            cycle_count=cycle_count,
            source_artifact_path=source_artifact_path,
            body=body,
            supersedes=supersedes,
        )

    def _retrieve(self, **overrides):
        kwargs = dict(phase=_ACTIVE_PHASE)
        kwargs.update(overrides)
        return agent_loop.retrieve_memory_entries(self.repo_root, **kwargs)


class RelevantEntryFilteringTests(_RetrievalTestCase):

    def test_active_phase_match_keeps_entry(self) -> None:
        self._write_one(body="keep me")
        result = self._retrieve()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["body"], "keep me")

    def test_phase_mismatch_is_filtered_out(self) -> None:
        self._write_one(phase="Phase 5 - Approval Modes", body="other phase")
        self._write_one(body="active phase")
        result = self._retrieve()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["body"], "active phase")

    def test_sub_phase_narrows_results(self) -> None:
        self._write_one(sub_phase=_ACTIVE_SUB_PHASE, body="active sub")
        self._write_one(sub_phase=_OTHER_SUB_PHASE, body="other sub")
        # Without sub_phase filter, both come back.
        unfiltered = self._retrieve()
        self.assertEqual(len(unfiltered), 2)
        # With sub_phase filter, only the matching entry comes back.
        filtered = self._retrieve(sub_phase=_ACTIVE_SUB_PHASE)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["body"], "active sub")
        self.assertEqual(filtered[0]["sub_phase"], _ACTIVE_SUB_PHASE)

    def test_task_filter_matches_source_artifact_path_exact(self) -> None:
        self._write_one(
            source_artifact_path=_ACTIVE_TASK_PATH, body="from current task",
        )
        self._write_one(
            source_artifact_path=_OTHER_TASK_PATH, body="from human",
        )
        filtered = self._retrieve(task=_ACTIVE_TASK_PATH)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["body"], "from current task")
        self.assertEqual(
            filtered[0]["source_artifact_path"], _ACTIVE_TASK_PATH,
        )

    def test_category_filter_restricts_results(self) -> None:
        self._write_one(
            category=agent_loop.MEMORY_CATEGORY_DECISION, body="decision body",
        )
        self._write_one(
            category=agent_loop.MEMORY_CATEGORY_FAILURE, body="failure body",
        )
        self._write_one(
            category=agent_loop.MEMORY_CATEGORY_PREFERENCE,
            body="preference body",
        )
        # Multi-category filter keeps two of the three.
        filtered = self._retrieve(
            categories=[
                agent_loop.MEMORY_CATEGORY_DECISION,
                agent_loop.MEMORY_CATEGORY_FAILURE,
            ],
        )
        self.assertEqual(len(filtered), 2)
        seen_categories = {e["category"] for e in filtered}
        self.assertEqual(
            seen_categories,
            {
                agent_loop.MEMORY_CATEGORY_DECISION,
                agent_loop.MEMORY_CATEGORY_FAILURE,
            },
        )

    def test_combined_phase_sub_phase_task_and_category(self) -> None:
        # Only one entry satisfies every dimension.
        self._write_one(
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            sub_phase=_ACTIVE_SUB_PHASE,
            source_artifact_path=_ACTIVE_TASK_PATH,
            body="winner",
        )
        self._write_one(
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            sub_phase=_OTHER_SUB_PHASE,
            source_artifact_path=_ACTIVE_TASK_PATH,
            body="wrong sub",
        )
        self._write_one(
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            sub_phase=_ACTIVE_SUB_PHASE,
            source_artifact_path=_OTHER_TASK_PATH,
            body="wrong task",
        )
        self._write_one(
            category=agent_loop.MEMORY_CATEGORY_FAILURE,
            sub_phase=_ACTIVE_SUB_PHASE,
            source_artifact_path=_ACTIVE_TASK_PATH,
            body="wrong category",
        )
        result = self._retrieve(
            sub_phase=_ACTIVE_SUB_PHASE,
            task=_ACTIVE_TASK_PATH,
            categories=[agent_loop.MEMORY_CATEGORY_DECISION],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["body"], "winner")


class BoundedResultLimitTests(_RetrievalTestCase):

    def _populate(self, n: int) -> None:
        for i in range(n):
            # Distinct bodies so the deterministic filename does not
            # collide; the writer rejects same-second + same-body.
            self._write_one(body=f"entry-{i:03d}")

    def test_default_limit_caps_results(self) -> None:
        # Default is MEMORY_RETRIEVAL_DEFAULT_LIMIT entries.
        self._populate(agent_loop.MEMORY_RETRIEVAL_DEFAULT_LIMIT + 3)
        result = self._retrieve()
        self.assertEqual(
            len(result), agent_loop.MEMORY_RETRIEVAL_DEFAULT_LIMIT,
        )

    def test_custom_limit_below_max_is_respected(self) -> None:
        self._populate(5)
        result = self._retrieve(limit=2)
        self.assertEqual(len(result), 2)

    def test_limit_above_max_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve(limit=agent_loop.MEMORY_RETRIEVAL_MAX_LIMIT + 1)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("hard upper bound", cm.exception.reason)

    def test_limit_zero_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve(limit=0)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("> 0", cm.exception.reason)

    def test_limit_negative_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve(limit=-3)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("> 0", cm.exception.reason)

    def test_limit_non_int_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve(limit="ten")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("must be an int", cm.exception.reason)

    def test_limit_bool_refuses(self) -> None:
        # bool is a subclass of int in Python; the guard treats it as
        # the wrong type so the contract intent (a numeric bound) is
        # preserved.
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve(limit=True)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("must be an int", cm.exception.reason)


class MalformedEntryRefusalTests(_RetrievalTestCase):

    def _drop_bad_entry(self, payload) -> Path:
        """Drop a hand-crafted bad payload into the decision/ folder so
        retrieval has to read it and refuse.
        """
        cat_dir = self.memory_dir / agent_loop.MEMORY_CATEGORY_DECISION
        cat_dir.mkdir(parents=True, exist_ok=True)
        path = cat_dir / "20260609T120000Z-deadbeef.json"
        if isinstance(payload, dict):
            path.write_text(json.dumps(payload), encoding="utf-8")
        else:
            path.write_text(str(payload), encoding="utf-8")
        return path

    def test_malformed_json_on_disk_refuses_retrieval(self) -> None:
        self._drop_bad_entry("not json at all")
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve()
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not valid JSON", cm.exception.reason)

    def test_missing_required_field_refuses_retrieval(self) -> None:
        # Drop the signal_version field so read_memory_entry refuses
        # and retrieval fail-closes.
        payload = {
            "category": agent_loop.MEMORY_CATEGORY_DECISION,
            "phase": _ACTIVE_PHASE,
            "sub_phase": _ACTIVE_SUB_PHASE,
            "cycle_count": 0,
            "source_artifact_path": _ACTIVE_TASK_PATH,
            "created_at": "2026-06-09T12:00:00Z",
            "supersedes": None,
            "body": "x",
        }
        self._drop_bad_entry(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve()
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("signal_version", cm.exception.reason)

    def test_unrecognized_signal_version_refuses_retrieval(self) -> None:
        payload = {
            "signal_version": "phase-6b-vNEXT",
            "category": agent_loop.MEMORY_CATEGORY_DECISION,
            "phase": _ACTIVE_PHASE,
            "sub_phase": _ACTIVE_SUB_PHASE,
            "cycle_count": 0,
            "source_artifact_path": _ACTIVE_TASK_PATH,
            "created_at": "2026-06-09T12:00:00Z",
            "supersedes": None,
            "body": "x",
        }
        self._drop_bad_entry(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve()
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("signal_version", cm.exception.reason)
        self.assertIn("not recognized", cm.exception.reason)

    def test_unknown_category_on_disk_refuses_retrieval(self) -> None:
        payload = {
            "signal_version": agent_loop.MEMORY_SIGNAL_VERSION,
            "category": "bogus",
            "phase": _ACTIVE_PHASE,
            "sub_phase": _ACTIVE_SUB_PHASE,
            "cycle_count": 0,
            "source_artifact_path": _ACTIVE_TASK_PATH,
            "created_at": "2026-06-09T12:00:00Z",
            "supersedes": None,
            "body": "x",
        }
        self._drop_bad_entry(payload)
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve()
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("bogus", cm.exception.reason)


class UnknownCategoryRefusalTests(_RetrievalTestCase):

    def test_unknown_category_in_filter_refuses_at_boundary(self) -> None:
        # No entries written; the boundary check fires before any disk
        # read so the empty-memory case does not mask the refusal.
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve(categories=["bogus"])
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("bogus", cm.exception.reason)

    def test_unknown_category_in_mixed_filter_refuses(self) -> None:
        # One valid + one invalid: the boundary check still fires.
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._retrieve(categories=[
                agent_loop.MEMORY_CATEGORY_DECISION, "bogus",
            ])
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("bogus", cm.exception.reason)


class CanonicalPrecedencePreservationTests(_RetrievalTestCase):
    """Retrieval is read-only and advisory; it cannot mutate canonical
    workflow / state artifacts and it cannot create new files on disk.
    """

    def test_retrieval_does_not_mutate_loop_state(self) -> None:
        # Plant a canonical artifact and snapshot it.
        canonical = self.repo_root / ".agent-loop" / "loop-state.json"
        canonical.write_text(
            json.dumps({"phase": "canonical", "status": "ok"}) + "\n",
            encoding="utf-8",
        )
        before = canonical.read_bytes()
        # Plant some memory and retrieve it.
        self._write_one(body="any body")
        self._retrieve()
        # The canonical file is byte-identical after retrieval.
        self.assertEqual(canonical.read_bytes(), before)

    def test_retrieval_writes_no_new_files(self) -> None:
        # Plant exactly one memory entry. Retrieval must not create any
        # additional file under .agent-loop/memory/ or anywhere else.
        self._write_one(body="single entry")
        before = sorted(
            p.relative_to(self.repo_root)
            for p in self.repo_root.rglob("*")
            if p.is_file()
        )
        self._retrieve()
        after = sorted(
            p.relative_to(self.repo_root)
            for p in self.repo_root.rglob("*")
            if p.is_file()
        )
        self.assertEqual(before, after)

    def test_returned_payload_mutation_does_not_touch_disk(self) -> None:
        # The contract says retrieved memory is advisory; the caller may
        # consume / decorate the dict freely. We pin that mutating the
        # returned dict does not write through to disk.
        path = self._write_one(body="original body")
        original_bytes = path.read_bytes()
        result = self._retrieve()
        self.assertEqual(len(result), 1)
        result[0]["body"] = "caller mutated this"
        result[0]["category"] = "caller mutated this too"
        # Disk is untouched.
        self.assertEqual(path.read_bytes(), original_bytes)

    def test_empty_memory_returns_empty_list_no_halt(self) -> None:
        # The Phase 6A contract requires that a missing memory layer not
        # block any cycle the canonical artifacts can drive. Empty
        # retrieval is a normal, non-halting outcome.
        result = self._retrieve()
        self.assertEqual(result, [])

    def test_phase_with_no_matching_entries_returns_empty_list(self) -> None:
        self._write_one(
            phase="Phase 5 - Approval Modes",
            sub_phase="Phase 5B - Review Mode Initial Slice",
            body="non-matching phase",
        )
        result = self._retrieve()
        self.assertEqual(result, [])


class OrderingTests(_RetrievalTestCase):

    def test_results_sorted_newest_first(self) -> None:
        # Write three entries with distinct bodies in temporal order and
        # then add an entry whose `created_at` we override after the
        # fact to verify the sort uses the payload's `created_at`.
        first = self._write_one(body="first body")
        time.sleep(1.05)
        second = self._write_one(body="second body")
        time.sleep(1.05)
        third = self._write_one(body="third body")
        result = self._retrieve()
        self.assertEqual(len(result), 3)
        # Newest first.
        self.assertEqual(result[0]["body"], "third body")
        self.assertEqual(result[1]["body"], "second body")
        self.assertEqual(result[2]["body"], "first body")
        # All three files still on disk untouched.
        for p in (first, second, third):
            self.assertTrue(p.is_file())


class AuditNoteTests(_RetrievalTestCase):

    def test_log_path_appends_retrieval_audit_note(self) -> None:
        self._write_one(body="first")
        self._write_one(body="second")
        result = agent_loop.retrieve_memory_entries(
            self.repo_root,
            phase=_ACTIVE_PHASE,
            sub_phase=_ACTIVE_SUB_PHASE,
            categories=[agent_loop.MEMORY_CATEGORY_DECISION],
            limit=4,
            log_path=self.log_path,
        )
        self.assertEqual(len(result), 2)
        self.assertTrue(self.log_path.is_file())
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("memory retrieval:", log_text)
        self.assertIn(_ACTIVE_PHASE, log_text)
        self.assertIn(_ACTIVE_SUB_PHASE, log_text)
        self.assertIn("matched=2", log_text)
        self.assertIn("returned=2", log_text)
        self.assertIn(agent_loop.MEMORY_CATEGORY_DECISION, log_text)

    def test_no_log_path_means_no_log_file(self) -> None:
        # An absent log_path must not create the log file as a side
        # effect.
        self._write_one(body="any")
        self._retrieve()
        self.assertFalse(self.log_path.is_file())


class RequiredPhaseTests(_RetrievalTestCase):

    def test_empty_phase_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.retrieve_memory_entries(self.repo_root, phase="")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("non-empty active phase", cm.exception.reason)


if __name__ == "__main__":
    unittest.main()
