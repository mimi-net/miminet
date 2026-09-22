---
description: Commits current changes.
---

1. Review changes (`git status`, `git diff`). If there are unrelated changes, ask the user how to handle them (separate commit or include in this one).

2. If no issue number ask for it (e.g. #53).

3. Stage relevant files:
   ```
   git add <files>
   ```

4. Commit in English with format:
   ```
   git commit -m "<type>(<scope>): <description> (#<number>)"
   ```
   Example: `docs(git): add branch naming rules (#53)`

Task: $ARGUMENTS
