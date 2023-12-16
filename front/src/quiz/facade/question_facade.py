import json

from miminet_model import db, User
from quiz.entity.entity import Section, VariableQuestion, Answer, MatchingQuestion, SortingQuestion, TextQuestion, \
    Question


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
    if section is None or section.is_deleted:
        return None, 404
    elif section.created_by_id != user.id:
        return None, 403
    question = Question()
    question.section_id = section_id
    question.created_by_id = user.id
    question.question_type = question_dict['question_type']

    if question_dict['question_type'] == "text":
        text_question = TextQuestion()
        text_question.text_type = question_dict['text_type']

        if question_dict['text_type'] == "sorting":
            sorting_question = create_sorting_question(question_dict['explanation'], question_dict['right_sequence'], user)
            text_question.sorting_question = sorting_question

        elif question_dict['text_type'] == "matching":
            matching_question = create_matching_question(question_dict['explanation'], question_dict['map'], user)
            text_question.matching_question = matching_question

        elif question_dict['text_type'] == "variable":
            variable_question = create_variable_question(question_dict['variants'], user)
            text_question.variable_question = variable_question

        else:
            return None, 400

        text_question.created_by_id = user.id
        question.text_question = text_question
        db.session.add(text_question)
        question.question_text = question_dict['question_text']
    else:
        return None, 400
    db.session.commit()

    return question.id, 201


def delete_question(question_id: str, user: User):
    question = Question.query.filter_by(id=question_id).first()
    if question is None:
        return 404
    elif question.created_by_id != user.id:
        return 403
    elif question.is_deleted:
        return 409
    if question.question_type == "text":
        text_question = question.text_question

        if text_question is not None:
            text_question.is_deleted = True

            if text_question.text_type == "variable":
                variable_question = text_question.variable_question
                if variable_question is not None:
                    variable_question.is_deleted = True
                    for answer in variable_question.answers:
                        if answer is not None:
                            answer.is_deleted = True

            if text_question.text_type == "sorting":
                sorting_question = text_question.sorting_question
                if sorting_question is not None:
                    sorting_question.is_deleted = True

            if text_question.text_type == "matching":
                sorting_question = text_question.sorting_question
                if sorting_question is not None:
                    sorting_question.is_deleted = True

    question.is_deleted = True
    db.session.commit()
    return 200
