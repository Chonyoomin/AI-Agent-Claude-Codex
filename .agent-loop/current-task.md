# Current Task

## Phase
Phase 10 - Future Product Features

## Sub-Phase
Phase 10Z - Model, Policy Pack, And Template Selection UX

## Status
Phase 10Y is complete and approved to advance. Phase 10Z is now active as the
next mainline slice focused on adding the first bounded desktop-managed
selection flow for models, policy packs, and project templates without letting
those choices become a hidden second source of truth.

## Task
Implement Phase 10Z for the agent loop. This slice should define and implement
the first bounded desktop-managed selection UX for model choices, policy packs,
project templates, and other high-level run presets without letting those
settings become a hidden second source of truth.

## Notes

- keep this slice bounded to a desktop-facing selection surface for models,
  policy packs, templates, and related presets; do not jump into packaging,
  controlled concurrency, or hidden orchestration work
- preserve the shipped ownership boundaries, evidence-review model, approval
  semantics, existing run-profile semantics, and canonical-artifact-first model
  while surfacing selection state in the UI
- do not widen into silent preset mutation, background daemons/watchers,
  packaging, or auto-update work
