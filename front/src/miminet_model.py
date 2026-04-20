import os
from os import urandom
import random
import json
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from miminet_config import (
    make_empty_network,
)
from sqlalchemy import (
    MetaData,
    BigInteger,
    Text,
    Boolean,
    TIMESTAMP,
    ForeignKey,
    not_,
    inspect,
)
from werkzeug.security import generate_password_hash
import psycopg2
from psycopg2 import OperationalError


def generate_cosmic_name():
    """Generates unique cosmic object name with timestamp"""
    try:
        with open("static/cosmic_names.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        config = {
            "cosmic_objects": ["Звезда", "Галактика", "Планета"],
            "prefixes": ["", "XB-", "NGC-"],
        }

    timestamp = datetime.now().strftime("%d%m%y")
    random_num = random.randint(100, 999)
    cosmic_type = random.choice(config["cosmic_objects"])
    prefix = random.choice(config["prefixes"])

    return f"{cosmic_type} {prefix}{timestamp}{random_num}"


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


class User(db.Model, UserMixin):  # type:ignore[name-defined]
    id = db.Column(BigInteger, primary_key=True, unique=True, autoincrement=True)

    role = db.Column(BigInteger, default=0, nullable=True)

    email = db.Column(Text, unique=True, nullable=True)
    password_hash = db.Column(Text, unique=False, nullable=True)

    nick = db.Column(Text, nullable=False)
    avatar_uri = db.Column(Text, default="empty.jpg", nullable=False)

    vk_id = db.Column(Text, nullable=True)
    google_id = db.Column(Text, nullable=True)
    yandex_id = db.Column(Text, nullable=True)
    tg_id = db.Column(Text, nullable=True)

    config = db.Column(Text, nullable=True)


class Network(db.Model):  # type:ignore[name-defined]
    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    author_id = db.Column(BigInteger, ForeignKey("user.id"), nullable=False)

    guid = db.Column(Text, nullable=False, unique=True)
    title = db.Column(Text, default=lambda: generate_cosmic_name(), nullable=False)

    description = db.Column(Text, default="", nullable=True)

    network = db.Column(Text, default=make_empty_network, nullable=False)
    preview_uri = db.Column(Text, default="first_network.jpg", nullable=False)

    # Is this network in share mode?
    share_mode = db.Column(Boolean, default=True)

    # Don't show networks for tasks
    is_task = db.Column(Boolean, default=False, nullable=False)


class Simulate(db.Model):  # type:ignore[name-defined]
    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    network_id = db.Column(BigInteger, ForeignKey("network.id"), nullable=False)
    task_guid = db.Column(Text, nullable=True, default="")
    # Do we finish? (False - new, True - simulation is finished)
    ready = db.Column(Boolean, default=False)
    packets = db.Column(Text, nullable=True, default="")


# Add new record to this table when you put a new simulation
# Set ready flag to True when simulation is over
# simulate_end will autp-update
class SimulateLog(db.Model):  # type:ignore[name-defined]
    id = db.Column(BigInteger, primary_key=True)
    author_id = db.Column(BigInteger, nullable=False)
    network_guid = db.Column(Text, nullable=False)
    network = db.Column(Text, default=make_empty_network, nullable=False)

    simulate_start = db.Column(TIMESTAMP(timezone=True), server_default=db.func.now())
    simulate_end = db.Column(TIMESTAMP(timezone=True), onupdate=db.func.now())

    ready = db.Column(Boolean, default=False, nullable=False)


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
    """Check if the target database exists.

    Args:
        host: Database host
        user: Database user
        password: Database password
        target_db: Target database name
        port: Database port (default: 5432)
        sslmode: SSL mode for connection (default: None, use 'require' for Yandex Cloud)
        sslrootcert: Path to SSL root certificate
        mode: Operation mode ('dev' or 'prod')
    """
    # 1. Try to connect to target_db directly
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
            print(f"[OK] Successfully connected to database '{target_db}'")
            return True
    except OperationalError:
        # If connection failed
        if mode == "prod":
            print(f"[ERROR] Database '{target_db}' does not exist or unreachable.")
            print(
                "[HINT] In PROD mode (Yandex Cloud), you must create the database manually via Console!"
            )
            # In PROD we DO NOT try to create DB via postgres system db
            raise

    # 2. Only if mode == 'dev' and connection failed
    print(
        f"[DEV] Target db '{target_db}' not found. Trying to create via 'postgres' db..."
    )

    sys_conn_params = conn_params.copy()
    sys_conn_params["dbname"] = "postgres"  # Connect to system DB

    try:
        with psycopg2.connect(**sys_conn_params) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (target_db,)
                )

                if not cur.fetchone():
                    print(f"[DEV] Creating database {target_db}...")
                    cur.execute(f"CREATE DATABASE {target_db}")
                else:
                    print(
                        f"[DEV] Database {target_db} exists but connection failed previously. Check permissions."
                    )
        return True
    except Exception as e:
        print(f"[ERROR] Failed to auto-create database in DEV mode: {e}")
        raise


def init_db(app):
    # Init DB
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

        # Проверить/создать БД для обоих режимов
        if postgres_host and postgres_user and postgres_password and postgres_db:
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

        # Logic for creating tables
        inspector = inspect(db.engine)
        tables_exist = inspector.has_table("user")

        if not tables_exist:
            print(f"[{mode.upper()}] Tables not found. Creating schema...")
            db.create_all()

            # Create test data only for DEV
            if mode == "dev":
                print("[DEV] Creating test users...")
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
            print(f"[{mode.upper()}] Schema exists.")
            # Only fix data if tables exist
            try:
                # Some networks can be marked as non-emulated in the database, we should fix them.
                print("[!] Fix nonemulated networks...")
                SimulateLog.query.filter(not_(SimulateLog.ready)).update(
                    {"ready": True}
                )
                db.session.commit()
            except Exception as e:
                print(f"[!] Error fixing nonemulated networks: {e}")
