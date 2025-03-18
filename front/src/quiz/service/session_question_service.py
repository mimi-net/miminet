import json
from markupsafe import Markup

from miminet_model import User, db
from quiz.service.check_practice_service import check_task
from quiz.entity.entity import (
    SessionQuestion,
    Answer,
    PracticeQuestion,
)
from quiz.util.dto import (
    QuestionDto,
    AnswerResultDto,
    PracticeAnswerResultDto,
    calculate_max_score,
)


def get_question_by_session_question_id(session_question_id: str):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()
    question = session_question.question

    if question is None or question.is_deleted:
        return None, 404

    section = question.section
    is_exam = section.is_exam if section else False

    return QuestionDto(session_question.created_by_id, question), is_exam, 200


def answer_on_session_question(
    session_question_id: str, answer_string: dict, user: User
):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()
    if session_question.created_by_id != user.id:
        return None, 403
    question = session_question.question

    # practice
    if question.question_type == 0:
        practice_question = PracticeQuestion.query.get(question.id)
        requirements = (
            json.loads(practice_question.requirements)
            if isinstance(practice_question.requirements, str)
            else practice_question.requirements
        )

        max_score = calculate_max_score(requirements)
        score, hints = check_task(requirements, answer_string["answer"])

        if score != max_score and len(hints) == 0:
            hints.append("По вашему решению не предусмотрены подсказки.")

        session_question.is_correct = score == max_score
        session_question.score = score
        session_question.max_score = max_score

        db.session.add(session_question)
        db.session.commit()

        return (
            PracticeAnswerResultDto(score, question.explanation, max_score, hints),
            200,
        )

    # variable
    if question.question_type == 1:
        answers = answer_string["answer"]
        is_correct = True
        for check in answers:
            answer = Answer.query.filter_by(
                question_id=question.id,
                variant=Markup.escape(check["variant"]),
            ).first()
            if not answer or not answer.is_correct:
                is_correct = False

        correct_count = Answer.query.filter_by(
            question_id=question.id, is_correct=True
        ).count()
        correct = is_correct and len(answers) == correct_count
        session_question.is_correct = correct
        db.session.add(session_question)
        db.session.commit()

        return AnswerResultDto(question.explanation, correct), 200

    # sorting
    if question.question_type == 2:
        answer = sorted(answer_string["answer"].items(), key=lambda x: int(x[0]))

        answers = Answer.query.filter_by(question_id=question.id).all()
        answer_set = sorted({(answer.position, answer.variant) for answer in answers})

        correct = (
            True
            if [value for key, value in answer] == [value for key, value in answer_set]
            else False
        )
        session_question.is_correct = correct
        db.session.add(session_question)
        db.session.commit()

        return AnswerResultDto(question.explanation, correct), 200

    # matching
    if question.question_type == 3:
        answers = Answer.query.filter_by(question_id=question.id).all()
        set1 = {(answer.left, answer.right) for answer in answers}
        set2 = set((item["left"], item["right"]) for item in answer_string["answer"])

        correct = set1 == set2
        session_question.is_correct = correct
        db.session.add(session_question)
        db.session.commit()

        return AnswerResultDto(question.explanation, correct), 200
