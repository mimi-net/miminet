from sqlalchemy import func
from markupsafe import Markup

from miminet_model import User, db
from quiz.service.session_question_service import is_answer_available
from quiz.entity.entity import (
    Question,
    QuizSession,
    SessionQuestion,
    Section,
    QuestionCategory,
)
from quiz.util.dto import SessionResultDto, get_question_type
import json
import random


def _humanize_text(value):
    if value is None:
        return ""
    return str(Markup.unescape(value))


def _format_answer_items(question_type: str, answer_value):
    if not answer_value:
        return []

    if question_type == "variable":
        if not isinstance(answer_value, list):
            return []

        return [
            _humanize_text(item.get("variant"))
            for item in answer_value
            if isinstance(item, dict) and item.get("variant")
        ]

    if question_type == "sorting":
        if isinstance(answer_value, dict):
            try:
                ordered_items = sorted(answer_value.items(), key=lambda item: int(item[0]))
            except (TypeError, ValueError):
                ordered_items = answer_value.items()

            return [
                f"{index + 1}. {_humanize_text(value)}"
                for index, (_, value) in enumerate(ordered_items)
                if value not in (None, "")
            ]

        if isinstance(answer_value, list):
            return [
                f"{index + 1}. {_humanize_text(value)}"
                for index, value in enumerate(answer_value)
                if value not in (None, "")
            ]

        return []

    if question_type == "matching":
        if not isinstance(answer_value, list):
            return []

        items = []
        for pair in answer_value:
            if not isinstance(pair, dict):
                continue

            left = _humanize_text(pair.get("left"))
            right = _humanize_text(pair.get("right"))
            if left or right:
                items.append(f"{left} -> {right}")

        return items

    return []


def _get_correct_answer_items(question: Question):
    question_type = get_question_type(question.question_type)
    answers = [
        answer for answer in question.answers if not getattr(answer, "is_deleted", False)
    ]

    if question_type == "variable":
        ordered_answers = sorted(
            (answer for answer in answers if answer.is_correct),
            key=lambda item: item.id,
        )
        return [
            _humanize_text(answer.variant)
            for answer in ordered_answers
            if answer.variant
        ]

    if question_type == "sorting":
        ordered_answers = sorted(
            answers,
            key=lambda item: (
                item.position is None,
                item.position if item.position is not None else 0,
                item.id,
            ),
        )
        return [
            f"{index + 1}. {_humanize_text(answer.variant)}"
            for index, answer in enumerate(ordered_answers)
            if answer.variant
        ]

    if question_type == "matching":
        ordered_answers = sorted(
            answers,
            key=lambda item: (
                _humanize_text(item.left),
                _humanize_text(item.right),
                item.id,
            ),
        )
        return [
            f"{_humanize_text(answer.left)} -> {_humanize_text(answer.right)}"
            for answer in ordered_answers
            if answer.left or answer.right
        ]

    return []


def _build_answer_details(session_question: SessionQuestion, include_answer_details: bool):
    question_type = get_question_type(session_question.question.question_type)
    if question_type == "practice" or not include_answer_details:
        return None

    correct_answer_items = _get_correct_answer_items(session_question.question)
    user_answer_items = _format_answer_items(question_type, session_question.user_answer)
    has_saved_answer = session_question.user_answer is not None
    user_answer_title = "Ваше решение"

    if not user_answer_items and session_question.is_correct and correct_answer_items:
        user_answer_items = list(correct_answer_items)
        user_answer_title = "Ваше решение (восстановлено)"
    elif not user_answer_items and (has_saved_answer or session_question.is_correct is False):
        user_answer_items = ["Ответ пользователя недоступен для этой попытки."]

    show_reference_answer = session_question.is_correct is False and bool(correct_answer_items)
    if not user_answer_items and not show_reference_answer:
        return None

    return {
        "has_preview": True,
        "user_answer_title": user_answer_title,
        "user_answer_items": user_answer_items,
        "correct_answer_title": "Правильный ответ",
        "correct_answer_items": correct_answer_items if show_reference_answer else [],
        "show_reference_answer": show_reference_answer,
    }


def _serialize_session_question(
    session_question: SessionQuestion, include_answer_details: bool
):
    question = session_question.question
    question_type = get_question_type(question.question_type)

    return {
        "id": session_question.id,
        "quiz_session_id": session_question.quiz_session_id,
        "question_id": session_question.question_id,
        "question_text": str(question.text or ""),
        "question_type": question_type,
        "is_correct": session_question.is_correct if include_answer_details else None,
        "score": session_question.score if include_answer_details else None,
        "max_score": session_question.max_score if include_answer_details else None,
        "network_guid": session_question.network_guid,
        "answer_details": _build_answer_details(
            session_question, include_answer_details
        ),
    }


def _build_question_results(quiz_session: QuizSession, include_answer_details: bool):
    results = sorted(quiz_session.sessions, key=lambda item: item.id)

    return [
        _serialize_session_question(
            session_question, include_answer_details=include_answer_details
        )
        for session_question in results
    ]


def start_session(section_id: str, user: User):
    section = Section.query.filter_by(id=section_id).first()
    if section is None or section.is_deleted:
        return None, None, 404

    quiz_session = QuizSession()
    quiz_session.created_by_id = user.id
    quiz_session.section_id = section_id
    db.session.add(quiz_session)

    if section.meta_description:
        for category_name, question_number in json.loads(
            section.meta_description
        ).items():
            category = QuestionCategory.query.filter_by(name=category_name).first()
            if not category:
                continue
            category_questions = Question.query.filter_by(
                category_id=category.id, is_deleted=False
            ).all()

            random_questions_list = random.sample(category_questions, question_number)

            for question in random_questions_list:
                session_question = SessionQuestion()
                session_question.question = question
                session_question.created_by_id = user.id
                session_question.quiz_session = quiz_session
                db.session.add(session_question)
    else:
        questions = Question.query.filter_by(
            section_id=section_id, is_deleted=False
        ).all()

        for question in questions:
            session_question = SessionQuestion()
            session_question.question = question
            session_question.created_by_id = user.id
            session_question.quiz_session = quiz_session
            db.session.add(session_question)

    db.session.commit()

    return (
        quiz_session.id,
        [sq.id for sq in quiz_session.sessions],  # type:ignore[attr-defined]
        201,
    )


def finish_session(quiz_session_id: str, user: User):
    quiz_session = QuizSession.query.filter_by(id=quiz_session_id).first()

    if quiz_session.created_by_id != user.id:
        return 403
    elif quiz_session is None:
        return 404

    quiz_session.finished_at = func.now()

    db.session.commit()

    return 200


def finish_old_sessions(user):
    unfinished_sessions = (
        QuizSession.query.filter_by(created_by_id=user.id, is_deleted=False)
        .filter(QuizSession.finished_at.is_(None))
        .all()
    )

    if not unfinished_sessions:
        return 204

    for qs in unfinished_sessions:
        section = qs.section
        test = section.test

        if section.timer == 0 and not test.is_retakeable:
            db.session.delete(qs)
        else:
            qs.finished_at = func.now()

    db.session.commit()
    return 200


def session_result(quiz_session_id: str):
    quiz_session = QuizSession.query.filter_by(id=quiz_session_id).first()

    if quiz_session.finished_at is None:
        return None, 403

    theory_questions = [
        q for q in quiz_session.sessions if q.question.question_type != 0
    ]

    practice_questions = [
        q for q in quiz_session.sessions if q.question.question_type == 0
    ]

    theory_count = len(theory_questions)

    time_spent = str(quiz_session.finished_at - quiz_session.created_on).split(".")[0]

    is_exam = quiz_session.section.is_exam
    answer_available = is_answer_available(quiz_session.section)
    available_from = quiz_session.section.results_available_from
    include_answer_details = not (is_exam and not answer_available)

    if is_exam and not answer_available:
        theory_correct = 0
    else:
        theory_correct = sum(1 for q in theory_questions if q.is_correct)

    if is_exam and not answer_available:
        practice_results = [
            {
                "question_id": q.question.id,
                "score": 0,
                "max_score": q.max_score,
                "network_guid": q.network_guid,
            }
            for q in practice_questions
        ]
    else:
        practice_results = [
            {
                "question_id": q.question.id,
                "score": q.score,
                "max_score": q.max_score,
                "network_guid": q.network_guid,
            }
            for q in practice_questions
        ]

    return {
        "test_name": quiz_session.section.test.name,
        "section_name": quiz_session.section.name,
        "time_spent": time_spent,
        "theory_correct": theory_correct,
        "theory_count": theory_count,
        "practice_results": practice_results,
        "results": _build_question_results(
            quiz_session, include_answer_details=include_answer_details
        ),
        "is_exam": is_exam,
        "answer_available": answer_available,
        "results_available_from": available_from,
    }, 200


def get_result_by_session_guid(session_guid: str):
    quiz_session = QuizSession.query.filter_by(guid=session_guid).first()

    if quiz_session is None:
        return None, 404

    result, status = session_result(quiz_session.id)

    if result is None:
        return None, status

    session_data = SessionResultDto(
        test_name=result["test_name"],
        section_name=result["section_name"],
        theory_correct=result["theory_correct"],
        theory_count=result["theory_count"],
        practice_results=result["practice_results"],
        results=result["results"],
        start_time=quiz_session.created_on.strftime("%m/%d/%Y, %H:%M:%S"),
        time_spent=result["time_spent"],
        is_exam=result["is_exam"],
        answer_available=result["answer_available"],
        available_from=result["results_available_from"],
    )

    return session_data, status
