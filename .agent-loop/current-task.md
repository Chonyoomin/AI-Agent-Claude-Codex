# Current Task

## Phase
Fix Phase B - Desktop Empty-Target Bootstrap Flow

## Sub-Phase
Fix Phase B2 - Desktop Bootstrap Form And Validation

## Status
Fix Phase B1 is complete and approved to advance. Fix Phase B2 is now active
as the next remediation slice focused on turning the approved desktop bootstrap
UX contract into a bounded in-app form and validation surface for empty-target
project setup, while preserving the shipped external-target/runtime boundaries.

## Task
Implement Fix Phase B2 for the agent loop. This slice should add the bounded
desktop bootstrap form, required-field entry flow, and fail-closed validation
surface for empty-target project setup without yet introducing direct desktop
bootstrap dispatch or weakening the shipped attach/bootstrap runtime contract.

## Notes

- keep this slice focused on the desktop form and validation layer only; do not
  widen into bootstrap dispatch, post-bootstrap activation, or hidden desktop
  automation
- preserve the shipped operator-input rule: no hidden defaults for
  `attached_by`, `bootstrapped_by`, `human_objective`, or `project_intent`
- preserve the shipped empty/full/partial/malformed target vocabulary and
  refusal boundaries instead of inventing a second UI-only state plane
