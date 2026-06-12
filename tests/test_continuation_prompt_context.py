"""Focused tests for the Phase 6H bounded continuation prompt
construction slice.

Scope of this suite (Phase 6H, narrow):
- `build_continuation_prompt_context(repo_root, ...)` assembles a
  structured dict from canonical loop-state + the active Phase 6F/6G
  token-exhaustion checkpoint + bounded evidence excerpts + advisory
  durable-memory entries (Phase 6C retrieval, advisory-only marker
  preserved).
- The dict carries an explicit `canonical_precedence_note` so the
  downstream consumer cannot accidentally treat advisory memory as
  canonical state.
- Refusal modes (all `halted_input_missing` unless noted): missing /
  malformed loop-state, unsupported `contract_version`
  (`halted_contract_version_mismatch`), ineligible halt status (the
  initial slice only handles `HALTED_TOKEN_EXHAUSTION`), missing
  active checkpoint, cycle-identity mismatch, `suspension_reason`
  other than `token_exhaustion`, out-of-bound `memory_entry_limit`,
  out-of-bound `evidence_byte_limit`.
- Bounds: memory entries default to
  `CONTINUATION_CONTEXT_DEFAULT_MEMORY_LIMIT`; evidence excerpts
  default to `CONTINUATION_CONTEXT_DEFAULT_EVIDENCE_BYTE_LIMIT` per
  file. Truncation is recorded structurally on both surfaces.
- Canonical-precedence preservation: building the context never
  mutates loop-state.json, never mutates the active checkpoint, never
  writes any canonical artifact, and the output artifact carries the
  explicit `canonical_precedence_note`.
- The `build-continuation-context` CLI subcommand goes through
  `main(argv)` HANDLERS dispatch and writes the structured dict to
  `.agent-loop/continuation-context.json` (or the `--output` path)
  with the same fail-closed refusal vocabulary the library function
  raises.

This slice does not serialize the context to a prompt string, does
not implement phase-boundary memory distillation, and does not
broaden context-file loading beyond the existing EVIDENCE_FILES set.
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
    "Phase 6H - Bounded Continuation Prompt Construction Initial Slice"
)
_ACTIVE_TASK = "Implement continuation prompt construction."
_PRE_SUSPENSION_STATUS = "awaiting_codex_review"
_PRE_SUSPENSION_AWAITING_HUMAN_FOR = None


def _baseline_loop_state(**overrides) -> dict:
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


class _ContinuationContextTestCase(unittest.TestCase):
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
        self.output_default = (
            self.repo_root / agent_loop.CONTINUATION_CONTEXT_OUTPUT_REL
        )

    def _write_state(self, **overrides) -> dict:
        data = _baseline_loop_state(**overrides)
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return data

    def _state_on_disk(self) -> dict:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _record_halted(self, **kwargs) -> Path:
        """Record a token-exhaustion event from the baseline state and
        leave loop-state at `HALTED_TOKEN_EXHAUSTION`."""
        self._write_state()
        defaults = {"active_prompt_path": ".agent-loop/claude-prompt.md"}
        defaults.update(kwargs)
        return agent_loop.record_token_exhaustion(self.repo_root, **defaults)

    def _plant_evidence_files(
        self, contents_by_rel: dict, default_text: str = "evidence body",
    ) -> None:
        """Plant each EVIDENCE_FILES path with caller-supplied text or
        `default_text` if not supplied."""
        for rel in agent_loop.EVIDENCE_FILES:
            p = self.repo_root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            text = contents_by_rel.get(rel, default_text)
            p.write_text(text, encoding="utf-8")


# ----- build_continuation_prompt_context: success shape -----


class BuildContextSuccessShapeTests(_ContinuationContextTestCase):

    def test_success_returns_structured_dict_with_required_keys(self) -> None:
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        ctx = agent_loop.build_continuation_prompt_context(
            self.repo_root, log_path=self.log_path,
        )
        # Top-level schema keys.
        for key in (
            "context_signal_version", "built_at",
            "canonical_state", "checkpoint",
            "evidence", "evidence_byte_limit_applied",
            "memory_advisory", "memory_limit_applied",
            "memory_truncated_at_limit",
            "canonical_precedence_note",
        ):
            self.assertIn(key, ctx)
        self.assertEqual(
            ctx["context_signal_version"],
            agent_loop.CONTINUATION_CONTEXT_SIGNAL_VERSION,
        )
        self.assertEqual(
            ctx["canonical_precedence_note"],
            agent_loop.CONTINUATION_CONTEXT_CANONICAL_PRECEDENCE_NOTE,
        )

    def test_canonical_state_subset_mirrors_loop_state(self) -> None:
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        ctx = agent_loop.build_continuation_prompt_context(self.repo_root)
        cs = ctx["canonical_state"]
        self.assertEqual(cs["phase"], _ACTIVE_PHASE)
        self.assertEqual(cs["sub_phase"], _ACTIVE_SUB_PHASE)
        self.assertEqual(cs["task"], _ACTIVE_TASK)
        self.assertEqual(cs["cycle_count"], 1)
        self.assertEqual(cs["approval_mode"], agent_loop.APPROVAL_MODE_REVIEW)
        # The halt vocabulary lands here; the checkpoint subset carries
        # the pre-suspension vocabulary instead.
        self.assertEqual(cs["halt_status"], agent_loop.HALTED_TOKEN_EXHAUSTION)
        self.assertEqual(
            cs["awaiting_human_for"],
            agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION,
        )

    def test_checkpoint_subset_preserves_pre_suspension_vocabulary(
        self,
    ) -> None:
        self._record_halted(continuation_budget=3)
        self._plant_evidence_files({}, default_text="ok")
        ctx = agent_loop.build_continuation_prompt_context(self.repo_root)
        cp = ctx["checkpoint"]
        self.assertEqual(
            cp["suspension_reason"],
            agent_loop.TOKEN_EXHAUSTION_SUSPENSION_REASON,
        )
        self.assertEqual(
            cp["active_prompt_path"], ".agent-loop/claude-prompt.md",
        )
        self.assertEqual(cp["continuation_budget"], 3)
        # The checkpoint side records the PRE-suspension status, not the
        # halt vocabulary (which lives on canonical_state.halt_status).
        self.assertEqual(cp["pre_suspension_status"], _PRE_SUSPENSION_STATUS)
        self.assertEqual(
            cp["pre_suspension_awaiting_human_for"],
            _PRE_SUSPENSION_AWAITING_HUMAN_FOR,
        )
        # The source_path points at the active checkpoint on disk.
        self.assertTrue(
            cp["source_path"].startswith(".agent-loop/memory/checkpoint/"),
            f"unexpected source_path: {cp['source_path']!r}",
        )


# ----- build_continuation_prompt_context: bounded evidence -----


class BuildContextEvidenceBoundsTests(_ContinuationContextTestCase):

    def test_evidence_excerpt_is_byte_bounded_and_marked_truncated(
        self,
    ) -> None:
        # Plant an evidence file that is larger than the limit so we
        # observe truncation.
        big = "X" * 100
        contents = {".agent-loop/git-status.log": big}
        self._record_halted()
        self._plant_evidence_files(contents, default_text="ok")
        ctx = agent_loop.build_continuation_prompt_context(
            self.repo_root, evidence_byte_limit=20,
        )
        ev = ctx["evidence"][".agent-loop/git-status.log"]
        self.assertFalse(ev["absent"])
        self.assertEqual(ev["byte_size_on_disk"], 100)
        self.assertEqual(ev["excerpt_byte_size"], 20)
        self.assertEqual(ev["excerpt"], "X" * 20)
        self.assertTrue(ev["truncated"])

    def test_evidence_excerpt_below_limit_is_not_marked_truncated(
        self,
    ) -> None:
        self._record_halted()
        self._plant_evidence_files(
            {".agent-loop/git-status.log": "short"}, default_text="ok",
        )
        ctx = agent_loop.build_continuation_prompt_context(
            self.repo_root, evidence_byte_limit=4096,
        )
        ev = ctx["evidence"][".agent-loop/git-status.log"]
        self.assertFalse(ev["truncated"])
        self.assertEqual(ev["excerpt"], "short")

    def test_missing_evidence_files_are_marked_absent(self) -> None:
        # Plant only one evidence file; the rest must be reported absent
        # rather than silently omitted (so the continuation runtime
        # sees the same absence the orchestrator would see).
        self._record_halted()
        present = self.repo_root / ".agent-loop/git-status.log"
        present.write_text("ok", encoding="utf-8")
        ctx = agent_loop.build_continuation_prompt_context(self.repo_root)
        ev = ctx["evidence"]
        self.assertFalse(ev[".agent-loop/git-status.log"]["absent"])
        for rel in agent_loop.EVIDENCE_FILES:
            if rel == ".agent-loop/git-status.log":
                continue
            self.assertTrue(
                ev[rel]["absent"],
                f"expected {rel} absent, got {ev[rel]!r}",
            )

    def test_refuses_on_evidence_byte_limit_zero(self) -> None:
        self._record_halted()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(
                self.repo_root, evidence_byte_limit=0,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("evidence_byte_limit", cm.exception.reason)

    def test_refuses_on_evidence_byte_limit_negative(self) -> None:
        self._record_halted()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(
                self.repo_root, evidence_byte_limit=-1,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")

    def test_refuses_on_evidence_byte_limit_above_safety_cap(self) -> None:
        self._record_halted()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(
                self.repo_root,
                evidence_byte_limit=(
                    agent_loop.CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT
                    + 1
                ),
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn(
            "CONTINUATION_CONTEXT_MAX_EVIDENCE_BYTE_LIMIT",
            cm.exception.reason,
        )

    def test_refuses_on_evidence_byte_limit_bool(self) -> None:
        # bool is a subclass of int; accepting True/False would silently
        # coerce to 1 / 0 which is not what the operator meant.
        self._record_halted()
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.build_continuation_prompt_context(
                self.repo_root, evidence_byte_limit=True,
            )


# ----- build_continuation_prompt_context: bounded memory -----


class BuildContextMemoryBoundsTests(_ContinuationContextTestCase):

    def _write_memory_entry(self, **overrides) -> Path:
        kwargs = dict(
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            phase=_ACTIVE_PHASE,
            sub_phase=_ACTIVE_SUB_PHASE,
            cycle_count=1,
            source_artifact_path=".agent-loop/loop-state.json",
            body="memory body",
        )
        kwargs.update(overrides)
        return agent_loop.write_memory_entry(self.repo_root, **kwargs)

    def test_memory_advisory_entries_carry_advisory_only_marker(self) -> None:
        self._record_halted()
        self._write_memory_entry(body="first")
        ctx = agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(len(ctx["memory_advisory"]), 1)
        entry = ctx["memory_advisory"][0]
        self.assertTrue(entry[agent_loop.MEMORY_RETRIEVAL_ADVISORY_FIELD])

    def test_memory_truncation_flag_set_when_more_matches_than_limit(
        self,
    ) -> None:
        # Plant 3 distinct memory entries (varying body so the
        # deterministic filename hash does not collide), then retrieve
        # with a limit of 1 so the truncation flag must be True.
        self._record_halted()
        for i in range(3):
            self._write_memory_entry(body=f"distinct body {i}")
        ctx = agent_loop.build_continuation_prompt_context(
            self.repo_root, memory_entry_limit=1,
        )
        self.assertEqual(len(ctx["memory_advisory"]), 1)
        self.assertTrue(ctx["memory_truncated_at_limit"])
        self.assertEqual(ctx["memory_limit_applied"], 1)

    def test_memory_truncation_flag_false_when_under_limit(self) -> None:
        self._record_halted()
        self._write_memory_entry(body="only one")
        ctx = agent_loop.build_continuation_prompt_context(
            self.repo_root, memory_entry_limit=8,
        )
        self.assertEqual(len(ctx["memory_advisory"]), 1)
        self.assertFalse(ctx["memory_truncated_at_limit"])

    def test_refuses_on_memory_entry_limit_out_of_bounds(self) -> None:
        self._record_halted()
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.build_continuation_prompt_context(
                self.repo_root,
                memory_entry_limit=(
                    agent_loop.MEMORY_RETRIEVAL_MAX_LIMIT + 1
                ),
            )

    def test_memory_advisory_excluded_from_other_phase(self) -> None:
        # An entry for a DIFFERENT phase must not bleed into the
        # context's advisory list.
        self._record_halted()
        self._write_memory_entry(
            phase="Phase 5 - Approval Modes",
            sub_phase="Phase 5A - Approval Modes Contract",
        )
        ctx = agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(ctx["memory_advisory"], [])


# ----- build_continuation_prompt_context: refusal modes -----


class BuildContextRefusalTests(_ContinuationContextTestCase):

    def test_refuses_when_status_is_not_eligible(self) -> None:
        # Non-halt loop-state. No checkpoint required to surface this
        # refusal because the eligibility check runs first.
        self._write_state()
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("eligible halt set", cm.exception.reason)

    def test_refuses_on_strict_gate_halt_status(self) -> None:
        # The strict-gate halt has its own existing resume path; this
        # builder must refuse it explicitly.
        self._write_state(
            status=agent_loop.HALTED_PRE_CLAUDE_PROMPT,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_PRE_CLAUDE_PROMPT
            ),
            approval_mode=agent_loop.APPROVAL_MODE_STRICT,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("eligible halt set", cm.exception.reason)

    def test_refuses_when_no_active_checkpoint(self) -> None:
        # Plant the token-exhaustion halt by hand but write no
        # checkpoint. The builder must refuse rather than try to
        # construct context from canonical state alone.
        self._write_state(
            status=agent_loop.HALTED_TOKEN_EXHAUSTION,
            awaiting_human_for=(
                agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
            ),
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("no active checkpoint", cm.exception.reason)

    def test_refuses_on_cycle_identity_mismatch(self) -> None:
        # Record under cycle_count=1, then mutate loop-state to a
        # different cycle_count so the Phase 6F validator refuses.
        self._record_halted()
        data = self._state_on_disk()
        data["cycle_count"] = 99
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("cycle_count", cm.exception.reason)

    def test_refuses_on_suspension_reason_other_than_token_exhaustion(
        self,
    ) -> None:
        # Plant the halt by hand and write a checkpoint with a
        # different (valid) suspension_reason. The builder's
        # suspension_reason guard must refuse.
        self._write_state()
        agent_loop.write_checkpoint_entry(
            self.repo_root,
            phase=_ACTIVE_PHASE,
            sub_phase=_ACTIVE_SUB_PHASE,
            task=_ACTIVE_TASK,
            cycle_count=1,
            status=_PRE_SUSPENSION_STATUS,
            approval_mode=agent_loop.APPROVAL_MODE_REVIEW,
            awaiting_human_for=_PRE_SUSPENSION_AWAITING_HUMAN_FOR,
            active_prompt_path=".agent-loop/claude-prompt.md",
            suspension_reason="human_interrupt",
            continuation_budget=2,
            source_artifact_path=".agent-loop/loop-state.json",
        )
        # Force the token-exhaustion halt onto loop-state.
        data = self._state_on_disk()
        data["status"] = agent_loop.HALTED_TOKEN_EXHAUSTION
        data["awaiting_human_for"] = (
            agent_loop.AWAITING_HUMAN_FOR_TOKEN_EXHAUSTION
        )
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("suspension_reason", cm.exception.reason)

    def test_refuses_on_unsupported_contract_version(self) -> None:
        self._record_halted()
        data = self._state_on_disk()
        data["contract_version"] = "phase-9z-from-the-future"
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(
            cm.exception.status, "halted_contract_version_mismatch",
        )

    def test_refuses_when_loop_state_missing(self) -> None:
        # No loop-state.json on disk.
        with self.assertRaises(agent_loop.HaltError):
            agent_loop.build_continuation_prompt_context(self.repo_root)


# ----- build_continuation_prompt_context: canonical-precedence -----


class BuildContextCanonicalPrecedenceTests(_ContinuationContextTestCase):

    def test_building_context_does_not_mutate_loop_state(self) -> None:
        self._record_halted()
        before = self.state_path.read_bytes()
        agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_building_context_does_not_mutate_active_checkpoint(self) -> None:
        path = self._record_halted()
        before = path.read_bytes()
        agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(path.read_bytes(), before)

    def test_building_context_does_not_create_continuation_artifact(
        self,
    ) -> None:
        # The library function never writes the audit artifact; only
        # the CLI handler does. This pins the library/handler split.
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertFalse(self.output_default.exists())

    def test_canonical_precedence_note_is_literal_constant(self) -> None:
        # Pin that the note is the named constant rather than a
        # call-site-formatted string; a consumer can rely on equality.
        self._record_halted()
        ctx = agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertIs(
            ctx["canonical_precedence_note"],
            agent_loop.CONTINUATION_CONTEXT_CANONICAL_PRECEDENCE_NOTE,
        )

    def test_audit_log_note_records_the_construction(self) -> None:
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        agent_loop.build_continuation_prompt_context(
            self.repo_root, log_path=self.log_path,
        )
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("continuation context built:", log_text)
        self.assertIn(
            f"signal_version='{agent_loop.CONTINUATION_CONTEXT_SIGNAL_VERSION}'",
            log_text,
        )

    def test_audit_log_not_appended_when_log_path_not_provided(self) -> None:
        # No log_path supplied -> the BUILDER appends no note. The log
        # may already exist from setUp side effects (e.g.
        # record_token_exhaustion's own audit), so the assertion is
        # "the log content is byte-equivalent across the build call".
        self._record_halted()
        before = (
            self.log_path.read_bytes() if self.log_path.exists() else b""
        )
        agent_loop.build_continuation_prompt_context(self.repo_root)
        after = (
            self.log_path.read_bytes() if self.log_path.exists() else b""
        )
        self.assertEqual(before, after)


# ----- cmd_build_continuation_context + main(argv) -----


class CmdBuildContinuationContextTests(_ContinuationContextTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root", return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_writes_default_output_artifact(self) -> None:
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        rc = self._run_main(["build-continuation-context"])
        self.assertEqual(rc, 0)
        self.assertTrue(self.output_default.is_file())
        payload = json.loads(self.output_default.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["context_signal_version"],
            agent_loop.CONTINUATION_CONTEXT_SIGNAL_VERSION,
        )
        self.assertEqual(payload["canonical_state"]["phase"], _ACTIVE_PHASE)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("continuation context built:", log_text)

    def test_cli_honors_explicit_output_override(self) -> None:
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        custom = self.al / "custom-context.json"
        rc = self._run_main([
            "build-continuation-context",
            "--output", str(custom),
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(custom.is_file())
        self.assertFalse(self.output_default.exists())

    def test_cli_honors_explicit_limits(self) -> None:
        self._record_halted()
        self._plant_evidence_files(
            {".agent-loop/git-status.log": "X" * 200}, default_text="ok",
        )
        rc = self._run_main([
            "build-continuation-context",
            "--memory-entry-limit", "4",
            "--evidence-byte-limit", "32",
        ])
        self.assertEqual(rc, 0)
        payload = json.loads(self.output_default.read_text(encoding="utf-8"))
        self.assertEqual(payload["memory_limit_applied"], 4)
        self.assertEqual(payload["evidence_byte_limit_applied"], 32)
        ev = payload["evidence"][".agent-loop/git-status.log"]
        self.assertTrue(ev["truncated"])
        self.assertEqual(ev["excerpt_byte_size"], 32)

    def test_cli_overwrites_existing_artifact(self) -> None:
        # The audit artifact is regenerable from canonical state; the
        # CLI must overwrite an existing file rather than append.
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        self.output_default.parent.mkdir(parents=True, exist_ok=True)
        self.output_default.write_text("stale\n", encoding="utf-8")
        rc = self._run_main(["build-continuation-context"])
        self.assertEqual(rc, 0)
        # New JSON content fully replaced the stale text.
        new_text = self.output_default.read_text(encoding="utf-8")
        self.assertNotIn("stale", new_text)
        payload = json.loads(new_text)
        self.assertEqual(
            payload["context_signal_version"],
            agent_loop.CONTINUATION_CONTEXT_SIGNAL_VERSION,
        )

    def test_cli_refuses_when_status_is_not_eligible(self) -> None:
        # Non-halt loop-state. The CLI handler routes the HaltError
        # through _halt so the structural refusal lands on disk.
        self._write_state()
        rc = self._run_main(["build-continuation-context"])
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        self.assertEqual(after["status"], "halted_input_missing")
        # No output artifact written on refusal.
        self.assertFalse(self.output_default.exists())

    def test_cli_refuses_on_invalid_limit_flags(self) -> None:
        self._record_halted()
        rc = self._run_main([
            "build-continuation-context",
            "--memory-entry-limit", "0",
        ])
        self.assertEqual(rc, 2)
        after = self._state_on_disk()
        self.assertEqual(after["status"], "halted_input_missing")
        self.assertFalse(self.output_default.exists())


# ----- Phase 6H fix-slice regression coverage -----


class BuildContextMemoryTruncationAtMaxCapTests(_ContinuationContextTestCase):
    """Regression coverage for the fix-slice memory truncation semantics.

    The prior implementation computed `memory_truncated_at_limit` by
    re-running `retrieve_memory_entries(...)` with
    `limit=MEMORY_RETRIEVAL_MAX_LIMIT` and comparing lengths against
    the caller's bounded retrieval. When the caller ALSO used
    `MEMORY_RETRIEVAL_MAX_LIMIT` and more entries than that actually
    matched on disk, both calls capped at the same length and the
    builder reported `memory_truncated_at_limit = False` even though
    advisory memory was hidden by the cap. The fixed implementation
    counts true matches by walking the entries with the same scope
    filters the retrieval primitive uses, so the truncation flag is
    truthful regardless of the caller's limit choice.
    """

    def _write_memory_entry(self, **overrides) -> Path:
        kwargs = dict(
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            phase=_ACTIVE_PHASE,
            sub_phase=_ACTIVE_SUB_PHASE,
            cycle_count=1,
            source_artifact_path=".agent-loop/loop-state.json",
            body="memory body",
        )
        kwargs.update(overrides)
        return agent_loop.write_memory_entry(self.repo_root, **kwargs)

    def test_memory_truncated_flag_true_at_max_cap_when_more_matches_exist(
        self,
    ) -> None:
        # Plant MEMORY_RETRIEVAL_MAX_LIMIT + 1 distinct in-scope memory
        # entries so a retrieval at the max cap necessarily hides at
        # least one. The fix's direct-walk count must observe this and
        # report `memory_truncated_at_limit = True`.
        self._record_halted()
        max_cap = agent_loop.MEMORY_RETRIEVAL_MAX_LIMIT
        for i in range(max_cap + 1):
            self._write_memory_entry(body=f"distinct body {i}")
        ctx = agent_loop.build_continuation_prompt_context(
            self.repo_root, memory_entry_limit=max_cap,
        )
        # The retrieval respects the caller's limit.
        self.assertEqual(len(ctx["memory_advisory"]), max_cap)
        self.assertEqual(ctx["memory_limit_applied"], max_cap)
        # The flag must be TRUTHFUL even though the limit equals the
        # max cap and the secondary check would have capped at the
        # same length.
        self.assertTrue(ctx["memory_truncated_at_limit"])

    def test_memory_truncated_flag_false_at_max_cap_when_no_hidden_entries(
        self,
    ) -> None:
        # Plant exactly MEMORY_RETRIEVAL_MAX_LIMIT in-scope entries:
        # no entries hidden, so the flag must remain False even when
        # the limit equals the max cap.
        self._record_halted()
        max_cap = agent_loop.MEMORY_RETRIEVAL_MAX_LIMIT
        for i in range(max_cap):
            self._write_memory_entry(body=f"distinct body {i}")
        ctx = agent_loop.build_continuation_prompt_context(
            self.repo_root, memory_entry_limit=max_cap,
        )
        self.assertEqual(len(ctx["memory_advisory"]), max_cap)
        self.assertFalse(ctx["memory_truncated_at_limit"])


class BuildContextUnreadableEvidenceRefusalTests(_ContinuationContextTestCase):
    """Regression coverage for the fix-slice unreadable-evidence
    handling. The prior implementation returned a success payload with
    an undocumented `read_error` schema branch when `Path.read_bytes`
    raised `OSError`; the fixed implementation refuses fail-closed via
    `HaltError("halted_input_missing", ...)` so the documented
    continuation-context schema does not silently grow an
    undocumented branch."""

    def _force_read_to_raise(self, target_rel: str):
        """Build a mock side_effect on `Path.read_bytes` that raises
        `OSError` for the target evidence file path and falls through
        to the real read for any other path. Returns the patcher
        context manager so the test can manage the patch lifetime."""
        real_read_bytes = Path.read_bytes
        target_path = self.repo_root / target_rel

        def _side_effect(self_path: Path, *args, **kwargs):
            if self_path.resolve() == target_path.resolve():
                raise OSError("simulated read failure")
            return real_read_bytes(self_path, *args, **kwargs)

        return mock.patch.object(Path, "read_bytes", _side_effect)

    def test_unreadable_evidence_file_causes_fail_closed_refusal(self) -> None:
        # Plant every evidence file so none are absent, then make ONE
        # of them raise OSError on read. The builder must refuse
        # rather than emit a success payload.
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        target_rel = ".agent-loop/git-diff.patch"
        with self._force_read_to_raise(target_rel):
            with self.assertRaises(agent_loop.HaltError) as cm:
                agent_loop.build_continuation_prompt_context(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        # The refusal message names the unreadable file so the
        # operator knows which evidence input to repair.
        self.assertIn(target_rel, cm.exception.reason)
        self.assertIn("unreadable", cm.exception.reason)

    def test_cli_subcommand_refuses_on_unreadable_evidence_file(self) -> None:
        # End-to-end through main(argv): the CLI handler routes the
        # HaltError through `_halt` and writes no output artifact.
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        target_rel = ".agent-loop/test-output.log"
        with self._force_read_to_raise(target_rel):
            with mock.patch.object(
                agent_loop, "find_repo_root", return_value=self.repo_root,
            ):
                rc = agent_loop.main(["build-continuation-context"])
        self.assertEqual(rc, 2)
        # loop-state.json carries the structural failure vocabulary.
        after = self._state_on_disk()
        self.assertEqual(after["status"], "halted_input_missing")
        # No success artifact written on refusal.
        self.assertFalse(self.output_default.exists())

    def test_no_evidence_payload_carries_a_read_error_branch(self) -> None:
        # Pin the documented schema: when readable, the per-file
        # evidence payload only carries (absent, byte_size_on_disk,
        # excerpt, excerpt_byte_size, truncated). No `read_error` key
        # should ever appear in the on-success payload.
        self._record_halted()
        self._plant_evidence_files({}, default_text="ok")
        ctx = agent_loop.build_continuation_prompt_context(self.repo_root)
        for rel, ev in ctx["evidence"].items():
            self.assertNotIn(
                "read_error", ev,
                f"unexpected `read_error` key on evidence entry {rel!r}",
            )


if __name__ == "__main__":
    unittest.main()
