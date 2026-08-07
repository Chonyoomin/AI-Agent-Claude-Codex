# Current Task

## Phase
Fix Phase C - Guided Non-Technical Desktop PRD-To-Run UX

## Sub-Phase
Fix Phase C1 - First-Run Setup Contract

## Status
Active and ready for implementation.

## Task
Define the non-technical desktop UX contract for selecting a project folder,
loading a PRD, choosing run behavior, starting/stopping the agent, and
understanding plain-English progress without terminal knowledge.

## Notes

- this slice is contract-first; it defines the single-user non-technical
  desktop flow before later runtime slices implement the UI
- the default experience should optimize for one local operator who dislikes
  terminals and wants "choose folder, load PRD, run"
- the shipped desktop app must remain canonical-artifact-first and must not
  invent a second UI-only orchestration plane
- technical CLI/runtime language should be hidden by default and exposed only
  in advanced views where necessary
