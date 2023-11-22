import datetime
from typing import List

from miminet_model import Section, Test, User


def to_section_dto_list(sections: List[Section]):
    dto_list: List[SectionDto] = []

    for i in range(len(sections)):
        section = sections[i]
        dto_list.append(SectionDto(section.name, section.timer, section.description))

    return dto_list


def to_test_dto_list(tests: List[Test]):
    dto_list: List[TestDto] = []

    for i in range(len(tests)):
        test = tests[i]
        user = test.created_by_user()
        dto_list.append(TestDto(test.name, test.created_by_user(), test.description))

    return dto_list


class SectionDto:
    def __init__(self, section_name: str, timer: datetime, description: str) -> None:
        self.section_name = section_name
        self.timer = timer
        self.description = description


class TestDto:
    def __init__(self, test_name: str, author_name: str, description: str) -> None:
        self.test_name = test_name
        self.author_name = author_name
        self.description = description
