"""Focused tests for the Phase 6D checkpoint artifact storage layer.

Scope of this suite (Phase 6D, narrow):
- valid writes: a structured checkpoint artifact lands under
  `.agent-loop/memory/checkpoint/`, populates every required
  Phase 6A memory-metadata field, and encodes every required
  checkpoint-specific body field. Every allowed `suspension_reason`
  (the four base reasons plus the four Phase 5C strict-gate halt
  statuses) and every allowed `active_prompt_path` (claude-prompt.md
  and fix-prompt.md) is accepted. A zero `continuation_budget` is
  accepted (it pins "no further continuation without explicit human
  approval").
- malformed-checkpoint write refusal: empty `task`, `status`,
  `approval_mode`; an `awaiting_human_for` that is the wrong type or
  empty string; an out-of-vocabulary `active_prompt_path` or
  `suspension_reason`; a `continuation_budget` that is bool, non-int,
  or negative.
- read-side schema validation: a non-checkpoint category, a missing or
  malformed body, a body missing any required checkpoint-specific
  field, an unrecognized `checkpoint_signal_version`, an out-of-
  vocabulary `active_prompt_path` or `suspension_reason`, and a bad
  `continuation_budget` each refuse fail-closed. The Phase 6B
  read-side memory-metadata refusals still propagate.
- write-boundary enforcement: checkpoint files live only under
  `.agent-loop/memory/checkpoint/`; a checkpoint write does not
  mutate any canonical workflow / state artifact; the listing helper
  returns only checkpoint entries.
- audit-note signature: the existing Phase 6B `memory write:` audit
  note still fires with `category='checkpoint'` when a `log_path` is
  supplied.

The Phase 6D implementation is storage only; no test in this suite
exercises checkpoint-consumption on resume, token-exhaustion
continuation chaining, or any continuation-driving runtime behavior,
because those are deferred to later 6x slices.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


_BASE_KWARGS = dict(
    phase="Phase 6 - Durable Memory and Optional Context Layer",
    sub_phase="Phase 6D - Checkpoint Artifact Storage Initial Slice",
    task="Implement checkpoint artifact storage.",
    cycle_count=0,
    status="awaiting_claude_implementation",
    approval_mode="review",
    awaiting_human_for=None,
    active_prompt_path=".agent-loop/claude-prompt.md",
    suspension_reason="token_exhaustion",
    continuation_budget=2,
    source_artifact_path=".agent-loop/current-task.md",
)


class _CheckpointTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        self.memory_dir = self.repo_root / agent_loop.MEMORY_DIR_REL
        self.checkpoint_dir = (
            self.memory_dir / agent_loop.MEMORY_CATEGORY_CHECKPOINT
        )
        self.log_path = self.repo_root / ".agent-loop" / "orchestrator.log"
        (self.repo_root / ".agent-loop").mkdir(parents=True, exist_ok=True)

    def _write(self, **overrides) -> Path:
        kwargs = dict(_BASE_KWARGS)
        kwargs.update(overrides)
        return agent_loop.write_checkpoint_entry(self.repo_root, **kwargs)


class WriteValidCheckpointTests(_CheckpointTestCase):

    def test_valid_write_creates_entry_under_checkpoint_dir(self) -> None:
        path = self._write()
        self.assertTrue(path.is_file())
        self.assertEqual(path.parent, self.checkpoint_dir)
        self.assertEqual(path.suffix, ".json")

    def test_required_memory_metadata_present_on_disk(self) -> None:
        path = self._write()
        raw = json.loads(path.read_text(encoding="utf-8"))
        # Phase 6B required memory metadata fields.
        for field in agent_loop.MEMORY_REQUIRED_FIELDS:
            self.assertIn(field, raw)
        self.assertEqual(
            raw["category"], agent_loop.MEMORY_CATEGORY_CHECKPOINT,
        )
        self.assertEqual(
            raw["signal_version"], agent_loop.MEMORY_SIGNAL_VERSION,
        )

    def test_required_checkpoint_body_fields_present_on_disk(self) -> None:
        path = self._write()
        raw = json.loads(path.read_text(encoding="utf-8"))
        body = json.loads(raw["body"])
        for field in agent_loop.CHECKPOINT_REQUIRED_BODY_FIELDS:
            self.assertIn(field, body)
        self.assertEqual(
            body["checkpoint_signal_version"],
            agent_loop.CHECKPOINT_SIGNAL_VERSION,
        )

    def test_each_allowed_suspension_reason_accepted(self) -> None:
        for reason in sorted(agent_loop.CHECKPOINT_ALLOWED_SUSPENSION_REASONS):
            with self.subTest(suspension_reason=reason):
                # Use a per-iteration suffix on `task` to make the body
                # text distinct so the deterministic filename hash does
                # not collide within the same wall-clock second.
                path = self._write(
                    suspension_reason=reason,
                    task=f"{_BASE_KWARGS['task']} ({reason})",
                )
                self.assertTrue(path.is_file())
                body = json.loads(
                    json.loads(path.read_text(encoding="utf-8"))["body"],
                )
                self.assertEqual(body["suspension_reason"], reason)

    def test_each_allowed_active_prompt_path_accepted(self) -> None:
        for prompt_path in sorted(agent_loop.CHECKPOINT_ACTIVE_PROMPT_PATHS):
            with self.subTest(active_prompt_path=prompt_path):
                path = self._write(
                    active_prompt_path=prompt_path,
                    task=f"{_BASE_KWARGS['task']} ({prompt_path})",
                )
                self.assertTrue(path.is_file())
                body = json.loads(
                    json.loads(path.read_text(encoding="utf-8"))["body"],
                )
                self.assertEqual(body["active_prompt_path"], prompt_path)

    def test_continuation_budget_zero_accepted(self) -> None:
        # Zero means "no further continuation is permitted without
        # explicit human approval"; the value is still recordable.
        path = self._write(continuation_budget=0)
        self.assertTrue(path.is_file())
        body = json.loads(
            json.loads(path.read_text(encoding="utf-8"))["body"],
        )
        self.assertEqual(body["continuation_budget"], 0)

    def test_awaiting_human_for_none_accepted(self) -> None:
        path = self._write(awaiting_human_for=None)
        self.assertTrue(path.is_file())
        body = json.loads(
            json.loads(path.read_text(encoding="utf-8"))["body"],
        )
        self.assertIsNone(body["awaiting_human_for"])

    def test_awaiting_human_for_string_accepted(self) -> None:
        path = self._write(
            awaiting_human_for="phase_complete_awaiting_human_approval",
        )
        body = json.loads(
            json.loads(path.read_text(encoding="utf-8"))["body"],
        )
        self.assertEqual(
            body["awaiting_human_for"],
            "phase_complete_awaiting_human_approval",
        )


class MalformedCheckpointWriteRefusalTests(_CheckpointTestCase):

    def test_empty_task_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(task="")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("task", cm.exception.reason)

    def test_empty_status_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(status="")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("status", cm.exception.reason)

    def test_empty_approval_mode_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(approval_mode="")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("approval_mode", cm.exception.reason)

    def test_awaiting_human_for_wrong_type_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(awaiting_human_for=123)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("awaiting_human_for", cm.exception.reason)

    def test_awaiting_human_for_empty_string_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(awaiting_human_for="")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("awaiting_human_for", cm.exception.reason)

    def test_invalid_active_prompt_path_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(active_prompt_path=".agent-loop/bogus.md")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("active_prompt_path", cm.exception.reason)

    def test_invalid_suspension_reason_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(suspension_reason="bogus_reason")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("suspension_reason", cm.exception.reason)

    def test_continuation_budget_non_int_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(continuation_budget="two")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("continuation_budget", cm.exception.reason)

    def test_continuation_budget_bool_refuses(self) -> None:
        # Python's bool is an int subclass; the guard must still refuse.
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(continuation_budget=True)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("continuation_budget", cm.exception.reason)

    def test_continuation_budget_negative_refuses(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            self._write(continuation_budget=-1)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("continuation_budget", cm.exception.reason)


class ReadCheckpointSchemaTests(_CheckpointTestCase):

    def _drop_checkpoint(self, body_payload, *, category=None) -> Path:
        """Hand-craft a memory-entry file with the given body payload.
        `body_payload` is JSON-encoded into the entry's `body` field
        (unless it is None, in which case `body` is set to None).
        `category` defaults to MEMORY_CATEGORY_CHECKPOINT.
        """
        cat = category or agent_loop.MEMORY_CATEGORY_CHECKPOINT
        cat_dir = self.memory_dir / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        if isinstance(body_payload, (dict, list)):
            body_str = json.dumps(body_payload)
        else:
            body_str = body_payload  # raw text, None, or a malformed string
        entry = {
            "signal_version": agent_loop.MEMORY_SIGNAL_VERSION,
            "category": cat,
            "phase": "Phase 6 - Durable Memory and Optional Context Layer",
            "sub_phase": "Phase 6D - Checkpoint Artifact Storage Initial Slice",
            "cycle_count": 0,
            "source_artifact_path": ".agent-loop/current-task.md",
            "created_at": "2026-06-09T12:00:00Z",
            "supersedes": None,
            "body": body_str,
        }
        path = cat_dir / "20260609T120000Z-deadbeef.json"
        path.write_text(json.dumps(entry), encoding="utf-8")
        return path

    def _valid_body(self, **overrides) -> dict:
        body = {
            "checkpoint_signal_version": agent_loop.CHECKPOINT_SIGNAL_VERSION,
            "task": "t",
            "status": "awaiting_claude_implementation",
            "approval_mode": "review",
            "awaiting_human_for": None,
            "active_prompt_path": ".agent-loop/claude-prompt.md",
            "suspension_reason": "token_exhaustion",
            "continuation_budget": 1,
        }
        body.update(overrides)
        return body

    def test_read_round_trip_returns_combined_dict(self) -> None:
        path = self._write()
        result = agent_loop.read_checkpoint_entry(path)
        # Memory-level fields.
        self.assertEqual(
            result["category"], agent_loop.MEMORY_CATEGORY_CHECKPOINT,
        )
        self.assertEqual(
            result["signal_version"], agent_loop.MEMORY_SIGNAL_VERSION,
        )
        # Checkpoint-body fields merged onto the top level.
        self.assertEqual(
            result["checkpoint_signal_version"],
            agent_loop.CHECKPOINT_SIGNAL_VERSION,
        )
        self.assertEqual(result["task"], _BASE_KWARGS["task"])
        self.assertEqual(result["status"], _BASE_KWARGS["status"])
        self.assertEqual(
            result["active_prompt_path"], _BASE_KWARGS["active_prompt_path"],
        )
        self.assertEqual(
            result["suspension_reason"], _BASE_KWARGS["suspension_reason"],
        )
        self.assertEqual(
            result["continuation_budget"],
            _BASE_KWARGS["continuation_budget"],
        )

    def test_read_refuses_non_checkpoint_category(self) -> None:
        # Drop a valid checkpoint body under the decision/ folder; the
        # outer memory schema is fine, but the category is not
        # 'checkpoint'.
        path = self._drop_checkpoint(
            self._valid_body(),
            category=agent_loop.MEMORY_CATEGORY_DECISION,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("checkpoint", cm.exception.reason)

    def test_read_refuses_missing_body(self) -> None:
        # body=None
        path = self._drop_checkpoint(None)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("no body", cm.exception.reason)

    def test_read_refuses_malformed_body_json(self) -> None:
        path = self._drop_checkpoint("not json at all")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not valid JSON", cm.exception.reason)

    def test_read_refuses_non_dict_body(self) -> None:
        path = self._drop_checkpoint([1, 2, 3])
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("JSON object", cm.exception.reason)

    def test_read_refuses_missing_required_body_field(self) -> None:
        body = self._valid_body()
        del body["task"]
        path = self._drop_checkpoint(body)
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("task", cm.exception.reason)

    def test_read_refuses_unrecognized_checkpoint_signal_version(self) -> None:
        path = self._drop_checkpoint(
            self._valid_body(checkpoint_signal_version="phase-6d-vNEXT"),
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("checkpoint_signal_version", cm.exception.reason)
        self.assertIn("not recognized", cm.exception.reason)

    def test_read_refuses_invalid_active_prompt_path(self) -> None:
        path = self._drop_checkpoint(
            self._valid_body(active_prompt_path=".agent-loop/bogus.md"),
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("active_prompt_path", cm.exception.reason)

    def test_read_refuses_invalid_suspension_reason(self) -> None:
        path = self._drop_checkpoint(
            self._valid_body(suspension_reason="bogus_reason"),
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("suspension_reason", cm.exception.reason)

    def test_read_refuses_non_int_continuation_budget(self) -> None:
        path = self._drop_checkpoint(
            self._valid_body(continuation_budget="two"),
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("continuation_budget", cm.exception.reason)

    def test_read_refuses_negative_continuation_budget(self) -> None:
        path = self._drop_checkpoint(
            self._valid_body(continuation_budget=-3),
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_checkpoint_entry(path)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("continuation_budget", cm.exception.reason)


class WriteBoundaryEnforcementTests(_CheckpointTestCase):

    def test_checkpoint_writes_only_under_memory_checkpoint_dir(self) -> None:
        path = self._write()
        rel = path.relative_to(self.repo_root).as_posix()
        self.assertTrue(
            rel.startswith(
                f"{agent_loop.MEMORY_DIR_REL}/"
                f"{agent_loop.MEMORY_CATEGORY_CHECKPOINT}/"
            ),
            f"checkpoint entry must live under memory/checkpoint/, got {rel}",
        )

    def test_checkpoint_write_does_not_mutate_canonical_artifacts(
        self,
    ) -> None:
        canonical = self.repo_root / ".agent-loop" / "loop-state.json"
        canonical.write_text(
            json.dumps({"phase": "canonical", "status": "ok"}) + "\n",
            encoding="utf-8",
        )
        before = canonical.read_bytes()
        self._write()
        agent_loop.list_checkpoint_entries(self.repo_root)
        self.assertEqual(canonical.read_bytes(), before)

    def test_writer_refuses_to_overwrite_existing_checkpoint(self) -> None:
        # The Phase 6B append-mostly behavior is inherited; force a
        # filename collision and assert refusal.
        path = self._write()
        # Mock the filename helper to return the same name for a
        # second call with the same body, so the existing-file guard
        # fires.
        import unittest.mock as mock

        with mock.patch.object(
            agent_loop, "_memory_entry_filename", return_value=path.name,
        ):
            with self.assertRaises(agent_loop.HaltError) as cm:
                self._write()
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("already exists", cm.exception.reason)


class ListCheckpointEntriesTests(_CheckpointTestCase):

    def test_list_returns_empty_when_checkpoint_dir_absent(self) -> None:
        self.assertEqual(
            agent_loop.list_checkpoint_entries(self.repo_root), [],
        )

    def test_list_returns_only_checkpoint_entries(self) -> None:
        # Write one checkpoint and one decision entry; the listing
        # helper must return only the checkpoint.
        ckpt = self._write()
        decision = agent_loop.write_memory_entry(
            self.repo_root,
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            phase="p", sub_phase="sp", cycle_count=0,
            source_artifact_path="human",
            body="some decision",
        )
        self.assertNotEqual(ckpt.parent.name, decision.parent.name)
        listed = agent_loop.list_checkpoint_entries(self.repo_root)
        self.assertEqual(listed, [ckpt])


class AuditNoteTests(_CheckpointTestCase):

    def test_log_path_appends_memory_write_note_with_checkpoint_category(
        self,
    ) -> None:
        # The Phase 6B writer emits "memory write: ... category='checkpoint'"
        # when checkpoint_writer delegates to it.
        self._write(log_path=self.log_path)
        self.assertTrue(self.log_path.is_file())
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("memory write:", log_text)
        self.assertIn("'checkpoint'", log_text)

    def test_no_log_path_means_no_log_file(self) -> None:
        self._write()  # no log_path
        self.assertFalse(self.log_path.is_file())


if __name__ == "__main__":
    unittest.main()
