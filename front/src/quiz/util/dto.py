import random
import uuid
from typing import List

from markupsafe import Markup

from miminet_model import Network, db
from quiz.entity.entity import (
    Section,
    Test,
    Question,
    Answer,
    PracticeQuestion,
    QuizSession,
)


def to_section_dto_list(sections: List[Section]):
    dto_list: List[SectionDto] = list(
        map(
            lambda our_section: SectionDto(
                section_id=our_section.id,
                section_name=our_section.name,
                timer=our_section.timer,
                description=our_section.description,
                question_count=len(our_section.questions),
                sessions_count=len(our_section.quiz_sessions),
            ),
            sections,
        )
    )

    return dto_list


def to_test_dto_list(tests: List[Test]):
    dto_list: List[TestDto] = list(
        map(
            lambda our_test: TestDto(
                test_id=our_test.id,
                test_name=our_test.name,
                author_name=our_test.created_by_user.nick,
                description=our_test.description,
                is_retakeable=our_test.is_retakeable,
                is_ready=our_test.is_ready,
                section_count=len(our_test.sections),
            ),
            tests,
        )
    )

    return dto_list


def to_question_for_editor_dto_list(questions: List[Question]):
    dto_list: List[QuestionForEditorDto] = list(
        map(
            lambda question: QuestionForEditorDto(
                question_id=question.id, question_text=question.text
            ),
            questions,
        )
    )

    return dto_list


class AnswerResultDto:
    def __init__(self, explanation, is_correct: bool) -> None:
        self.explanation = explanation
        self.is_correct = is_correct

    def to_dict(self):
        if isinstance(self.explanation, list):
            return {"explanation": [self.explanation], "is_correct": self.is_correct}
        else:
            return {"explanation": self.explanation, "is_correct": self.is_correct}


class AnswerDto:
    def __init__(self, question_type: str, answer: Answer) -> None:
        if question_type == "matching":
            self.left = answer.left
            self.right = answer.right
        else:
            self.variant = answer.variant

    def to_dict(self):
        attributes = ["variant", "left", "right"]
        data = {attr: getattr(self, attr) for attr in attributes if hasattr(self, attr)}
        return data


class PracticeQuestionDto:
    def __init__(self, user_id, practice_question: PracticeQuestion) -> None:
        attributes = [
            "description",
            "available_host",
            "available_l1_hub",
            "available_server",
            "available_l2_switch",
            "available_l3_router",
        ]

        for attribute in attributes:
            setattr(self, attribute, getattr(practice_question, attribute))

        net = Network.query.filter(
            Network.guid == practice_question.start_configuration
        ).first()
        escaped_string = net.network.replace('\\"', '"').replace('"', '\\"')

        u = uuid.uuid4()
        net_copy = Network(
            guid=str(u),
            author_id=user_id,
            network=net.network,
            title=net.title,
            description="Network copy",
            preview_uri=net.preview_uri,
            is_task=True,
        )
        db.session.add(net_copy)
        db.session.commit()

        self.start_configuration = escaped_string
        self.network_guid = net_copy.guid

    def to_dict(self):
        attributes = [
            "description",
            "available_host",
            "available_l1_hub",
            "available_server",
            "available_l2_switch",
            "available_l3_router",
            "start_configuration",
            "network_guid",
        ]

        return {attribute: str(getattr(self, attribute)) for attribute in attributes}


def get_question_type(question_type: int):
    types = {0: "practice", 1: "variable", 2: "sorting", 3: "matching"}
    return types.get(question_type, "")


class QuestionDto:
    def __init__(self, user_id, question: Question) -> None:
        self.question_type = get_question_type(question.question_type)
        self.question_text = Markup.unescape(question.text)
        self.correct_count = 0

        if self.question_type == "practice":
            self.practice_question = PracticeQuestionDto(user_id, question.practice_question).to_dict()  # type: ignore
            return

        filtered_answers = Answer.query.filter_by(
            question_id=question.id, is_deleted=False
        ).all()

        if self.question_type == "variable":
            self.correct_count = sum(answer.is_correct for answer in filtered_answers)

        self.answers = [
            AnswerDto(question_type=self.question_type, answer=answer).to_dict()
            for answer in filtered_answers
        ]
        random.shuffle(self.answers)

        # text_question = question.text_question
        # self.text_type = text_question.text_type

        # if self.question_type == "variable":
        #     variable_question = text_question.variable_question
        #     self.answers = [
        #         AnswerDto(answer_text=i.answer_text).to_dict()
        #         for i in Answer.query.filter_by(
        #             variable_question_id=variable_question.id, is_deleted=False
        #         ).all()
        #     ]
        #
        # elif self.question_type == "matching":
        #     matching_question = text_question.matching_question
        #
        #     data = matching_question.map
        #     keys = list(data.keys())
        #     values = list(data.values())
        #     random.shuffle(keys)
        #     res = {keys[i]: values[i] for i in range(len(keys))}
        #
        #     self.answers = json.dumps(res)
        #
        # elif self.question_type == "sorting":
        #     sorting_question = text_question.sorting_question
        #     words = sorting_question.right_sequence.split()
        #     random.shuffle(words)
        #     self.answers = " ".join(words)


class SectionDto:
    def __init__(
        self,
        section_id: str,
        section_name: str,
        timer: str,
        description: str,
        question_count: int,
        sessions_count: int,
    ):
        self.section_id = section_id
        self.section_name = section_name
        self.timer = timer
        self.description = description
        self.question_count = question_count
        self.sessions_count = sessions_count

        session = (
            QuizSession.query.filter(QuizSession.section_id == section_id)
            .order_by(QuizSession.finished_at.desc())
            .first()
        )
        if session:
            self.last_correct_count = sum(
                1 for question in session.sessions if question.is_correct
            )


class TestDto:
    def __init__(
        self,
        test_id: str,
        test_name: str,
        author_name: str,
        description: str,
        is_retakeable: bool,
        is_ready: bool,
        section_count: int,
    ):
        self.test_id = test_id
        self.test_name = test_name
        self.author_name = author_name
        self.description = description
        self.is_retakeable = is_retakeable
        self.is_ready = is_ready
        self.section_count = section_count


class QuestionForEditorDto:
    def __init__(self, question_id: str, question_text: str):
        self.question_id = question_id
        self.question_text = question_text


class SessionResultDto:
    def __init__(
        self,
        test_name: str,
        section_name: str,
        correct_answers: int,
        answers_count: int,
        start_time: str,
        time_spent: str,
    ):
        self.test_name = test_name
        self.section_name = section_name
        self.correct_answers = correct_answers
        self.answers_count = answers_count
        self.start_time = start_time
        self.time_spent = time_spent
