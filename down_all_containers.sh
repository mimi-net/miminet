#!/bin/sh
# Downing all containers

# Читаем MODE из front/.env, если не установлен в окружении
if [ -z "$MODE" ]; then
    if [ -f "front/.env" ]; then
        MODE=$(grep "^MODE=" front/.env | cut -d '=' -f2)
    fi
    # Если MODE все еще пустой, используем dev по умолчанию
    MODE="${MODE:-dev}"
fi

echo "[!] Stopping containers in $MODE mode"

# Остановка backend
cd back || exit
sudo docker compose down
cd ..

# Остановка frontend с выбором docker-compose файла
cd front || exit
if [ "$MODE" = "prod" ]; then
    echo "[!] Using docker-compose-prod.yml"
    sudo docker compose -f docker-compose-prod.yml down
else
    echo "[!] Using docker-compose.yml"
    sudo docker compose down
fi
cd ..

sudo docker ps -a