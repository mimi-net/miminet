from miminet_model import db, User
from quiz.entity.entity import Test
from quiz.util.dto import to_test_dto_list


def create_test(name: str, description: str, user: User):
    test = Test()
    test.created_by_id = user.id
    test.name = name
    test.description = description

    db.session.add(test)
    db.session.commit()
    return test.id


def get_tests_by_owner(user: User):
    tests = Test.query.filter_by(created_by_id=user.id).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_all_tests():
    tests = Test.query.all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos
