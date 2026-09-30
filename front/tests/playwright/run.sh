#!/bin/sh
# Запуск Playwright-тестов фронтенда.
#
# Из корня репозитория:
#   sh front/tests/playwright/run.sh              # весь набор в 4 процесса
#   sh front/tests/playwright/run.sh test_vlan.py # один файл
#   sh front/tests/playwright/run.sh . --headed   # с видимым браузером
#
# Приложение должно быть запущено (./start_all_containers.sh).
# Docker для самих тестов не нужен: браузер поднимается как обычный процесс.
set -e

# nginx внутри docker-сети слушает 172.18.0.2, но снаружи этот адрес отдаёт 502,
# поэтому с хоста тесты ходят на localhost. Переопределяется переменной окружения.
TEST_TARGET_HOST="${TEST_TARGET_HOST:-127.0.0.1}"
export TEST_TARGET_HOST

# Четыре процесса проходят набор примерно за минуту вместо трёх. Больше можно,
# но выигрыша уже нет.
WORKERS="${WORKERS:-4}"

REPO_ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$(dirname "$0")"

# --project привязывает запуск к окружению репозитория: без него активированный
# в оболочке VIRTUAL_ENV (например, back/tests/.venv) перехватил бы pytest.
UV="uv run --project $REPO_ROOT"

if ! $UV python -c "import playwright" 2>/dev/null; then
    echo "[!] playwright не установлен, выполните: uv sync && uv run playwright install chromium" >&2
    exit 1
fi

if ! $UV python -c "import xdist" 2>/dev/null; then
    echo "[!] pytest-xdist не установлен, выполните: uv sync" >&2
    exit 1
fi

if [ "$#" -eq 0 ]; then
    set -- .
fi

echo "[!] Тесты идут на http://$TEST_TARGET_HOST, воркеров: $WORKERS"
exec $UV pytest "$@" -n "$WORKERS"
