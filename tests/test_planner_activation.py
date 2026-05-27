"""Focused tests for the Phase 4C activator in `scripts/agent_loop.py`.

Scope:
- Approval-signal parsing: exact-literal-token enforcement (`## Approval`
  section, `APPROVED_FOR_ACTIVATION` on its own line, label-match
  against `## Label`).
- Refusal paths the Phase 4A contract names: missing `## Approval`
  section, malformed token (alternate capitalization, extra words on
  the line), label mismatch, missing `.agent-loop/proposed-phase.md`,
  missing or malformed `.agent-loop/loop-state.json`, empty
  required-proposal-section bodies, unparseable label.
- Activation success path: TASK.md / current-task.md / current-phase.md
  / phase-plan.md / loop-state.json all rewritten per the Phase 4A
  contract; planner.log records the approval source.
- Write-boundary discipline: the activator never writes any file
  outside the Phase 4A activation-allowed set.
- Specific contract invariants: `## Human Objective` and
  `## Project Intent` preserved verbatim in TASK.md;
  `.agent-loop/phase-plan.md` historical sub-phase BODIES (Objective /
  Definition of done / Exclusions) are not rewritten; `loop-state.json`
  reset preserves `max_cycles` / `contract_version` / runtime version
  fields.

Tests build a minimal synthetic repository per case via
`TemporaryDirectory`; the activator is invoked through
`agent_loop.run_activation` so failures point at the specific function
rather than at argparse.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


CONCRETE_PROPOSAL_BODY = """\
# Proposed Phase

## Label

Phase 4D - Planner-Orchestrator Integration

## Objective

Add the planner-orchestrator integration the Phase 4A contract anticipates: scripts/agent_loop.py invokes run_planner from inside the orchestrator's post-approval handoff so that .agent-loop/proposed-phase.md is refreshed before the human is asked to advance to the next sub-phase. The integration never auto-activates the planner's proposal; activation remains a separate human-approved step.

## Definition of done

- scripts/agent_loop.py wires the planner into the orchestrator's post-approval path so .agent-loop/proposed-phase.md is refreshed once per APPROVED_FOR_HUMAN_REVIEW verdict
- the integration writes a single note: line to .agent-loop/orchestrator.log per planner invocation, never two
- tests/test_planner_integration.py covers a successful integration call, a planner-refusal path that the orchestrator surfaces without halting, and a verification that no activation files are written by the integration call
- README.md is updated so the Current Status section names Phase 4D as active and describes the post-approval planner refresh

## Exclusions

- no Phase 4E optional planner adapter (deferred)
- no Phase 5 approval-mode behavior
- no Phase 6 optional context and tool layer
- no Phase 7 editor / VS Code integration
- no Phase 8 documentation polish
- no MCP support
- no Git automation
- no auto-activation of planner-authored proposals under any verdict

## Files likely involved

- scripts/agent_loop.py
- tests/test_planner_integration.py
- .agent-loop/proposed-phase.md
- .agent-loop/planner.log
- .agent-loop/orchestrator.log
- README.md

## Required contract changes

None

## Cycle-size estimate

2

## Dependencies

- Phase 4A - Planning Contract: complete-approved
- Phase 4B - Planner Initial Slice: complete-approved

## Risk areas

- the integration must not block the orchestrator return path: a planner refusal must be logged and ignored for control-flow purposes
- the planner runs after the verdict is persisted, so a planner failure can never reverse the verdict
- auto-invocation increases planner.log noise; the integration must log exactly one note: line per invocation
"""


def _proposal_with_approval(approval_body: str = "") -> str:
    """Return the concrete proposal body plus an optional `## Approval`
    section appended after `## Risk areas`. When approval_body is empty,
    no `## Approval` section is added.
    """
    if not approval_body:
        return CONCRETE_PROPOSAL_BODY
    return CONCRETE_PROPOSAL_BODY.rstrip() + "\n\n## Approval\n\n" + approval_body.strip() + "\n"


VALID_APPROVAL_BODY = (
    "Approving: Phase 4D - Planner-Orchestrator Integration\n\n"
    "APPROVED_FOR_ACTIVATION\n"
)


class _ActivationRepo:
    """Builder for a synthetic repository configured for activation tests.

    The repo contains a complete TASK.md (with `## Human Objective` and
    `## Project Intent` sections that the activator must preserve
    verbatim), a phase-plan.md whose `## Active Phase` line and active
    sub-phase `### Status` paragraph mark Phase 4C as currently active,
    a loop-state.json carrying realistic runtime fields, and (by
    default) the concrete Phase 4D proposal at .agent-loop/proposed-
    phase.md with no `## Approval` section yet.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / ".agent-loop").mkdir(parents=True, exist_ok=True)
        # Repo-root markers required by find_repo_root.
        (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        (root / "CLAUDE.md").write_text("# CLAUDE\n", encoding="utf-8")
        (root / "README.md").write_text("# README\n", encoding="utf-8")
        # ROADMAP.md must contain the parent phase heading the activator
        # looks up to resolve `## Active Phase` body text.
        (root / "ROADMAP.md").write_text(
            "# ROADMAP\n\n## Phase 4 - Phase Planning Automation\n\n"
            "Sub-phased planning automation work.\n",
            encoding="utf-8",
        )
        self.human_objective_marker = "HUMAN_OBJECTIVE_VERBATIM_MARKER_DO_NOT_TOUCH"
        self.project_intent_marker = "PROJECT_INTENT_VERBATIM_MARKER_DO_NOT_TOUCH"
        (root / "TASK.md").write_text(
            self._initial_task_md(), encoding="utf-8",
        )
        (root / ".agent-loop" / "current-task.md").write_text(
            "# Current Task\n\nPhase 4C in progress.\n", encoding="utf-8",
        )
        (root / ".agent-loop" / "current-phase.md").write_text(
            "# Current Phase\n\nPhase 4 - Phase Planning Automation "
            "(sub-phase: Phase 4C - Planner Activation Writes)\n",
            encoding="utf-8",
        )
        self.initial_loop_state = {
            "phase": "Phase 4 - Phase Planning Automation",
            "sub_phase": "Phase 4C - Planner Activation Writes",
            "task": "Implement the activation step.",
            "status": "awaiting_claude_implementation",
            "cycle_count": 0,
            "max_cycles": 5,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": "phase-3a-v2",
            "claude_version": "claude-opus-4-7",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
        }
        (root / ".agent-loop" / "loop-state.json").write_text(
            json.dumps(self.initial_loop_state, indent=2) + "\n",
            encoding="utf-8",
        )
        (root / ".agent-loop" / "phase-plan.md").write_text(
            self._initial_phase_plan(), encoding="utf-8",
        )
        # Default proposal: the concrete Phase 4D proposal without an
        # `## Approval` section. Individual tests override via
        # `with_proposal(...)`.
        (root / ".agent-loop" / "proposed-phase.md").write_text(
            CONCRETE_PROPOSAL_BODY, encoding="utf-8",
        )

    def _initial_task_md(self) -> str:
        return (
            "# TASK.md\n\n"
            "## Human Objective\n\n"
            f"{self.human_objective_marker}\n\n"
            "## Project Intent\n\n"
            f"{self.project_intent_marker}\n\n"
            "## Active Phase\n\n"
            "Phase 4 - Phase Planning Automation\n\n"
            "## Active Sub-Phase\n\n"
            "Phase 4C - Planner Activation Writes\n\n"
            "## Phase Status\n\n"
            "Phase 4C in flight.\n\n"
            "## Active Task\n\n"
            "Implement the activation step.\n\n"
            "## Phase Outcome Required Now\n\n"
            "- activator works end-to-end\n\n"
            "## Next-Phase Gate\n\n"
            "Do not start the next sub-phase until approved.\n\n"
            "## Out Of Scope For Current Phase\n\n"
            "- planner-orchestrator auto-integration\n"
        )

    def _initial_phase_plan(self) -> str:
        return (
            "# Phase Plan\n\n"
            "## Active Phase\n\n"
            "Phase 4 - Phase Planning Automation (sub-phase: "
            "Phase 4C - Planner Activation Writes)\n\n"
            "## Phase 4A - Planning Contract\n\n"
            "### Status\n\n"
            "Complete. Approved for human review.\n\n"
            "### Objective\n\n"
            "Original Phase 4A objective body that must NOT be rewritten on activation.\n\n"
            "## Phase 4B - Planner Initial Slice (Proposal Generation)\n\n"
            "### Status\n\n"
            "Complete. Approved for human review.\n\n"
            "### Objective\n\n"
            "Original Phase 4B objective body that must NOT be rewritten on activation.\n\n"
            "## Phase 4C - Planner Activation Writes\n\n"
            "### Status\n\n"
            "Active. Phase 4C activation-step implementation in flight.\n\n"
            "### Objective\n\n"
            "Original Phase 4C objective body that must NOT be rewritten on activation.\n"
        )

    def with_proposal(self, body: str) -> "_ActivationRepo":
        (self.root / ".agent-loop" / "proposed-phase.md").write_text(
            body, encoding="utf-8",
        )
        return self


class _ActivationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = _ActivationRepo(Path(self._tmp.name))

    def _read(self, rel: str) -> str:
        return (self.repo.root / rel).read_text(encoding="utf-8")

    def _read_loop_state(self) -> dict:
        return json.loads(self._read(".agent-loop/loop-state.json"))

    def assertActivationRefused(self, code_substring: str) -> None:
        log_path = self.repo.root / agent_loop.PLANNER_LOG_PATH_REL
        self.assertTrue(log_path.exists(), "planner.log must exist after refusal")
        text = log_path.read_text(encoding="utf-8")
        self.assertIn("activation refused", text)
        self.assertIn(code_substring, text)
        self.assertIn(" note: ", text)


# --- approval-signal refusal paths ---

class ApprovalRefusalTests(_ActivationTestCase):

    def test_refuses_when_proposed_phase_md_missing(self) -> None:
        (self.repo.root / agent_loop.PROPOSAL_PATH_REL).unlink()
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("no_proposal")

    def test_refuses_when_no_approval_section(self) -> None:
        # _ActivationRepo's default proposal has no `## Approval` section.
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("no_approval_section")

    def test_refuses_when_approval_body_empty(self) -> None:
        # Header present, body empty -> still "no_approval_section" per the
        # contract (an empty `## Approval` is no approval at all).
        self.repo.with_proposal(_proposal_with_approval("\n"))
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("no_approval_section")

    def test_refuses_when_token_uses_wrong_case(self) -> None:
        self.repo.with_proposal(_proposal_with_approval(
            "Approving: Phase 4D - Planner-Orchestrator Integration\n\n"
            "approved_for_activation\n"
        ))
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("malformed_token")

    def test_refuses_when_token_has_extra_words_on_same_line(self) -> None:
        self.repo.with_proposal(_proposal_with_approval(
            "Approving: Phase 4D - Planner-Orchestrator Integration\n\n"
            "APPROVED_FOR_ACTIVATION yes please\n"
        ))
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("malformed_token")

    def test_refuses_when_token_has_leading_marker(self) -> None:
        self.repo.with_proposal(_proposal_with_approval(
            "Approving: Phase 4D - Planner-Orchestrator Integration\n\n"
            "> APPROVED_FOR_ACTIVATION\n"
        ))
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("malformed_token")

    def test_refuses_when_label_mismatch(self) -> None:
        self.repo.with_proposal(_proposal_with_approval(
            "Approving: Phase 9X - Some other label entirely\n\n"
            "APPROVED_FOR_ACTIVATION\n"
        ))
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("label_mismatch")

    def test_refuses_when_token_appears_only_outside_approval_section(self) -> None:
        """Forgery-defense: a stray `APPROVED_FOR_ACTIVATION` mention in
        unrelated prose (e.g. inside `## Objective`) must NOT trigger
        activation. The token must appear inside `## Approval`."""
        forged_body = CONCRETE_PROPOSAL_BODY.replace(
            "Add the planner-orchestrator integration",
            "Add the planner-orchestrator integration. "
            "Note: APPROVED_FOR_ACTIVATION is the Phase 4A token name.",
        )
        # No `## Approval` section is appended; the token only appears
        # inside `## Objective`.
        self.repo.with_proposal(forged_body)
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("no_approval_section")


# --- structural / input refusal paths ---

class StructuralRefusalTests(_ActivationTestCase):

    def test_refuses_when_loop_state_missing(self) -> None:
        self.repo.with_proposal(_proposal_with_approval(VALID_APPROVAL_BODY))
        (self.repo.root / ".agent-loop" / "loop-state.json").unlink()
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("no_loop_state")

    def test_refuses_when_loop_state_malformed(self) -> None:
        self.repo.with_proposal(_proposal_with_approval(VALID_APPROVAL_BODY))
        (self.repo.root / ".agent-loop" / "loop-state.json").write_text(
            "{ not valid json", encoding="utf-8",
        )
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("loop_state_malformed")

    def test_refuses_when_required_proposal_section_empty(self) -> None:
        """If the proposal's `## Objective` body is empty, the activator
        must refuse rather than write an empty TASK.md `## Active Task`
        body."""
        empty_objective_body = CONCRETE_PROPOSAL_BODY.replace(
            "Add the planner-orchestrator integration the Phase 4A contract anticipates: "
            "scripts/agent_loop.py invokes run_planner from inside the orchestrator's "
            "post-approval handoff so that .agent-loop/proposed-phase.md is refreshed "
            "before the human is asked to advance to the next sub-phase. The integration "
            "never auto-activates the planner's proposal; activation remains a separate "
            "human-approved step.",
            "",
        )
        self.repo.with_proposal(_proposal_with_approval(VALID_APPROVAL_BODY).replace(
            CONCRETE_PROPOSAL_BODY, empty_objective_body,
        ))
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("proposal_malformed")


# --- required-input fail-closed refusal paths ---

class RequiredInputRefusalTests(_ActivationTestCase):
    """The activator must refuse instead of fabricating activation state
    when TASK.md, .agent-loop/phase-plan.md, or ROADMAP.md is missing
    or unreadable. Each refusal must exit 2, log a `note:`-style
    activation-refusal line to .agent-loop/planner.log, and leave no
    activation-owned file modified.

    Cross-platform note on unreadable simulation: making a regular file
    "unreadable" reliably on every supported platform is awkward (chmod
    000 is a POSIX-only convention; Windows ACL manipulation depends on
    the file system and the running user). The tests here cover the
    missing-file paths on every platform and one cross-platform
    OS-error simulation (replacing the file with a directory of the
    same name) so the unreadable code path is exercised without a
    permission API call.
    """

    def setUp(self) -> None:
        super().setUp()
        self.repo.with_proposal(_proposal_with_approval(VALID_APPROVAL_BODY))

    def _snapshot_activation_owned(self) -> dict:
        """Snapshot the on-disk bytes of every activation-owned file
        (plus planner.log, which gains a refusal entry but no
        activation rewrite). Tolerates paths that are not regular files
        (e.g. directories from the unreadable-simulation trick) by
        recording `None` for those entries so the helper does not raise
        during the unreadable-file refusal tests."""
        snap: dict = {}
        for rel in agent_loop.ACTIVATOR_ALLOWED_WRITE_FILES:
            p = self.repo.root / rel
            if p.is_file():
                snap[rel] = p.read_bytes()
            else:
                snap[rel] = None
        return snap

    def _assert_activation_owned_unchanged_except_log(
        self, before: dict, after: dict, *, ignore: tuple = (),
    ) -> None:
        ignore_set = set(ignore) | {agent_loop.PLANNER_LOG_PATH_REL}
        for rel in agent_loop.ACTIVATOR_ALLOWED_WRITE_FILES:
            if rel in ignore_set:
                # planner.log legitimately gains the refusal note; other
                # ignored entries are the file the test deliberately
                # mutated to simulate unreadability (the activator did
                # not touch it; the test did).
                continue
            self.assertEqual(
                before.get(rel), after.get(rel),
                f"activation-owned file {rel} was modified on a refusal path",
            )

    # --- missing-file refusals ---

    def test_refuses_when_task_md_missing(self) -> None:
        (self.repo.root / "TASK.md").unlink()
        before = self._snapshot_activation_owned()
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("task_md_missing")
        self._assert_activation_owned_unchanged_except_log(
            before, self._snapshot_activation_owned(),
        )

    def test_refuses_when_phase_plan_md_missing(self) -> None:
        (self.repo.root / ".agent-loop" / "phase-plan.md").unlink()
        before = self._snapshot_activation_owned()
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("phase_plan_missing")
        self._assert_activation_owned_unchanged_except_log(
            before, self._snapshot_activation_owned(),
        )

    def test_refuses_when_roadmap_md_missing(self) -> None:
        (self.repo.root / "ROADMAP.md").unlink()
        before = self._snapshot_activation_owned()
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused("roadmap_missing")
        self._assert_activation_owned_unchanged_except_log(
            before, self._snapshot_activation_owned(),
        )

    # --- unreadable simulation (cross-platform via "file replaced by a
    # directory of the same name", which causes `Path.read_text` to
    # raise an OSError subclass on every platform we target -
    # `IsADirectoryError` on POSIX, `PermissionError` on Windows; both
    # are caught by `_read_text_strict`'s `except OSError` block).

    def _swap_file_for_dir(self, path: Path) -> None:
        """Replace `path` (a regular file) with a directory of the same
        name. Registers an addCleanup that restores the original file
        bytes so the TemporaryDirectory teardown does not trip on
        Windows trying to delete a dir whose name conflicts with the
        original file's content snapshot."""
        original_bytes = path.read_bytes()
        path.unlink()
        path.mkdir()
        def restore() -> None:
            if path.is_dir():
                path.rmdir()
            if not path.exists():
                path.write_bytes(original_bytes)
        self.addCleanup(restore)

    def _run_unreadable_case(
        self, target_rel: str, expected_code: str,
    ) -> None:
        before = self._snapshot_activation_owned()
        self._swap_file_for_dir(self.repo.root / target_rel)
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertActivationRefused(expected_code)
        after = self._snapshot_activation_owned()
        # The activation-owned file we mutated will read None in the
        # after-snapshot because it is now a directory; ignore it in the
        # comparison (the test mutated it, not the activator).
        self._assert_activation_owned_unchanged_except_log(
            before, after, ignore=(target_rel,),
        )

    def test_refuses_when_task_md_unreadable(self) -> None:
        self._run_unreadable_case("TASK.md", "task_md_unreadable")

    def test_refuses_when_phase_plan_md_unreadable(self) -> None:
        self._run_unreadable_case(
            ".agent-loop/phase-plan.md", "phase_plan_unreadable",
        )

    def test_refuses_when_roadmap_md_unreadable(self) -> None:
        self._run_unreadable_case("ROADMAP.md", "roadmap_unreadable")


# --- activation success path ---

class ActivationSuccessTests(_ActivationTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.repo.with_proposal(_proposal_with_approval(VALID_APPROVAL_BODY))

    def test_exit_code_zero_on_success(self) -> None:
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 0)

    def test_task_md_active_phase_sections_rewritten(self) -> None:
        agent_loop.run_activation(self.repo.root)
        task_md = self._read("TASK.md")
        # The activator should rewrite Active Phase, Active Sub-Phase,
        # and the related sections from the activated proposal.
        self.assertIn(
            "## Active Sub-Phase\n\nPhase 4D - Planner-Orchestrator Integration",
            task_md,
        )
        self.assertIn(
            "## Active Phase\n\nPhase 4 - Phase Planning Automation",
            task_md,
        )
        # Active Task body now carries the proposal's Objective text.
        self.assertIn("Add the planner-orchestrator integration", task_md)

    def test_task_md_preserves_human_objective_and_project_intent_verbatim(self) -> None:
        agent_loop.run_activation(self.repo.root)
        task_md = self._read("TASK.md")
        # Human-owned sections must be preserved character-for-character.
        self.assertIn(self.repo.human_objective_marker, task_md)
        self.assertIn(self.repo.project_intent_marker, task_md)
        # The headers must remain.
        self.assertIn("## Human Objective", task_md)
        self.assertIn("## Project Intent", task_md)

    def test_current_task_md_rewritten_for_new_subphase(self) -> None:
        agent_loop.run_activation(self.repo.root)
        text = self._read(".agent-loop/current-task.md")
        self.assertIn("# Current Task", text)
        self.assertIn("Phase 4D - Planner-Orchestrator Integration", text)
        self.assertIn("agent_loop.py activate", text)

    def test_current_phase_md_rewritten_for_new_subphase(self) -> None:
        agent_loop.run_activation(self.repo.root)
        text = self._read(".agent-loop/current-phase.md")
        self.assertIn(
            "Phase 4 - Phase Planning Automation (sub-phase: "
            "Phase 4D - Planner-Orchestrator Integration)",
            text,
        )

    def test_loop_state_reset_per_contract(self) -> None:
        agent_loop.run_activation(self.repo.root)
        state = self._read_loop_state()
        # Reset fields set per contract.
        self.assertEqual(state["status"], "awaiting_claude_implementation")
        self.assertEqual(state["cycle_count"], 0)
        self.assertIsNone(state["last_verdict"])
        self.assertIsNone(state["last_verdict_phase"])
        # phase / sub_phase / task set from the approved proposal.
        self.assertEqual(state["phase"], "Phase 4 - Phase Planning Automation")
        self.assertEqual(
            state["sub_phase"], "Phase 4D - Planner-Orchestrator Integration",
        )
        self.assertIn("planner-orchestrator integration", state["task"])
        # Orchestrator-owned runtime fields preserved verbatim from the
        # pre-activation state.
        initial = self.repo.initial_loop_state
        for field in ("max_cycles", "contract_version", "claude_version",
                      "codex_version", "orchestrator_version"):
            self.assertEqual(
                state[field], initial[field],
                f"{field} must be preserved per the Phase 3A contract",
            )

    def test_phase_plan_active_phase_line_updated(self) -> None:
        agent_loop.run_activation(self.repo.root)
        text = self._read(".agent-loop/phase-plan.md")
        # The first non-empty line under `## Active Phase` must now name
        # the activated sub-phase.
        self.assertIn(
            "## Active Phase\n\nPhase 4 - Phase Planning Automation "
            "(sub-phase: Phase 4D - Planner-Orchestrator Integration)",
            text,
        )

    def test_phase_plan_appends_new_sub_phase_section(self) -> None:
        agent_loop.run_activation(self.repo.root)
        text = self._read(".agent-loop/phase-plan.md")
        self.assertIn("## Phase 4D - Planner-Orchestrator Integration", text)
        # The new section must carry its own `### Status` / `### Objective`
        # / `### Definition of done` / `### Exclusions` headers.
        # Find the new sub-phase section body.
        idx = text.find("## Phase 4D - Planner-Orchestrator Integration")
        appended = text[idx:]
        self.assertIn("### Status", appended)
        self.assertIn("### Objective", appended)
        self.assertIn("### Definition of done", appended)
        self.assertIn("### Exclusions", appended)
        self.assertIn(
            "Active. Activated by `python scripts/agent_loop.py activate`",
            appended,
        )

    def test_phase_plan_historical_bodies_not_rewritten(self) -> None:
        """The substantive `### Objective` body of every previously-
        recorded sub-phase MUST be preserved verbatim. The activator
        flips the previously-active sub-phase's `### Status` opening
        line as a transition note, but it does NOT touch the body of
        any historical sub-phase section."""
        agent_loop.run_activation(self.repo.root)
        text = self._read(".agent-loop/phase-plan.md")
        for marker in (
            "Original Phase 4A objective body that must NOT be rewritten on activation.",
            "Original Phase 4B objective body that must NOT be rewritten on activation.",
            "Original Phase 4C objective body that must NOT be rewritten on activation.",
        ):
            self.assertIn(marker, text, f"historical body missing: {marker!r}")

    def test_phase_plan_prior_active_status_marked_complete(self) -> None:
        """Transition-marking edit: the previously-active sub-phase's
        `### Status` opening line must flip from `Active. ...` to
        `Complete. Closed by activation of ...`."""
        agent_loop.run_activation(self.repo.root)
        text = self._read(".agent-loop/phase-plan.md")
        # The previously-active Phase 4C status line must now read "Complete."
        idx = text.find("## Phase 4C - Planner Activation Writes")
        section = text[idx : idx + 400]
        self.assertIn("Complete. Closed by activation of", section)

    def test_planner_log_records_approval_source(self) -> None:
        agent_loop.run_activation(self.repo.root)
        log = self._read(agent_loop.PLANNER_LOG_PATH_REL)
        # The contract requires: file path, mtime, and the literal
        # approval line.
        self.assertIn(" note: ", log)
        self.assertIn(f"activated [{agent_loop.ACTIVATOR_VERSION}]", log)
        self.assertIn(
            "Phase 4D - Planner-Orchestrator Integration", log,
        )
        self.assertIn("approval_source=", log)
        self.assertIn("approval_mtime=", log)
        self.assertIn(f"approval_line='{agent_loop.APPROVAL_TOKEN}'", log)


# --- write boundary ---

class ActivationWriteBoundaryTests(_ActivationTestCase):

    def setUp(self) -> None:
        super().setUp()
        self.repo.with_proposal(_proposal_with_approval(VALID_APPROVAL_BODY))

    def test_activate_writes_only_phase_4a_allowed_files(self) -> None:
        before = self._snapshot_files()
        rc = agent_loop.run_activation(self.repo.root)
        self.assertEqual(rc, 0)
        after = self._snapshot_files()
        # Sets of files BOTH modified (existing) and newly created.
        new_files = set(after) - set(before)
        modified_files = {
            p for p in (set(before) & set(after)) if before[p] != after[p]
        }
        touched = new_files | modified_files
        allowed_paths = {
            str(self.repo.root / rel)
            for rel in agent_loop.ACTIVATOR_ALLOWED_WRITE_FILES
        }
        unexpected = sorted(touched - allowed_paths)
        self.assertEqual(
            unexpected, [],
            f"activator wrote outside its allowed set: {unexpected}",
        )

    def test_activate_does_not_modify_proposed_phase_md(self) -> None:
        """The activator must NOT mutate the proposal it consumed. The
        proposal stays on disk as the audit trail; planner.log records
        the approval-source mtime that future tools can cross-check."""
        before = self._read(agent_loop.PROPOSAL_PATH_REL)
        agent_loop.run_activation(self.repo.root)
        after = self._read(agent_loop.PROPOSAL_PATH_REL)
        self.assertEqual(before, after)

    def _snapshot_files(self) -> dict:
        snapshot: dict = {}
        for dirpath, _dirs, files in os.walk(self.repo.root):
            for name in files:
                path = Path(dirpath) / name
                snapshot[str(path)] = path.read_bytes()
        return snapshot


# --- parser-only unit tests ---

class ApprovalParserUnitTests(unittest.TestCase):
    """Direct tests for `check_approval` so parser regressions surface
    without spinning up a synthetic repo for each case."""

    def _proposal(self, approval_body: str = "") -> str:
        return _proposal_with_approval(approval_body)

    def test_valid_approval_returns_approval_source(self) -> None:
        proposal_path = Path("dummy-path")
        # Use NamedTemporaryFile-ish: stat() is needed by check_approval
        # for mtime. Write to a temp file so the stat call succeeds.
        with TemporaryDirectory() as td:
            p = Path(td) / "proposed-phase.md"
            p.write_text(self._proposal(VALID_APPROVAL_BODY), encoding="utf-8")
            result = agent_loop.check_approval(p.read_text(encoding="utf-8"), p)
        self.assertIsInstance(result, agent_loop.ApprovalSource)
        self.assertEqual(
            result.label, "Phase 4D - Planner-Orchestrator Integration",
        )
        self.assertEqual(result.approval_line, agent_loop.APPROVAL_TOKEN)

    def test_no_label_body_refuses(self) -> None:
        text = (
            "# Proposed Phase\n\n## Label\n\n\n\n## Objective\n\nbody\n"
        )
        with TemporaryDirectory() as td:
            p = Path(td) / "proposed-phase.md"
            p.write_text(text, encoding="utf-8")
            result = agent_loop.check_approval(text, p)
        self.assertIsInstance(result, agent_loop.ActivationRefusal)
        self.assertEqual(result.code, "no_label")


if __name__ == "__main__":
    unittest.main(verbosity=2)
