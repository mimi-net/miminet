from miminet_model import db, User
from quiz.entity.entity import Test
from quiz.util.dto import to_test_dto_list
from sqlalchemy.orm import joinedload, selectinload

TEST_LIST_RELATIONS = (
    joinedload(Test.created_by_user),
    selectinload(Test.sections),
)


def _get_tests_with_relations(**filters):
    return Test.query.options(*TEST_LIST_RELATIONS).filter_by(**filters).all()


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
    tests = _get_tests_with_relations(created_by_id=user.id, is_deleted=False)
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_retakeable_tests():
    tests = _get_tests_with_relations(is_deleted=False, is_retakeable=True)
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_all_tests():
    tests = _get_tests_with_relations(is_deleted=False, is_ready=True)
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def get_deleted_tests_by_owner(user: User):
    tests = _get_tests_with_relations(created_by_id=user.id, is_deleted=True)
    test_dtos = to_test_dto_list(tests)

    return test_dtos


def delete_test(user: User, test_id: str):
    test = Test.query.filter_by(id=test_id).first()
    if test is None:
        return 404
    elif test.is_deleted is True:
        return 409
    elif test.created_by_id != user.id:
        return 403
    else:
        test.is_deleted = True
        db.session.commit()
        return 200


def edit_test(
    user: User, test_id: str, name: str, description: str, is_retakeable: bool
):
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
    tests = (
        Test.query.options(*TEST_LIST_RELATIONS)
        .join(User, User.id == Test.created_by_id)
        .filter(User.nick == author_name)
        .filter(Test.is_deleted.is_(False))
        .filter(Test.is_ready.is_(True))
        .all()
    )
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
