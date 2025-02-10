import uuid
import json
import logging
from copy import deepcopy

from miminet_model import db, User, Network
from quiz.entity.entity import (
    Section,
    Question,
    PracticeQuestion,
    Answer,
    QuestionCategory
)

def create_single_question(section_id: str, question_dict, user: User):
    if section_id:
        section = Section.query.filter_by(id=section_id).first()
        if section is None or section.is_deleted:
            return None, 404
        elif section.created_by_id != user.id:
            return None, 403

    question = Question()
    if section_id:
        question.section_id = section_id

    question.created_by_id = user.id
    question.text = question_dict["text"]
    question.explanation = question_dict.get("explanation", "")

    if "category" in question_dict:
        category = QuestionCategory.query.filter_by(name=question_dict["category"]).first()
        if category:
            question.category_id = category.id

    if question_dict["question_type"] == "variable":
        question.question_type = 1  # 1 - variable
        for variant in question_dict["variants"]:
            answer = Answer()
            answer.variant = variant["answer_text"]
            answer.is_correct = variant.get("is_correct", False)
            answer.question = question
            db.session.add(answer)

    elif question_dict["question_type"] == "sorting":
        question.question_type = 2  # 2 - sorting
        for sorting_answer in question_dict["sorting_answers"]:
            answer = Answer()
            answer.variant = sorting_answer["answer_text"]
            answer.position = sorting_answer["position"]
            answer.question = question
            db.session.add(answer)

    elif question_dict["question_type"] == "matching":
        question.question_type = 3  # 3 - matching
        for pair in question_dict["matching_pairs"]:
            answer = Answer()
            answer.left = pair["left"]
            answer.right = pair["right"]
            answer.question = question
            db.session.add(answer)

    elif question_dict["question_type"] == "practice":
        question.question_type = 0  # 0 - practice
        practice_question = PracticeQuestion()
        attributes = [
            "description",
            "explanation",
            "available_host",
            "available_l2_switch",
            "available_l1_hub",
            "available_l3_router",
            "available_server",
        ]
        for attribute in attributes:
            setattr(practice_question, attribute, question_dict[attribute])

        net = Network.query.filter(
            Network.guid == question_dict["start_configuration"]
        ).first()

        if net is None:
            return None, 404

        original_network = json.loads(net.network)
        modified_network = deepcopy(original_network)
        modified_network.pop("packets", None)
        modified_network.pop("pcap", None)
        modified_network_json = json.dumps(modified_network)
        u = uuid.uuid4()

        net_copy = Network(
            guid=str(u),
            author_id=user.id,
            network=modified_network_json,
            title=net.title,
            description="Task start configuration copy",
            preview_uri=net.preview_uri,
            is_task=True,
        )
        
        db.session.add(net_copy)
        db.session.commit()

        practice_question.start_configuration = net_copy.guid
        practice_question.created_by_id = user.id
        practice_question.requirements = question_dict["requirements"]

        question.practice_question = practice_question
        db.session.add(practice_question)
    else:
        return None, 400

    db.session.add(question)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error("Ошибка при коммите вопроса: %s", e)
        return None, 500

    return question.id, 201


def create_question(section_id: str, question_data, user: User):
    """
    Если question_data – список, то обрабатывает все объекты.
    Если одиночный объект – обрабатывает его.
    Возвращает кортеж: (список созданных ID, HTTP статус)
    """
    created_ids = []
    if isinstance(question_data, list):
        for q_data in question_data:
            q_id, status = create_single_question(section_id, q_data, user)
            if status == 201:
                created_ids.append(q_id)
            else:
                logging.error("Ошибка создания вопроса: %s (код %s)", q_data, status)

        if not created_ids:
            return None, 400
        return created_ids, 201
    else:
        return create_single_question(section_id, question_data, user)


def delete_question(question_id: str, user: User):
    question = Question.query.filter_by(id=question_id).first()
    if question is None:
        return 404
    elif question.created_by_id != user.id or user.role < 1:
        return 403
    elif question.is_deleted:
        return 409

    # Not practice question
    # if question.question_type != 0:

    # else:
    if question.question_type == 0:
        practice_question = question.practice_question
        if practice_question is not None:
            db.session.delete(practice_question)

    # question.is_deleted = True
    db.session.delete(question)
    db.session.commit()
    return 200
