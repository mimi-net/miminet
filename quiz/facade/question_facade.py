import json

from miminet_model import db, User
from quiz.entity.entity import Section, VariableQuestion, Answer, MatchingQuestion, SortingQuestion, TextQuestion, \
    Question


# {section_id: 1, question_type: 'text', question_text: 'some text', text_type: 'variable', variants: [{answer_text: 'text1', explanation:'explanation', is_correct: true}]}
def create_variable_question(variants: list, user: User):
    variable_question = VariableQuestion()
    variable_question.created_by_id = user.id
    for answer_json in variants:
        answer = Answer()
        answer.answer_text = answer_json['answer_text']
        answer.explanation = answer_json['explanation']
        answer.is_correct = answer_json['is_correct']
        variable_question.answers.append(answer)
        answer.created_by_id = user.id
        db.session.add(answer)
    db.session.add(variable_question)
    return variable_question


def create_matching_question(explanation: str, matching_str: str, user: User):
    matching_question = MatchingQuestion()
    matching_question.explanation = explanation
    matching_question.map = matching_str
    matching_question.created_by_id = user.id
    db.session.add(matching_question)

    return matching_question


def create_sorting_question(explanation: str, sorting_str: str, user: User):
    sorting_question = SortingQuestion()
    sorting_question.explanation = explanation
    sorting_question.right_sequence = sorting_str
    sorting_question.created_by_id = user.id
    db.session.add(sorting_question)
    return sorting_question


def create_question(section_id: str, question_dict: dict, user: User):
    section = Section.query.filter_by(id=section_id).first()
    if section is None:
        return None, 404
    elif section.created_by_id != user.id:
        return None, 405
    question = Question()
    question.section_id = section_id
    question.created_by_id = user.id
    question.question_type = question_dict['question_type']
    if question_dict['question_type'] == "text":
        text_question = TextQuestion()
        text_question.text_type = question_dict['text_type']
        if question_dict['text_type'] == "sorting":
            sorting_question = create_sorting_question(question_dict['explanation'], question_dict['right_sequence'], user)
            text_question.sorting_question.append(sorting_question)
        elif question_dict['text_type'] == "matching":
            matching_question = create_matching_question(question_dict['explanation'], question_dict['map'], user)
            text_question.matching_question.append(matching_question)
        elif question_dict['text_type'] == "variable":
            variable_question = create_variable_question(question_dict['variants'], user)
            text_question.variable_question.append(variable_question)
        else:
            raise Exception('Невозможно создать текстовый вопрос данного типа')
        text_question.created_by_id = user.id
        question.text_question.append(text_question)
        db.session.add(text_question)
        question.question_text = question_dict['question_text']
    else:
        raise Exception('Невозможно создать вопрос данного типа')
    db.session.commit()

    return question.id, 201
