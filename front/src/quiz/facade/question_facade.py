import uuid

from miminet_model import db, User, Network
from quiz.entity.entity import (
    Section,
    Question,
    PracticeQuestion,
    PracticeTask,
)


# def create_variable_question(variants: list, user: User):
#     variable_question = VariableQuestion()
#     variable_question.created_by_id = user.id
#     for answer_json in variants:
#         answer = Answer()
#         answer.answer_text = answer_json["answer_text"]
#         answer.explanation = answer_json["explanation"]
#         answer.is_correct = answer_json["is_correct"]
#         variable_question.answers.append(answer)
#         answer.created_by_id = user.id
#         db.session.add(answer)
#     db.session.add(variable_question)
#     return variable_question
#
#
# def create_matching_question(explanation: str, matching_str: str, user: User):
#     matching_question = MatchingQuestion()
#     matching_question.explanation = explanation
#     matching_question.map = matching_str
#     matching_question.created_by_id = user.id
#     db.session.add(matching_question)
#
#     return matching_question
#
#
# def create_sorting_question(explanation: str, sorting_str: str, user: User):
#     sorting_question = SortingQuestion()
#     sorting_question.explanation = explanation
#     sorting_question.right_sequence = sorting_str
#     sorting_question.created_by_id = user.id
#     db.session.add(sorting_question)
#
#     return sorting_question


def create_practice_task(task: str, user: User):
    practice_task = PracticeTask()
    practice_task.task = task
    practice_task.created_by_id = user.id
    db.session.add(practice_task)

    return practice_task


def create_question(section_id: str, question_dict: dict, user: User):
    section = Section.query.filter_by(id=section_id).first()
    if section is None or section.is_deleted:
        return None, 404
    elif section.created_by_id != user.id:
        return None, 403

    question = Question()
    question.section_id = section_id
    question.created_by_id = user.id

    if question_dict["question_type"] == "text":
        pass
        # question.question_type = question_dict["question_type"]
        # text_question = TextQuestion()
        # text_question.text_type = question_dict["text_type"]
        #
        # if question_dict["text_type"] == "sorting":
        #     sorting_question = create_sorting_question(
        #         question_dict["explanation"], question_dict["right_sequence"], user
        #     )
        #     text_question.sorting_question = sorting_question
        #
        # elif question_dict["text_type"] == "matching":
        #     matching_question = create_matching_question(
        #         question_dict["explanation"], question_dict["map"], user
        #     )
        #     text_question.matching_question = matching_question
        #
        # elif question_dict["text_type"] == "variable":
        #     variable_question = create_variable_question(
        #         question_dict["variants"], user
        #     )
        #     text_question.variable_question = variable_question
        #
        # else:
        #     return None, 400
        #
        # text_question.created_by_id = user.id
        # question.text_question = text_question
        # db.session.add(text_question)
        # question.question_text = question_dict["question_text"]

    elif question_dict["question_type"] == "practice":
        practice_question = PracticeQuestion()

        attributes = [
            "description",
            "explanation",
            # "start_configuration",
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

        u = uuid.uuid4()
        net_copy = Network(
            guid=str(u),
            author_id=user.id,
            network=net.network,
            title=net.title,
            description="Task start configuration copy",
            preview_uri=net.preview_uri,
            is_task=True,
        )
        db.session.add(net_copy)
        db.session.commit()

        practice_question.start_configuration = net_copy.guid

        question.question_type = 0
        practice_question.created_by_id = user.id
        practice_question.practice_tasks = [  # type: ignore
            create_practice_task(question_dict["tasks"], user)
        ]
        # practice_question.network = question_dict['network']
        question.practice_question = practice_question
        db.session.add(practice_question)
        question.question_text = question_dict["text"]
    else:
        return None, 400
    db.session.commit()

    return question.id, 201


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
    #     text_question = question.text_question
    #
    #     if text_question is not None:
    #         text_question.is_deleted = True
    #
    #         if text_question.text_type == "variable":
    #             variable_question = text_question.variable_question
    #             if variable_question is not None:
    #                 variable_question.is_deleted = True
    #                 for answer in variable_question.answers:
    #                     if answer is not None:
    #                         answer.is_deleted = True
    #
    #         if text_question.text_type == "sorting":
    #             sorting_question = text_question.sorting_question
    #             if sorting_question is not None:
    #                 sorting_question.is_deleted = True
    #
    #         if text_question.text_type == "matching":
    #             sorting_question = text_question.sorting_question
    #             if sorting_question is not None:
    #                 sorting_question.is_deleted = True
    # else:
    if question.question_type == 0:
        practice_question = question.practice_question
        if practice_question is not None:
            db.session.delete(practice_question)

    # question.is_deleted = True
    db.session.delete(question)
    db.session.commit()
    return 200
