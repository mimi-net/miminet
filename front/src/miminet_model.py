import shutil
from os import urandom
from pathlib import Path

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from miminet_config import (
    SQLITE_DATABASE_BACKUP_NAME,
    SQLITE_DATABASE_NAME,
    make_empty_network,
)
from sqlalchemy import MetaData
from werkzeug.security import generate_password_hash

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
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), unique=False, nullable=True)

    nick = db.Column(db.String(255), nullable=False)
    avatar_uri = db.Column(db.String(512), default="empty.jpg", nullable=False)

    vk_id = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), nullable=True)


class Network(db.Model):  # type:ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    guid = db.Column(db.String(512), nullable=False)
    title = db.Column(db.String(1024), default="Новая сеть", nullable=False)

    description = db.Column(db.String(4096), default="", nullable=True)

    network = db.Column(db.UnicodeText, default=make_empty_network, nullable=False)
    preview_uri = db.Column(db.String(255), default="first_network.jpg", nullable=False)

    # Is this network in share mode?
    share_mode = db.Column(db.Boolean, default=True)


class Simulate(db.Model):  # type:ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    network_id = db.Column(db.Integer, db.ForeignKey("network.id"), nullable=False)
    task_guid = db.Column(db.String(512), nullable=False)
    # Do we finish? (False - new, True - simulation is finished)
    ready = db.Column(db.Boolean, default=False)
    packets = db.Column(db.UnicodeText, nullable=True, default="")


# Add new record to this table when you put a new simulation
# Set ready flag to True when simulation is over
# simulate_end will autp-update
class SimulateLog(db.Model):  # type:ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, nullable=False)
    network_guid = db.Column(db.String(512), nullable=False)
    network = db.Column(db.UnicodeText, default=make_empty_network, nullable=False)

    simulate_start = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    simulate_end = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    ready = db.Column(db.Boolean, default=False, nullable=False)


def init_db(app):
    # Data

    users = []

    # Check if db file already exists. If so, backup it
    db_file = Path(SQLITE_DATABASE_NAME)
    if db_file.is_file():
        shutil.copyfile(SQLITE_DATABASE_NAME, SQLITE_DATABASE_BACKUP_NAME)

    # Init DB
    with app.app_context():
        print("Create DB: " + app.config["SQLALCHEMY_DATABASE_URI"])
        db.session.commit()  # https://stackoverflow.com/questions/24289808/drop-all-freezes-in-flask-with-sqlalchemy
        db.drop_all()
        db.create_all()

    # Create users
    print("Create users")
    for user in users:
        u = User(
            email=user["email"],
            password_hash=generate_password_hash(urandom(16).hex()),
            nick=user["nick"],
        )

        with app.app_context():
            db.session.add(u)
            db.session.commit()
