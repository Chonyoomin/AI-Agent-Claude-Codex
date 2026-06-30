# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10V - RAG Source Selection Contract And Desktop UX

## Status
Phase 10U is complete and approved to advance. Phase 10V is now active as the next mainline slice focused on defining how repo-local docs, PRDs, notes, standards, and other knowledge sources can be selected from the desktop app, how provenance and freshness are exposed to the operator, and how advisory-only retrieval remains distinct from canonical artifacts.

## Task
Implement Phase 10V for the agent loop. This slice should define how repo-local docs, PRDs, notes, standards, and other knowledge sources can be selected from the desktop app, how provenance and freshness are exposed to the operator, and how advisory-only retrieval remains distinct from canonical artifacts.

## Notes

- keep this slice bounded to the RAG source-selection contract and desktop UX; do not jump into indexing, retrieval runtime, or concurrency work yet
- preserve the shipped ownership boundaries, evidence-review model, approval semantics, desktop-app boundaries, and canonical-artifact-first model while defining bounded advisory-only RAG source selection
- do not widen into hidden orchestration, silent in-flight loop mutation, background ingestion/indexing, packaging, or auto-update work
