"""Focused tests for the Phase 6O LangChain support layer.

Scope of this suite (Phase 6O, narrow):
- `is_langchain_support_enabled(cli_flag, env_value)` returns False
  by default; True when the CLI flag is set; resolves the env var
  case-insensitively against the recognized truthy / falsy sets;
  refuses fail-closed on a typo (any unrecognized env value).
- The three helper classes (`LangChainPromptHelper`,
  `LangChainRetrievalHelper`, `LangChainToolRegistry`) refuse
  fail-closed when called without explicit opt-in. Importing or
  instantiating them is safe; only calling a method raises.
- `LangChainPromptHelper.build_prompt_payload(...)` returns a
  structured advisory-only payload with `support_signal_version`,
  `advisory_only=True`, the literal canonical-precedence note, a
  `canonical_state` subset of loop-state, and a deterministic
  `system_prompt_block`; re-reads loop-state on every call (no
  caching); never mutates canonical state; refuses on missing /
  malformed loop-state through the shipped validators.
- `LangChainRetrievalHelper.retrieve(...)` delegates to the shipped
  `retrieve_memory_entries(...)` and preserves the advisory marker
  on every returned entry verbatim; refuses fail-closed if any
  returned entry is missing the marker.
- `LangChainToolRegistry.list_tools()` returns the four named
  read-only tools; `invoke(...)` dispatches to the matching shipped
  inspector and refuses on an unknown tool name.
- The `langchain-support-eval` CLI subcommand routes through
  `main(argv)` HANDLERS dispatch, refuses fail-closed when not
  opted in, honors the CLI flag and the env var, lets CLI override
  env, writes the output artifact to
  `.agent-loop/langchain-support.json`, and never modifies the
  runtime selection or invokes `run` / `resume` / `auto-continue`.
- Default-runtime preservation: the support layer never modifies the
  Phase 6N runtime-selection seam, never instantiates the LangGraph
  mirror, and never mutates the runtime-config artifact.

This slice does not import the real `langchain` package; the helpers
are pure-stdlib structural support (same shape as the Phase 6N
LangGraph mirror). A future slice can swap the implementations
behind the same helper interface to wire the real package without
changing the contract surface.
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
    data = {
        "phase": "Phase 6 - Durable Memory and Optional Context Layer",
        "sub_phase": "Phase 6O - LangChain Support Layer",
        "task": "Implement the LangChain support layer.",
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


class _LangChainSupportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name).resolve()
        self.al = self.repo_root / ".agent-loop"
        self.al.mkdir(parents=True, exist_ok=True)
        self.state_path = self.al / "loop-state.json"
        self.log_path = self.al / "orchestrator.log"
        self.output_path = (
            self.repo_root / agent_loop.LANGCHAIN_SUPPORT_OUTPUT_REL
        )
        # Make sure the env var is clean.
        self._saved_env = os.environ.pop(
            agent_loop.LANGCHAIN_SUPPORT_ENV_VAR, None,
        )

    def tearDown(self) -> None:
        if self._saved_env is not None:
            os.environ[agent_loop.LANGCHAIN_SUPPORT_ENV_VAR] = (
                self._saved_env
            )

    def _write_state(self, **overrides) -> dict:
        data = _baseline_state(**overrides)
        self.state_path.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8",
        )
        return data


# ----- is_langchain_support_enabled -----


class IsLangchainSupportEnabledTests(_LangChainSupportTestCase):

    def test_default_false_when_both_unset(self) -> None:
        self.assertFalse(
            agent_loop.is_langchain_support_enabled(False, None),
        )

    def test_cli_flag_true_returns_true(self) -> None:
        self.assertTrue(
            agent_loop.is_langchain_support_enabled(True, None),
        )

    def test_cli_flag_true_overrides_env_falsy(self) -> None:
        self.assertTrue(
            agent_loop.is_langchain_support_enabled(True, "off"),
        )

    def test_env_truthy_one_returns_true(self) -> None:
        self.assertTrue(
            agent_loop.is_langchain_support_enabled(False, "1"),
        )

    def test_env_truthy_true_case_insensitive(self) -> None:
        self.assertTrue(
            agent_loop.is_langchain_support_enabled(False, "TRUE"),
        )

    def test_env_falsy_off_returns_false(self) -> None:
        self.assertFalse(
            agent_loop.is_langchain_support_enabled(False, "off"),
        )

    def test_env_empty_string_returns_false(self) -> None:
        self.assertFalse(
            agent_loop.is_langchain_support_enabled(False, ""),
        )

    def test_env_garbage_refuses_fail_closed(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop.is_langchain_support_enabled(
                False, "garbage",
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not in the recognized", cm.exception.reason)


# ----- _ensure_langchain_support_enabled guard -----


class EnsureLangchainSupportEnabledTests(_LangChainSupportTestCase):

    def test_passes_when_enabled(self) -> None:
        # No exception expected.
        agent_loop._ensure_langchain_support_enabled(enabled=True)

    def test_refuses_when_disabled(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._ensure_langchain_support_enabled(
                enabled=False,
            )
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("opt-in", cm.exception.reason)


# ----- LangChainPromptHelper -----


class LangChainPromptHelperTests(_LangChainSupportTestCase):

    def test_instantiation_without_opt_in_is_safe(self) -> None:
        # Constructing the helper does not raise; only invoking it
        # without opt-in does.
        helper = agent_loop.LangChainPromptHelper(self.repo_root)
        self.assertEqual(
            helper.support_signal_version,
            agent_loop.LANGCHAIN_SUPPORT_SIGNAL_VERSION,
        )

    def test_build_refuses_when_not_enabled(self) -> None:
        helper = agent_loop.LangChainPromptHelper(self.repo_root)
        with self.assertRaises(agent_loop.HaltError) as cm:
            helper.build_prompt_payload()
        self.assertEqual(cm.exception.status, "halted_input_missing")

    def test_build_returns_payload_with_required_keys(self) -> None:
        self._write_state()
        helper = agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        )
        payload = helper.build_prompt_payload()
        for key in (
            "support_signal_version",
            "built_at",
            "advisory_only",
            "canonical_precedence_note",
            "canonical_state",
            "system_prompt_block",
        ):
            self.assertIn(key, payload)

    def test_build_payload_carries_advisory_only_true(self) -> None:
        self._write_state()
        helper = agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        )
        payload = helper.build_prompt_payload()
        self.assertIs(payload["advisory_only"], True)

    def test_build_payload_carries_literal_precedence_note(
        self,
    ) -> None:
        self._write_state()
        helper = agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        )
        payload = helper.build_prompt_payload()
        self.assertIs(
            payload["canonical_precedence_note"],
            agent_loop.LANGCHAIN_SUPPORT_CANONICAL_PRECEDENCE_NOTE,
        )

    def test_build_payload_canonical_state_mirrors_loop_state(
        self,
    ) -> None:
        data = self._write_state(cycle_count=5)
        helper = agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        )
        payload = helper.build_prompt_payload()
        cs = payload["canonical_state"]
        self.assertEqual(cs["phase"], data["phase"])
        self.assertEqual(cs["sub_phase"], data["sub_phase"])
        self.assertEqual(cs["task"], data["task"])
        self.assertEqual(cs["cycle_count"], 5)
        self.assertEqual(cs["approval_mode"], data["approval_mode"])

    def test_build_refuses_on_missing_loop_state(self) -> None:
        helper = agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            helper.build_prompt_payload()
        self.assertEqual(cm.exception.status, "halted_input_missing")

    def test_build_refuses_on_unsupported_contract_version(
        self,
    ) -> None:
        self._write_state(contract_version="phase-9z-vX")
        helper = agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            helper.build_prompt_payload()
        self.assertEqual(
            cm.exception.status, "halted_contract_version_mismatch",
        )

    def test_build_does_not_mutate_loop_state(self) -> None:
        self._write_state()
        before = self.state_path.read_bytes()
        agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        ).build_prompt_payload()
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_build_emits_audit_note_when_log_path_supplied(
        self,
    ) -> None:
        self._write_state()
        agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        ).build_prompt_payload(log_path=self.log_path)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            agent_loop.LANGCHAIN_SUPPORT_AUDIT_NOTE_PREFIX, log_text,
        )
        self.assertIn("prompt_payload built", log_text)

    def test_build_no_log_writes_when_log_path_omitted(self) -> None:
        self._write_state()
        before = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        ).build_prompt_payload()
        after = (
            self.log_path.read_bytes()
            if self.log_path.exists() else b""
        )
        self.assertEqual(before, after)


# ----- LangChainRetrievalHelper -----


class LangChainRetrievalHelperTests(_LangChainSupportTestCase):

    def test_retrieve_refuses_when_not_enabled(self) -> None:
        helper = agent_loop.LangChainRetrievalHelper(self.repo_root)
        with self.assertRaises(agent_loop.HaltError):
            helper.retrieve(phase="Phase 6")

    def test_retrieve_returns_empty_when_no_memory(self) -> None:
        helper = agent_loop.LangChainRetrievalHelper(
            self.repo_root, enabled=True,
        )
        results = helper.retrieve(phase="Phase 6")
        self.assertEqual(results, [])

    def test_retrieve_preserves_advisory_marker(self) -> None:
        # Plant one memory entry through the shipped writer, then
        # retrieve via the helper; the advisory marker must be present.
        agent_loop.write_memory_entry(
            self.repo_root,
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            phase="Phase 6",
            sub_phase="6O",
            cycle_count=1,
            source_artifact_path=".agent-loop/loop-state.json",
            body=json.dumps({"decision": "test"}),
        )
        helper = agent_loop.LangChainRetrievalHelper(
            self.repo_root, enabled=True,
        )
        results = helper.retrieve(phase="Phase 6", sub_phase="6O")
        self.assertEqual(len(results), 1)
        self.assertTrue(
            results[0][agent_loop.MEMORY_RETRIEVAL_ADVISORY_FIELD],
        )

    def test_retrieve_delegates_to_shipped_retriever(self) -> None:
        helper = agent_loop.LangChainRetrievalHelper(
            self.repo_root, enabled=True,
        )
        with mock.patch.object(
            agent_loop, "retrieve_memory_entries", return_value=[],
        ) as spy:
            helper.retrieve(phase="Phase 6", sub_phase="6O")
        spy.assert_called_once()
        kw = spy.call_args.kwargs
        self.assertEqual(kw["phase"], "Phase 6")
        self.assertEqual(kw["sub_phase"], "6O")

    def test_retrieve_refuses_on_missing_advisory_marker(self) -> None:
        helper = agent_loop.LangChainRetrievalHelper(
            self.repo_root, enabled=True,
        )
        # Mock shipped retrieve to return a malformed (advisory-less)
        # entry. The wrapper must refuse fail-closed.
        with mock.patch.object(
            agent_loop, "retrieve_memory_entries",
            return_value=[{"phase": "Phase 6", "category": "decision"}],
        ):
            with self.assertRaises(agent_loop.HaltError) as cm:
                helper.retrieve(phase="Phase 6")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("non-advisory", cm.exception.reason)


# ----- LangChainToolRegistry -----


class LangChainToolRegistryTests(_LangChainSupportTestCase):

    def test_list_tools_refuses_when_not_enabled(self) -> None:
        reg = agent_loop.LangChainToolRegistry(self.repo_root)
        with self.assertRaises(agent_loop.HaltError):
            reg.list_tools()

    def test_invoke_refuses_when_not_enabled(self) -> None:
        reg = agent_loop.LangChainToolRegistry(self.repo_root)
        with self.assertRaises(agent_loop.HaltError):
            reg.invoke("read_loop_state")

    def test_list_tools_returns_named_set(self) -> None:
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        tools = reg.list_tools()
        self.assertEqual(len(tools), 4)
        names = {t["name"] for t in tools}
        self.assertEqual(
            names, set(agent_loop.LANGCHAIN_SUPPORT_TOOL_NAMES),
        )
        for t in tools:
            self.assertEqual(t["kind"], "read")
            self.assertEqual(
                t["support_signal_version"],
                agent_loop.LANGCHAIN_SUPPORT_SIGNAL_VERSION,
            )

    def test_invoke_read_loop_state_returns_loaded_state(self) -> None:
        data = self._write_state(cycle_count=2)
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        loaded = reg.invoke("read_loop_state")
        self.assertEqual(loaded["phase"], data["phase"])
        self.assertEqual(loaded["cycle_count"], 2)

    def test_invoke_list_memory_entries_returns_relative_paths(
        self,
    ) -> None:
        path = agent_loop.write_memory_entry(
            self.repo_root,
            category=agent_loop.MEMORY_CATEGORY_DECISION,
            phase="Phase 6", sub_phase="6O", cycle_count=1,
            source_artifact_path=".agent-loop/loop-state.json",
            body=json.dumps({"d": "ok"}),
        )
        rel = path.relative_to(self.repo_root).as_posix()
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        results = reg.invoke("list_memory_entries")
        self.assertIn(rel, results)

    def test_invoke_load_active_checkpoint_returns_none_when_absent(
        self,
    ) -> None:
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        self.assertIsNone(reg.invoke("load_active_checkpoint"))

    def test_invoke_unknown_tool_refuses(self) -> None:
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            reg.invoke("write_memory_entry")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("not in the registry", cm.exception.reason)

    def test_invoke_read_loop_state_refuses_on_malformed_state(
        self,
    ) -> None:
        # Phase 6O fix: a parseable-but-structurally-invalid
        # loop-state must refuse fail-closed through the shipped
        # validator chain, not leak through as a partial dict.
        self.state_path.write_text(
            json.dumps({"phase": "P"}) + "\n", encoding="utf-8",
        )
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            reg.invoke("read_loop_state")
        self.assertEqual(cm.exception.status, "halted_input_missing")
        self.assertIn("missing required keys", cm.exception.reason)

    def test_invoke_read_loop_state_refuses_on_unsupported_contract(
        self,
    ) -> None:
        self._write_state(contract_version="phase-bogus-vX")
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            reg.invoke("read_loop_state")
        self.assertEqual(
            cm.exception.status, "halted_contract_version_mismatch",
        )

    def test_invoke_read_loop_state_refuses_on_missing_file(
        self,
    ) -> None:
        # No loop-state.json written.
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            reg.invoke("read_loop_state")
        self.assertEqual(cm.exception.status, "halted_input_missing")

    def test_invoke_read_loop_state_returns_full_validated_state(
        self,
    ) -> None:
        # Post-fix: success path returns the full validated dict (the
        # same shape the rest of the orchestrator works with), not a
        # narrower projection.
        data = self._write_state(cycle_count=3)
        reg = agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        )
        loaded = reg.invoke("read_loop_state")
        self.assertEqual(loaded["phase"], data["phase"])
        self.assertEqual(loaded["cycle_count"], 3)
        self.assertEqual(
            loaded["contract_version"], data["contract_version"],
        )
        self.assertEqual(
            loaded["approval_mode"], data["approval_mode"],
        )

    def test_tool_names_are_all_read_only(self) -> None:
        # Defense-in-depth: every name in the static set is read-only;
        # the registry never exposes a write-side tool in this slice.
        for name in agent_loop.LANGCHAIN_SUPPORT_TOOL_NAMES:
            self.assertNotIn("write", name)
            self.assertNotIn("delete", name)


# ----- cmd_langchain_support_eval -----


class CmdLangchainSupportEvalTests(_LangChainSupportTestCase):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root",
            return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_cli_refuses_when_not_opted_in(self) -> None:
        # No CLI flag, no env var: refuse via _halt with rc=2.
        self._write_state()
        rc = self._run_main(["langchain-support-eval"])
        self.assertEqual(rc, 2)
        self.assertFalse(self.output_path.exists())

    def test_cli_writes_output_when_cli_flag_set(self) -> None:
        self._write_state()
        rc = self._run_main([
            "langchain-support-eval",
            "--enable-langchain-support",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(self.output_path.is_file())
        artifact = json.loads(
            self.output_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            artifact["support_signal_version"],
            agent_loop.LANGCHAIN_SUPPORT_SIGNAL_VERSION,
        )
        self.assertIs(artifact["advisory_only"], True)
        self.assertIn("prompt_payload", artifact)
        self.assertIn("tools_registered", artifact)
        self.assertEqual(len(artifact["tools_registered"]), 4)

    def test_cli_env_var_opts_in_when_flag_omitted(self) -> None:
        self._write_state()
        os.environ[agent_loop.LANGCHAIN_SUPPORT_ENV_VAR] = "1"
        try:
            rc = self._run_main(["langchain-support-eval"])
        finally:
            os.environ.pop(
                agent_loop.LANGCHAIN_SUPPORT_ENV_VAR, None,
            )
        self.assertEqual(rc, 0)
        self.assertTrue(self.output_path.is_file())

    def test_cli_refuses_on_garbage_env_value(self) -> None:
        self._write_state()
        os.environ[agent_loop.LANGCHAIN_SUPPORT_ENV_VAR] = "garbage"
        try:
            rc = self._run_main(["langchain-support-eval"])
        finally:
            os.environ.pop(
                agent_loop.LANGCHAIN_SUPPORT_ENV_VAR, None,
            )
        self.assertEqual(rc, 2)
        self.assertFalse(self.output_path.exists())

    def test_cli_audit_note_lands_in_log(self) -> None:
        self._write_state()
        self._run_main([
            "langchain-support-eval",
            "--enable-langchain-support",
        ])
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn(
            agent_loop.LANGCHAIN_SUPPORT_AUDIT_NOTE_PREFIX, log_text,
        )
        self.assertIn("eval written", log_text)

    def test_cli_refuses_on_missing_loop_state_when_opted_in(
        self,
    ) -> None:
        # Loop-state not planted but support opted in. The prompt
        # helper's load_loop_state refuses fail-closed; rc=2.
        self.assertFalse(self.state_path.exists())
        rc = self._run_main([
            "langchain-support-eval",
            "--enable-langchain-support",
        ])
        self.assertEqual(rc, 2)
        self.assertFalse(self.output_path.exists())


# ----- Default-runtime preservation -----


class LangchainSupportDoesNotControlRuntimeTests(
    _LangChainSupportTestCase,
):

    def _run_main(self, argv) -> int:
        with mock.patch.object(
            agent_loop, "find_repo_root",
            return_value=self.repo_root,
        ):
            return agent_loop.main(argv)

    def test_eval_does_not_invoke_run_normal_cycle(self) -> None:
        # langchain-support-eval is read-only against the runtime
        # plane. Spy on run_normal_cycle / run_strict_resume /
        # run_auto_continue to confirm none are called.
        self._write_state()
        with mock.patch.object(
            agent_loop, "run_normal_cycle", return_value=0,
        ) as rnc, mock.patch.object(
            agent_loop, "run_strict_resume", return_value=0,
        ) as rsr, mock.patch.object(
            agent_loop, "run_auto_continue", return_value=0,
        ) as rac:
            self._run_main([
                "langchain-support-eval",
                "--enable-langchain-support",
            ])
        rnc.assert_not_called()
        rsr.assert_not_called()
        rac.assert_not_called()

    def test_eval_does_not_instantiate_langgraph_adapter(self) -> None:
        # The 6N LangGraph mirror must not be touched by 6O code.
        self._write_state()
        with mock.patch.object(
            agent_loop,
            "LangGraphExperimentalRuntimeAdapter",
        ) as lg:
            self._run_main([
                "langchain-support-eval",
                "--enable-langchain-support",
            ])
        lg.assert_not_called()

    def test_eval_does_not_mutate_runtime_config(self) -> None:
        # The 6N persisted runtime-config artifact must not be
        # touched by 6O code. Plant it, run the 6O eval, assert
        # it is byte-equivalent.
        self._write_state()
        agent_loop.write_runtime_config(self.repo_root, "local")
        cfg_path = (
            self.repo_root / agent_loop.RUNTIME_CONFIG_REL
        )
        before = cfg_path.read_bytes()
        self._run_main([
            "langchain-support-eval",
            "--enable-langchain-support",
        ])
        self.assertEqual(cfg_path.read_bytes(), before)

    def test_helper_call_does_not_mutate_loop_state(self) -> None:
        # Library-level confirmation: a full helper exercise does
        # not modify loop-state on disk.
        self._write_state()
        before = self.state_path.read_bytes()
        agent_loop.LangChainPromptHelper(
            self.repo_root, enabled=True,
        ).build_prompt_payload(log_path=self.log_path)
        agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        ).list_tools()
        agent_loop.LangChainToolRegistry(
            self.repo_root, enabled=True,
        ).invoke("read_loop_state")
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_eval_does_not_write_outside_named_artifact_and_log(
        self,
    ) -> None:
        # Snapshot every file outside the output artifact AND the
        # orchestrator log; assert byte-equivalence after the eval.
        self._write_state()
        snapshot: dict = {}
        for p in self.repo_root.rglob("*"):
            if (
                p.is_file()
                and p != self.output_path
                and p != self.log_path
            ):
                snapshot[p] = p.read_bytes()
        self._run_main([
            "langchain-support-eval",
            "--enable-langchain-support",
        ])
        for p, before in snapshot.items():
            self.assertEqual(
                p.read_bytes(), before, f"mutated {p}",
            )


if __name__ == "__main__":
    unittest.main()
