# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10AB - Controlled Concurrent Operation Contract

## Status
Phase 10AA is complete and approved to advance. Phase 10AB is now active as
the next mainline slice focused on defining the controlled-concurrency
contract required before any overlapping Codex/Claude work is allowed.

## Task
Implement Phase 10AB for the agent loop. This slice should define the overlap
rules, ownership boundaries, stale-artifact detection, review/fix invalidation
rules, and recovery behavior required before any concurrent Codex/Claude work
is allowed.

## Notes

- keep this slice bounded to the controlled concurrent-operation contract; do
  not jump into actually enabling overlap execution yet
- preserve the shipped ownership boundaries, evidence-review model, approval
  semantics, artifact source-of-truth model, and halt/recovery behavior while
  defining future overlap rules
- do not widen into silent background orchestration, hidden parallel workers,
  packaging, or auto-update work
