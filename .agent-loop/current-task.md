# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10AE - Framework Evaluation Beyond The Native Loop

## Status
Phase 10AD is complete and approved to advance. Phase 10AE is now active as
the next mainline slice focused on evaluating whether framework layers such as
CrewAI, LangGraph, and LangChain add real value beyond the shipped native
Codex/Claude loop now that the desktop surface, MCP/RAG controls, durable
memory, and controlled-concurrency model are in place.

## Task
Implement Phase 10AE for the agent loop. This slice should evaluate framework
options beyond the native loop and define a bounded comparison surface for
CrewAI, LangGraph, LangChain, or similar delegated-role runtimes without
rewriting the shipped Codex/Claude ownership model.

## Notes

- keep this slice evaluation-first and bounded; do not widen into a full
  framework migration, hidden orchestrator, or parallel worker runtime
- preserve the shipped ownership boundaries, evidence-review model, approval
  semantics, artifact source-of-truth model, and desktop/runtime contracts
  while comparing framework affordances against the native loop
- do not widen into packaging, auto-update work, live multi-worker scheduling,
  or any path that replaces the current shipped Python runtime by stealth
