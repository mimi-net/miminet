---
description: Commits current changes.
---

1. Check current changes:
   ```
   git status
   ```

2. Review the diff:
   ```
   git diff
   ```

3. If there are unrelated changes in working directory, ask the user how to handle them (separate commit or include in this one).

4. If no issue number ask for the issue number (e.g. #53). Use "chore" or skip parentheses.

5. Stage relevant files:
   ```
   git add <files>
   ```

6. Commit on English with format:
   ```
   git commit -m "<modules_or_files>: <description> (#<number>)"
   ```
   Example: `AGENTS.md, commands: update commit rules (#53)`

Task: $ARGUMENTS