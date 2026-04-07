import uuid
import json
import logging
import os

from flask import session

import lti_provider.controller as lti
from quiz.facade.json_schema_validation import validate_requirements

from miminet_model import db, User, Network
from quiz.entity.entity import (
    Section,
    Question,
    PracticeQuestion,
    Answer,
    QuestionCategory,
    QuestionImage,
)

UPLOAD_FOLDER = "/app/static/quiz_images"


def create_single_question(section_id: str, question_dict, user: User):
    if "requirements" in question_dict:
        validation_result = validate_requirements(question_dict["requirements"])
        if validation_result is not True:
            return {"message": validation_result}, 400

    question = Question()
    question.section_id = section_id

    question.created_by_id = user.id
    question.text = question_dict["text"]
    question.explanation = question_dict.get("explanation", "")

    category_name = question_dict.get("category")
    if category_name:
        category = QuestionCategory.query.filter_by(name=category_name).first()
        if category:
            question.category_id = category.id

    qtype = question_dict["question_type"]

    if qtype == "variable":
        question.question_type = 1
        for variant in question_dict["variants"]:
            answer = Answer(
                variant=variant["answer_text"],
                is_correct=variant.get("is_correct", False),
                question=question,
                created_by_id=user.id,
            )
            db.session.add(answer)

    elif qtype == "sorting":
        question.question_type = 2
        for sorting_answer in question_dict["sorting_answers"]:
            answer = Answer(
                variant=sorting_answer["answer_text"],
                position=sorting_answer["position"],
                question=question,
                created_by_id=user.id,
            )
            db.session.add(answer)

    elif qtype == "matching":
        question.question_type = 3
        for pair in question_dict["matching_pairs"]:
            answer = Answer(
                left=pair["left"],
                right=pair["right"],
                question=question,
                created_by_id=user.id,
            )
            db.session.add(answer)

    elif qtype == "practice":
        question.question_type = 0
        practice_question = PracticeQuestion()

        for attr in [
            "description",
            "explanation",
            "available_host",
            "available_l2_switch",
            "available_l1_hub",
            "available_l3_router",
            "available_server",
        ]:
            setattr(practice_question, attr, question_dict.get(attr, ""))

        net = Network.query.filter(
            Network.guid == question_dict["start_configuration"]
        ).first()

        if net is None:
            net_guid = question_dict["start_configuration"]
            return {"message": f"Сеть {net_guid} не найдена"}, 404

        question_network = json.loads(net.network)
        question_network.pop("packets", None)
        question_network.pop("pcap", None)

        net.network = json.dumps(question_network)
        net.author_id = 0
        net.title = question_dict["text"]
        net.description = question_dict["description"]

        db.session.add(net)
        db.session.commit()

        practice_question.start_configuration = net.guid
        practice_question.created_by_id = user.id

        requirements = question_dict.get("requirements")
        if requirements:
            practice_question.requirements = requirements
        else:
            practice_question.requirements = question_dict["network_scenarios"]

        question.practice_question = practice_question
        db.session.add(practice_question)
    else:
        return None, 400

    db.session.add(question)

    if "images" in question_dict:
        missing_images = []
        for image_filename in question_dict["images"]:
            file_path = os.path.join(UPLOAD_FOLDER, image_filename)
            if os.path.exists(file_path):
                qi = QuestionImage()
                qi.file_path = f"/quiz/images/{image_filename}"
                qi.question = question
                db.session.add(qi)
            else:
                missing_images.append(image_filename)

        if missing_images:
            return {"missing": missing_images}, 400

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

    if section_id:
        section = Section.query.filter_by(id=section_id).first()
        if (section is None or section.is_deleted) and isinstance(question_data, list):
            return None, None, 404
        elif section.created_by_id != user.id:
            return None, None, 403
    else:
        section = Section()
        section.timer = question_data["timer"]
        section.name = question_data["text"]
        section.description = question_data["description"]
        section.max_score = question_data["max_score"]
        db.session.add(section)
        db.session.commit()

    if isinstance(question_data, list):
        for q_data in question_data:
            q_id, status = create_single_question(section.id, q_data, user)
            if status == 201:
                created_ids.append(q_id)
            else:
                logging.error("Ошибка создания вопроса: %s (код %s)", q_data, status)

        if not created_ids:
            return None, None, 400
        return section.id, created_ids, 201
    else:
        q_id, status = create_single_question(section.id, question_data, user)

        if "launch_id" in session: return lti.send(section), q_id, status
        return section.id, q_id, status


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
