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
    tests = Test.query.filter_by(created_by_id=user.id, is_deleted=False).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_all_tests():
    tests = Test.query.all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_deleted_tests_by_owner(user: User):
    tests = Test.query.filter_by(created_by_id=user.id, is_deleted=True).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def delete_test(user: User, test_id: str):
    test = Test.query.filter_by(id=test_id).first()
    if test is None or test.is_deleted is True:
        return 404
    elif test.created_by_id != user.id:
        return 405
    else:
        test.is_deleted = True
        db.session.commit()
        return 200


def edit_test(user: User, test_id: str, name: str, description: str):
    test = Test.query.filter_by(id=test_id).first()
    if test is None or test.is_deleted is True:
        return 404
    elif test.created_by_id != user.id:
        return 405
    else:
        test.name = name
        test.description = description
        db.session.commit()
        return 200


def get_tests_by_author_name(author_name: str):
    tests = (db.session.query(User, Test)
             .filter(User.email == author_name)
             .filter(User.id == Test.created_by_id)
             .filter(Test.is_deleted is False))
    test_dtos = to_test_dto_list(tests)

    return test_dtos
