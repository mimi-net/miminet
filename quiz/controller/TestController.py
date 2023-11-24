import json
from uuid import UUID

from flask_login import login_required, current_user
from flask import redirect, url_for, request, flash, make_response, jsonify

from quiz.service.TestService import create_test, get_tests_by_owner, get_all_tests, delete_test, \
    get_deleted_tests_by_owner


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)


@login_required
def create_test_endpoint():
    user = current_user
    res_id = create_test(name=request.args.get('name', type=str),
                         description=request.args.get('description', type=str),
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
    test_id = request.args.get('id', type=int)
    deleted = delete_test(current_user, test_id)
    if deleted == 404:
        ret = {'message': 'Тест не существует', 'id': test_id}
    elif deleted == 405:
        ret = {'message': 'Попытка удалить чужой тест', 'id': test_id}
    else:
        ret = {'message': 'Тест удалён', 'id': test_id}
    return make_response(jsonify(ret), deleted)