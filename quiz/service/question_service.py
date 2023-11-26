from quiz.entity.entity import Section
from quiz.util.dto import QuestionDto


def get_questions_by_section(section_id: str):
    section = Section.query.filter_by(id=section_id, is_deleted=False).first()
    if section is None:
        return None, 404
    not_deleted_questions = list(map(lambda question : QuestionDto(question),
                                     filter(lambda question: question.is_deleted is False, section.questions)))

    return not_deleted_questions, 200


