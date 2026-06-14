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


if __name__ == "__main__":
    unittest.main()
