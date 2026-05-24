import uuid

from miminet_model import db
from sqlalchemy import TIMESTAMP, BigInteger, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func


class AiInterviewSetting(db.Model):  # type: ignore[name-defined]
    __tablename__ = "ai_interview_setting"

    id = db.Column(BigInteger, primary_key=True)
    is_ai_test_enabled = db.Column(Boolean, default=False, nullable=False)
    llm_proxy_enabled = db.Column(Boolean, default=False, nullable=False)
    llm_proxy_url = db.Column(Text, nullable=True)
    llm_proxy_env_fallback_enabled = db.Column(Boolean, default=True, nullable=False)
    llm_proxy_check_status = db.Column(Text, nullable=True)
    llm_proxy_check_message = db.Column(Text, nullable=True)
    llm_proxy_check_ip = db.Column(Text, nullable=True)
    llm_proxy_checked_at = db.Column(TIMESTAMP(timezone=True), nullable=True)
    llm_provider_check_status = db.Column(Text, nullable=True)
    llm_provider_check_message = db.Column(Text, nullable=True)
    llm_provider_checked_at = db.Column(TIMESTAMP(timezone=True), nullable=True)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    updated_on = db.Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )

    def __str__(self):
        return "AI interview settings"


def create_ai_interview_tables():
    for table in (
        AiInterviewSetting.__table__,
        AiInterviewAccessCode.__table__,
        AiInterviewAttempt.__table__,
        AiInterviewSession.__table__,
        AiInterviewTurn.__table__,
    ):
        table.create(db.engine, checkfirst=True)


class AiInterviewAccessCode(db.Model):  # type: ignore[name-defined]
    __tablename__ = "ai_interview_access_code"

    id = db.Column(BigInteger, primary_key=True)
    code = db.Column(Text, nullable=False, unique=True)
    label = db.Column(Text, nullable=True)
    is_active = db.Column(Boolean, default=True, nullable=False)
    created_by_id = db.Column(BigInteger, ForeignKey("user.id"), nullable=True)
    expires_at = db.Column(TIMESTAMP(timezone=True), nullable=False)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    updated_on = db.Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )

    attempts = db.relationship(
        "AiInterviewAttempt",
        back_populates="access_code",
        order_by="AiInterviewAttempt.created_on",
    )

    def __str__(self):
        return self.code or self.label or f"AI access code {self.id}"


class AiInterviewAttempt(db.Model):  # type: ignore[name-defined]
    __tablename__ = "ai_interview_attempt"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "access_code_id",
            name="uq_ai_interview_attempt_user_access_code_model",
        ),
    )

    id = db.Column(BigInteger, primary_key=True)
    user_id = db.Column(BigInteger, ForeignKey("user.id"), nullable=False)
    access_code_id = db.Column(
        BigInteger, ForeignKey("ai_interview_access_code.id"), nullable=True
    )
    status = db.Column(Text, default="ready", nullable=False)
    reset_by_id = db.Column(BigInteger, ForeignKey("user.id"), nullable=True)
    reset_on = db.Column(TIMESTAMP(timezone=True), nullable=True)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    updated_on = db.Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )

    sessions = db.relationship(
        "AiInterviewSession",
        back_populates="attempt",
        order_by="AiInterviewSession.created_on",
    )
    access_code = db.relationship("AiInterviewAccessCode", back_populates="attempts")

    def __str__(self):
        return f"AI attempt for user {self.user_id}"


class AiInterviewSession(db.Model):  # type: ignore[name-defined]
    __tablename__ = "ai_interview_session"

    id = db.Column(BigInteger, primary_key=True)
    guid = db.Column(Text, default=lambda: str(uuid.uuid4()), nullable=False, unique=True)
    attempt_id = db.Column(
        BigInteger, ForeignKey("ai_interview_attempt.id"), nullable=False
    )
    status = db.Column(Text, default="active", nullable=False)
    selected_topics = db.Column(db.JSON, default=list, nullable=False)
    topic_schedule = db.Column(db.JSON, default=list, nullable=False)
    final_result = db.Column(db.JSON, nullable=True)
    provider_name = db.Column(Text, nullable=False)
    llm_call_count = db.Column(BigInteger, default=0, nullable=False)
    finished_at = db.Column(TIMESTAMP(timezone=True), nullable=True)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    updated_on = db.Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )

    attempt = db.relationship("AiInterviewAttempt", back_populates="sessions")
    turns = db.relationship(
        "AiInterviewTurn",
        back_populates="session",
        order_by="AiInterviewTurn.position",
        cascade="all, delete-orphan",
    )

    def __str__(self):
        return f"AI interview session {self.guid}"


class AiInterviewTurn(db.Model):  # type: ignore[name-defined]
    __tablename__ = "ai_interview_turn"
    __table_args__ = (
        UniqueConstraint("session_id", "position", name="uq_ai_interview_turn_position"),
    )

    id = db.Column(BigInteger, primary_key=True)
    session_id = db.Column(
        BigInteger, ForeignKey("ai_interview_session.id"), nullable=False
    )
    position = db.Column(BigInteger, nullable=False)
    topic_key = db.Column(Text, nullable=False)
    focus = db.Column(db.JSON, default=dict, nullable=False)
    question = db.Column(Text, nullable=False)
    expected_concepts = db.Column(db.JSON, default=list, nullable=False)
    answer = db.Column(Text, nullable=True)
    feedback = db.Column(Text, nullable=True)
    answer_summary = db.Column(Text, nullable=True)
    analysis = db.Column(db.JSON, nullable=True)
    generation_rag = db.Column(db.JSON, default=dict, nullable=False)
    evaluation_rag = db.Column(db.JSON, default=dict, nullable=False)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    answered_on = db.Column(TIMESTAMP(timezone=True), nullable=True)

    session = db.relationship("AiInterviewSession", back_populates="turns")

    def __str__(self):
        return f"AI interview turn {self.position}"
