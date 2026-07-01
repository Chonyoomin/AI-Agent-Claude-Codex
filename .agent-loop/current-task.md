# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10W - RAG Local Index And Retrieval Controls

## Status
Phase 10V is complete and approved to advance. Phase 10W is now active as the next mainline slice focused on adding the first bounded controller-local RAG index and retrieval-control runtime on top of the shipped source-selection contract.

## Task
Implement Phase 10W for the agent loop. This slice should add the first bounded local RAG index and retrieval-control runtime so the loop can pull only the most relevant repo-local PRD sections, docs, decisions, standards, and failure/fix patterns into a run without replacing canonical artifacts.

## Notes

- keep this slice bounded to a controller-local RAG index and retrieval-control runtime; do not jump into remote retrieval, concurrency, packaging, or fully autonomous orchestration work
- preserve the shipped ownership boundaries, evidence-review model, approval semantics, desktop-app boundaries, and canonical-artifact-first model while adding bounded local retrieval
- do not widen into hidden orchestration, silent in-flight loop mutation, background daemons/watchers, packaging, or auto-update work
