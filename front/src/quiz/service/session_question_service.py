import json
from markupsafe import Markup
from datetime import datetime
from zoneinfo import ZoneInfo

from miminet_model import User, Network, db
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

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def is_answer_available(section):
    available_answer = True
    if section and section.results_available_from:
        now_moscow = datetime.now(MOSCOW_TZ)

        if section.results_available_from.tzinfo is None:
            results_time = section.results_available_from.replace(tzinfo=MOSCOW_TZ)
        else:
            results_time = section.results_available_from.astimezone(MOSCOW_TZ)

        available_answer = results_time <= now_moscow

    return available_answer


def get_question_by_session_question_id(session_question_id: str):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()

    if session_question is None:
        return 404

    question = session_question.question

    if question is None or question.is_deleted:
        return 404

    section = session_question.quiz_session.section

    if section is None:
        return 404

    is_exam = section.is_exam
    timer = section.timer
    available_from = section.results_available_from
    available_answer = is_answer_available(section)

    return (
        QuestionDto(session_question.created_by_id, question, session_question.id),
        is_exam,
        timer,
        available_answer,
        available_from,
        200,
    )


def check_theory_answer(session_question, question, answer):
    # variable
    if question.question_type == 1:
        answers = answer["answer"]
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
        session_question.score = 1 if session_question.is_correct else 0
        session_question.max_score = 1
        db.session.add(session_question)
        db.session.commit()

        return AnswerResultDto(question.explanation, correct), 200

    # sorting
    if question.question_type == 2:
        answer = sorted(answer["answer"].items(), key=lambda x: int(x[0]))

        answers = Answer.query.filter_by(question_id=question.id).all()
        answer_set = sorted({(answer.position, answer.variant) for answer in answers})

        correct = (
            True
            if [value for key, value in answer] == [value for key, value in answer_set]
            else False
        )
        session_question.is_correct = correct
        session_question.score = 1 if session_question.is_correct else 0
        session_question.max_score = 1
        db.session.add(session_question)
        db.session.commit()

        return AnswerResultDto(question.explanation, correct), 200

    # matching
    if question.question_type == 3:
        answers = Answer.query.filter_by(question_id=question.id).all()
        set1 = {(answer.left, answer.right) for answer in answers}
        set2 = set((item["left"], item["right"]) for item in answer["answer"])

        correct = set1 == set2
        session_question.is_correct = correct
        session_question.score = 1 if session_question.is_correct else 0
        session_question.max_score = 1
        db.session.add(session_question)
        db.session.commit()

        return AnswerResultDto(question.explanation, correct), 200

    return None, 400


def handle_exam_answer(session_question_id: str, answer, user: User):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()
    if not session_question or session_question.created_by_id != user.id:
        return None, None, 403

    question = session_question.question

    if question.question_type == 0:  # практика
        practice_question = PracticeQuestion.query.get(question.id)
        requirements = (
            json.loads(practice_question.requirements)
            if isinstance(practice_question.requirements, str)
            else practice_question.requirements
        )

        network = Network.query.filter_by(guid=answer["answer"]).first()
        network.author_id = 0
        network_data = json.loads(network.network) if network else None

        if not requirements or not network_data:
            return None, None, 403

        session_question.is_correct = False
        db.session.add(network)
        db.session.add(session_question)
        db.session.commit()

        return requirements, network_data, 200

    result_dto, status = check_theory_answer(session_question, question, answer)
    return result_dto, None, status


def answer_on_exam_question(session_question_id: str, networks_to_check):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()
    if not session_question or session_question.question.question_type != 0:
        return

    total_score = 0
    total_max_score = 0

    for network_json, animation_json, requirements_json in networks_to_check:
        network_data = (
            json.loads(network_json) if isinstance(network_json, str) else network_json
        )
        animation_data = (
            json.loads(animation_json)
            if isinstance(animation_json, str)
            else animation_json
        )
        requirements = (
            json.loads(requirements_json)
            if isinstance(requirements_json, str)
            else requirements_json
        )

        network_data["packets"] = json.loads(animation_data)

        max_score = calculate_max_score(requirements)
        score, _ = check_task(requirements, network_data)

        total_score += score
        total_max_score += max_score

    session_question.is_correct = total_score == total_max_score
    session_question.score = total_score
    session_question.max_score = total_max_score

    db.session.add(session_question)
    db.session.commit()


def answer_on_session_question(session_question_id: str, answer, user: User):
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
        score, hints = check_task(requirements, answer["answer"])

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

    else:
        result, status = check_theory_answer(session_question, question, answer)
        return (result, status)
