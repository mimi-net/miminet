import json

from miminet_model import User, db
from quiz.entity.entity import (
    SessionQuestion,
    Answer,
    PracticeQuestion,
)
from quiz.util.dto import QuestionDto, AnswerResultDto


def get_question_by_session_question_id(session_question_id: str):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()
    question = session_question.question
    user_id = session_question.created_by_id
    if question is None or question.is_deleted is True:
        return None, 404

    return QuestionDto(user_id, question), 200


def check_task(task_dict, answer):
    nodes = answer["nodes"]
    edges = answer["edges"]
    packets = answer["packets"]

    task = task_dict["task"]
    if task == "ping 1 host":
        from_node = task_dict["from"]
        to_node = task_dict["to"]

        request = []
        reply = []

        for packet in packets:

            type = packet[0]["config"]["type"]
            source = packet[0]["config"]["source"]
            target = packet[0]["config"]["target"]

            if "ICMP echo-request" in type:
                if not request:
                    request.append(source)
                    request.append(target)

                if request[-1] != source:
                    request.append(source)

                if request[-1] != target:
                    request.append(target)

            elif "ICMP echo-reply" in type:
                if not reply:
                    reply.append(source)
                    reply.append(target)

                if reply[-1] != source:
                    reply.append(source)

                if reply[-1] != target:
                    reply.append(target)

            else:
                continue

        if (request and reply and request[0] == from_node and request[-1] == to_node
                and reply[0] == to_node and reply[-1] == from_node):
            return True
        else:
            return False


def answer_on_session_question(session_question_id: str, answer_string: dict, user: User):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()
    if session_question.created_by_id != user.id:
        return None, 403
    question = session_question.question

    # practice
    if question.question_type == 0:
        practice_question = PracticeQuestion.query.filter_by(id=question.id).first()
        tasks = practice_question.practice_tasks
        is_correct = True
        correct_count = 0
        for task in tasks:
            result = check_task(json.loads(task.task), answer_string["answer"])
            is_correct &= result
            correct_count += 1 if result else 0

        is_correct &= correct_count == len(tasks)

        session_question.is_correct = is_correct
        db.session.add(session_question)
        db.session.commit()

        return AnswerResultDto(practice_question.explanation, is_correct), 200

    # variable
    if question.question_type == 1:
        answers = answer_string["answer"]
        is_correct = True
        for check in answers:
            answer = Answer.query.filter_by(
                question_id=question.id,
                variant=check["variant"],
            ).first()
            if not answer.is_correct:
                is_correct = False

        correct_count = Answer.query.filter_by(question_id=question.id, is_correct=True).count()
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

        correct = True if [value for key, value in answer] == [value for key, value in answer_set] else False
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
