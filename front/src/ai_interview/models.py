import uuid

from miminet_model import db
from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func


class AiInterviewSetting(db.Model):
    __tablename__ = "ai_interview_setting"

    id = db.Column(BigInteger, primary_key=True)
    llm_provider_check_status = db.Column(Text, nullable=True)
    llm_provider_check_message = db.Column(Text, nullable=True)
    llm_provider_checked_at = db.Column(TIMESTAMP(timezone=True), nullable=True)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    updated_on = db.Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )

    def __str__(self):
        return "AI testing settings"


def create_ai_interview_tables():
    for table in (
        AiInterviewSetting.__table__,
        AiInterviewAccessCode.__table__,
        AiInterviewSession.__table__,
        AiInterviewTurn.__table__,
    ):
        table.create(db.engine, checkfirst=True)


class AiInterviewAccessCode(db.Model):
    __tablename__ = "ai_interview_access_code"

    id = db.Column(BigInteger, primary_key=True)
    code = db.Column(Text, nullable=False, unique=True)
    label = db.Column(Text, nullable=True)
    is_active = db.Column(Boolean, default=True, nullable=False)
    is_used = db.Column(Boolean, default=False, nullable=False)
    expires_at = db.Column(TIMESTAMP(timezone=True), nullable=False)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    updated_on = db.Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )

    sessions = db.relationship(
        "AiInterviewSession",
        back_populates="access_code",
        order_by="AiInterviewSession.created_on",
    )

    def __str__(self):
        return self.code or self.label or f"AI access code {self.id}"


class AiInterviewSession(db.Model):
    __tablename__ = "ai_interview_session"
    __table_args__ = (
        UniqueConstraint("access_code_id", name="uq_ai_interview_session_access_code"),
    )

    id = db.Column(BigInteger, primary_key=True)
    guid = db.Column(
        Text, default=lambda: str(uuid.uuid4()), nullable=False, unique=True
    )
    user_id = db.Column(BigInteger, ForeignKey("user.id"), nullable=False)
    access_code_id = db.Column(
        BigInteger, ForeignKey("ai_interview_access_code.id"), nullable=True
    )
    status = db.Column(Text, default="active", nullable=False)
    selected_topics = db.Column(db.JSON, default=list, nullable=False)
    final_result = db.Column(db.JSON, nullable=True)
    finished_at = db.Column(TIMESTAMP(timezone=True), nullable=True)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    updated_on = db.Column(
        TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now()
    )

    access_code = db.relationship("AiInterviewAccessCode", back_populates="sessions")
    turns = db.relationship(
        "AiInterviewTurn",
        back_populates="session",
        order_by="AiInterviewTurn.position",
        cascade="all, delete-orphan",
    )

    def __str__(self):
        return f"AI testing session {self.guid}"


class AiInterviewTurn(db.Model):
    __tablename__ = "ai_interview_turn"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "position", name="uq_ai_interview_turn_position"
        ),
    )

    id = db.Column(BigInteger, primary_key=True)
    session_id = db.Column(
        BigInteger, ForeignKey("ai_interview_session.id"), nullable=False
    )
    position = db.Column(BigInteger, nullable=False)
    topic_key = db.Column(Text, nullable=False)
    focus = db.Column(db.JSON, default=dict, nullable=False)
    question = db.Column(Text, nullable=False)
    answer = db.Column(Text, nullable=True)
    feedback = db.Column(Text, nullable=True)
    analysis = db.Column(db.JSON, nullable=True)
    created_on = db.Column(TIMESTAMP(timezone=True), default=func.now())
    answered_on = db.Column(TIMESTAMP(timezone=True), nullable=True)

    session = db.relationship("AiInterviewSession", back_populates="turns")

    def __str__(self):
        return f"AI testing turn {self.position}"
