from sqlalchemy import func

from miminet_model import User, db
from quiz.entity.entity import Question, QuizSession, SessionQuestion, Section
from quiz.util.dto import SessionResultDto


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
