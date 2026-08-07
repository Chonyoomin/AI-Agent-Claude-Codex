# Current Task

## Phase
Fix Phase C - Guided Non-Technical Desktop PRD-To-Run UX

## Sub-Phase
Fix Phase C2 - Project Folder Picker And Classification Surface

## Status
Active and ready for implementation.

## Task
Add the guided desktop folder picker and classify the selected folder as an
existing project, empty folder, partial target, or malformed target with
plain-English next-step messaging.

## Notes

- this slice implements only the folder picker and target classification
  surface defined by the completed C1 contract
- the default experience should optimize for one local operator who dislikes
  terminals and wants "choose folder, load PRD, run"
- the shipped desktop app must remain canonical-artifact-first and must not
  invent a second UI-only orchestration plane
- technical CLI/runtime language should remain hidden by default and exposed
  only in the existing advanced-detail surface
- PRD selection, run controls, and run-console behavior remain deferred to C3
  through C8
