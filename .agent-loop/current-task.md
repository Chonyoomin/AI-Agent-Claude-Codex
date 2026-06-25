# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10I - Minimal External UI Run/Resume Controls

## Status
Phase 10H is complete. Fix Phase A is complete. Phase 10I is now active as the next mainline slice focused on adding bounded external UI run/resume controls on top of the shipped read-only surface.

## Task
Implement Phase 10I for the agent loop. This slice should add bounded run/resume/inspect controls to the external UI on top of the shipped Phase 10H read-only surface, while preserving the CLI-first contract, canonical repo artifacts as the source of truth, and all existing approval and ownership boundaries.

## Notes

- preserve the shipped Phase 10H read-only UI boundaries and add only the bounded run/resume/inspect controls required for this slice
- keep the UI advisory-vs-canonical boundary intact: repo artifacts on disk remain the source of truth
- do not widen into artifact-dashboard, controlled-concurrency, MCP, RAG, GitHub, or policy-pack work
