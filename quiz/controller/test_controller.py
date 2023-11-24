import json
from uuid import UUID

from flask_login import login_required, current_user
from flask import request, make_response, jsonify

from quiz.service.test_service import create_test, get_tests_by_owner, get_all_tests, delete_test, \
    get_deleted_tests_by_owner, edit_test, get_tests_by_author_name
from quiz.util.encoder import UUIDEncoder


@login_required
def create_test_endpoint():
    user = current_user
    res_id = create_test(name=request.form.get('name', type=str),
                         description=request.form.get('description', type=str),
                         user=user)
    ret = {'message': 'Тест добавлен', 'id': res_id}

    return make_response(jsonify(ret), 201)


@login_required
def get_tests_by_owner_endpoint():
    user = current_user
    res = get_tests_by_owner(user)

    return make_response(json.dumps([obj.__dict__ for obj in res], cls=UUIDEncoder), 200)


@login_required
def get_all_tests_endpoint():
    return make_response(json.dumps([obj.__dict__ for obj in get_all_tests()], cls=UUIDEncoder), 200)


@login_required
def get_deleted_tests_by_owner_endpoint():
    user = current_user
    res = get_deleted_tests_by_owner(user)

    return make_response(json.dumps([obj.__dict__ for obj in res], cls=UUIDEncoder), 200)


@login_required
def delete_test_endpoint():
    test_id = request.form.get('id', type=str)
    deleted = delete_test(current_user, test_id)
    if deleted == 404:
        ret = {'message': 'Тест не существует', 'id': test_id}
    elif deleted == 405:
        ret = {'message': 'Попытка удалить чужой тест', 'id': test_id}
    else:
        ret = {'message': 'Тест удалён', 'id': test_id}

    return make_response(jsonify(ret), deleted)


@login_required
def edit_test_endpoint():
    test_id = request.form.get('id', type=str)
    edited = edit_test(user=current_user,
                    name=request.form.get('name', type=str),
                    test_id=test_id,
                    description=request.form.get('description', type=str)
                    )
    if edited == 404:
        ret = {'message': 'Тест не существует', 'id': test_id}
    elif edited == 405:
        ret = {'message': 'Попытка редактировать чужой тест', 'id': test_id}
    else:
        ret = {'message': 'Тест редактирован', 'id': test_id}

    return make_response(jsonify(ret), edited)


@login_required
def get_tests_by_author_name_endpoint():
    tests = get_tests_by_author_name(request.form.get('author_name', type=str))

    return make_response(json.dumps([obj.__dict__ for obj in tests], cls=UUIDEncoder), 200)