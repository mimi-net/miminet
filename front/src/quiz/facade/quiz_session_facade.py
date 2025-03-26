import logging

from sqlalchemy import func

from miminet_model import User, db
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
    test = section.test
    if section is None or section.is_deleted:
        return None, None, 404
    if (
        not test.is_retakeable
        and QuizSession.query.filter_by(
            section_id=section_id, created_by_id=user.id, is_deleted=False
        ).first()
        is not None
    ):
        return None, None, 403
    quiz_session = QuizSession()
    quiz_session.created_by_id = user.id
    quiz_session.section_id = section_id
    db.session.add(quiz_session)

    if section.meta_description:
        for category_name, question_number in json.loads(
            section.meta_description
        ).items():
            category = QuestionCategory.query.filter_by(name=category_name).first()
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

    return quiz_session.id, [i.id for i in quiz_session.sessions], 201  # type: ignore


def finish_session(quiz_session_id: str, user: User):
    quiz_session = QuizSession.query.filter_by(id=quiz_session_id).first()

    if quiz_session.created_by_id != user.id:
        return 403
    elif quiz_session is None:
        return 404

    quiz_session.finished_at = func.now()

    db.session.commit()

    return 200


def session_result(quiz_session_id: str):
    quiz_session = QuizSession.query.filter_by(id=quiz_session_id).first()

    if quiz_session.finished_at is None:
        return None, None, None, 403

    theory_questions = [
        q for q in quiz_session.sessions if q.question.question_type != 0
    ]

    practice_questions = [
        q for q in quiz_session.sessions if q.question.question_type == 0
    ]

    theory_correct = sum(1 for q in theory_questions if q.is_correct)
    theory_count = len(theory_questions)

    practice_results = [
        {
            "question_id": q.question.id,
            "score": q.score,
            "max_score": q.max_score,
        }
        for q in practice_questions
    ]

    time_spent = str(quiz_session.finished_at - quiz_session.created_on).split(".")[0]

    return {
        "time_spent": time_spent,
        "theory_correct": theory_correct,
        "theory_count": theory_count,
        "practice_results": practice_results,
    }, 200


def get_result_by_session_guid(session_guid: str):
    quiz_session = QuizSession.query.filter_by(guid=session_guid).first()

    if quiz_session is None:
        return None, None, 404

    results = SessionQuestion.query.filter_by(quiz_session_id=quiz_session.id).all()
    result, status = session_result(quiz_session.id)

    question_results = [{
        "id": sq.id,
        "quiz_session_id": sq.quiz_session_id,
        "question_id": sq.question_id,
        "question_text": sq.question.text,  
        "is_correct": sq.is_correct,
        "score": sq.score,
        "max_score": sq.max_score
    } for sq in results]
    
    session_data = SessionResultDto(
        test_name=quiz_session.section.test.name,
        section_name=quiz_session.section.name,
        theory_correct=result["theory_correct"],
        theory_count=result["theory_count"],
        practice_results=result["practice_results"],
        results=question_results,  
        start_time=quiz_session.created_on.strftime("%m/%d/%Y, %H:%M:%S"),
        time_spent=result["time_spent"],
    )

    return session_data, status

