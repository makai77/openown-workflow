---
description: Advance the project to the next phase by updating context/current-feature.md. Use when the user says a phase is done, asks to move to the next phase, or wants to update the current feature file.
disable-model-invocation: true
---

## Current phase file

!`cat context/current-feature.md`

## Instructions

1. **Confirm the phase is done** — ask the user to confirm every item in the "Done when" checklist is met and committed. Do not proceed if any item is unconfirmed.

2. **Identify the next phase** — read the "Next" list in the file above. The first item becomes the new "Now".

3. **Rewrite `context/current-feature.md`**:
   - Set **## Now** to the next phase, including:
     - Phase name and number
     - The relevant Playbook section(s) (e.g. "Playbook §5 + §8.2")
     - A concrete "Done when" checklist
     - A clear "Do NOT start X yet" boundary
   - Update **## Next** to remove the phase that is now "Now" and shift the remaining list up
   - Preserve the **## Decisions / notes** section and remind the user to add anything decided during the completed phase

4. **Report** what changed and confirm the file is saved. The user's next session will automatically load the updated phase context.
