import json
import shutil
import uuid
from os import urandom

from pathlib import Path
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declared_attr
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy import MetaData, types
from werkzeug.security import generate_password_hash
from flask_sqlalchemy import SQLAlchemy

from flask_login import UserMixin


from miminet_config import SQLITE_DATABASE_NAME, SQLITE_DATABASE_BACKUP_NAME, make_empty_network

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


class GUID(TypeDecorator):
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class Json(TypeDecorator):

    @property
    def python_type(self):
        return object

    impl = types.String

    def process_bind_param(self, value, dialect):
        return json.dumps(value)

    def process_literal_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None


class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), unique=False, nullable=True)

    nick = db.Column(db.String(255), nullable=False)
    avatar_uri = db.Column(db.String(512), default='empty.jpg', nullable=False)

    vk_id = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), nullable=True)


class Network(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    guid = db.Column(db.String(512), nullable=False)
    title = db.Column(db.String(1024), default='Новая сеть', nullable=False)

    description = db.Column(db.String(4096), default='', nullable=True)

    network = db.Column(db.UnicodeText, default=make_empty_network, nullable=False)
    preview_uri = db.Column(db.String(255), default='first_network.jpg', nullable=False)

    # Is this network in share mode?
    share_mode = db.Column(db.Boolean, default=True)


class Simulate(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    network_id = db.Column(db.Integer, db.ForeignKey('network.id'), nullable=False)

    # Do we finish? (False - new, True - simulation is finished)
    ready = db.Column(db.Boolean, default=False)
    packets = db.Column(db.UnicodeText, nullable=True, default='')


# Add new record to this table when you put a new simulation
# Set ready flag to True when simulation is over
# simulate_end will autp-update
class SimulateLog(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, nullable=False)
    network_guid = db.Column(db.String(512), nullable=False)
    network = db.Column(db.UnicodeText, default=make_empty_network, nullable=False)

    simulate_start = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    simulate_end = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    ready = db.Column(db.Boolean, default=False, nullable=False)


class IdMixin(object):

    __table_args__ = {'extend_existing': True}

    id = db.Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))


class SoftDeleteMixin(object):

    __table_args__ = {'extend_existing': True}

    is_deleted = db.Column(db.Boolean, default=False)


class TimeMixin(object):

    __table_args__ = {'extend_existing': True}

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())


class CreatedByMixin(object):

    __table_args__ = {'extend_existing': True}

    @declared_attr
    def created_by_id(cls):
        return db.Column('created_by_id', db.ForeignKey('user.id'))

    @declared_attr
    def created_by_user(cls):
        return relationship("User")


class Test(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "test"

    name = db.Column(db.String(512), default="")
    description = db.Column(db.String(512), default="")

    sections = relationship("Section", back_populates="test")


class Section(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "section"

    name = db.Column(db.String(512), default="")
    description = db.Column(db.String(512), default="")
    timer = db.Column(db.DateTime, default=db.func.now())
    test_id = db.Column(db.ForeignKey("test.id"))

    test = relationship("Test", back_populates="sections")
    questions = relationship("Question", back_populates="section")


class Question(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "question"

    question_text = db.Column(db.String(512), default="")
    question_type = db.Column(db.String(32), default="")
    section_id = db.Column(GUID(), db.ForeignKey(Section.id))

    section = relationship("Section", back_populates="questions")

    text_question = relationship(
        'TextQuestion',
        uselist=False,
        backref=db.backref('question', uselist=False)
    )


class TextQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "text_question"

    id = db.Column(GUID(), db.ForeignKey(Question.id), primary_key=True)
    text_type = db.Column(db.String(32), default="")

    question = relationship(
        'Question',
        uselist=False,
        backref=db.backref('text_question', uselist=False)
    )


class SortingQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "sorting_question"

    id = db.Column(GUID(), db.ForeignKey('text_question.id'), primary_key=True)
    right_sequence = db.Column(db.UnicodeText, default="")
    explanation = db.Column(db.String(512), default="")


class MatchingQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "matching_question"

    id = db.Column(GUID(), db.ForeignKey('text_question.id'), primary_key=True)
    map = db.Column(Json(), default="")
    explanation = db.Column(db.String(512), default="")


class VariableQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "variable_question"

    id = db.Column(GUID(), db.ForeignKey('text_question.id'), primary_key=True)

    answers = relationship("Answer", back_populates="variable_question")


class Answer(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model):

    __tablename__ = "answer"

    answer_text = db.Column(db.String(512), default="")
    explanation = db.Column(db.String(512), default="")
    is_correct = db.Column(db.Boolean, default="")

    variable_question_id = db.Column(GUID(), db.ForeignKey("variable_question.id"))
    variable_question = relationship("VariableQuestion", back_populates="answers")


def init_db(app):
    # Data

    users=[
    ]

    # Check if db file already exists. If so, backup it
    db_file = Path(SQLITE_DATABASE_NAME)
    if db_file.is_file():
        shutil.copyfile(SQLITE_DATABASE_NAME, SQLITE_DATABASE_BACKUP_NAME)

    # Init DB
    with app.app_context():
        print ("Create DB: " + app.config['SQLALCHEMY_DATABASE_URI'])
        db.session.commit()  # https://stackoverflow.com/questions/24289808/drop-all-freezes-in-flask-with-sqlalchemy
        db.drop_all()
        db.create_all()

    # Create users
    print("Create users")
    for user in users:
        u = User(email=user['email'], password_hash=generate_password_hash(urandom(16).hex()),
                  nick=user['nick'])

        with app.app_context():
            db.session.add(u)
            db.session.commit()
