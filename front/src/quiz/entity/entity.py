import json
import uuid

from sqlalchemy import func, BigInteger, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr
from sqlalchemy.types import TypeDecorator

from miminet_model import db


class GUID(TypeDecorator):
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(Text())

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

    impl = Text

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

    id = db.Column(BigInteger, primary_key=True)


class SoftDeleteMixin(object):
    __table_args__ = ({"extend_existing": True},)

    is_deleted = db.Column(Boolean, default=False)


class TimeMixin(object):
    __table_args__ = ({"extend_existing": True},)

    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    updated_on = db.Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )


class CreatedByMixin(object):
    __table_args__ = ({"extend_existing": True},)

    @declared_attr
    def created_by_id(cls):
        return db.Column("created_by_id", ForeignKey("user.id"))

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

    name = db.Column(Text, default="Название теста")
    description = db.Column(Text, default="")
    is_ready = db.Column(Boolean, default=False)
    is_retakeable = db.Column(Boolean, default=False)

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

    name = db.Column(Text, default="Название раздела")
    description = db.Column(Text, default="")
    timer = db.Column(BigInteger, default=30)
    test_id = db.Column(BigInteger, ForeignKey("test.id"))
    is_exam = db.Column(Boolean, default=False)
    meta_description = db.Column(Text, default="")
    results_available_from = db.Column(TIMESTAMP(timezone=True), nullable=True)

    test = db.relationship("Test", back_populates="sections")
    questions = db.relationship("Question", back_populates="section")
    quiz_sessions = db.relationship("QuizSession", back_populates="section")

    __table_args__ = (db.Index("section_test_id_is_deleted", "test_id", "is_deleted"),)

    def __str__(self):
        return self.name

    def get_id(self):
        return self.id


class QuestionImage(db.Model):  # type:ignore[name-defined]
    __tablename__ = "question_image"
    id = db.Column(BigInteger, primary_key=True)
    question_id = db.Column(BigInteger, ForeignKey("question.id"))
    file_path = db.Column(Text)

    question = db.relationship("Question", back_populates="images")


class Question(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "question"

    text = db.Column(Text, default="", nullable=False)

    # 0 -- practice
    # 1 -- variable
    # 2 -- sorting
    # 3 -- matching
    question_type = db.Column(BigInteger, default=1, nullable=False)
    section_id = db.Column(BigInteger, ForeignKey(Section.id))

    explanation = db.Column(Text, default="")

    section = db.relationship("Section", uselist=False, back_populates="questions")

    practice_question = db.relationship(
        "PracticeQuestion", uselist=False, back_populates="question"
    )
    session_questions = db.relationship("SessionQuestion", back_populates="question")

    answers = db.relationship("Answer", back_populates="question")
    images = db.relationship("QuestionImage", back_populates="question")

    category_id = db.Column(BigInteger, ForeignKey("question_category.id"))

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

    guid = db.Column(Text, default=lambda: str(uuid.uuid4()))

    section_id = db.Column(BigInteger, ForeignKey(Section.id))
    finished_at = db.Column(TIMESTAMP(timezone=True))

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

    quiz_session_id = db.Column(BigInteger, ForeignKey(QuizSession.id))
    question_id = db.Column(BigInteger, ForeignKey(Question.id))
    is_correct = db.Column(Boolean)
    score = db.Column(BigInteger, default=0)
    max_score = db.Column(BigInteger, default=0)

    network_guid = db.Column(Text, nullable=True)

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

    variant = db.Column(Text, default="", nullable=False)
    is_correct = db.Column(Boolean, default=False)
    position = db.Column(BigInteger, nullable=True)
    left = db.Column(Text, default="", nullable=True)
    right = db.Column(Text, default="", nullable=True)

    question_id = db.Column(BigInteger, ForeignKey(Question.id))

    question = db.relationship("Question", back_populates="answers")


class PracticeQuestion(
    IdMixin,
    SoftDeleteMixin,
    TimeMixin,
    CreatedByMixin,
    db.Model,  # type:ignore[name-defined]
):
    __tablename__ = "practice_question"

    id = db.Column(BigInteger, ForeignKey("question.id"), primary_key=True)
    start_configuration = db.Column(Text, ForeignKey("network.guid"))

    description = db.Column(Text, default="")
    available_host = db.Column(BigInteger, default=0)
    available_l2_switch = db.Column(BigInteger, default=0)
    available_l1_hub = db.Column(BigInteger, default=0)
    available_l3_router = db.Column(BigInteger, default=0)
    available_server = db.Column(BigInteger, default=0)
    requirements = db.Column(db.JSON, default={})

    question = db.relationship(
        "Question", uselist=False, back_populates="practice_question"
    )


# Table for question categories.
class QuestionCategory(db.Model):  # type:ignore[name-defined]
    id = db.Column(BigInteger, primary_key=True)
    name = db.Column(Text, nullable=False, default="Тестовая категория")

    def __repr__(self):
        return self.id

    def __str__(self):
        return self.name

    def get_id(self):
        return self.id
