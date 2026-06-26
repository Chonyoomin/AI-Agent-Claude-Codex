# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10J - Artifact Dashboard Contract

## Status
Phase 10I is complete. Phase 10J is now active as the next mainline slice focused on defining the artifact dashboard contract for external UI work without replacing canonical artifacts.

## Task
Define Phase 10J for the agent loop. This slice should specify how review summaries, diff views, progress history, approval actions, token/cost reporting, and failure analytics should be surfaced in the external UI without replacing canonical artifacts on disk.

## Notes

- keep the dashboard contract documentation-first in this slice; do not jump straight to runtime implementation
- preserve the shipped advisory-vs-canonical boundary so dashboards remain derived views over canonical artifacts
- do not widen into dashboard runtime implementation, controlled-concurrency, MCP, RAG, GitHub, or policy-pack work
