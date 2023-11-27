from quiz.entity.entity import Question
from quiz.util.dto import to_question_for_editor_dto_list


def get_questions_by_section(section_id: str):
    questions = Question.query.filter_by(section_id=section_id, is_deleted=False).all()
    if questions is None:
        return None, 404

    return to_question_for_editor_dto_list(questions), 200


def get_question(question_id: str):
    question = Question.query.filter_by(id=question_id).first()
    if question is None:
        return None, 404

    return question, 200
