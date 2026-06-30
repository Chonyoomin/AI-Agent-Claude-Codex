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

Phase 10 - Future Product Features

## Active Sub-Phase

Phase 10U - MCP Action Guardrails And Per-Tool Approval Policies

## Phase Status

Phase 10T is complete and approved to advance. Phase 10U is now active as the next mainline slice focused on adding the mutation boundaries, refusal behavior, auditing, per-tool allow-lists, and approval prompts required before any non-read-only MCP-assisted runtime action is allowed through the desktop app.

## Active Task

Implement Phase 10U for the agent loop. This slice should add the mutation boundaries, refusal behavior, auditing, per-tool allow-lists, and approval prompts required before any non-read-only MCP-assisted runtime action is allowed through the desktop app.

## Phase Outcome Required Now

- `TASK.md`, `.agent-loop/current-task.md`, `.agent-loop/current-phase.md`, and `.agent-loop/loop-state.json` identify Phase 10 / 10U as active
- `.agent-loop/phase-plan.md` records Phase 10T as closed history and contains a `## Phase 10U - MCP Action Guardrails And Per-Tool Approval Policies` section with concrete objective, done criteria, and exclusions
- the repository adds the mutation boundaries, refusal behavior, auditing, per-tool allow-lists, and approval prompts required before any non-read-only MCP-assisted runtime action is allowed through the desktop app
- the implementation follows the shipped Phase 10O MCP integration contract, Phase 10S MCP server selection UX contract, and Phase 10T read-only assistance surface, preserving the canonical-artifact-first model while introducing bounded mutation guardrails
- the implementation preserves approval gating, evidence review, external-workspace boundaries, desktop/UI boundaries, and the Phase 10I library-callable cap instead of introducing hidden automation, silent mutation, or a parallel state store
- focused validation proves the mutation-capable MCP action guardrails are bounded, auditable, and do not widen into RAG runtime, packaging, or controlled-concurrency work
- `README.md` reflects that Phase 10U is active and that MCP action guardrails and per-tool approval policies are now the implementation focus

## Next-Phase Gate

Do not widen the desktop app beyond MCP read-only assistance until:

- Phase 10U receives `APPROVED_FOR_HUMAN_REVIEW`
- the human approves the MCP mutation-guardrails slice
- any RAG runtime, policy-pack, packaging, or controlled-concurrency work is activated through its own later phase instead of being folded into this slice

## Out Of Scope For Current Phase

- any broad MCP runtime expansion beyond the bounded mutation-capable guardrails defined for this slice, or any tool-execution path that bypasses the approved approval and audit policies
- any hidden background control plane or second orchestrator that bypasses the shipped Python runtime
- any automatic next-phase activation behavior that bypasses or rewrites the shipped Phase 4 planner / activation separation
- any claim that fully autonomous PRD-to-product execution is already solved
- any external-workspace target dispatch beyond the shipped attach/bootstrap/runtime surfaces, concurrent Codex/Claude overlap execution, RAG layer, or model-policy extensibility work
- any rewrite of current shipped behavior just to make future autonomy work easier
- rewriting contracts in `AGENTS.md` or `CLAUDE.md`
- inventing unreviewable autonomous behavior that the repo does not currently ship just to simplify the implementation
- collapsing later Phase 10 RAG, policy-pack, packaging, or concurrency work into this slice
- implementation of end-to-end fully autonomous PRD-to-product execution
- fabrication of `.agent-loop/codex-review.md` content (Codex-owned)
- any change to the Phase 2A Evidence Collection Contract
- any change to the Phase 3A Orchestrator Contract body
- any change to the Phase 4A Planning Contract body
- any change to `scripts/run_checks.sh`
- adding any project-wide CI suite beyond focused validation for the MCP read-only assistance surfaces
- Git automation (no commit, push, branch, stash, reset, checkout, tag)
