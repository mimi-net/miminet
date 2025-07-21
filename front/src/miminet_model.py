from os import urandom

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from miminet_config import (
    make_empty_network,
)
from sqlalchemy import MetaData, BigInteger, Text, Boolean, TIMESTAMP, ForeignKey, not_
from werkzeug.security import generate_password_hash
import psycopg2


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


class Network(db.Model):  # type:ignore[name-defined]
    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    author_id = db.Column(BigInteger, ForeignKey("user.id"), nullable=False)

    guid = db.Column(Text, nullable=False, unique=True)
    title = db.Column(Text, default="Новая сеть", nullable=False)

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


def ensure_db_exists(host, user, password, target_db):
    """Check if the target database exists."""
    try:
        with psycopg2.connect(
            dbname="postgres", user=user, password=password, host=host, port=5432
        ) as conn:
            print(f"[✓] Checking if database '{target_db}' exists...")
            conn.autocommit = True

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (target_db,)
                )

                if not cur.fetchone():
                    print(f"[!] Database '{target_db}' not found. Creating...")
                    cur.execute(f"CREATE DATABASE {target_db}")
                    return False
                else:
                    print(f"[Ok] Database '{target_db}' exists.")
                    return True
    except Exception as e:
        print(f"[X] Error ensuring database exists: {e}")
        raise


def init_db(app):
    # Init DB
    with app.app_context():
        try:
            # Some networks can be marked as non-emulated in the database, we should fix them.
            print("[!] Fix nonemulated networks...")
            SimulateLog.query.filter(not_(SimulateLog.ready)).update({"ready": True})
            db.session.commit()
        except Exception:
            print("[!] Database not found. Creating...")
            db.session.commit()  # https://stackoverflow.com/questions/24289808/drop-all-freezes-in-flask-with-sqlalchemy
            db.drop_all()
            db.create_all()

            print("[!] Create users...")
            users = []

            for user in users:
                u = User(
                    email=user["email"],
                    password_hash=generate_password_hash(urandom(16).hex()),
                    nick=user["nick"],
                )

                db.session.add(u)
                db.session.commit()
