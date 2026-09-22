---
description: Creates a feature (feat) branch and implements a task.
---

1. Switch to `main` branch:
   ```
   git checkout main
   ```

2. Pull latest changes:
   ```
   git pull origin main
   ```

3. Based on the task description, generate a branch name. See `docs/GIT.md`

4. Create and switch to a new branch:
   ```
   git checkout -b feat/<issue>-<description>
   ```

5. Study the codebase and describe an implementation plan.
6. *DO NOT* implement plan until user approve it!
7. User *CAN* clarify plan and ask for changes. 
8. Implement the task *ONLY* after user approve plan. 
9. Implement the task by following project best practices (see AGENTS.md,).
10. *DO NOT* implement any test.

Task: $ARGUMENTS