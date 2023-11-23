from flask_login import login_required, current_user
from flask import redirect, url_for, request, flash, make_response, jsonify

from quiz.service.TestService import create_test, get_tests


@login_required
def create_test_endpoint():
    user = current_user
    print(request.form.get('name'))
    res_id = create_test(name=request.form.get('name'),
                         description=request.form.get('description'),
                         user=user)
    ret = {'message': 'Тест добавлен', 'id': res_id}
    return make_response(jsonify(ret))


@login_required
def get_tests_endpoint():
    user = current_user
    res = get_tests(user)

    return make_response(jsonify(res))
