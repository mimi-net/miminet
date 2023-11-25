import json

from miminet_model import db
from quiz.entity.entity import Section, VariableQuestion, Answer, MatchingQuestion, SortingQuestion, TextQuestion, \
    Question


# {section_id: 1, question_type: 'text', question_text: 'some text', text_type: 'variable', variants: [{answer_text: 'text1', explanation:'explanation', is_correct: true}]}
def create_variable_question(variants: list):
    variable_question = VariableQuestion()
    for answer_json in variants:
        new_json = json.loads(answer_json)
        answer = Answer()
        answer.answer_text = new_json['answer_text']
        answer.explanation = new_json['explanation']
        answer.is_correct = new_json['is_correct']
        answer.variable_question_id = variable_question.id
        db.session.add(answer)
    db.session.add(variable_question)
    return variable_question


def create_matching_question(explanation: str, matching_str: str):
    matching_question = MatchingQuestion()
    matching_question.explanation = explanation
    matching_question.map = matching_str
    db.session.add(matching_question)

    return matching_question


def create_sorting_question(explanation: str, sorting_str: str):
    sorting_question = SortingQuestion()
    sorting_question.explanation = explanation
    sorting_question.map = sorting_str
    db.session.add(sorting_question)
    return sorting_question


def create_question(question_json: str):
    question_dict = json.loads(question_json)
    question = Question()
    if question_dict['question_type'] == "text":
        text_question = TextQuestion()
        text_question.text_type = question_dict['text_type']
        if question_dict['text_type'] == "sorting":
            sorting_question = create_sorting_question(question_dict['explanation'], question_dict['right_sequence'])
            text_question.id = sorting_question.id
        elif question_dict['text_type'] == "matching":
            matching_question = create_matching_question(question_dict['explanation'], question_dict['map'])
            text_question.id = matching_question.id
        elif question_dict['text_type'] == "variable":
            variable_question = create_variable_question(question_dict['variants'])
            text_question.id = variable_question
        else:
            raise Exception('Невозможно создать текстовый вопрос данного типа')
        db.session.add(text_question)
        question.id = text_question.id
        question.question_text = question_dict['question_text']
    else:
        raise Exception('Невозможно создать вопрос данного типа')
    db.session.commit()

    return question.id