# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10L - Desktop App Shell Contract

## Status
Phase 10K is complete. Phase 10L is now active as the next mainline slice focused on defining the first native desktop-app shell for the external UI so operation no longer depends on terminal-only workflows.

## Task
Define Phase 10L for the agent loop. This slice should specify the desktop-app shell boundaries, controller/target selection flow, polling model, artifact-opening behavior, and the safe bridge between the desktop shell and the shipped Python orchestrator/view surfaces.

## Notes

- keep this slice documentation-first; do not jump into desktop runtime implementation yet
- preserve the shipped ownership boundaries, phase gating, and canonical-artifact-first model while defining the desktop shell
- do not widen into hidden UI-side orchestration, controlled-concurrency runtime, MCP, RAG, GitHub, or policy-pack work
