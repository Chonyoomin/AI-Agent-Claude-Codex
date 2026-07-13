# Claude Code Task

## Phase
Phase 10AE - Framework Evaluation Beyond The Native Loop

## Objective
Evaluate framework options beyond the native loop and define a bounded
comparison surface for CrewAI, LangGraph, LangChain, or similar delegated-role
runtimes without rewriting the shipped Codex/Claude ownership model.

## Context
The repo is parked back on the main roadmap after the approved `Fix Phase B`
desktop bootstrap remediation track. `Phase 10AE` is the latest mainline slice
and should be treated as the active mainline implementation prompt when working
from the current repo state.

This slice is evaluation-first, not migration-first. The shipped desktop app,
external-target control, MCP/RAG surfaces, durable memory, continuation model,
and controlled-concurrency boundaries now exist in-repo. The task here is to
compare what a framework layer would add beyond that shipped native loop and to
make those tradeoffs explicit in repo artifacts and UI/reporting surfaces where
appropriate.

Work against the actual repo state. Do not rely on prior chat context.

## Required work
- add or refine a bounded framework-evaluation surface that compares the
  shipped native loop against at least:
  - `native_loop`
  - `langgraph`
  - `langchain`
  - `crewai`
- make the comparison explicit rather than narrative-only:
  - where each framework could help
  - where each framework would conflict with shipped ownership/review/approval
    boundaries
  - what should remain native-loop-only
- ensure the evaluation surface is auditable from canonical/advisory repo
  artifacts rather than hidden judgment in code comments alone
- preserve the shipped desktop/runtime boundaries while surfacing the
  evaluation in operator-visible form where appropriate
- add or update focused tests for the evaluation surface
- update `README.md` if the shipped operator-visible behavior or documented
  current implementation focus changes

## Constraints
- Follow `CLAUDE.md`.
- Do not modify `AGENTS.md`.
- Do not modify `CLAUDE.md`.
- Stay evaluation-only and bounded.
- Do not silently swap the shipped runtime to a framework-backed path.
- Do not add a hidden orchestrator, delegated worker runtime, or broad
  background execution model under the banner of “evaluation”.
- Do not weaken approval gating, evidence review, overlap-safety, or
  canonical-artifact-first boundaries.
- Prefer small, testable, reversible changes.

## Important guardrails
- Framework code is an evaluation seam, not a replacement for the current
  shipped Codex/Claude ownership model.
- LangGraph may be treated as the strongest explicit state-machine comparison
  candidate.
- LangChain should remain a support-layer comparison, not the primary top-level
  orchestrator.
- CrewAI or similar delegated-role runtimes should be evaluated against the
  repo’s ownership, audit, and review boundaries, not just for convenience.
- Keep this slice centered on explicit comparison and bounded operator-facing
  reporting.

## Likely files
- `scripts/agent_loop.py`
- `tests/test_desktop_app.py`
- `tests/test_documentation_consistency.py`
- `README.md`
- any focused framework-evaluation tests already present in the repo

## Required output
After implementation, write `.agent-loop/claude-summary.md` using the required
Claude Implementation Summary format and include the validation you ran.
