---
description: Creates a feature (feat) branch and implements a task.
---

1. Create and switch to a new branch from fresh `main`. Generate the name per `docs/GIT.md`:
   ```
   git checkout main && git pull --ff-only && git checkout -b feat/<issue>-<description>
   ```

2. Study the codebase and describe an implementation plan. Implement *ONLY* after user approves the plan.

Task: $ARGUMENTS
