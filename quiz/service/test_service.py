from miminet_model import db, User
from quiz.entity.entity import Test
from quiz.util.dto import to_test_dto_list


def create_test(name: str, description: str, user: User, is_retakeable: bool):
    test = Test()
    test.created_by_id = user.id
    test.name = name
    test.description = description
    test.is_retakeable = is_retakeable

    db.session.add(test)
    db.session.commit()

    return test.id


def get_test(test_id: str):
    test = Test.query.filter_by(id=test_id).first()
    if test is None:
        return None, 404

    return test, 200


def get_tests_by_owner(user: User):
    tests = Test.query.filter_by(created_by_id=user.id, is_deleted=False).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_retakeable_tests():
    tests = Test.query.filter_by(is_deleted=False, is_retakeable=True).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_all_tests():
    tests = Test.query.filter_by(is_deleted=False, is_ready=True).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_deleted_tests_by_owner(user: User):
    tests = Test.query.filter_by(created_by_id=user.id, is_deleted=True).all()
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def delete_test(user: User, test_id: str):
    test = Test.query.filter_by(id=test_id).first()
    if test is None or test.is_deleted is True:
        return 409
    elif test.created_by_id != user.id:
        return 403
    else:
        test.is_deleted = True
        db.session.commit()
        return 200


def edit_test(user: User, test_id: str, name: str, description: str, is_retakeable: bool):
    test = Test.query.filter_by(id=test_id).first()
    if test is None or test.is_deleted is True:
        return 404
    elif test.created_by_id != user.id:
        return 403
    else:
        test.name = name
        test.description = description
        test.is_retakeable = is_retakeable
        db.session.commit()
        return 200


def get_tests_by_author_name(author_name: str):
    tests = (db.session.query(User, Test)
             .filter(User.nick == author_name)
             .filter(User.id == Test.created_by_id)
             .filter(Test.is_deleted is False)
             .filter(Test.is_ready is True))
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def publish_or_unpublish_test(user: User, test_id: str, is_to_publish: bool):
    test = Test.query.filter_by(id=test_id).first()
    if test is None or test.is_deleted is True:
        return 404
    elif test.created_by_id != user.id:
        return 403
    else:
        test.is_ready = is_to_publish
        db.session.commit()
        return 200

