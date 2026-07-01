# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10Y - Capacity Recovery And Resume Console

## Status
Phase 10X is complete and approved to advance. Phase 10Y is now active as the next mainline slice focused on surfacing capacity-halt visibility, checkpoint presence, bounded resume policy, and operator recovery controls in the desktop app.

## Task
Implement Phase 10Y for the agent loop. This slice should add the first desktop capacity recovery and resume console so token or rate-limit halts, checkpoint presence, bounded automatic-resume policy, retry or backoff state, and operator override or resume actions are understandable without introducing a hidden second control plane.

## Notes

- keep this slice bounded to a desktop-facing capacity-recovery and resume-console surface; do not jump into model/policy selection, concurrency, packaging, or hidden orchestration work
- preserve the shipped ownership boundaries, evidence-review model, approval semantics, checkpoint/continuation boundaries, and canonical-artifact-first model while surfacing halt-recovery state in the UI
- do not widen into silent loop mutation, background daemons/watchers, packaging, or auto-update work
