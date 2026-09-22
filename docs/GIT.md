# GIT.md — именование веток и коммитов

## Именования веток

**ОБЯЗАТЕЛЬНО** в формате: 
 - `<type>/<issue>-<описание>`
 - если issue нет запросить у пользователя с вариантом `<type>/chore-<описание>`.

* **ОБЯЗАТЕЛЬНО** только `kebab-case`, нижний регистр, латиница, цифры и `-`. Без `_`, заглавных букв, пробелов и имени автора.
* `type`: `feat|fix|hotfix|chore|docs|refactor|test|ci|revert`.
* `scope` (если нужен): суффиксом `-front|-back|-infra`, отдельный уровень не создавать.
* 2-4 слова с глаголом. Хорошо: `fix/zombie-processes-back`, `feat/321-vlan-filter-front`. Плохо: `patch-1`, `Add-HostHacker`, `ElenaBakova/fix-typo`.
* Создание только от свежего `main`: `git checkout main && git pull && git checkout -b <имя>`.