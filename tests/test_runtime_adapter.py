"""Focused tests for the Phase 6N experimental LangGraph runtime
mirror.

Scope of this suite (Phase 6N, narrow):
- `resolve_runtime_adapter_id(cli_value, env_value)` returns the
  default `local` when both inputs are unset; CLI takes precedence
  over env; an empty string is treated as 'unset'; refuses fail-
  closed on any id outside `RUNTIME_ADAPTERS_SUPPORTED`.
- `make_runtime_adapter(runtime_id)` returns a `LocalRuntimeAdapter`
  for `local`, a `LangGraphExperimentalRuntimeAdapter` for
  `langgraph`, refuses on any other id.
- `LocalRuntimeAdapter.evaluate(...)` returns a sentinel dict and
  does NOT read or mutate any canonical artifact (the local path is
  the shipped in-process flow, not an adapter-driven path).
- `LangGraphExperimentalRuntimeAdapter.evaluate(...)` walks the
  fixed ordered `LANGGRAPH_NODE_NAMES` list, re-loads loop-state on
  every node entry (no caching across hops), emits one
  `runtime adapter: langgraph_experimental ...` audit note per node
  plus begin / complete book-end notes, never writes canonical
  state, and re-raises every shipped-validator `HaltError` verbatim.
- The `runtime-adapter-eval` CLI subcommand routes through
  `main(argv)` HANDLERS dispatch, honors `--runtime`, honors the
  `AGENT_LOOP_RUNTIME` env var, lets CLI override env, and refuses
  via `_halt` on every refusal path.
- Default-runtime preservation: when `--runtime` is absent and the
  env var is unset, the default `local` runtime is selected and no
  langgraph code runs.
- Canonical-precedence preservation: the experimental mirror does
  NOT mutate `loop-state.json`, does NOT mutate any source memory
  entry, does NOT write any canonical artifact, and re-loads
  canonical state on every node entry.

This slice does not implement LangChain support-layer work, CrewAI
evaluation, or any broader multi-framework orchestration. The
"mirror" is a pure-stdlib structural emulation of LangGraph's
StateGraph pattern; a future slice that wires the real `langgraph`
package would swap the implementation behind the same adapter
interface without changing the contract surface.
"""

from __future__ import annotations

import argparse
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

import agent_loop  # noqa: E402 - sys.path is set above


def _baseline_state(**overrides) -> dict:
    """Loop-state shape the runtime adapter validates."""
    data = {
        "phase": "Phase 6 - Durable Memory and Optional Context Layer",
        "sub_phase": "Phase 6N - Experimental LangGraph Runtime Mirror",
        "task": "Implement experimental LangGraph runtime mirror.",
        "status": "awaiting_claude_implementation",
        "cycle_count": 0,
        "max_cycles": 3,
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


class _RuntimeAdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name).resolve()
        self.al = self.repo_root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        self.state_path = self.al / "loop-state.json"
        self.log_path = self.al / "orchestrator.log"
        # Make sure the env var is clean between tests so a leaked
        # value does not silently affect runtime resolution.
        self._saved_env = os.environ.pop(
            agent_loop.RUNTIME_ADAPTER_ENV_VAR, None,
        )

    def tearDown(self) -> None:
        if self._saved_env is not None:
            os.environ[agent_loop.RUNTIME_ADAPTER_ENV_VAR] = (
                self._saved_env
            )

    def _write_state(self, **overrides) -> dict:
        data = _baseline_state(**overrides)
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return data


# ----- resolve_runtime_adapter_id -----


class ResolveRuntimeAdapterIdTests(_RuntimeAdapterTestCase):

    def test_returns_default_when_both_unset(self) -> None:
        self.assertEqual(
            agent_loop.resolve_runtime_adapter_id(None, None),
            agent_loop.RUNTIME_ADAPTER_DEFAULT,
        )

    def test_returns_default_when_both_empty_string(self) -> None:
        self.assertEqual(
            agent_loop.resolve_runtime_adapter_id("", ""),
            agent_loop.RUNTIME_ADAPTER_DEFAULT,
        )

    def test_cli_takes_precedence_over_env(self) -> None:
        self.assertEqual(
            agent_loop.resolve_runtime_adapter_id(
                "langgraph", "local",
            ),
            "langgraph",
        )

    def test_env_used_when_cli_omitted(self) -> None:
        self.assertEqual(
            agent_loop.resolve_runtime_adapter_id(None, "langgraph"),
            "langgraph",
        )

    def test_cli_empty_string_falls_through_to_env(self) -> None:
        self.assertEqual(
            agent_loop.resolve_runtime_adapter_id("", "langgraph"),
            "langgraph",
        )

    def test_refuses_unsupported_runtime_id(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.resolve_runtime_adapter_id("crewai", None)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not in the supported set", cm.exception.reason)

    def test_refuses_unsupported_id_from_env(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.resolve_runtime_adapter_id(None, "openai_swarm")
        self.assertEqual(cm.exception.status, "halted_input_missing")

    def test_accepts_explicit_local_selection(self) -> None:
        self.assertEqual(
            agent_loop.resolve_runtime_adapter_id("local", None),
            "local",
        )


# ----- make_runtime_adapter -----


class MakeRuntimeAdapterTests(_RuntimeAdapterTestCase):

    def test_returns_local_adapter_for_local_id(self) -> None:
        adapter = agent_loop.make_runtime_adapter("local")
        self.assertIsInstance(adapter, agent_loop.LocalRuntimeAdapter)
        self.assertEqual(
            adapter.runtime_id, agent_loop.RUNTIME_ADAPTER_DEFAULT,
        )

    def test_returns_langgraph_adapter_for_langgraph_id(self) -> None:
        adapter = agent_loop.make_runtime_adapter("langgraph")
        self.assertIsInstance(
            adapter,
            agent_loop.LangGraphExperimentalRuntimeAdapter,
        )
        self.assertEqual(
            adapter.runtime_id, agent_loop.LANGGRAPH_RUNTIME_ID,
        )

    def test_refuses_on_unsupported_id(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.make_runtime_adapter("openai_swarm")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("supported set", cm.exception.reason)


# ----- LocalRuntimeAdapter -----


class LocalRuntimeAdapterTests(_RuntimeAdapterTestCase):

    def test_evaluate_returns_local_sentinel(self) -> None:
        adapter = agent_loop.LocalRuntimeAdapter()
        result = adapter.evaluate(self.repo_root)
        self.assertEqual(result["runtime_id"], "local")
        self.assertEqual(
            result["outcome"], "local_default_unchanged",
        )

    def test_evaluate_does_not_read_loop_state(self) -> None:
        # The local sentinel must not require loop-state to exist.
        # Loop-state is intentionally NOT planted in this test.
        self.assertFalse(self.state_path.exists())
        adapter = agent_loop.LocalRuntimeAdapter()
        result = adapter.evaluate(self.repo_root)
        self.assertEqual(result["runtime_id"], "local")

    def test_evaluate_does_not_mutate_canonical_state(self) -> None:
        self._write_state()
        before = self.state_path.read_bytes()
        adapter = agent_loop.LocalRuntimeAdapter()
        adapter.evaluate(self.repo_root, log_path=self.log_path)
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_evaluate_emits_audit_note_when_log_path_supplied(
        self,
    ) -> None:
        adapter = agent_loop.LocalRuntimeAdapter()
        adapter.evaluate(self.repo_root, log_path=self.log_path)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            agent_loop.RUNTIME_ADAPTER_AUDIT_NOTE_PREFIX, log_text,
        )
        self.assertIn("local local_default_sentinel", log_text)

    def test_evaluate_emits_no_log_when_log_path_omitted(
        self,
    ) -> None:
        before = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        adapter = agent_loop.LocalRuntimeAdapter()
        adapter.evaluate(self.repo_root)
        after = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        self.assertEqual(before, after)


# ----- LangGraphExperimentalRuntimeAdapter: success shape -----


class LangGraphAdapterSuccessShapeTests(_RuntimeAdapterTestCase):

    def test_evaluate_returns_runtime_id_and_node_names(self) -> None:
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        result = adapter.evaluate(self.repo_root)
        self.assertEqual(
            result["runtime_id"], agent_loop.LANGGRAPH_RUNTIME_ID,
        )
        self.assertEqual(
            result["node_names"],
            list(agent_loop.LANGGRAPH_NODE_NAMES),
        )

    def test_evaluate_walks_every_node_in_fixed_order(self) -> None:
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        result = adapter.evaluate(self.repo_root)
        node_results = result["node_results"]
        self.assertEqual(
            list(node_results.keys()),
            list(agent_loop.LANGGRAPH_NODE_NAMES),
        )

    def test_evaluate_records_per_node_results(self) -> None:
        data = self._write_state(cycle_count=2)
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        result = adapter.evaluate(self.repo_root)
        nr = result["node_results"]
        self.assertEqual(nr["load_state"]["phase"], data["phase"])
        self.assertEqual(
            nr["load_state"]["sub_phase"], data["sub_phase"],
        )
        self.assertEqual(nr["load_state"]["cycle_count"], 2)
        self.assertTrue(nr["validate_state"]["valid"])
        self.assertIn("memory_entries_seen", nr["consult_memory"])
        self.assertIn(
            "active_checkpoint_present", nr["consult_checkpoint"],
        )
        self.assertEqual(
            nr["evaluate"]["approval_mode"], data["approval_mode"],
        )

    def test_consult_checkpoint_reports_false_when_no_checkpoint(
        self,
    ) -> None:
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        result = adapter.evaluate(self.repo_root)
        self.assertFalse(
            result["node_results"]["consult_checkpoint"][
                "active_checkpoint_present"
            ],
        )

    def test_consult_memory_reports_zero_when_no_memory(self) -> None:
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        result = adapter.evaluate(self.repo_root)
        self.assertEqual(
            result["node_results"]["consult_memory"][
                "memory_entries_seen"
            ],
            0,
        )


# ----- LangGraph adapter: audit notes -----


class LangGraphAdapterAuditNoteTests(_RuntimeAdapterTestCase):

    def test_emits_begin_and_complete_book_end_notes(self) -> None:
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        adapter.evaluate(self.repo_root, log_path=self.log_path)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental evaluate_begin", log_text,
        )
        self.assertIn(
            "langgraph_experimental evaluate_complete", log_text,
        )

    def test_emits_one_audit_note_per_node(self) -> None:
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        adapter.evaluate(self.repo_root, log_path=self.log_path)
        log_text = self.log_path.read_text(encoding="utf-8")
        for node in agent_loop.LANGGRAPH_NODE_NAMES:
            self.assertIn(
                f"langgraph_experimental node={node}", log_text,
                f"missing audit note for node={node}",
            )

    def test_audit_note_prefix_matches_contract_constant(self) -> None:
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        adapter.evaluate(self.repo_root, log_path=self.log_path)
        log_text = self.log_path.read_text(encoding="utf-8")
        # Every runtime-adapter line carries the contract prefix.
        for line in log_text.splitlines():
            if agent_loop.LANGGRAPH_RUNTIME_ID in line:
                self.assertIn(
                    agent_loop.RUNTIME_ADAPTER_AUDIT_NOTE_PREFIX,
                    line,
                )

    def test_emits_no_audit_notes_when_log_path_omitted(self) -> None:
        self._write_state()
        before = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        adapter.evaluate(self.repo_root)
        after = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        self.assertEqual(before, after)


# ----- LangGraph adapter: halt / refusal mirroring -----


class LangGraphAdapterRefusalTests(_RuntimeAdapterTestCase):

    def test_refuses_when_loop_state_missing(self) -> None:
        # Loop-state not planted; the first node's load_loop_state
        # call refuses fail-closed with the shipped HaltError
        # vocabulary.
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        with self.assertRaises(agent_loop.HaltError) as cm:
            adapter.evaluate(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")

    def test_refuses_on_unsupported_contract_version(self) -> None:
        self._write_state(contract_version="phase-9z-vX")
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        with self.assertRaises(agent_loop.HaltError) as cm:
            adapter.evaluate(self.repo_root)
        self.assertEqual(
            cm.exception.status, "halted_contract_version_mismatch",
        )

    def test_refuses_on_missing_required_loop_state_field(self) -> None:
        data = _baseline_state()
        del data["phase"]
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        with self.assertRaises(agent_loop.HaltError) as cm:
            adapter.evaluate(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")

    def test_refuse_at_first_node_does_not_run_later_nodes(
        self,
    ) -> None:
        # Loop-state missing; the first node refuses BEFORE the
        # consult_memory or consult_checkpoint nodes run. Spy on
        # list_memory_entries and _load_active_checkpoint to confirm
        # they are not called.
        with mock.patch.object(
            agent_loop, "list_memory_entries",
        ) as me, mock.patch.object(
            agent_loop, "_load_active_checkpoint",
        ) as cp:
            adapter = (
                agent_loop.LangGraphExperimentalRuntimeAdapter()
            )
            with self.assertRaises(agent_loop.HaltError):
                adapter.evaluate(self.repo_root)
        me.assert_not_called()
        cp.assert_not_called()


# ----- LangGraph adapter: canonical-precedence -----


class LangGraphAdapterCanonicalPrecedenceTests(_RuntimeAdapterTestCase):

    def test_does_not_mutate_loop_state(self) -> None:
        self._write_state()
        before = self.state_path.read_bytes()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        adapter.evaluate(self.repo_root, log_path=self.log_path)
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_does_not_mutate_source_memory_entries(self) -> None:
        self._write_state()
        planted = agent_loop.write_memory_entry(
            self.repo_root,
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            phase="Phase 6 - Durable Memory and Optional Context Layer",
            sub_phase=(
                "Phase 6N - Experimental LangGraph Runtime Mirror"
            ),
            cycle_count=1,
            source_artifact_path=".agent-loop/loop-state.json",
            body=json.dumps({"decision": "test"}),
        )
        before = planted.read_bytes()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        adapter.evaluate(self.repo_root, log_path=self.log_path)
        self.assertEqual(planted.read_bytes(), before)

    def test_writes_only_to_orchestrator_log(self) -> None:
        # Every file outside .agent-loop/orchestrator.log must be
        # byte-equivalent across the call (the adapter only appends
        # to the log; no canonical artifact is touched).
        self._write_state()
        snapshot: dict = {}
        for p in self.repo_root.rglob("*"):
            if p.is_file() and p != self.log_path:
                snapshot[p] = p.read_bytes()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        adapter.evaluate(self.repo_root, log_path=self.log_path)
        for p, before in snapshot.items():
            self.assertEqual(
                p.read_bytes(), before, f"mutated {p}",
            )

    def test_reloads_loop_state_on_every_node(self) -> None:
        # Per the 6M framework-state subordination rule, every node
        # MUST re-load loop-state from disk (no caching across hops).
        # Wrap load_loop_state and assert it was called once per node.
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        with mock.patch.object(
            agent_loop, "load_loop_state",
            side_effect=agent_loop.load_loop_state,
        ) as spy:
            adapter.evaluate(self.repo_root)
        self.assertEqual(
            spy.call_count, len(agent_loop.LANGGRAPH_NODE_NAMES),
        )


# ----- LangGraph adapter: checkpoint compatibility -----


class LangGraphAdapterCheckpointCompatibilityTests(
    _RuntimeAdapterTestCase,
):

    def test_consult_checkpoint_uses_shipped_load_active_checkpoint(
        self,
    ) -> None:
        # Spy on the shipped selector to confirm the adapter routes
        # through it rather than implementing a parallel selection.
        self._write_state()
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        with mock.patch.object(
            agent_loop, "_load_active_checkpoint",
            side_effect=agent_loop._load_active_checkpoint,
        ) as spy:
            adapter.evaluate(self.repo_root)
        self.assertEqual(spy.call_count, 1)

    def test_consult_checkpoint_reports_true_when_checkpoint_present(
        self,
    ) -> None:
        # Plant a checkpoint through the shipped writer; the adapter
        # must report active_checkpoint_present=True.
        data = self._write_state(
            status=(
                agent_loop.HALTED_TOKEN_EXHAUSTION
            ),
            awaiting_human_for=(
                agent_loop.TOKEN_EXHAUSTION_SUSPENSION_REASON
            ),
        )
        agent_loop.write_checkpoint_entry(
            self.repo_root,
            phase=data["phase"],
            sub_phase=data["sub_phase"],
            cycle_count=data["cycle_count"],
            source_artifact_path=".agent-loop/loop-state.json",
            task=data["task"],
            status=data["status"],
            approval_mode=data["approval_mode"],
            awaiting_human_for=data["awaiting_human_for"],
            active_prompt_path=".agent-loop/claude-prompt.md",
            suspension_reason="token_exhaustion",
            continuation_budget=2,
        )
        adapter = agent_loop.LangGraphExperimentalRuntimeAdapter()
        result = adapter.evaluate(self.repo_root)
        self.assertTrue(
            result["node_results"]["consult_checkpoint"][
                "active_checkpoint_present"
            ],
        )


# ----- cmd_runtime_adapter_eval + main(argv) -----


class CmdRuntimeAdapterEvalTests(_RuntimeAdapterTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root",
            return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_default_selects_local_runtime(self) -> None:
        # No --runtime, no env var, no loop-state planted; the local
        # sentinel runs cleanly because it does not require state.
        rc = self._run_main(["runtime-adapter-eval"])
        self.assertEqual(rc, 0)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("local local_default_sentinel", log_text)
        self.assertNotIn("langgraph_experimental", log_text)

    def test_cli_runtime_flag_selects_langgraph(self) -> None:
        self._write_state()
        rc = self._run_main([
            "runtime-adapter-eval", "--runtime", "langgraph",
        ])
        self.assertEqual(rc, 0)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental evaluate_begin", log_text,
        )
        self.assertIn(
            "langgraph_experimental evaluate_complete", log_text,
        )

    def test_cli_env_var_selects_langgraph_when_flag_omitted(
        self,
    ) -> None:
        self._write_state()
        os.environ[agent_loop.RUNTIME_ADAPTER_ENV_VAR] = "langgraph"
        try:
            rc = self._run_main(["runtime-adapter-eval"])
        finally:
            os.environ.pop(
                agent_loop.RUNTIME_ADAPTER_ENV_VAR, None,
            )
        self.assertEqual(rc, 0)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental evaluate_begin", log_text,
        )

    def test_cli_flag_overrides_env_var(self) -> None:
        os.environ[agent_loop.RUNTIME_ADAPTER_ENV_VAR] = "langgraph"
        try:
            rc = self._run_main([
                "runtime-adapter-eval", "--runtime", "local",
            ])
        finally:
            os.environ.pop(
                agent_loop.RUNTIME_ADAPTER_ENV_VAR, None,
            )
        self.assertEqual(rc, 0)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("local local_default_sentinel", log_text)
        self.assertNotIn(
            "langgraph_experimental evaluate_begin", log_text,
        )

    def test_cli_refuses_unsupported_runtime_via_halt(self) -> None:
        rc = self._run_main([
            "runtime-adapter-eval", "--runtime", "crewai",
        ])
        self.assertEqual(rc, 2)

    def test_cli_refuses_when_langgraph_evaluated_without_loop_state(
        self,
    ) -> None:
        # The langgraph mirror requires loop-state on the first node;
        # missing state refuses via _halt with rc=2 and no canonical
        # artifact appears under the .agent-loop dir.
        self.assertFalse(self.state_path.exists())
        rc = self._run_main([
            "runtime-adapter-eval", "--runtime", "langgraph",
        ])
        self.assertEqual(rc, 2)


# ----- Default-runtime preservation -----


class DefaultRuntimePreservationTests(_RuntimeAdapterTestCase):

    def test_default_path_does_not_invoke_langgraph_adapter(
        self,
    ) -> None:
        # Spy on the LangGraph adapter constructor; the default
        # selection must not instantiate it.
        with mock.patch.object(
            agent_loop,
            "LangGraphExperimentalRuntimeAdapter",
        ) as cls:
            adapter = agent_loop.make_runtime_adapter("local")
        self.assertIsInstance(
            adapter, agent_loop.LocalRuntimeAdapter,
        )
        cls.assert_not_called()

    def test_default_resolution_does_not_touch_canonical_state(
        self,
    ) -> None:
        # `resolve_runtime_adapter_id(None, None)` is pure; the
        # default-resolution path must not require any artifact on
        # disk.
        self.assertFalse(self.state_path.exists())
        runtime_id = agent_loop.resolve_runtime_adapter_id(None, None)
        self.assertEqual(runtime_id, "local")

    def test_local_adapter_evaluation_leaves_repo_byte_equivalent(
        self,
    ) -> None:
        # Plant a loop-state file; running the local sentinel via
        # the CLI must not mutate it (the audit log appends one line,
        # but no canonical artifact is touched).
        self._write_state()
        before = self.state_path.read_bytes()
        with mock.patch.object(
            agent_loop, "find_repo_root",
            return_value=self.repo_root,
        ):
            rc = agent_loop.main(["runtime-adapter-eval"])
        self.assertEqual(rc, 0)
        self.assertEqual(self.state_path.read_bytes(), before)


# ----- read_runtime_config / write_runtime_config / clear_runtime_config -----


class RuntimeConfigReadWriteTests(_RuntimeAdapterTestCase):

    @property
    def config_path(self) -> Path:
        return self.repo_root / agent_loop.RUNTIME_CONFIG_REL

    def test_read_returns_none_when_file_absent(self) -> None:
        self.assertFalse(self.config_path.exists())
        self.assertIsNone(agent_loop.read_runtime_config(self.repo_root))

    def test_write_persists_selected_runtime(self) -> None:
        path = agent_loop.write_runtime_config(
            self.repo_root, "langgraph",
        )
        self.assertEqual(path, self.config_path)
        self.assertTrue(self.config_path.is_file())
        payload = json.loads(
            self.config_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            payload["runtime_config_signal_version"],
            agent_loop.RUNTIME_CONFIG_SIGNAL_VERSION,
        )
        self.assertEqual(payload["selected_runtime"], "langgraph")

    def test_read_returns_persisted_selection(self) -> None:
        agent_loop.write_runtime_config(self.repo_root, "langgraph")
        self.assertEqual(
            agent_loop.read_runtime_config(self.repo_root),
            "langgraph",
        )

    def test_write_refuses_unsupported_runtime(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.write_runtime_config(self.repo_root, "crewai")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertFalse(self.config_path.exists())

    def test_clear_removes_persisted_config(self) -> None:
        agent_loop.write_runtime_config(self.repo_root, "langgraph")
        self.assertTrue(self.config_path.is_file())
        removed = agent_loop.clear_runtime_config(self.repo_root)
        self.assertTrue(removed)
        self.assertFalse(self.config_path.exists())
        self.assertIsNone(
            agent_loop.read_runtime_config(self.repo_root),
        )

    def test_clear_when_absent_returns_false(self) -> None:
        self.assertFalse(self.config_path.exists())
        self.assertFalse(
            agent_loop.clear_runtime_config(self.repo_root),
        )

    def test_read_refuses_non_json_file(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("not json {", encoding="utf-8")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_runtime_config(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not valid JSON", cm.exception.reason)

    def test_read_refuses_top_level_not_dict(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("[]", encoding="utf-8")
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_runtime_config(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("JSON object", cm.exception.reason)

    def test_read_refuses_missing_required_key(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({"selected_runtime": "langgraph"}),
            encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_runtime_config(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("required key", cm.exception.reason)

    def test_read_refuses_unrecognized_signal_version(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({
                "runtime_config_signal_version": "phase-6z-vX",
                "selected_runtime": "langgraph",
            }),
            encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_runtime_config(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("signal_version", cm.exception.reason)

    def test_read_refuses_unsupported_selected_runtime(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps({
                "runtime_config_signal_version": (
                    agent_loop.RUNTIME_CONFIG_SIGNAL_VERSION
                ),
                "selected_runtime": "crewai",
            }),
            encoding="utf-8",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.read_runtime_config(self.repo_root)
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("supported set", cm.exception.reason)


# ----- _resolve_runtime_with_persisted: precedence -----


class ResolveRuntimeWithPersistedTests(_RuntimeAdapterTestCase):

    def test_default_when_all_three_sources_unset(self) -> None:
        self.assertEqual(
            agent_loop._resolve_runtime_with_persisted(
                self.repo_root, None, None,
            ),
            "local",
        )

    def test_persisted_config_used_when_cli_and_env_unset(self) -> None:
        agent_loop.write_runtime_config(self.repo_root, "langgraph")
        self.assertEqual(
            agent_loop._resolve_runtime_with_persisted(
                self.repo_root, None, None,
            ),
            "langgraph",
        )

    def test_env_overrides_persisted_config(self) -> None:
        agent_loop.write_runtime_config(self.repo_root, "local")
        self.assertEqual(
            agent_loop._resolve_runtime_with_persisted(
                self.repo_root, None, "langgraph",
            ),
            "langgraph",
        )

    def test_cli_overrides_env_and_persisted(self) -> None:
        agent_loop.write_runtime_config(self.repo_root, "langgraph")
        self.assertEqual(
            agent_loop._resolve_runtime_with_persisted(
                self.repo_root, "local", "langgraph",
            ),
            "local",
        )

    def test_persisted_refusal_propagates(self) -> None:
        # A malformed persisted config refuses fail-closed even when
        # CLI and env are unset (the persisted file is the active
        # source, not the default).
        config_path = self.repo_root / agent_loop.RUNTIME_CONFIG_REL
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("not json", encoding="utf-8")
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._resolve_runtime_with_persisted(
                self.repo_root, None, None,
            )


# ----- _apply_runtime_selection: wired entry-point dispatch -----


class ApplyRuntimeSelectionTests(_RuntimeAdapterTestCase):

    def _make_args(self, runtime=None) -> argparse.Namespace:
        return argparse.Namespace(runtime=runtime)

    def test_returns_none_for_default_local(self) -> None:
        # Local must return None without reading any canonical state
        # or emitting an audit note; the default-runtime path is
        # byte-equivalent to the pre-6N behavior.
        before = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        rc = agent_loop._apply_runtime_selection(
            self.repo_root, self._make_args(), hop_kind="run",
        )
        self.assertIsNone(rc)
        after = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        self.assertEqual(before, after)

    def test_runs_pre_pass_for_langgraph(self) -> None:
        # Selecting langgraph runs the mirror's evaluate(...) pass,
        # which emits the dispatch + evaluate-begin + per-node +
        # evaluate-complete audit notes.
        self._write_state()
        rc = agent_loop._apply_runtime_selection(
            self.repo_root,
            self._make_args(runtime="langgraph"),
            hop_kind="run",
        )
        self.assertIsNone(rc)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental dispatch hop_kind='run'",
            log_text,
        )
        self.assertIn(
            "langgraph_experimental evaluate_begin", log_text,
        )
        self.assertIn(
            "langgraph_experimental evaluate_complete", log_text,
        )

    def test_persisted_config_drives_dispatch_when_no_cli_or_env(
        self,
    ) -> None:
        self._write_state()
        agent_loop.write_runtime_config(self.repo_root, "langgraph")
        rc = agent_loop._apply_runtime_selection(
            self.repo_root, self._make_args(), hop_kind="resume",
        )
        self.assertIsNone(rc)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental dispatch hop_kind='resume'",
            log_text,
        )

    def test_unsupported_id_returns_halt_exit_code(self) -> None:
        os.environ[agent_loop.RUNTIME_ADAPTER_ENV_VAR] = "crewai"
        try:
            rc = agent_loop._apply_runtime_selection(
                self.repo_root,
                self._make_args(),
                hop_kind="auto-continue",
            )
        finally:
            os.environ.pop(
                agent_loop.RUNTIME_ADAPTER_ENV_VAR, None,
            )
        self.assertEqual(rc, 2)

    def test_langgraph_with_missing_loop_state_returns_halt_exit(
        self,
    ) -> None:
        # The mirror's first node calls load_loop_state which refuses
        # via HaltError; _apply_runtime_selection routes it through
        # _halt and returns rc=2.
        self.assertFalse(self.state_path.exists())
        rc = agent_loop._apply_runtime_selection(
            self.repo_root,
            self._make_args(runtime="langgraph"),
            hop_kind="run",
        )
        self.assertEqual(rc, 2)


# ----- cmd_run / cmd_resume / cmd_auto_continue wiring -----


class WiredEntryPointTests(_RuntimeAdapterTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root",
            return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cmd_run_default_local_path_calls_run_normal_cycle(
        self,
    ) -> None:
        # Default (no --runtime, no env, no persisted): cmd_run must
        # dispatch directly to run_normal_cycle without invoking the
        # langgraph adapter. Spy on both targets.
        with mock.patch.object(
            agent_loop, "run_normal_cycle", return_value=0,
        ) as rnc, mock.patch.object(
            agent_loop, "LangGraphExperimentalRuntimeAdapter",
        ) as lg:
            rc = self._run_main(["run"])
        self.assertEqual(rc, 0)
        rnc.assert_called_once_with(self.repo_root)
        lg.assert_not_called()

    def test_cmd_run_with_langgraph_runs_pre_pass_then_default(
        self,
    ) -> None:
        # --runtime=langgraph runs the mirror evaluate pass FIRST
        # (audit notes land in orchestrator.log) and THEN delegates
        # to run_normal_cycle for the actual work. Canonical artifact
        # precedence preserved.
        self._write_state()
        with mock.patch.object(
            agent_loop, "run_normal_cycle", return_value=0,
        ) as rnc:
            rc = self._run_main(["run", "--runtime", "langgraph"])
        self.assertEqual(rc, 0)
        rnc.assert_called_once_with(self.repo_root)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental dispatch hop_kind='run'",
            log_text,
        )

    def test_cmd_auto_continue_default_calls_run_auto_continue(
        self,
    ) -> None:
        with mock.patch.object(
            agent_loop, "run_auto_continue", return_value=0,
        ) as rac, mock.patch.object(
            agent_loop, "LangGraphExperimentalRuntimeAdapter",
        ) as lg:
            rc = self._run_main(["auto-continue"])
        self.assertEqual(rc, 0)
        rac.assert_called_once_with(self.repo_root)
        lg.assert_not_called()

    def test_cmd_auto_continue_with_langgraph_runs_pre_pass(
        self,
    ) -> None:
        self._write_state()
        with mock.patch.object(
            agent_loop, "run_auto_continue", return_value=0,
        ) as rac:
            rc = self._run_main([
                "auto-continue", "--runtime", "langgraph",
            ])
        self.assertEqual(rc, 0)
        rac.assert_called_once_with(self.repo_root)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental dispatch hop_kind='auto-continue'",
            log_text,
        )

    def test_cmd_resume_default_uses_existing_dispatch(self) -> None:
        # Default (no --runtime): cmd_resume falls through to the
        # pre-6N dispatch. Missing loop-state -> run_strict_resume,
        # which raises its own halt; we just confirm the langgraph
        # adapter is NOT instantiated on the default path.
        with mock.patch.object(
            agent_loop, "run_strict_resume", return_value=2,
        ) as rsr, mock.patch.object(
            agent_loop, "LangGraphExperimentalRuntimeAdapter",
        ) as lg:
            rc = self._run_main(["resume"])
        self.assertEqual(rc, 2)
        rsr.assert_called_once_with(self.repo_root)
        lg.assert_not_called()

    def test_cmd_resume_with_langgraph_runs_pre_pass_then_dispatch(
        self,
    ) -> None:
        # --runtime=langgraph runs the mirror evaluate pass FIRST,
        # then the existing resume dispatch. Confirm both audit
        # notes land and run_strict_resume is invoked (no token-
        # exhaustion halt is planted, so the default branch).
        self._write_state()
        with mock.patch.object(
            agent_loop, "run_strict_resume", return_value=0,
        ) as rsr:
            rc = self._run_main(["resume", "--runtime", "langgraph"])
        self.assertEqual(rc, 0)
        rsr.assert_called_once_with(self.repo_root)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental dispatch hop_kind='resume'",
            log_text,
        )

    def test_cmd_run_persisted_config_drives_langgraph_pre_pass(
        self,
    ) -> None:
        # No --runtime, no env: the persisted config selects
        # langgraph. The pre-pass runs, then run_normal_cycle.
        self._write_state()
        agent_loop.write_runtime_config(self.repo_root, "langgraph")
        with mock.patch.object(
            agent_loop, "run_normal_cycle", return_value=0,
        ) as rnc:
            rc = self._run_main(["run"])
        self.assertEqual(rc, 0)
        rnc.assert_called_once_with(self.repo_root)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "langgraph_experimental dispatch hop_kind='run'",
            log_text,
        )

    def test_cmd_run_cli_overrides_persisted_langgraph_back_to_local(
        self,
    ) -> None:
        # Persisted config selects langgraph; --runtime=local
        # overrides back to the default and the mirror does NOT run.
        agent_loop.write_runtime_config(self.repo_root, "langgraph")
        with mock.patch.object(
            agent_loop, "run_normal_cycle", return_value=0,
        ) as rnc, mock.patch.object(
            agent_loop, "LangGraphExperimentalRuntimeAdapter",
        ) as lg:
            rc = self._run_main(["run", "--runtime", "local"])
        self.assertEqual(rc, 0)
        rnc.assert_called_once_with(self.repo_root)
        lg.assert_not_called()


# ----- cmd_set_runtime_config -----


class CmdSetRuntimeConfigTests(_RuntimeAdapterTestCase):

    @property
    def config_path(self) -> Path:
        return self.repo_root / agent_loop.RUNTIME_CONFIG_REL

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root",
            return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_writes_persisted_config(self) -> None:
        rc = self._run_main([
            "set-runtime-config", "--runtime", "langgraph",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(self.config_path.is_file())
        payload = json.loads(
            self.config_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(payload["selected_runtime"], "langgraph")

    def test_cli_clear_removes_persisted_config(self) -> None:
        agent_loop.write_runtime_config(self.repo_root, "langgraph")
        rc = self._run_main(["set-runtime-config", "--clear"])
        self.assertEqual(rc, 0)
        self.assertFalse(self.config_path.exists())

    def test_cli_clear_when_absent_is_idempotent(self) -> None:
        # Clearing an absent config is rc=0 (the post-condition is
        # 'default off', which is already satisfied).
        self.assertFalse(self.config_path.exists())
        rc = self._run_main(["set-runtime-config", "--clear"])
        self.assertEqual(rc, 0)

    def test_cli_refuses_unsupported_runtime_via_halt(self) -> None:
        rc = self._run_main([
            "set-runtime-config", "--runtime", "crewai",
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(self.config_path.exists())

    def test_cli_requires_runtime_or_clear(self) -> None:
        # argparse rejects an invocation with neither flag.
        with self.assertRaises(SystemExit) as cm:
            self._run_main(["set-runtime-config"])
        self.assertEqual(cm.exception.code, 2)

    def test_cli_emits_persist_audit_note(self) -> None:
        self._run_main([
            "set-runtime-config", "--runtime", "langgraph",
        ])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            "runtime-config persisted: selected_runtime='langgraph'",
            log_text,
        )

    def test_cli_emits_clear_audit_note(self) -> None:
        self._run_main(["set-runtime-config", "--clear"])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("runtime-config cleared", log_text)


if __name__ == "__main__":
    unittest.main()
