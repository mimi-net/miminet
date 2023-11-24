import json
from datetime import datetime
from uuid import UUID

from flask_login import login_required, current_user
from flask import request, make_response, jsonify, abort

from quiz.service.section_service import create_section, get_sections_by_test, get_deleted_sections_by_test, \
    delete_section, edit_section
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
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        ret = {'message': 'Секция добавлена', 'id': res[0]}

        return make_response(jsonify(ret), 201)


@login_required
def get_sections_by_test_endpoint():
    res = get_sections_by_test(request.json['test_id'])
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        return make_response(json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder), res[1])


@login_required
def get_deleted_sections_by_test_endpoint():
    res = get_deleted_sections_by_test(request.json['test_id'], current_user)
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        return make_response(json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder), res[1])


@login_required
def delete_section_endpoint():
    section_id = request.json['id']
    deleted = delete_section(current_user, section_id)
    if deleted == 404:
        ret = {'message': 'Раздел не существует', 'id': section_id}
    elif deleted == 405:
        ret = {'message': 'Попытка удалить чужой раздел', 'id': section_id}
    else:
        ret = {'message': 'Раздел удалён', 'id': section_id}

    return make_response(jsonify(ret), deleted)


@login_required
def edit_section_endpoint():
    section_id = request.form.get('id', type=str)
    edited = edit_section(user=current_user,
                          name=request.json['name'],
                          section_id=section_id,
                          description=request.json['description'],
                          timer=datetime.strptime(request.json['timer'], '%H:%M:%S')
                          )
    if edited == 404:
        ret = {'message': 'Секции не существует', 'id': section_id}
    elif edited == 405:
        ret = {'message': 'Попытка редактировать чужую секцию', 'id': section_id}
    else:
        ret = {'message': 'Секция редактирована', 'id': section_id}

    return make_response(jsonify(ret), edited)
