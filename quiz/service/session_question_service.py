import json

from miminet_model import User, db
from quiz.entity.entity import SessionQuestion, TextQuestion, MatchingQuestion, SortingQuestion, \
    Answer
from quiz.util.dto import QuestionDto, AnswerResultDto


def get_question_by_session_question_id(session_question_id: str):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()
    question = session_question.question
    if question is None or question.is_deleted is True:
        return None, 404

    return QuestionDto(question), 200


def answer_on_session_question(session_question_id: str, answer_string: dict, user: User):
    session_question = SessionQuestion.query.filter_by(id=session_question_id).first()
    if session_question.created_by_id != user.id:
        return None, 403
    question = session_question.question
    if question.question_type == "text":
        text_question = TextQuestion.query.filter_by(id=question.id).first()

        if text_question.text_type == "variable":
            explanation_list = []
            answers = answer_string['answer']
            is_correct = True
            correct_count = 0
            answer_count = 0
            for check in answers:  # redo
                answer = Answer.query.filter_by(variable_question_id=text_question.id, answer_text=check['answer_text']).first()
                explanation_list.append(answer.explanation)
                answer_count += 1
                if not answer.is_correct:
                    is_correct = False
                else:
                    correct_count += 1
            correct = is_correct and answer_count == correct_count
            session_question.is_correct = correct
            db.session.add(session_question)
            db.session.commit()

            return AnswerResultDto(
                explanation_list,
                correct
            ), 200

        elif text_question.text_type == "matching":
            matching_question = MatchingQuestion.query.filter_by(id=text_question.id).first()
            correct = matching_question.map == answer_string['answer']
            session_question.is_correct = correct
            db.session.add(session_question)
            db.session.commit()

            return AnswerResultDto(
                matching_question.explanation,
                correct
            ), 200

        elif text_question.text_type == "sorting":
            sorting_question = SortingQuestion.query.filter_by(id=text_question.id).first()
            correct = answer_string['answer'] == sorting_question.right_sequence
            session_question.is_correct = correct
            db.session.add(session_question)
            db.session.commit()

            return AnswerResultDto(
                sorting_question.explanation,
                correct
            ), 200
