import json
from uuid import UUID

from flask_login import login_required, current_user
from flask import redirect, url_for, request, flash, make_response, jsonify

from quiz.service.TestService import create_test, get_tests_by_owner, get_all_tests


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)


@login_required
def create_test_endpoint():
    user = current_user
    print(request.args.get('name', type=str))
    res_id = create_test(name=request.args.get('name', type=str),
                         description=request.args.get('description', type=str),
                         user=user)
    ret = {'message': 'Тест добавлен', 'id': res_id}
    return make_response(jsonify(ret))


@login_required
def get_tests_by_owner_endpoint():
    user = current_user
    res = get_tests_by_owner(user)

    return make_response(json.dumps([obj.__dict__ for obj in res], cls=UUIDEncoder))


@login_required
def get_all_tests_endpoint():
    return make_response(json.dumps([obj.__dict__ for obj in get_all_tests()], cls=UUIDEncoder))
