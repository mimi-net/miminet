from sqlalchemy import func

from miminet_model import User, db
from quiz.service.session_question_service import is_answer_available
from quiz.entity.entity import (
    Question,
    QuizSession,
    SessionQuestion,
    Section,
    QuestionCategory,
)
from quiz.util.dto import SessionResultDto
import json
import random


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


def finish_old_session(quiz_session_id: str, user: User):
    quiz_session = QuizSession.query.filter_by(id=quiz_session_id).first()

    if not quiz_session:
        return 404
    elif quiz_session.created_by_id != user.id:
        return 403
    elif quiz_session is None:
        return 404

    section = quiz_session.section
    test = section.test

    if quiz_session.finished_at is None and section.timer == 0:
        if not test.is_retakeable:
            db.session.delete(quiz_session)
            db.session.commit()
            return 200

    quiz_session.finished_at = func.now()
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
        "time_spent": time_spent,
        "theory_correct": theory_correct,
        "theory_count": theory_count,
        "practice_results": practice_results,
        "is_exam": is_exam,
        "answer_available": answer_available,
        "results_available_from": available_from,
    }, 200


def get_result_by_session_guid(session_guid: str):
    quiz_session = QuizSession.query.filter_by(guid=session_guid).first()

    if quiz_session is None:
        return None, 404

    results = SessionQuestion.query.filter_by(quiz_session_id=quiz_session.id).all()
    result, status = session_result(quiz_session.id)

    if result is None:
        return None, status

    question_results = [
        {
            "id": sq.id,
            "quiz_session_id": sq.quiz_session_id,
            "question_id": sq.question_id,
            "question_text": sq.question.text,
            "is_correct": sq.is_correct,
            "score": sq.score,
            "max_score": sq.max_score,
            "network_guid": sq.network_guid,
        }
        for sq in results
    ]

    is_exam = quiz_session.section.is_exam
    answer_available = is_answer_available(quiz_session.section)
    available_from = quiz_session.section.results_available_from

    session_data = SessionResultDto(
        test_name=quiz_session.section.test.name,
        section_name=quiz_session.section.name,
        theory_correct=result["theory_correct"],
        theory_count=result["theory_count"],
        practice_results=result["practice_results"],
        results=question_results,
        start_time=quiz_session.created_on.strftime("%m/%d/%Y, %H:%M:%S"),
        time_spent=result["time_spent"],
        is_exam=is_exam,
        answer_available=answer_available,
        available_from=available_from,
    )

    return session_data, status
