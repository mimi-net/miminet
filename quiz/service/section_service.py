from datetime import datetime

from miminet_model import db, User
from quiz.entity.entity import Section, Test
from quiz.util.dto import to_section_dto_list


def create_section(test_id: str, name: str, description: str, timer: datetime, user: User):
    test = Test.query.filter_by(id=test_id, is_deleted=False).first()
    if test is None:
        return "", 404
    elif test.created_by_id != user.id:
        return "", 405
    else:
        section = Section()
        section.test_id = test_id
        section.name = name
        section.description = description
        section.timer = timer
        section.created_by_id = user.id
        db.session.add(section)
        db.session.commit()
        return section.id, 200


def get_section(section_id: str):
    section = Section.query.filter_by(id=section_id).first()
    if section is None:
        return "", 404

    return section, 200


def get_sections_by_test(test_id: str):
    test = Test.query.filter_by(id=test_id, is_deleted=False).first()
    if test is None:
        return [], 404
    not_deleted_sections = list(filter(lambda section: section.is_deleted is False, test.sections))
    section_dtos = to_section_dto_list(not_deleted_sections)

    return section_dtos, 200


def get_deleted_sections_by_test(test_id: str, user: User):
    test = Test.query.filter_by(id=test_id, is_deleted=False).first()
    if test is None:
        return [], 404
    elif test.created_by_id != user.id:
        return [], 405
    deleted_sections = list(filter(lambda section: section.is_deleted is True, test.sections))
    section_dtos = to_section_dto_list(deleted_sections)

    return section_dtos, 200


def delete_section(user: User, section_id: str):
    section = Section.query.filter_by(id=section_id).first()
    if section is None or section.is_deleted is True:
        return 404
    elif section.created_by_id != user.id:
        return 405
    else:
        section.is_deleted = True
        db.session.commit()
        return 200


def edit_section(user: User, section_id: str, name: str, description: str, timer: datetime):
    section = Section.query.filter_by(id=section_id).first()
    if section is None or section.is_deleted is True:
        return 404
    elif section.created_by_id != user.id:
        return 405
    else:
        section.name = name
        section.description = description
        section.timer = timer
        db.session.commit()
        return 200
