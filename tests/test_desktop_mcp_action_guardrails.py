"""Phase 10U - MCP Action Guardrails And Per-Tool Approval Policies
tests.

Exercises:
  - module-level constants (signal version, precedence note,
    closed effect-class / mutation-scope / approval-policy /
    enablement-state / approval-requirement / audit-required-field
    / refusal-reason enumerations)
  - the closed `_DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY` shape
  - the `_desktop_mcp_action_guardrails_validate_descriptor(...)`
    validator (positive + every closed-enumeration negative,
    including the cross-check that the parent server id exists in
    `_DESKTOP_MCP_ASSISTANCE_REGISTRY` and carries
    `deferred_mutating_class`)
  - per-requirement approval-state computation
  - the closed three-state enablement state machine including
    the Phase 10U fail-closed default
    (`refused_until_policy_update`) that survives even with every
    operator input satisfied
  - `build_desktop_mcp_action_guardrails_view(...)` shape +
    HaltError soft-failure on the loop-state delegate
  - `render_desktop_mcp_action_guardrails_text(...)` per-line
    attribution
  - `build_desktop_mcp_action_guardrails_controls(...)` widget
    descriptor shape (every control disabled in this slice
    because `phase_10u_runtime_available` is hard-coded False)
  - `cmd_view_desktop_mcp_action_guardrails(...)` CLI handler
    wiring (Phase-10L-mandated `--controller-root` REQUIRED
    refusal, missing-marker refusal, Phase 7C always-exit-0 rule,
    handler-registered, parser-accepts-subcommand)
  - integration into `assemble_desktop_app_view(...)` and
    `render_desktop_app_text(...)` (the new `MCP Action
    Guardrails (Phase 10U)` sub-view)
  - non-mutation invariants (no orchestrator.log write, no
    loop-state mutation, no `_halt(...)` invocation, no
    subprocess spawn, no network socket open, no Phase 10I cap
    widening, no canonical artifact write)
"""
from __future__ import annotations

import argparse
import io
import json
import socket
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402


CONTRACT_VERSION = "phase-3a-v2"


def _make_controller(
    td: Path,
    status: str = "awaiting_claude_implementation",
    approval_mode: str = "review",
) -> Path:
    td.mkdir(parents=True, exist_ok=True)
    (td / "AGENTS.md").write_text("test\n", encoding="utf-8")
    (td / "CLAUDE.md").write_text("test\n", encoding="utf-8")
    (td / "TASK.md").write_text(
        "# TASK.md\n## Human Objective\n\ntest task\n",
        encoding="utf-8",
    )
    (td / ".agent-loop").mkdir()
    (td / ".agent-loop" / "loop-state.json").write_text(
        json.dumps({
            "phase": "Phase 10 - Future Product Features",
            "sub_phase": (
                "Phase 10U - MCP Action Guardrails And "
                "Per-Tool Approval Policies"
            ),
            "task": "phase-10u-test",
            "status": status,
            "cycle_count": 1,
            "max_cycles": 3,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": CONTRACT_VERSION,
            "claude_version": "claude-opus-4-7",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
            "approval_mode": approval_mode,
            "awaiting_human_for": None,
        }),
        encoding="utf-8",
    )
    return td


def _full_inputs() -> dict:
    """Return per-session operator inputs that satisfy every
    operator-side approval requirement for every registry action.
    Used by tests that prove the Phase 10U fail-closed default
    survives even when the operator has supplied everything they
    can supply.
    """
    action_ids = [
        spec["action_id"]
        for spec in agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY
    ]
    return {
        "identity": "yoomin",
        "acknowledged_action_ids": frozenset(action_ids),
        "dry_run_reviewed_action_ids": frozenset(action_ids),
        "policy_permitted_action_ids": frozenset(action_ids),
    }


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
class ConstantsTests(unittest.TestCase):

    def test_signal_version(self) -> None:
        self.assertEqual(
            agent_loop.DESKTOP_MCP_ACTION_GUARDRAILS_SIGNAL_VERSION,
            "phase-10u-v1",
        )

    def test_precedence_note_pins_phase_10u_contract(self) -> None:
        note = (
            agent_loop.DESKTOP_MCP_ACTION_GUARDRAILS_PRECEDENCE_NOTE
        )
        for needle in (
            "Phase 10U",
            "Phase 10O",
            "Phase 10S",
            "Phase 10T",
            "Phase 10I",
            "deferred_mutating_class",
            "refused_until_policy_update",
            "phase_10u_runtime_available",
            "NEVER spawns a subprocess",
            "NEVER opens a network socket",
            "NEVER mutates any canonical artifact",
            "NEVER widens the Phase 10I cap",
        ):
            self.assertIn(needle, note)

    def test_effect_classes_closed_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.MCP_ACTION_EFFECT_CLASSES,
            (
                "posts_external_artifact",
                "mutates_external_state",
                "triggers_remote_workflow",
            ),
        )

    def test_mutation_scopes_closed_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.MCP_ACTION_MUTATION_SCOPES,
            (
                "external_artifact",
                "external_state",
                "external_workflow",
            ),
        )

    def test_approval_policies_closed_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.MCP_ACTION_APPROVAL_POLICIES,
            (
                "per_action_explicit_approval",
                "per_session_explicit_approval",
                "refused_until_policy_update",
            ),
        )

    def test_enablement_states_closed_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.MCP_ACTION_ENABLEMENT_STATES,
            (
                "disabled_by_default",
                "enabled_pending_runtime",
                "refused_until_policy_update",
            ),
        )

    def test_approval_requirements_closed_enumeration(
        self,
    ) -> None:
        self.assertEqual(
            agent_loop.MCP_ACTION_APPROVAL_REQUIREMENTS,
            (
                "operator_per_action_acknowledgement",
                "operator_supplied_identity",
                "approval_mode_supports_action",
                "phase_10u_runtime_available",
                "policy_pack_permits_action",
                "audit_log_appendable",
                "dry_run_payload_reviewed",
            ),
        )

    def test_audit_required_fields_closed_enumeration(
        self,
    ) -> None:
        # Anchor the closed audit-entry envelope a future runtime
        # slice MUST persist verbatim; widening this envelope
        # without explicitly extending this constant is a contract
        # violation.
        self.assertEqual(
            agent_loop.MCP_ACTION_AUDIT_REQUIRED_FIELDS,
            (
                "action_id",
                "server_id",
                "operator_identity",
                "approval_mode",
                "action_dispatched_at_utc",
                "dry_run_payload_sha256",
                "policy_pack_rule_id",
                "operator_per_action_acknowledgement_at_utc",
                "outcome",
                "refusal_reason",
            ),
        )

    def test_refusal_reasons_closed_enumeration(self) -> None:
        self.assertEqual(
            agent_loop.MCP_ACTION_REFUSAL_REASONS,
            (
                "approval_mode_strict",
                "runtime_not_available",
                "policy_pack_refuses_action",
                "operator_identity_missing",
                "operator_acknowledgement_missing",
                "dry_run_unreviewed",
                "audit_log_unappendable",
            ),
        )

    def test_permitted_approval_modes(self) -> None:
        self.assertEqual(
            agent_loop.MCP_ACTION_PERMITTED_APPROVAL_MODES,
            frozenset({"review", "autonomous"}),
        )


# ---------------------------------------------------------------------------
# Registry shape
# ---------------------------------------------------------------------------
class RegistryShapeTests(unittest.TestCase):

    def test_registry_is_non_empty_tuple(self) -> None:
        registry = agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY
        self.assertIsInstance(registry, tuple)
        self.assertGreater(len(registry), 0)

    def test_every_registry_entry_validates(self) -> None:
        for spec in (
            agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY
        ):
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )

    def test_every_registry_action_id_unique(self) -> None:
        ids = [
            spec["action_id"]
            for spec in (
                agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY
            )
        ]
        self.assertEqual(len(ids), len(set(ids)))

    def test_registry_covers_every_effect_class(self) -> None:
        seen_effect_classes = {
            spec["effect_class"]
            for spec in (
                agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY
            )
        }
        self.assertEqual(
            seen_effect_classes,
            set(agent_loop.MCP_ACTION_EFFECT_CLASSES),
        )

    def test_every_registry_entry_targets_deferred_mutating_server(
        self,
    ) -> None:
        server_classes = {
            entry["id"]: entry["permission_class"]
            for entry in (
                agent_loop._DESKTOP_MCP_ASSISTANCE_REGISTRY
            )
        }
        for spec in (
            agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY
        ):
            self.assertEqual(
                server_classes.get(spec["server_id"]),
                "deferred_mutating_class",
                f"action {spec['action_id']!r} parent "
                f"server {spec['server_id']!r} must be a "
                f"deferred_mutating_class server",
            )


# ---------------------------------------------------------------------------
# Validator: positive + every closed-enumeration negative
# ---------------------------------------------------------------------------
class ValidatorTests(unittest.TestCase):

    def _valid_spec(self) -> dict:
        return dict(
            agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY[0]
        )

    def test_accepts_valid_spec(self) -> None:
        agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
            self._valid_spec(),
        )

    def test_refuses_non_dict(self) -> None:
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                ["nope"],
            )
        self.assertIn("not a dict", str(cm.exception))

    def test_refuses_missing_string_field(self) -> None:
        spec = self._valid_spec()
        del spec["display_name"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )

    def test_refuses_empty_string_field(self) -> None:
        spec = self._valid_spec()
        spec["description"] = ""
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )

    def test_refuses_missing_list_field(self) -> None:
        spec = self._valid_spec()
        del spec["enablement_steps"]
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )

    def test_refuses_unknown_effect_class(self) -> None:
        spec = self._valid_spec()
        spec["effect_class"] = "deletes_universe"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn("effect_class", str(cm.exception))

    def test_refuses_unknown_mutation_scope(self) -> None:
        spec = self._valid_spec()
        spec["mutation_scope"] = "global_state"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn("mutation_scope", str(cm.exception))

    def test_refuses_unknown_approval_policy(self) -> None:
        spec = self._valid_spec()
        spec["approval_policy"] = "no_approval_required"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn("approval_policy", str(cm.exception))

    def test_refuses_unknown_default_enablement_state(
        self,
    ) -> None:
        spec = self._valid_spec()
        spec["default_enablement_state"] = "auto_enabled"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn(
            "default_enablement_state", str(cm.exception),
        )

    def test_refuses_unknown_approval_requirement(self) -> None:
        spec = self._valid_spec()
        spec["approval_requirements"] = (
            "unknown_requirement",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn(
            "approval_requirements", str(cm.exception),
        )

    def test_refuses_unknown_audit_field(self) -> None:
        spec = self._valid_spec()
        spec["audit_required_fields"] = (
            "leaked_secret_blob",
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn("audit_required_fields", str(cm.exception))

    def test_refuses_unknown_enablement_step_type(self) -> None:
        spec = self._valid_spec()
        spec["enablement_steps"] = (
            {"type": "shell_exec", "content": "rm -rf /"},
        )
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn("enablement_step type", str(cm.exception))

    def test_refuses_step_with_non_string_content(self) -> None:
        spec = self._valid_spec()
        spec["enablement_steps"] = (
            {"type": "manual_edit", "content": 42},
        )
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )

    def test_refuses_unknown_parent_server(self) -> None:
        spec = self._valid_spec()
        spec["server_id"] = "definitely_not_a_real_server"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn(
            "server_id", str(cm.exception),
        )

    def test_refuses_read_only_parent_server(self) -> None:
        # The Phase 10S `local_repo_docs` server is
        # read_only_advisory_class; pointing an action at it must
        # be refused fail-closed.
        spec = self._valid_spec()
        spec["server_id"] = "local_repo_docs"
        with self.assertRaises(agent_loop.HaltError) as cm:
            agent_loop._desktop_mcp_action_guardrails_validate_descriptor(
                spec,
            )
        self.assertIn(
            "deferred_mutating_class", str(cm.exception),
        )


# ---------------------------------------------------------------------------
# Approval-state computation
# ---------------------------------------------------------------------------
class ApprovalStateTests(unittest.TestCase):

    def _spec(self) -> dict:
        return dict(
            agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY[0]
        )

    def test_all_unsatisfied_default(self) -> None:
        state = (
            agent_loop._desktop_mcp_action_guardrails_compute_approval_state(
                self._spec(),
                approval_mode=None,
                phase_10u_runtime_available=False,
                operator_per_action_acknowledgement=False,
                operator_supplied_identity=False,
                policy_pack_permits_action=False,
                audit_log_appendable=False,
                dry_run_payload_reviewed=False,
            )
        )
        for req in agent_loop.MCP_ACTION_APPROVAL_REQUIREMENTS:
            self.assertFalse(state[req]["satisfied"], req)

    def test_strict_mode_refuses_approval(self) -> None:
        state = (
            agent_loop._desktop_mcp_action_guardrails_compute_approval_state(
                self._spec(),
                approval_mode="strict",
                phase_10u_runtime_available=True,
                operator_per_action_acknowledgement=True,
                operator_supplied_identity=True,
                policy_pack_permits_action=True,
                audit_log_appendable=True,
                dry_run_payload_reviewed=True,
            )
        )
        self.assertFalse(
            state["approval_mode_supports_action"]["satisfied"],
        )

    def test_review_mode_supports_approval(self) -> None:
        state = (
            agent_loop._desktop_mcp_action_guardrails_compute_approval_state(
                self._spec(),
                approval_mode="review",
                phase_10u_runtime_available=False,
                operator_per_action_acknowledgement=False,
                operator_supplied_identity=False,
                policy_pack_permits_action=False,
                audit_log_appendable=False,
                dry_run_payload_reviewed=False,
            )
        )
        self.assertTrue(
            state["approval_mode_supports_action"]["satisfied"],
        )

    def test_autonomous_mode_supports_approval(self) -> None:
        state = (
            agent_loop._desktop_mcp_action_guardrails_compute_approval_state(
                self._spec(),
                approval_mode="autonomous",
                phase_10u_runtime_available=False,
                operator_per_action_acknowledgement=False,
                operator_supplied_identity=False,
                policy_pack_permits_action=False,
                audit_log_appendable=False,
                dry_run_payload_reviewed=False,
            )
        )
        self.assertTrue(
            state["approval_mode_supports_action"]["satisfied"],
        )


# ---------------------------------------------------------------------------
# Enablement-state machine
# ---------------------------------------------------------------------------
class EnablementStateMachineTests(unittest.TestCase):

    def _spec(self) -> dict:
        return dict(
            agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY[0]
        )

    def test_refused_when_runtime_not_available(self) -> None:
        spec = self._spec()
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        state["phase_10u_runtime_available"] = {
            "satisfied": False,
        }
        value, reason = (
            agent_loop._desktop_mcp_action_guardrails_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "refused_until_policy_update")
        self.assertIn(
            "phase_10u_runtime_available", reason,
        )

    def test_refused_when_audit_log_unappendable(self) -> None:
        spec = self._spec()
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        state["audit_log_appendable"] = {"satisfied": False}
        value, reason = (
            agent_loop._desktop_mcp_action_guardrails_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "refused_until_policy_update")
        self.assertIn("audit_log_appendable", reason)

    def test_disabled_when_operator_side_unsatisfied(self) -> None:
        spec = self._spec()
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        state["operator_per_action_acknowledgement"] = {
            "satisfied": False,
        }
        value, reason = (
            agent_loop._desktop_mcp_action_guardrails_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "disabled_by_default")
        self.assertIn(
            "operator_per_action_acknowledgement", reason,
        )

    def test_enabled_when_every_requirement_satisfied(
        self,
    ) -> None:
        spec = self._spec()
        state = {
            req: {"satisfied": True}
            for req in spec["approval_requirements"]
        }
        value, reason = (
            agent_loop._desktop_mcp_action_guardrails_compute_enablement_state(
                spec, approval_state=state,
            )
        )
        self.assertEqual(value, "enabled_pending_runtime")
        self.assertIn("future Phase 10 runtime slice", reason)


# ---------------------------------------------------------------------------
# Audit-entry shape helper
# ---------------------------------------------------------------------------
class AuditEntryShapeTests(unittest.TestCase):

    def test_audit_entry_shape_matches_required_fields(
        self,
    ) -> None:
        spec = dict(
            agent_loop._DESKTOP_MCP_ACTION_GUARDRAILS_REGISTRY[0]
        )
        shape = (
            agent_loop._desktop_mcp_action_guardrails_audit_entry_shape(
                spec,
            )
        )
        self.assertEqual(
            set(shape.keys()),
            set(spec["audit_required_fields"]),
        )
        for value in shape.values():
            self.assertIsNone(value)


# ---------------------------------------------------------------------------
# Operator-input normalizer
# ---------------------------------------------------------------------------
class OperatorInputsNormalizerTests(unittest.TestCase):

    def test_none_returns_empty_defaults(self) -> None:
        result = (
            agent_loop._desktop_mcp_action_guardrails_normalize_operator_inputs(
                None,
            )
        )
        self.assertEqual(result["identity"], "")
        self.assertEqual(result["acknowledged_action_ids"], frozenset())
        self.assertEqual(
            result["dry_run_reviewed_action_ids"], frozenset(),
        )
        self.assertEqual(
            result["policy_permitted_action_ids"], frozenset(),
        )

    def test_strips_identity_whitespace(self) -> None:
        result = (
            agent_loop._desktop_mcp_action_guardrails_normalize_operator_inputs(
                {"identity": "  yoomin  "},
            )
        )
        self.assertEqual(result["identity"], "yoomin")

    def test_coerces_lists_to_frozenset(self) -> None:
        result = (
            agent_loop._desktop_mcp_action_guardrails_normalize_operator_inputs(
                {
                    "acknowledged_action_ids": [
                        "github_post_pr_comment",
                    ],
                    "dry_run_reviewed_action_ids": [
                        "github_edit_pr_metadata",
                    ],
                    "policy_permitted_action_ids": [
                        "github_trigger_workflow",
                    ],
                },
            )
        )
        self.assertIsInstance(
            result["acknowledged_action_ids"], frozenset,
        )
        self.assertIn(
            "github_post_pr_comment",
            result["acknowledged_action_ids"],
        )

    def test_refuses_non_dict(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_action_guardrails_normalize_operator_inputs(
                ["nope"],
            )

    def test_refuses_non_string_identity(self) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_action_guardrails_normalize_operator_inputs(
                {"identity": 42},
            )

    def test_refuses_non_iterable_acknowledged_action_ids(
        self,
    ) -> None:
        with self.assertRaises(agent_loop.HaltError):
            agent_loop._desktop_mcp_action_guardrails_normalize_operator_inputs(
                {"acknowledged_action_ids": 42},
            )


# ---------------------------------------------------------------------------
# build_desktop_mcp_action_guardrails_view shape
# ---------------------------------------------------------------------------
class BuildViewTests(unittest.TestCase):

    def test_view_shape_fields(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                )
            )
        for key in (
            "view_signal_version",
            "controller_path_canonical",
            "current_loop_state_status",
            "controller_loop_state_approval_mode",
            "phase_10t_runtime_available",
            "phase_10u_runtime_available",
            "operator_inputs",
            "effect_classes",
            "mutation_scopes",
            "approval_policies",
            "enablement_states",
            "approval_requirements",
            "audit_required_fields",
            "refusal_reasons",
            "actions",
            "precedence_note",
        ):
            self.assertIn(key, view, key)
        self.assertEqual(
            view["view_signal_version"], "phase-10u-v1",
        )
        self.assertTrue(view["phase_10t_runtime_available"])
        self.assertFalse(view["phase_10u_runtime_available"])

    def test_view_reflects_loop_state_status_and_mode(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(
                Path(td) / "c",
                status="awaiting_codex_review",
                approval_mode="autonomous",
            )
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                )
            )
        self.assertEqual(
            view["current_loop_state_status"],
            "awaiting_codex_review",
        )
        self.assertEqual(
            view["controller_loop_state_approval_mode"],
            "autonomous",
        )

    def test_view_soft_fails_on_missing_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "c"
            controller.mkdir()
            (controller / "AGENTS.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "CLAUDE.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / "TASK.md").write_text(
                "x", encoding="utf-8",
            )
            (controller / ".agent-loop").mkdir()
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                )
            )
        self.assertIsNone(view["current_loop_state_status"])
        self.assertIsNone(
            view["controller_loop_state_approval_mode"],
        )

    def test_every_action_refused_by_default(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                )
            )
        for action in view["actions"]:
            self.assertEqual(
                action["enablement_state"],
                "refused_until_policy_update",
                action["action_id"],
            )

    def test_fail_closed_default_survives_full_operator_inputs(
        self,
    ) -> None:
        # The headline Phase 10U guardrail: even with every
        # operator-side requirement satisfied (identity supplied,
        # per-action acknowledgement, dry-run reviewed, policy
        # pack permits), the contract-only slice keeps every
        # action `refused_until_policy_update` because the
        # runtime is not available and the audit log is not
        # canonical-mirror-appendable. A future runtime slice
        # flipping `phase_10u_runtime_available` to True must be
        # what unlocks dispatch; the operator inputs alone MUST
        # NOT bypass the boundary.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                    operator_inputs=_full_inputs(),
                )
            )
        for action in view["actions"]:
            self.assertEqual(
                action["enablement_state"],
                "refused_until_policy_update",
                action["action_id"],
            )

    def test_operator_inputs_mirror_in_view(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_action_ids": [
                            "github_post_pr_comment",
                        ],
                        "dry_run_reviewed_action_ids": [
                            "github_edit_pr_metadata",
                        ],
                        "policy_permitted_action_ids": [
                            "github_trigger_workflow",
                        ],
                    },
                )
            )
        op = view["operator_inputs"]
        self.assertEqual(op["identity"], "me")
        self.assertEqual(
            op["acknowledged_action_ids"],
            ["github_post_pr_comment"],
        )
        self.assertEqual(
            op["dry_run_reviewed_action_ids"],
            ["github_edit_pr_metadata"],
        )
        self.assertEqual(
            op["policy_permitted_action_ids"],
            ["github_trigger_workflow"],
        )

    def test_action_descriptor_carries_audit_entry_canonical_shape(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                )
            )
        for action in view["actions"]:
            shape = action["audit_entry_canonical_shape"]
            self.assertIsInstance(shape, dict)
            self.assertEqual(
                set(shape.keys()),
                set(action["audit_required_fields"]),
            )
            for value in shape.values():
                self.assertIsNone(value)


# ---------------------------------------------------------------------------
# render_desktop_mcp_action_guardrails_text
# ---------------------------------------------------------------------------
class RenderTextTests(unittest.TestCase):

    def _view(self) -> dict:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            return (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                )
            )

    def test_renders_signal_version_header(self) -> None:
        lines = (
            agent_loop.render_desktop_mcp_action_guardrails_text(
                self._view(),
            )
        )
        self.assertTrue(
            any("phase-10u-v1" in line for line in lines),
        )

    def test_renders_every_action_with_attribution_tags(
        self,
    ) -> None:
        view = self._view()
        lines = (
            agent_loop.render_desktop_mcp_action_guardrails_text(
                view,
            )
        )
        output = "\n".join(lines)
        # Every action surfaces as `[refused]` in this slice
        # (Phase 10U fail-closed default); `[mcp-action]` only
        # appears when the runtime ships and the operator inputs
        # promote the action to `enabled_pending_runtime`.
        for tag in (
            "[refused]",
            "[mcp-effect]",
            "[mcp-mutation]",
            "[mcp-policy]",
            "[mcp-approval]",
            "[mcp-enablement]",
            "[mcp-audit]",
            "[deferred-runtime]",
            "[canonical mirror]",
            "[advisory]",
        ):
            self.assertIn(tag, output, tag)
        # Every registry action id surfaced.
        for action in view["actions"]:
            self.assertIn(action["action_id"], output)

    def test_renders_operator_inputs_mirror_lines(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                    operator_inputs={
                        "identity": "me",
                        "acknowledged_action_ids": [
                            "github_post_pr_comment",
                        ],
                        "policy_permitted_action_ids": [
                            "github_post_pr_comment",
                        ],
                    },
                )
            )
        output = "\n".join(
            agent_loop.render_desktop_mcp_action_guardrails_text(
                view,
            )
        )
        self.assertIn("operator_inputs.identity", output)
        self.assertIn(
            "operator_inputs.acknowledged_action_ids", output,
        )
        self.assertIn(
            "operator_inputs.dry_run_reviewed_action_ids", output,
        )
        self.assertIn(
            "operator_inputs.policy_permitted_action_ids", output,
        )


# ---------------------------------------------------------------------------
# build_desktop_mcp_action_guardrails_controls
# ---------------------------------------------------------------------------
class BuildControlsTests(unittest.TestCase):

    def test_controls_one_per_action(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                )
            )
        controls = (
            agent_loop.build_desktop_mcp_action_guardrails_controls(
                view,
            )
        )
        self.assertEqual(len(controls), len(view["actions"]))
        for control in controls:
            self.assertIn("id", control)
            self.assertIn("label", control)
            self.assertIn("enabled", control)
            self.assertIn("dispatch_mode", control)
            self.assertEqual(
                control["dispatch_mode"], "copy_paste",
            )
            self.assertEqual(
                control["category"], "mutation_action_guardrail",
            )

    def test_every_control_disabled_in_this_slice(self) -> None:
        # Phase 10U ships the contract only; every control MUST
        # render as disabled regardless of operator input.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = (
                agent_loop.build_desktop_mcp_action_guardrails_view(
                    controller,
                    operator_inputs=_full_inputs(),
                )
            )
        controls = (
            agent_loop.build_desktop_mcp_action_guardrails_controls(
                view,
            )
        )
        for control in controls:
            self.assertFalse(control["enabled"], control["id"])


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------
class CmdHandlerTests(unittest.TestCase):

    def _make_args(self, **kwargs) -> argparse.Namespace:
        defaults = {
            "controller_root": None,
            "operator_identity": None,
            "acknowledge_action": None,
            "dry_run_reviewed_action": None,
            "policy_permit_action": None,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_refuses_missing_controller_root(self) -> None:
        args = self._make_args(controller_root=None)
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            rc = agent_loop.cmd_view_desktop_mcp_action_guardrails(
                args,
            )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())
        self.assertIn(
            "--controller-root is required", buf_err.getvalue(),
        )

    def test_refuses_missing_markers(self) -> None:
        with TemporaryDirectory() as td:
            controller = Path(td) / "no_markers"
            controller.mkdir()
            args = self._make_args(controller_root=str(controller))
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(
                buf_err,
            ):
                rc = (
                    agent_loop.cmd_view_desktop_mcp_action_guardrails(
                        args,
                    )
                )
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED", buf_err.getvalue())
        self.assertIn(
            "missing required markers", buf_err.getvalue(),
        )

    def test_phase_7c_reporter_pattern_exits_zero(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = self._make_args(controller_root=str(controller))
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(
                buf_err,
            ):
                rc = (
                    agent_loop.cmd_view_desktop_mcp_action_guardrails(
                        args,
                    )
                )
        self.assertEqual(rc, 0)
        self.assertIn(
            "[desktop-mcp-action-guardrails]", buf_out.getvalue(),
        )

    def test_operator_input_flags_thread_through(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = self._make_args(
                controller_root=str(controller),
                operator_identity="me",
                acknowledge_action=["github_post_pr_comment"],
                dry_run_reviewed_action=[
                    "github_post_pr_comment",
                ],
                policy_permit_action=["github_post_pr_comment"],
            )
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            with redirect_stdout(buf_out), redirect_stderr(
                buf_err,
            ):
                rc = (
                    agent_loop.cmd_view_desktop_mcp_action_guardrails(
                        args,
                    )
                )
        self.assertEqual(rc, 0)
        # Even with the operator inputs supplied the action stays
        # refused (Phase 10U fail-closed default) because the
        # runtime is unavailable; the operator_inputs mirror line
        # MUST still surface the supplied values so a reviewer can
        # see exactly which inputs flowed in.
        output = buf_out.getvalue()
        self.assertIn("operator_inputs.identity", output)
        self.assertIn("'me'", output)
        self.assertIn(
            "['github_post_pr_comment']", output,
        )
        self.assertIn(
            "refused_until_policy_update", output,
        )

    def test_handler_registered(self) -> None:
        self.assertIn(
            "view-desktop-mcp-action-guardrails",
            agent_loop.HANDLERS,
        )
        self.assertIs(
            agent_loop.HANDLERS[
                "view-desktop-mcp-action-guardrails"
            ],
            agent_loop.cmd_view_desktop_mcp_action_guardrails,
        )

    def test_parser_accepts_subcommand(self) -> None:
        parser = agent_loop.build_parser()
        args = parser.parse_args([
            "view-desktop-mcp-action-guardrails",
            "--controller-root", ".",
            "--operator-identity", "me",
            "--acknowledge-action", "github_post_pr_comment",
            "--dry-run-reviewed-action", "github_post_pr_comment",
            "--policy-permit-action", "github_post_pr_comment",
        ])
        self.assertEqual(
            args.cmd, "view-desktop-mcp-action-guardrails",
        )
        self.assertEqual(args.operator_identity, "me")
        self.assertEqual(
            args.acknowledge_action, ["github_post_pr_comment"],
        )
        self.assertEqual(
            args.dry_run_reviewed_action,
            ["github_post_pr_comment"],
        )
        self.assertEqual(
            args.policy_permit_action,
            ["github_post_pr_comment"],
        )


# ---------------------------------------------------------------------------
# Integration: assemble_desktop_app_view + render_desktop_app_text
# ---------------------------------------------------------------------------
class DesktopAppIntegrationTests(unittest.TestCase):

    def test_assemble_includes_mcp_action_guardrails_view_key(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
        self.assertIn("mcp_action_guardrails_view", view)
        sub = view["mcp_action_guardrails_view"]
        self.assertIsInstance(sub, dict)
        self.assertEqual(
            sub["view_signal_version"], "phase-10u-v1",
        )

    def test_assemble_delegates_to_build_view(self) -> None:
        sentinel = {
            "view_signal_version": "phase-10u-v1",
            "controller_path_canonical": "/tmp/sentinel",
            "current_loop_state_status": None,
            "controller_loop_state_approval_mode": None,
            "phase_10t_runtime_available": True,
            "phase_10u_runtime_available": False,
            "operator_inputs": {
                "identity": "",
                "acknowledged_action_ids": [],
                "dry_run_reviewed_action_ids": [],
                "policy_permitted_action_ids": [],
            },
            "effect_classes": [],
            "mutation_scopes": [],
            "approval_policies": [],
            "enablement_states": [],
            "approval_requirements": [],
            "audit_required_fields": [],
            "refusal_reasons": [],
            "actions": [],
            "precedence_note": "sentinel-precedence",
        }
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(
                agent_loop,
                "build_desktop_mcp_action_guardrails_view",
                return_value=sentinel,
            ) as mocked:
                view = agent_loop.assemble_desktop_app_view(
                    controller,
                )
        mocked.assert_called_once_with(controller)
        self.assertIs(view["mcp_action_guardrails_view"], sentinel)

    def test_render_includes_phase_10u_label(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        self.assertIn(
            "=== MCP Action Guardrails (Phase 10U) ===", output,
        )
        self.assertIn("phase-10u-v1", output)

    def test_render_includes_phase_10u_attribution(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            view = agent_loop.assemble_desktop_app_view(controller)
            lines = agent_loop.render_desktop_app_text(view)
        output = "\n".join(lines)
        # Phase 10U attribution tags: every action surfaces as
        # `[refused]` in the assemble-default path (the
        # assemble_desktop_app_view does not thread operator
        # inputs), and `[mcp-audit]` surfaces the closed audit-
        # entry envelope per action.
        self.assertIn("[refused]", output)
        self.assertIn("[mcp-audit]", output)
        self.assertIn("[mcp-effect]", output)
        self.assertIn("[mcp-mutation]", output)


# ---------------------------------------------------------------------------
# Non-mutation invariants
# ---------------------------------------------------------------------------
class NonMutationInvariantsTests(unittest.TestCase):

    def test_render_does_not_open_socket(self) -> None:
        # The Phase 10U surface MUST NEVER open a network socket
        # (read-side or write-side) during a render.
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                controller_root=str(controller),
                operator_identity=None,
                acknowledge_action=None,
                dry_run_reviewed_action=None,
                policy_permit_action=None,
            )
            with mock.patch.object(
                socket, "socket",
            ) as patched_socket:
                buf_out = io.StringIO()
                with redirect_stdout(buf_out):
                    rc = (
                        agent_loop.cmd_view_desktop_mcp_action_guardrails(
                            args,
                        )
                    )
        self.assertEqual(rc, 0)
        patched_socket.assert_not_called()

    def test_render_does_not_spawn_subprocess(self) -> None:
        import subprocess
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            args = argparse.Namespace(
                controller_root=str(controller),
                operator_identity=None,
                acknowledge_action=None,
                dry_run_reviewed_action=None,
                policy_permit_action=None,
            )
            patches = [
                mock.patch.object(subprocess, "run"),
                mock.patch.object(subprocess, "Popen"),
                mock.patch.object(subprocess, "call"),
                mock.patch.object(subprocess, "check_call"),
                mock.patch.object(subprocess, "check_output"),
                mock.patch("os.system"),
            ]
            mocks = [p.start() for p in patches]
            try:
                buf_out = io.StringIO()
                with redirect_stdout(buf_out):
                    rc = (
                        agent_loop.cmd_view_desktop_mcp_action_guardrails(
                            args,
                        )
                    )
            finally:
                for p in patches:
                    p.stop()
        self.assertEqual(rc, 0)
        for m in mocks:
            m.assert_not_called()

    def test_render_does_not_invoke_halt(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            with mock.patch.object(agent_loop, "_halt") as halt:
                view = (
                    agent_loop.build_desktop_mcp_action_guardrails_view(
                        controller,
                    )
                )
        self.assertEqual(view["view_signal_version"], "phase-10u-v1")
        halt.assert_not_called()

    def test_render_does_not_mutate_loop_state(self) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            ls_path = (
                controller / ".agent-loop" / "loop-state.json"
            )
            before = ls_path.read_bytes()
            agent_loop.build_desktop_mcp_action_guardrails_view(
                controller,
            )
            after = ls_path.read_bytes()
        self.assertEqual(before, after)

    def test_render_does_not_append_to_orchestrator_log(
        self,
    ) -> None:
        with TemporaryDirectory() as td:
            controller = _make_controller(Path(td) / "c")
            log_path = (
                controller / ".agent-loop" / "orchestrator.log"
            )
            agent_loop.build_desktop_mcp_action_guardrails_view(
                controller,
            )
        self.assertFalse(log_path.exists())

    def test_does_not_widen_phase_10i_library_callable_cap(
        self,
    ) -> None:
        # The Phase 10I three-control library-callable cap MUST be
        # preserved exactly; Phase 10U introduces ZERO new
        # library-callable controls.
        library_call_ids = {
            spec["id"]
            for spec in agent_loop._EXTERNAL_UI_CONTROL_REGISTRY
            if spec["dispatch_mode"] == "library_call"
        }
        self.assertEqual(
            library_call_ids,
            {
                "view-external-status",
                "view-external-controls",
                "inspect-external-target",
            },
            "Phase 10U MUST NOT widen the Phase 10I library-"
            "callable control surface beyond the three shipped "
            "controls",
        )


if __name__ == "__main__":
    unittest.main()
