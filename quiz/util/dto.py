import datetime
import json
import random
from typing import List

from quiz.entity.entity import Section, Test, Question


def to_section_dto_list(sections: List[Section]):
    dto_list: List[SectionDto] = []

    for i in range(len(sections)):
        section = sections[i]
        dto_list.append(SectionDto(section.id, section.name, section.timer, section.description))

    return dto_list


def to_test_dto_list(tests: List[Test]):
    dto_list: List[TestDto] = []

    for i in range(len(tests)):
        test = tests[i]
        dto_list.append(
            TestDto(test_id=test.id,
                    test_name=test.name,
                    author_name=test.created_by_user.email,
                    description=test.description,
                    is_retakeable=test.is_retakeable,
                    is_ready=test.is_ready)
                    )

    return dto_list


class AnswerDto:
    def __init__(self, answer_text: str, explanation: str, is_correct: bool) -> None:
        self.answer_text = answer_text
        self.explanation = explanation
        self.is_correct = is_correct


class QuestionDto:
    def __init__(self, question: Question) -> None:
        self.question_type = question.question_type
        self.question_text = question.question_text
        if self.question_type == "text":
            text_question = question.text_question
            self.text_type = text_question.text_type
            if text_question.text_type == "variable":
                self.answers = [
                    AnswerDto(answer_text=i.answer_text,
                              explanation=i.explanation,
                              is_correct=i.is_correct) for i in text_question.variable_question.answers]
            elif text_question.text_type == "matching":
                data = json.load(text_question.matching_question.map)
                random.shuffle(data)
                self.explanation = text_question.matching_question.explanation
                self.answers = json.dumps(data)
            elif text_question.text_type == "sorting":
                words = text_question.sorting_question.right_sequence.split()
                random.shuffle(words)
                self.explanation = text_question.sorting_question.explanation
                self.answers = " ".join(words)


class SectionDto:
    def __init__(self, section_id: str, section_name: str, timer: datetime, description: str):
        self.section_id = section_id
        self.section_name = section_name
        self.timer = timer
        self.description = description


class TestDto:
    def __init__(self, test_id: str, test_name: str, author_name: str, description: str, is_retakeable: bool, is_ready: bool):
        self.test_id = test_id
        self.test_name = test_name
        self.author_name = author_name
        self.description = description
        self.is_retakeable = is_retakeable
        self.is_ready = is_ready
