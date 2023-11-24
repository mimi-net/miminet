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
    tests = Test.query.filter_by(created_by_id=user.id, deleted=False).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_all_tests():
    tests = Test.query.all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_deleted_tests_by_owner(user: User):
    tests = Test.query.filter_by(created_by_id=user.id, deleted=True).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def delete_test(user_id: id, test_id: int):
    test = Test.query.filter_by(id=test_id).first()
    if test is None or test.is_deleted is True:
        return 404
    elif test.created_by_id != user_id:
        return 405
    else:
        Test.is_deleted = True
        return 200

