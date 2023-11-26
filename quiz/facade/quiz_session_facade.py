from datetime import datetime

from miminet_model import User, db
from quiz.entity.entity import Question, QuizSession, SessionQuestion


def start_session(section_id: str, user: User):
    quiz_session = QuizSession()
    quiz_session.created_by_id = user.id
    quiz_session.section_id = section_id
    db.session.add(quiz_session)

    questions = Question.query.filter_by(section_id=section_id).all()

    for question in questions:
        session_question = SessionQuestion()
        session_question.question = question
        session_question.created_by_id = user.id
        session_question.quiz_session = quiz_session
        db.session.add(session_question)
    db.session.commit()

    return [i.id for i in quiz_session.sessions], 201


def finish_session(quiz_session_id: str, user: User):
    quiz_session = QuizSession.query.filter_by(id=quiz_session_id)

    if quiz_session.created_by_id != user.id:
        return None, 405
    elif quiz_session is None:
        return None, 404

    quiz_session.finished_at = datetime.now()

    db.session.add(quiz_session)
    db.session.commit()
