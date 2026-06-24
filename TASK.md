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

Fix Phases - Targeted Remediation Track

## Active Sub-Phase

Fix Phase A - Automatic Local Claude/Codex Invocation Reliability

## Phase Status

Phase 10H is complete and approved for human review. Fix Phase A is now active as a targeted remediation slice to make the shipped Claude/Codex adapter seams reliable for real local automatic invocation without renumbering or disturbing the main roadmap phases.

## Active Task

Implement Fix Phase A for the agent loop. This slice should define and validate the real local adapter contract for `AGENT_LOOP_CLAUDE_CMD` and `AGENT_LOOP_CODEX_CMD`, provide first-party wrapper support or templates for invoking both CLIs automatically, and prove that the shipped intra-phase loop can run without manual prompt transfer when those adapter commands are configured correctly.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, and `.agent-loop/current-phase.md` identify Fix Phase A as active
- `.agent-loop/phase-plan.md` records Phase 10H as closed history and contains a `## Fix Phase A - Automatic Local Claude/Codex Invocation Reliability` section with `### Status` / `### Objective` / `### Definition of done` / `### Exclusions`
- the repository documents and enforces the concrete success/failure contract for `AGENT_LOOP_CLAUDE_CMD` and `AGENT_LOOP_CODEX_CMD`
- the repository ships first-party wrapper support or wrapper templates sufficient to drive local Claude and Codex CLI invocation without manual prompt transfer
- focused validation proves the orchestrator fail-closes when adapter commands do not produce fresh canonical artifacts and succeeds when correctly configured wrappers do
- `README.md` and operator docs clearly distinguish "automatic local Claude/Codex invocation" from the still-separate fully autonomous PRD-to-product mode

## Next-Phase Gate

Do not treat automatic local agent invocation as equivalent to fully autonomous PRD-to-product execution until:

- Fix Phase A receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the local automatic adapter path as reliable enough to use for future automation work
- Codex updates the canonical phase/task artifacts before treating any later autonomy remediation as active work

## Out Of Scope For Current Phase

- any mutating external UI control or broader Phase 10 UI expansion
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch, concurrent Codex/Claude overlap execution, MCP integration, RAG layer, GitHub integration, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing future remediation or roadmap work into this planning slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- recursive invocation of the locally installed `claude` CLI
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite to the repository beyond focused retry/re-probe coverage
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
