import json

from flask_login import login_required, current_user
from flask import request, make_response, jsonify, render_template, abort

from quiz.service.test_service import create_test, get_tests_by_owner, get_all_tests, delete_test, \
    get_deleted_tests_by_owner, edit_test, get_tests_by_author_name, publish_or_unpublish_test, get_retakeable_tests, \
    get_test
from quiz.util.encoder import UUIDEncoder


@login_required
def create_test_endpoint():
    user = current_user
    res_id = create_test(name=request.json['name'],
                         description=request.json['description'],
                         user=user,
                         is_retakeable=request.json['is_retakeable'])
    ret = {'message': 'Тест добавлен', 'id': res_id}

    return make_response(jsonify(ret), 201)


@login_required
def get_test_endpoint():
    res = get_test(request.args['id'])
    if res[1] == 404:
        abort(404)

    return make_response(jsonify(res), res[0])


@login_required
def get_tests_by_owner_endpoint():
    user = current_user
    res = get_tests_by_owner(user)

    return make_response(json.dumps([obj.__dict__ for obj in res], cls=UUIDEncoder), 200)


@login_required
def get_all_tests_endpoint():
    quizzes = get_all_tests()
    return make_response(render_template("quiz/quizzes.html", quizzes=quizzes), 200)


@login_required
def get_retakeable_tests_endpoint():
    tests = get_retakeable_tests()

    return make_response(tests, 200)


@login_required
def get_deleted_tests_by_owner_endpoint():
    user = current_user
    res = get_deleted_tests_by_owner(user)

    return make_response(json.dumps([obj.__dict__ for obj in res], cls=UUIDEncoder), 200)


@login_required
def delete_test_endpoint():
    test_id = request.args['id']
    deleted = delete_test(current_user, test_id)
    if deleted == 404:
        ret = {'message': 'Тест не существует', 'id': test_id}
    elif deleted == 403:
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
                       description=request.json['description'],
                       is_retakeable=request.json['is_retakeable']
                       )
    if edited == 404:
        ret = {'message': 'Тест не существует', 'id': test_id}
    elif edited == 403:
        ret = {'message': 'Попытка редактировать чужой тест', 'id': test_id}
    else:
        ret = {'message': 'Тест редактирован', 'id': test_id}

    return make_response(jsonify(ret), edited)


@login_required
def get_tests_by_author_name_endpoint():
    tests = get_tests_by_author_name(request.json['author_name'])

    return make_response(json.dumps([obj.__dict__ for obj in tests], cls=UUIDEncoder), 200)


@login_required
def publish_or_unpublish_test_endpoint():
    is_to_publish = request.json['to_publish']
    test_id = request.args['id']
    published = publish_or_unpublish_test(user=current_user,
                                          test_id=test_id,
                                          is_to_publish=is_to_publish
                                          )
    if published == 404:
        ret = {'message': 'Тест не существует', 'id': test_id}
    elif published == 403:
        ret = {'message': 'Попытка опубликовать чужой тест', 'id': test_id}
    else:
        if is_to_publish:
            ret = {'message': 'Тест опубликован', 'id': test_id}
        else:
            ret = {'message': 'В данный момент тест невозможно пройти', 'id': test_id}

    return make_response(jsonify(ret), published)
