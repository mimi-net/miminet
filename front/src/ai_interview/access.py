import secrets
from datetime import datetime, timedelta, timezone

from ai_interview.errors import InterviewError, InterviewUnavailable
from ai_interview.models import (
    AiInterviewAccessCode,
    AiInterviewSession,
)
from miminet_model import db


ACCESS_CODE_TTL_DAYS = 5


def now_utc():
    return datetime.now(timezone.utc)


def normalize_access_code(code):
    return "".join(ch for ch in str(code or "") if ch.isdigit())


def generate_numeric_access_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _expires_at_utc(access_code):
    expires_at = access_code.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at


def delete_access_code(access_code):
    db.session.query(AiInterviewSession).filter_by(
        access_code_id=access_code.id
    ).update(
        {"access_code_id": None},
        synchronize_session=False,
    )
    db.session.delete(access_code)


def cleanup_expired_access_codes(commit=True):
    expired_codes = AiInterviewAccessCode.query.filter(
        AiInterviewAccessCode.expires_at <= now_utc()
    ).all()
    for access_code in expired_codes:
        delete_access_code(access_code)
    if expired_codes and commit:
        db.session.commit()
    return len(expired_codes)


def create_access_code(label=None, days_valid=ACCESS_CODE_TTL_DAYS):
    cleanup_expired_access_codes()
    days_valid = max(1, int(days_valid or ACCESS_CODE_TTL_DAYS))

    for _ in range(20):
        code = generate_numeric_access_code()
        if AiInterviewAccessCode.query.filter_by(code=code).first() is None:
            access_code = AiInterviewAccessCode(
                code=code,
                label=str(label or "").strip() or None,
                expires_at=now_utc() + timedelta(days=days_valid),
                is_active=True,
            )
            db.session.add(access_code)
            db.session.commit()
            return code, access_code

    raise InterviewError("Не удалось сгенерировать уникальный код доступа.")


def _access_code_is_current(access_code):
    expires_at = _expires_at_utc(access_code)
    return access_code.is_active and expires_at is not None and expires_at > now_utc()


def find_valid_access_code(code):
    normalized = normalize_access_code(code)
    if len(normalized) != 6:
        raise InterviewError("Код доступа должен состоять из 6 цифр.")

    cleanup_expired_access_codes()
    access_code = AiInterviewAccessCode.query.filter_by(code=normalized).first()
    if access_code is None:
        raise InterviewUnavailable("Код доступа не найден.")
    if not access_code.is_active:
        raise InterviewUnavailable("Код доступа отключен преподавателем.")
    if not _access_code_is_current(access_code):
        raise InterviewUnavailable("Срок действия кода доступа истек.")
    return access_code
