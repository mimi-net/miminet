from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from miminet_config import make_empty_network
from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    ForeignKey,
    MetaData,
    Text,
)


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)

# Node types that live on the canvas but take no part in the emulation: back
# drops them before building the topology. Adding, editing or removing one
# leaves the network's last simulation valid.
NON_EMULATED_NODE_TYPES = frozenset({"textbox"})


class User(db.Model, UserMixin):  # type: ignore[name-defined]
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
    ai_keys = db.Column(Text, nullable=True)


class Network(db.Model):  # type: ignore[name-defined]
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


class Simulate(db.Model):  # type: ignore[name-defined]
    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    network_id = db.Column(BigInteger, ForeignKey("network.id"), nullable=False)
    task_guid = db.Column(Text, nullable=True, default="")
    # Do we finish? (False - new, True - simulation is finished)
    ready = db.Column(Boolean, default=False)
    packets = db.Column(Text, nullable=True, default="")


# Add new record to this table when you put a new simulation
# Set ready flag to True when simulation is over
# simulate_end will autp-update
class SimulateLog(db.Model):  # type: ignore[name-defined]
    id = db.Column(BigInteger, primary_key=True)
    author_id = db.Column(BigInteger, nullable=False)
    network_guid = db.Column(Text, nullable=False)
    network = db.Column(Text, default=make_empty_network, nullable=False)

    simulate_start = db.Column(TIMESTAMP(timezone=True), server_default=db.func.now())
    simulate_end = db.Column(TIMESTAMP(timezone=True), onupdate=db.func.now())

    ready = db.Column(Boolean, default=False, nullable=False)
