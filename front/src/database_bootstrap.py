"""Подготовка базы данных и схемы приложения при запуске."""

import logging
import os
from os import urandom
from datetime import datetime, timezone
import re

import psycopg2
from miminet_model import SimulateLog, User, db
from psycopg2 import OperationalError
from sqlalchemy import inspect, not_
from werkzeug.security import generate_password_hash

# Сохраняем имя логгера для существующих фильтров и обработчиков.
logger = logging.getLogger("miminet_model")


def ensure_db_exists(
    host,
    user,
    password,
    target_db,
    port=5432,
    sslmode=None,
    sslrootcert=None,
    mode="dev",
):
    """Проверяем доступность базы, в режиме разработки создаём отсутствующую.

    Параметры подключения и TLS передаются драйверу. В рабочем режиме
    ошибка целевого подключения передаётся вызывающему без создания базы.
    """
    # Сначала пробуем подключиться непосредственно к целевой базе.
    conn_params = {
        "dbname": target_db,
        "user": user,
        "password": password,
        "host": host,
        "port": port,
    }
    if sslmode:
        conn_params["sslmode"] = sslmode
    if sslrootcert:
        conn_params["sslrootcert"] = sslrootcert

    try:
        with psycopg2.connect(**conn_params) as conn:
            logger.info(f"[OK] Successfully connected to database '{target_db}'")
            return True
    except OperationalError:
        # В рабочем режиме автоматическое создание базы запрещено.
        if mode == "prod":
            logger.error(
                f"[ERROR] Database '{target_db}' does not exist or unreachable."
            )
            logger.error(
                "[HINT] In PROD mode (Yandex Cloud), you must create the database manually via Console!"
            )
            # Не подключаемся к системной базе postgres в режиме prod.
            raise

    # После ошибки подключения проверяем наличие базы через системный каталог.
    logger.info(
        f"[DEV] Target db '{target_db}' not found. Trying to create via 'postgres' db..."
    )

    sys_conn_params = conn_params.copy()
    sys_conn_params["dbname"] = "postgres"  # Системная база для подготовки стенда.

    try:
        with psycopg2.connect(**sys_conn_params) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (target_db,)
                )

                if not cur.fetchone():
                    logger.info(f"[DEV] Creating database {target_db}...")
                    cur.execute(f"CREATE DATABASE {target_db}")
                else:
                    logger.warning(
                        f"[DEV] Database {target_db} exists but connection failed previously. Check permissions."
                    )
        return True
    except Exception as e:
        logger.error(f"[ERROR] Failed to auto-create database in DEV mode: {e}")
        raise


def _log_repair_failure(mode, error):
    """Пишем место сбоя и безопасный контекст без SQL, параметров и цепочки причин."""
    error_type = type(error).__name__
    driver_error = getattr(error, "orig", error)
    sqlstate = getattr(driver_error, "pgcode", None)
    if not isinstance(sqlstate, str) or not re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
        sqlstate = "unknown"
    event_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    # SQLAlchemy включает SQL и параметры в str(error). Обычный exc_info=True
    # также напечатал бы исходные причины. Сохраняем кадры, но заменяем значение
    # исключения безопасным объектом без исходного сообщения и причин.
    safe_error = RuntimeError(f"{error_type}: database exception details omitted")
    logger.error(
        "[!] Error fixing nonemulated networks "
        "(stage=repair_pending_logs mode=%s error=%s sqlstate=%s time=%s)",
        mode,
        error_type,
        sqlstate,
        event_time,
        exc_info=(RuntimeError, safe_error, error.__traceback__),
        extra={
            "bootstrap_stage": "repair_pending_logs",
            "bootstrap_mode": mode,
            "error_type": error_type,
            "sqlstate": sqlstate,
            "event_time": event_time,
        },
    )


def init_db(app):
    """Создаём отсутствующую схему или завершаем оставшиеся журналы эмуляции."""
    mode = os.getenv("MODE", "dev")

    with app.app_context():
        # Получить параметры подключения в зависимости от режима
        if mode == "dev":
            # Локальный PostgreSQL
            postgres_host = os.getenv("POSTGRES_HOST")
            postgres_user = os.getenv("POSTGRES_DEFAULT_USER")
            postgres_password = os.getenv("POSTGRES_DEFAULT_PASSWORD", "my_postgres")
            postgres_db = os.getenv("POSTGRES_DATABASE_NAME")
            postgres_port = 5432
            postgres_sslmode = None
            postgres_sslrootcert = None
        elif mode == "prod":
            # Yandex Cloud PostgreSQL
            postgres_host = os.getenv("YANDEX_POSTGRES_HOST")
            postgres_user = os.getenv("YANDEX_POSTGRES_USER")
            postgres_password = os.getenv("YANDEX_POSTGRES_PASSWORD")
            postgres_db = os.getenv("YANDEX_POSTGRES_DB", "miminet")
            postgres_port = int(os.getenv("YANDEX_POSTGRES_PORT", "6432"))
            postgres_sslmode = os.getenv("YANDEX_POSTGRES_SSLMODE", "verify-full")
            postgres_sslrootcert = os.getenv(
                "YANDEX_POSTGRES_SSLROOTCERT", "/app/.postgresql/root.crt"
            )
        else:
            raise ValueError(f"Unknown MODE: {mode}")

        # Явный SQLALCHEMY_DATABASE_URI означает, что базу подготовил вызывающий.
        # В этом случае не проверяем и не создаём другую БД из переменных MODE.
        uri_override = os.getenv("SQLALCHEMY_DATABASE_URI")
        if (
            not uri_override
            and postgres_host
            and postgres_user
            and postgres_password
            and postgres_db
        ):
            ensure_db_exists(
                postgres_host,
                postgres_user,
                postgres_password,
                postgres_db,
                port=postgres_port,
                sslmode=postgres_sslmode,
                sslrootcert=postgres_sslrootcert,
                mode=mode,
            )

        # Проверяем схему через тот же экземпляр db, которым пользуются модели.
        inspector = inspect(db.engine)
        tables_exist = inspector.has_table("user")

        if not tables_exist:
            logger.info(f"[{mode.upper()}] Tables not found. Creating schema...")
            db.create_all()

            # Начальные тестовые данные создаются только в режиме разработки.
            if mode == "dev":
                logger.info("[DEV] Creating test users...")
                users = []

                for user in users:
                    u = User(
                        email=user["email"],
                        password_hash=generate_password_hash(urandom(16).hex()),
                        nick=user["nick"],
                    )

                    db.session.add(u)
                    db.session.commit()
        else:
            logger.info(f"[{mode.upper()}] Schema exists.")
            # Восстанавливаем состояние журналов только при существующей схеме.
            try:
                # Отмечаем оставшиеся незавершённые журналы как готовые.
                logger.info("[!] Fix nonemulated networks...")
                SimulateLog.query.filter(not_(SimulateLog.ready)).update(
                    {"ready": True}
                )
                db.session.commit()
            except Exception as e:
                _log_repair_failure(mode, e)
