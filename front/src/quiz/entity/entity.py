import json
import uuid

from sqlalchemy import types, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr
from sqlalchemy.types import TypeDecorator, CHAR

from miminet_model import db


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
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


class IdMixin(object):
    __table_args__ = ({"extend_existing": True},)

    id = db.Column(db.Integer, primary_key=True)


class SoftDeleteMixin(object):
    __table_args__ = ({"extend_existing": True},)

    is_deleted = db.Column(db.Boolean, default=False)


class TimeMixin(object):
    __table_args__ = ({"extend_existing": True},)

    created_on = db.Column(db.DateTime, default=func.now())
    updated_on = db.Column(db.DateTime, default=func.now(), onupdate=func.now())


class CreatedByMixin(object):
    __table_args__ = ({"extend_existing": True},)

    @declared_attr
    def created_by_id(cls):
        return db.Column("created_by_id", db.ForeignKey("user.id"))

    @declared_attr
    def created_by_user(cls):
        return db.relationship("User")


class Test(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "test"

    name = db.Column(db.String(512), default="Название теста")
    description = db.Column(db.String(512), default="")
    is_ready = db.Column(db.Boolean, default=False)
    is_retakeable = db.Column(db.Boolean, default=False)

    sections = db.relationship("Section", back_populates="test")

    def __str__(self):
        return self.name

    def get_id(self):
        return self.id


class Section(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "section"

    name = db.Column(db.String(512), default="Название раздела")
    description = db.Column(db.String(512), default="")
    timer = db.Column(db.Integer, default=30)
    test_id = db.Column(db.Integer, db.ForeignKey("test.id"))
    is_exam = db.Column(db.Boolean, default=False)

    test = db.relationship("Test", back_populates="sections")
    questions = db.relationship("Question", back_populates="section")
    quiz_sessions = db.relationship("QuizSession", back_populates="section")

    __table_args__ = (db.Index("section_test_id_is_deleted", "test_id", "is_deleted"),)

    def __str__(self):
        return self.name

    def get_id(self):
        return self.id


class Question(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "question"

    text = db.Column(db.String(1024), default="", nullable=False)

    # 0 -- practice
    # 1 -- variable
    # 2 -- sorting
    # 3 -- matching
    question_type = db.Column(db.Integer, default=1, nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey(Section.id))

    explanation = db.Column(db.String(512), default="")

    section = db.relationship("Section", uselist=False, back_populates="questions")

    practice_question = db.relationship(
        "PracticeQuestion", uselist=False, back_populates="question"
    )
    session_questions = db.relationship("SessionQuestion", back_populates="question")

    answers = db.relationship("Answer", back_populates="question")

    category_id = db.Column(db.Integer, db.ForeignKey("question_category.id"))

    __table_args__ = (
        db.Index("question_section_id_is_deleted_ind", "section_id", "is_deleted"),
    )


class QuizSession(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "quiz_session"

    guid = db.Column(db.String(512), default=lambda: str(uuid.uuid4()))

    section_id = db.Column(db.Integer, db.ForeignKey(Section.id))
    finished_at = db.Column(db.DateTime)

    section = db.relationship("Section", back_populates="quiz_sessions")
    sessions = db.relationship("SessionQuestion", back_populates="quiz_session")


class SessionQuestion(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "session_question"

    quiz_session_id = db.Column(db.Integer, db.ForeignKey(QuizSession.id))
    question_id = db.Column(db.Integer, db.ForeignKey(Question.id))
    is_correct = db.Column(db.Boolean)
    score = db.Column(db.Integer, default=0)
    max_score = db.Column(db.Integer, default=0)

    quiz_session = db.relationship("QuizSession", back_populates="sessions")
    question = db.relationship("Question", back_populates="session_questions")


class Answer(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "answer"

    variant = db.Column(db.String(512), default="", nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, nullable=True)
    left = db.Column(db.String(512), default="", nullable=True)
    right = db.Column(db.String(512), default="", nullable=True)

    question_id = db.Column(db.Integer, db.ForeignKey(Question.id))

    question = db.relationship("Question", back_populates="answers")


class PracticeQuestion(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "practice_question"

    id = db.Column(db.Integer, db.ForeignKey("question.id"), primary_key=True)
    start_configuration = db.Column(db.String(512), db.ForeignKey("network.guid"))

    description = db.Column(db.String(512), default="")
    available_host = db.Column(db.Integer, default=0)
    available_l2_switch = db.Column(db.Integer, default=0)
    available_l1_hub = db.Column(db.Integer, default=0)
    available_l3_router = db.Column(db.Integer, default=0)
    available_server = db.Column(db.Integer, default=0)
    requirements = db.Column(db.JSON, default={})

    question = db.relationship(
        "Question", uselist=False, back_populates="practice_question"
    )


# Table for question categories.
class QuestionCategory(db.Model):  # type:ignore[name-defined]
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1024), nullable=False, default="Тестовая категория")

    def __repr__(self):
        return self.id

    def __str__(self):
        return self.name

    def get_id(self):
        return self.id