"""Focused tests for the Phase 4B planner slice in `scripts/agent_loop.py`.

Scope:
- Each major refusal path defined by the Phase 4A Planning Contract
  (unresolved NEEDS_FIXES, FAILED_REQUIRES_HUMAN, halted_* status,
  orchestrator-in-flight status, stale evidence, unreadable evidence,
  prior-approved proposal, threshold-halt-on-NEEDS_FIXES).
- The valid proposal-generation path on a fresh-start state.
- The contract-side proposal validator (label collision, blocking
  dependency, vague Definition-of-done bullet, too-many-files,
  self-approval-token guard).
- A write-boundary smoke check that the planner never creates any file
  outside the Phase 4A "Files the planner is allowed to write" set.

These tests build a minimal synthetic repository tree per case (no
network, no real subprocess); the planner is invoked through its
module-level functions, not the CLI binary, so failures point at the
specific function rather than at argparse.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import agent_loop  # noqa: E402 - sys.path is set above


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ascii_payload(state: str, captured_at: str) -> str:
    return (
        "command: stub\n"
        f"state: {state}\n"
        f"captured_at: {captured_at}\n"
        "----\n"
        "(synthetic test payload)\n"
    )


class _Repo:
    """Builder for a synthetic .agent-loop repo tree.

    Use `.with_state(...)` to override loop-state.json fields and
    `.with_evidence_age(...)` to control evidence freshness relative to
    the summary / review mtimes.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / ".agent-loop").mkdir(parents=True, exist_ok=True)

        # Repo-root markers required by find_repo_root.
        (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        (root / "TASK.md").write_text(
            "# TASK\n## Active Phase\nPhase 4 - Phase Planning Automation\n",
            encoding="utf-8",
        )
        (root / "ROADMAP.md").write_text("# ROADMAP\n", encoding="utf-8")
        (root / "README.md").write_text("# README\n", encoding="utf-8")
        (root / "CLAUDE.md").write_text("# CLAUDE\n", encoding="utf-8")

        self.state = {
            "phase": "Phase 4 - Phase Planning Automation",
            "sub_phase": "Phase 4B - Planner Initial Slice",
            "task": "Implement planner proposal generation.",
            "status": "awaiting_claude_implementation",
            "cycle_count": 0,
            "max_cycles": 3,
            "last_verdict": None,
            "last_verdict_phase": None,
            "contract_version": "phase-3a-v2",
            "claude_version": "claude-opus-4-7",
            "codex_version": None,
            "orchestrator_version": "phase-3d-v0",
        }
        self._write_state()
        self._write_phase_plan(
            closed_subphases=(
                "Phase 3E - End-to-End MVP Verification",
                "Phase 4A - Planning Contract",
            ),
            active_subphase="Phase 4B - Planner Initial Slice (Proposal Generation)",
        )
        self.summary_path = root / ".agent-loop" / "claude-summary.md"
        self.review_path = root / ".agent-loop" / "codex-review.md"
        self.summary_path.write_text("# Claude Implementation Summary\n", encoding="utf-8")
        self.review_path.write_text("# Codex Review\n", encoding="utf-8")
        self.with_evidence_age(seconds_after_summary=60)

    def _write_state(self) -> None:
        (self.root / ".agent-loop" / "loop-state.json").write_text(
            json.dumps(self.state, indent=2) + "\n", encoding="utf-8",
        )

    def _write_phase_plan(self, closed_subphases, active_subphase: str) -> None:
        parts = ["# Phase Plan", "", "## Active Phase", "", active_subphase, ""]
        for label in closed_subphases:
            parts.extend([
                f"## {label}",
                "",
                "### Status",
                "",
                "Complete. Reviewed and approved for human review.",
                "",
            ])
        parts.extend([
            f"## {active_subphase}",
            "",
            "### Status",
            "",
            "Active. Implementation in flight.",
            "",
        ])
        (self.root / ".agent-loop" / "phase-plan.md").write_text(
            "\n".join(parts), encoding="utf-8",
        )

    def with_state(self, **overrides) -> "_Repo":
        self.state.update(overrides)
        self._write_state()
        return self

    def with_evidence_age(
        self, seconds_after_summary: int = 60,
        missing_captured_at_for: tuple = (),
    ) -> "_Repo":
        """Write the six evidence files with `captured_at` set relative to
        the summary mtime. Positive `seconds_after_summary` makes the
        evidence newer than the summary (fresh); negative makes it older
        (stale). Files in `missing_captured_at_for` are written without a
        `captured_at:` line so the planner's unreadable-evidence path
        triggers.
        """
        summary_mtime = self.summary_path.stat().st_mtime
        cap_epoch = summary_mtime + seconds_after_summary
        cap_iso = _iso(datetime.fromtimestamp(cap_epoch, tz=timezone.utc))
        for rel in agent_loop.EVIDENCE_FILES:
            p = self.root / rel
            if rel in missing_captured_at_for:
                p.write_text(
                    "command: stub\nstate: Not run\n----\n(no captured_at)\n",
                    encoding="utf-8",
                )
            else:
                p.write_text(_ascii_payload("Not run", cap_iso), encoding="utf-8")
        return self

    def with_existing_proposal(self, body: str) -> "_Repo":
        (self.root / ".agent-loop" / "proposed-phase.md").write_text(
            body, encoding="utf-8",
        )
        return self


class _RepoTestCase(unittest.TestCase):
    """Sets up a per-test TemporaryDirectory and a fresh `_Repo`."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = _Repo(Path(self._tmp.name))

    def assertNoProposal(self) -> None:
        self.assertFalse(
            (self.repo.root / agent_loop.PROPOSAL_PATH_REL).exists(),
            "planner must not write proposed-phase.md on refusal",
        )

    def assertProposalWritten(self) -> Path:
        p = self.repo.root / agent_loop.PROPOSAL_PATH_REL
        self.assertTrue(p.exists(), "planner did not write proposed-phase.md")
        return p


# --- refusal paths ---

class RefusalPathsTests(_RepoTestCase):

    def test_refuses_when_last_verdict_needs_fixes(self) -> None:
        self.repo.with_state(last_verdict="NEEDS_FIXES")
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertNoProposal()

    def test_refuses_when_failed_requires_human(self) -> None:
        self.repo.with_state(last_verdict="FAILED_REQUIRES_HUMAN")
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertNoProposal()

    def test_refuses_when_halted_status(self) -> None:
        self.repo.with_state(status="halted_max_cycles_reached")
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertNoProposal()

    def test_refuses_when_orchestrator_in_flight(self) -> None:
        for in_flight in agent_loop.ORCHESTRATOR_IN_FLIGHT_STATUSES:
            with self.subTest(status=in_flight):
                self.repo.with_state(status=in_flight)
                rc = agent_loop.run_planner(self.repo.root)
                self.assertEqual(rc, 2)
                self.assertNoProposal()

    def test_refuses_when_threshold_halt_on_needs_fixes(self) -> None:
        self.repo.with_state(
            cycle_count=3, max_cycles=3, last_verdict="NEEDS_FIXES",
        )
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertNoProposal()

    def test_refuses_when_evidence_is_stale(self) -> None:
        self.repo.with_evidence_age(seconds_after_summary=-300)
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertNoProposal()

    def test_refuses_when_evidence_captured_at_missing(self) -> None:
        self.repo.with_evidence_age(
            seconds_after_summary=60,
            missing_captured_at_for=(".agent-loop/test-output.log",),
        )
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertNoProposal()

    def test_refuses_when_prior_proposal_carries_approval_token(self) -> None:
        self.repo.with_existing_proposal(
            "# Proposed Phase\n\n## Approval\n\nAPPROVED_FOR_ACTIVATION\n"
        )
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        # Prior proposal must NOT be overwritten by refusal.
        self.assertIn(
            "APPROVED_FOR_ACTIVATION",
            (self.repo.root / agent_loop.PROPOSAL_PATH_REL).read_text(encoding="utf-8"),
        )

    def test_refuses_when_loop_state_missing(self) -> None:
        (self.repo.root / ".agent-loop" / "loop-state.json").unlink()
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertNoProposal()

    def test_refuses_when_loop_state_malformed_json(self) -> None:
        (self.repo.root / ".agent-loop" / "loop-state.json").write_text(
            "{not: valid json", encoding="utf-8",
        )
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 2)
        self.assertNoProposal()


# --- success path ---

class GenerationSuccessTests(_RepoTestCase):

    def test_generates_valid_proposal_on_fresh_start(self) -> None:
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 0)
        proposal_path = self.assertProposalWritten()
        text = proposal_path.read_text(encoding="utf-8")

        # Title and every required section header present, in order.
        self.assertTrue(text.startswith(agent_loop.PROPOSAL_TITLE))
        cursor = 0
        for header in agent_loop.PROPOSAL_REQUIRED_SECTIONS:
            idx = text.find(header, cursor)
            self.assertNotEqual(idx, -1, f"missing {header!r}")
            cursor = idx + len(header)

        # The self-approval guard: a planner-authored proposal must NEVER
        # contain the activation token.
        self.assertNotIn(agent_loop.APPROVAL_TOKEN, text)

        # The contract validator must pass against the generated text.
        self.assertIsNone(agent_loop.validate_proposal_structure(text))

    def test_proposed_label_does_not_collide_with_active_sub_phase(self) -> None:
        agent_loop.run_planner(self.repo.root)
        text = (self.repo.root / agent_loop.PROPOSAL_PATH_REL).read_text(encoding="utf-8")
        # The active sub-phase is Phase 4B; the next-letter bump must
        # land on Phase 4C, not collide back onto Phase 4B.
        self.assertNotIn("## Label\n\nPhase 4B", text)
        self.assertIn("Phase 4C", text)

    def test_planner_log_contains_outcome_line(self) -> None:
        agent_loop.run_planner(self.repo.root)
        log_path = self.repo.root / agent_loop.PLANNER_LOG_PATH_REL
        self.assertTrue(log_path.exists())
        text = log_path.read_text(encoding="utf-8")
        self.assertIn("proposal written", text)
        self.assertIn(agent_loop.PLANNER_VERSION, text)


# --- proposal-content validator tests ---

class ProposalValidatorTests(unittest.TestCase):

    def _baseline_inputs(self) -> agent_loop.PlannerInputs:
        return agent_loop.PlannerInputs(
            repo_root=Path("."),
            loop_state={"sub_phase": "Phase 4B - X", "phase": "Phase 4 - X"},
            summary_mtime=None,
            review_mtime=None,
            evidence_captured_ats={},
            evidence_missing=[],
            phase_plan_text="",
            existing_labels={"Phase 4B - X"},
            closed_labels=["Phase 4A - Planning Contract"],
            task_md_text="",
            roadmap_md_text="",
            proposed_phase_existing=None,
        )

    def _baseline_draft(self) -> agent_loop.ProposalDraft:
        return agent_loop.ProposalDraft(
            label="Phase 4C - Test slice",
            objective="Implement a small slice.",
            definition_of_done=[
                "scripts/agent_loop.py exposes a new CLI subcommand with exit code 0 on success"
            ],
            exclusions=["no Git automation"],
            files_likely_involved=["scripts/agent_loop.py"],
            required_contract_changes="None",
            cycle_size_estimate=2,
            cycle_size_justification=None,
            dependencies=[("Phase 4A - Planning Contract", "complete-approved")],
            risk_areas=["this is a test stub"],
        )

    def test_baseline_draft_passes(self) -> None:
        self.assertIsNone(
            agent_loop.validate_proposal_against_contract(
                self._baseline_draft(), self._baseline_inputs(),
            )
        )

    def test_refuses_label_collision(self) -> None:
        draft = self._baseline_draft()
        draft.label = "Phase 4B - collides"
        problem = agent_loop.validate_proposal_against_contract(
            draft, self._baseline_inputs(),
        )
        self.assertIsNotNone(problem)
        self.assertIn("collides", problem)

    def test_refuses_blocking_dependency_status(self) -> None:
        draft = self._baseline_draft()
        draft.dependencies = [("Phase 4B - X", "active-in-flight")]
        problem = agent_loop.validate_proposal_against_contract(
            draft, self._baseline_inputs(),
        )
        self.assertIsNotNone(problem)
        self.assertIn("active-in-flight", problem)

    def test_refuses_unknown_dependency_status(self) -> None:
        draft = self._baseline_draft()
        draft.dependencies = [("Phase 4A - Planning Contract", "totally-made-up")]
        problem = agent_loop.validate_proposal_against_contract(
            draft, self._baseline_inputs(),
        )
        self.assertIsNotNone(problem)
        self.assertIn("totally-made-up", problem)

    def test_refuses_when_too_many_files(self) -> None:
        draft = self._baseline_draft()
        draft.files_likely_involved = [f"file_{i}.md" for i in range(11)]
        problem = agent_loop.validate_proposal_against_contract(
            draft, self._baseline_inputs(),
        )
        self.assertIsNotNone(problem)
        self.assertIn("> 10", problem)

    def test_refuses_when_no_testable_dod_bullet(self) -> None:
        draft = self._baseline_draft()
        draft.definition_of_done = ["the next phase produces excellent results"]
        problem = agent_loop.validate_proposal_against_contract(
            draft, self._baseline_inputs(),
        )
        self.assertIsNotNone(problem)
        self.assertIn("verifiable end state", problem)

    def test_refuses_when_dod_bullet_uses_vague_language(self) -> None:
        draft = self._baseline_draft()
        draft.definition_of_done = [
            "scripts/agent_loop.py exits 0 on the new subcommand",
            "improve overall code quality across the planner",
        ]
        problem = agent_loop.validate_proposal_against_contract(
            draft, self._baseline_inputs(),
        )
        self.assertIsNotNone(problem)
        self.assertIn("vague", problem)

    def test_refuses_oversized_cycle_estimate_without_justification(self) -> None:
        draft = self._baseline_draft()
        draft.cycle_size_estimate = 5
        draft.cycle_size_justification = None
        problem = agent_loop.validate_proposal_against_contract(
            draft, self._baseline_inputs(),
        )
        self.assertIsNotNone(problem)
        self.assertIn("Cycle-size", problem)

    def test_self_approval_token_is_refused(self) -> None:
        draft = self._baseline_draft()
        draft.objective = (
            "Implement the slice. APPROVED_FOR_ACTIVATION should never appear here."
        )
        problem = agent_loop.validate_proposal_against_contract(
            draft, self._baseline_inputs(),
        )
        self.assertIsNotNone(problem)
        self.assertIn(agent_loop.APPROVAL_TOKEN, problem)


# --- write-boundary smoke test ---

class WriteBoundaryTests(_RepoTestCase):

    def test_planner_writes_only_proposal_and_log(self) -> None:
        before = set(_walk(self.repo.root))
        rc = agent_loop.run_planner(self.repo.root)
        self.assertEqual(rc, 0)
        after = set(_walk(self.repo.root))
        new = sorted(after - before)
        allowed = {
            str(self.repo.root / agent_loop.PROPOSAL_PATH_REL),
            str(self.repo.root / agent_loop.PLANNER_LOG_PATH_REL),
        }
        unexpected = [p for p in new if p not in allowed]
        self.assertEqual(unexpected, [], f"planner wrote outside its allowed set: {unexpected}")


def _walk(root: Path):
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            yield str(Path(dirpath) / name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
