# TASK.md

## Human Objective

Build the Agentic AI Coding Loop project from start to finish as a phase-gated local orchestration system where:

- Codex plans the work, updates task state, reviews implementation, and generates fix prompts
- Claude Code implements only the active phase
- the local orchestrator captures evidence and enforces loop state
- each phase stops for human approval before the next phase begins
- the system never auto-commits or auto-pushes

## Project Intent

The goal is to let a human provide the desired outcome once, then have the Codex and Claude loop carry the project forward phase by phase with review, fixes, and human gating between phases.

## Active Phase

Phase 3 - Scripted Orchestrator MVP

## Active Sub-Phase

Phase 3E - End-to-End MVP Verification

## Phase Status

Phase 3D (subprocess-driven Claude/Codex adapters) is complete and approved by the human to advance. Phase 3E is operational verification: actually execute `python scripts/agent_loop.py run` against the repository's real `.agent-loop/` workflow, observe what happens, fix any concrete operational bug the live run reveals, and document the residual risks honestly. Approval modes, Git automation, editor integration, and a package-layout refactor remain deferred.

## Active Task

Execute and harden the Phase 3E end-to-end MVP verification of `scripts/agent_loop.py`. Run at least one real bounded orchestrator cycle against the repository's actual `.agent-loop/` workflow; prefer the subprocess path if the required local commands are usable, otherwise fall back to the manual-handoff path and state that clearly. Observe and record: which adapter path was used, which status transitions actually landed in `.agent-loop/loop-state.json`, which artifact mtimes actually advanced, which lines appeared in `.agent-loop/orchestrator.log`, and what the cycle's terminal state was (success path, halt path, or fix-cycle path). Fix any concrete operational bug the live run reveals with a minimal targeted change to `scripts/agent_loop.py`; if no bug is revealed, do not make speculative code changes. Update `README.md` only if the real operator workflow differs from what is currently documented.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 3 / 3E as active
- `.agent-loop/phase-plan.md` marks Phase 3D complete and contains a Phase 3E section
- at least one real bounded orchestrator run was actually executed against the repository's `.agent-loop/` workflow; the chosen adapter path and the reason for the choice are explicitly recorded
- `.agent-loop/claude-summary.md` truthfully describes the real run, clearly separating live-run observations from prior cycles' synthetic validation
- `.agent-loop/orchestrator.log` reflects the real run (this file did not exist before Phase 3E)
- any concrete operational bug revealed by the live run is fixed with minimal targeted code change; if no bug is revealed, `scripts/agent_loop.py` is unchanged
- the final on-disk state is left coherent and reviewable
- no approval modes, no Git automation, no editor integration, no recursive invocation of the locally installed `claude` CLI

## Next-Phase Gate

Do not start the next phase or 3x sub-phase (approval modes, editor integration, package-layout refactor, etc.) until:

- this Phase 3E slice receives `APPROVED_FOR_HUMAN_REVIEW`
- the human explicitly approves moving to the next sub-phase
- Codex updates `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` for the next sub-phase

## Out Of Scope For Current Phase

- approval mode implementation (Phase 5)
- editor integration (Phase 7)
- MCP support (future)
- recursive invocation of the locally installed `claude` CLI (would spawn a nested Claude Code session inside the current one - unsafe and outside the operational verification scope)
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- speculative code changes to `scripts/agent_loop.py` that are not justified by a concrete live-run observation
- any change to the Phase 2A Evidence Collection Contract
- any change to `scripts/run_checks.sh`
- any change to the Phase 3A Orchestrator Contract body
- adding any real test/lint/typecheck/build suite to the repository (still a documentation-only project)
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
