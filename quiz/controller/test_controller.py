import json

from flask_login import login_required, current_user
from flask import request, make_response, jsonify, render_template

from quiz.service.test_service import create_test, get_tests_by_owner, get_all_tests, delete_test, \
    get_deleted_tests_by_owner, edit_test, get_tests_by_author_name
from quiz.util.encoder import UUIDEncoder


@login_required
def create_test_endpoint():
    user = current_user
    res_id = create_test(name=request.json['name'],
                         description=request.json['description'],
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
    quizzes = get_all_tests()
    return make_response( render_template("quiz/quizzes.html", quizzes=quizzes), 200)


@login_required
def get_deleted_tests_by_owner_endpoint():
    user = current_user
    res = get_deleted_tests_by_owner(user)

    return make_response(json.dumps([obj.__dict__ for obj in res], cls=UUIDEncoder), 200)


@login_required
def delete_test_endpoint():
    test_id = request.json['id']
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
    test_id = request.json['id']
    edited = edit_test(user=current_user,
                       name=request.json['name'],
                       test_id=test_id,
                       description=request.json['description']
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
    tests = get_tests_by_author_name(request.json['author_name'])

    return make_response(json.dumps([obj.__dict__ for obj in tests], cls=UUIDEncoder), 200)
