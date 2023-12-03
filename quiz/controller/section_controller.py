import json
import requests
from datetime import datetime

from flask_login import login_required, current_user
from flask import request, make_response, jsonify, abort, render_template, url_for

from quiz.service.section_service import create_section, get_sections_by_test, get_deleted_sections_by_test, \
    delete_section, edit_section, get_section, publish_or_unpublish_test_by_section
from quiz.service.test_service import get_test
from quiz.util.encoder import UUIDEncoder


@login_required
def create_section_endpoint():
    user = current_user
    res = create_section(name=request.json['name'],
                         description=request.json['description'],
                         user=user,
                         test_id=request.json['test_id'],
                         timer=datetime.strptime(request.json['timer'], '%H:%M:%S')
                         )
    if res[1] == 404 or res[1] == 403:
        abort(res[1])

    ret = {'message': 'Раздел добавлен', 'id': res[0]}

    return make_response(jsonify(ret), res[1])


@login_required
def get_section_endpoint():
    res = get_section(request.args['id'])
    if res[1] == 404:
        abort(404)

    return make_response(jsonify(res), res[0])


@login_required
def get_sections_by_test_endpoint():
    test_id = request.args['test_id']
    res = get_sections_by_test(test_id)
    if res[1] == 404 or res[1] == 403:
        abort(res[1])
    else:
        sections = res[0]
        test = get_test(test_id)[0]
        return make_response(render_template("quiz/quiz.html", test=test, sections=sections), 200)


@login_required
def get_deleted_sections_by_test_endpoint():
    res = get_deleted_sections_by_test(request.args['test_id'], current_user)
    if res[1] == 404 or res[1] == 403:
        abort(res[1])
    else:
        return make_response(json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder), res[1])


@login_required
def delete_section_endpoint():
    section_id = request.args['id']
    deleted = delete_section(current_user, section_id)
    if deleted == 404:
        ret = {'message': 'Раздел не существует', 'id': section_id}
    elif deleted == 403:
        ret = {'message': 'Попытка удалить чужой раздел', 'id': section_id}
    else:
        ret = {'message': 'Раздел удалён', 'id': section_id}

    return make_response(jsonify(ret), deleted)


@login_required
def edit_section_endpoint():
    section_id = request.json['id']
    edited = edit_section(user=current_user,
                          name=request.json['name'],
                          section_id=section_id,
                          description=request.json['description'],
                          timer=datetime.strptime(request.json['timer'], '%H:%M:%S')
                          )
    if edited == 404:
        ret = {'message': 'Раздел не существует', 'id': section_id}
    elif edited == 403:
        ret = {'message': 'Попытка редактировать чужой раздел', 'id': section_id}
    else:
        ret = {'message': 'Раздел редактирован', 'id': section_id}

    return make_response(jsonify(ret), edited)


@login_required
def publish_or_unpublish_test_by_section_endpoint():
    is_to_publish = request.json['to_publish']
    section_id = request.args['id']
    published = publish_or_unpublish_test_by_section(user=current_user,
                                                     section_id=section_id,
                                                     is_to_publish=is_to_publish
                                                     )
    if published == 404:
        ret = {'message': 'Тест по данной секции не существует', 'id': section_id}
    elif published == 403:
        ret = {'message': 'Попытка опубликовать чужой тест по данной секции ', 'id': section_id}
    else:
        if is_to_publish:
            ret = {'message': 'Тест по данной секции опубликован', 'id': section_id}
        else:
            ret = {'message': 'В данный момент тест по данной секции невозможно пройти', 'id': section_id}

    return make_response(jsonify(ret), published)
