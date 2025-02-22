from sqlalchemy import func

from miminet_model import User, QuestionCategory, db
from quiz.entity.entity import Question, QuizSession, SessionQuestion, Section
from quiz.util.dto import SessionResultDto
import json
import random


def start_session(section_id: str, user: User):
    section = Section.query.filter_by(id=section_id).first()

    if section is None or section.is_deleted:
        return None, None, 404
    
    test = section.test

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
        for category_name, question_number in json.loads(section.meta_description).items():
            category = QuestionCategory.query.filter_by(name=category_name).first()
            category_questions = Question.query.filter_by(category_id=category.id, is_deleted=False).all()

            if question_number > len(category_questions):
                return None, None, 410

            random_questions_list = random.sample(category_questions, question_number)

            for question in random_questions_list:
                session_question = SessionQuestion()
                session_question.question = question
                session_question.created_by_id = user.id
                session_question.quiz_session = quiz_session
                db.session.add(session_question)
    else:
        questions = Question.query.filter_by(section_id=section_id, is_deleted=False).all()

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
    correct = 0
    if quiz_session.finished_at is None:
        return None, None, None, 403
    question_count = len(quiz_session.sessions)
    time_spent = str(quiz_session.finished_at - quiz_session.created_on).split(".")[0]
    for question in list(
        filter(lambda x: x.is_correct is not None, quiz_session.sessions)
    ):
        if question.is_correct:
            correct += 1
    return correct, question_count, time_spent, 200


def get_result_by_session_guid(session_guid: str):
    quiz_session = QuizSession.query.filter_by(guid=session_guid).first()
    result = session_result(quiz_session.id)

    session_data = SessionResultDto(
        quiz_session.section.test.name,
        quiz_session.section.name,
        result[0],
        result[1],
        quiz_session.created_on.strftime("%m/%d/%Y, %H:%M:%S"),
        str(result[2]),
    )

    session_questions = SessionQuestion.query.filter_by(
        quiz_session_id=quiz_session.id
    ).all()
    questions_result = [
        {
            "question_text": question.question.text,
            "is_correct": str(question.is_correct),
        }
        for question in session_questions
    ]

    return session_data, questions_result, 200
