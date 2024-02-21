import json
import uuid
from datetime import datetime

from sqlalchemy import types
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import declared_attr

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

    id = db.Column(db.String(511), primary_key=True, default=lambda: str(uuid.uuid4()))


class SoftDeleteMixin(object):

    __table_args__ = ({"extend_existing": True},)

    is_deleted = db.Column(db.Boolean, default=False)


class TimeMixin(object):

    __table_args__ = ({"extend_existing": True},)

    created_on = db.Column(db.DateTime, default=datetime.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=datetime.now())


class CreatedByMixin(object):

    __table_args__ = ({"extend_existing": True},)

    @declared_attr
    def created_by_id(cls):
        return db.Column("created_by_id", db.ForeignKey("user.id"))

    @declared_attr
    def created_by_user(cls):
        return db.relationship("User")


class Test(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "test"

    name = db.Column(db.String(511), default="")
    description = db.Column(db.String(511), default="")
    is_ready = db.Column(db.Boolean, default=False)
    is_retakeable = db.Column(db.Boolean, default=False)

    sections = db.relationship("Section", back_populates="test")

    __table_args__ = (
        db.Index("test_id_is_deleted_ind", "id", "is_deleted"),
        db.Index("test_created_by_id_is_deleted_ind", "created_by_id", "is_deleted"),
    )


class Section(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "section"

    name = db.Column(db.String(511), default="")
    description = db.Column(db.String(511), default="")
    timer = db.Column(db.DateTime, default=db.func.now())
    test_id = db.Column(db.ForeignKey("test.id"))

    test = db.relationship("Test", back_populates="sections")
    questions = db.relationship("Question", back_populates="section")
    quiz_sessions = db.relationship("QuizSession", back_populates="section")

    __table_args__ = (db.Index("section_test_id_is_deleted", "test_id", "is_deleted"),)


class Question(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "question"

    question_text = db.Column(db.String(511), default="")
    question_type = db.Column(db.String(31), default="")
    section_id = db.Column(db.String(511), db.ForeignKey(Section.id))

    section = db.relationship("Section", uselist=False, back_populates="questions")

    text_question = db.relationship(
        "TextQuestion", uselist=False, back_populates="question"
    )
    practice_question = db.relationship(
        "PracticeQuestion", uselist=False, back_populates="question"
    )

    session_questions = db.relationship("SessionQuestion", back_populates="question")

    __table_args__ = (
        db.Index("question_section_id_is_deleted_ind", "section_id", "is_deleted"),
    )


class QuizSession(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "quiz_session"

    section_id = db.Column(db.String(512), db.ForeignKey(Section.id))
    finished_at = db.Column(db.DateTime)

    section = db.relationship("Section", back_populates="quiz_sessions")
    sessions = db.relationship("SessionQuestion", back_populates="quiz_session")


class SessionQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "session_question"

    quiz_session_id = db.Column(db.String(511), db.ForeignKey(QuizSession.id))
    question_id = db.Column(db.String(511), db.ForeignKey(Question.id))
    is_correct = db.Column(db.Boolean)

    quiz_session = db.relationship("QuizSession", back_populates="sessions")
    question = db.relationship("Question", back_populates="session_questions")


class TextQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "text_question"

    id = db.Column(db.String(511), db.ForeignKey(Question.id), primary_key=True)
    text_type = db.Column(db.String(31), default="")

    question = db.relationship("Question", back_populates="text_question")
    sorting_question = db.relationship(
        "SortingQuestion", uselist=False, back_populates="text_question"
    )
    variable_question = db.relationship(
        "VariableQuestion", uselist=False, back_populates="text_question"
    )
    matching_question = db.relationship(
        "MatchingQuestion", uselist=False, back_populates="text_question"
    )


class SortingQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "sorting_question"

    id = db.Column(db.String(511), db.ForeignKey("text_question.id"), primary_key=True)
    right_sequence = db.Column(db.UnicodeText, default="")
    explanation = db.Column(db.String(511), default="")

    text_question = db.relationship("TextQuestion", back_populates="sorting_question")


class MatchingQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "matching_question"

    id = db.Column(db.String(512), db.ForeignKey("text_question.id"), primary_key=True)
    map = db.Column(Json(), default="")
    explanation = db.Column(db.String(511), default="")

    text_question = db.relationship("TextQuestion", back_populates="matching_question")


class VariableQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "variable_question"

    id = db.Column(db.String(512), db.ForeignKey("text_question.id"), primary_key=True)

    answers = db.relationship("Answer", back_populates="variable_question")
    text_question = db.relationship("TextQuestion", back_populates="variable_question")


class Answer(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "answer"

    answer_text = db.Column(db.String(511), default="")
    explanation = db.Column(db.String(511), default="")
    is_correct = db.Column(db.Boolean, default=False)

    variable_question_id = db.Column(
        db.String(511), db.ForeignKey("variable_question.id")
    )
    variable_question = db.relationship("VariableQuestion", back_populates="answers")

    __table_args__ = (
        db.Index(
            "answer_variable_question_id_answer_text_ind",
            "variable_question_id",
            "answer_text",
        ),
        db.Index(
            "answer_variable_question_id_is_correct_ind",
            "variable_question_id",
            "is_correct",
        ),
    )


class PracticeQuestion(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "practice_question"

    id = db.Column(db.String(511), db.ForeignKey("question.id"), primary_key=True)
    start_configuration = db.Column(
        db.String(511), db.ForeignKey("network.guid"), unique=True
    )

    description = db.Column(db.String(511), default="")
    explanation = db.Column(db.String(511), default="")
    available_host = db.Column(db.Integer, default=0)
    available_l2_switch = db.Column(db.Integer, default=0)
    available_l1_hub = db.Column(db.Integer, default=0)
    available_l3_router = db.Column(db.Integer, default=0)
    available_server = db.Column(db.Integer, default=0)

    question = db.relationship(
        "Question", uselist=False, back_populates="practice_question"
    )
    # network = db.relationship('Network', uselist=False, back_populates='practice_question')
    practice_tasks = db.relationship("PracticeTask", back_populates="practice_question")


class PracticeTask(IdMixin, SoftDeleteMixin, TimeMixin, CreatedByMixin, db.Model): # type:ignore[name-defined]

    __tablename__ = "practice_task"

    task = db.Column(db.String(511), default="")

    practice_question_id = db.Column(
        db.String(511), db.ForeignKey("practice_question.id")
    )
    practice_question = db.relationship(
        "PracticeQuestion", back_populates="practice_tasks"
    )
