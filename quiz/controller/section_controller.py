import json
from datetime import datetime
from uuid import UUID

from flask_login import login_required, current_user
from flask import request, make_response, jsonify, abort

from quiz.service.section_service import create_section, get_sections_by_test, get_deleted_sections_by_test, \
    delete_section, edit_section


class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return obj.hex
        return json.JSONEncoder.default(self, obj)


@login_required
def create_section_endpoint():
    user = current_user
    res = create_section(name=request.args.get('name', type=str),
                         description=request.args.get('description', type=str),
                         user=user,
                         test_id=request.args.get('test_id', type=str),
                         timer=datetime.strptime(request.args.get('timer', type=str), '%H:%M:%S')
                         )
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        ret = {'message': 'Секция добавлена', 'id': res[0]}

        return make_response(jsonify(ret), 201)


@login_required
def get_sections_by_test_endpoint():
    res = get_sections_by_test(request.args.get('test_id', type=str))
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        return make_response(json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder), res[1])


@login_required
def get_deleted_sections_by_test_endpoint():
    res = get_deleted_sections_by_test(request.args.get('test_id', type=str), current_user)
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        return make_response(json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder), res[1])


@login_required
def delete_section_endpoint():
    section_id = request.args.get('id', type=str)
    deleted = delete_section(current_user, section_id)
    if deleted == 404:
        ret = {'message': 'Секция не существует', 'id': section_id}
    elif deleted == 405:
        ret = {'message': 'Попытка удалить чужую секцию', 'id': section_id}
    else:
        ret = {'message': 'Секция удалена', 'id': section_id}

    return make_response(jsonify(ret), deleted)


@login_required
def edit_section_endpoint():
    section_id = request.form.get('id', type=str)
    edited = edit_section(user=current_user,
                          name=request.form.get('name', type=str),
                          section_id=section_id,
                          description=request.form.get('description', type=str),
                          timer=datetime.strptime(request.args.get('timer', type=str), '%H:%M:%S')
                          )
    if edited == 404:
        ret = {'message': 'Секции не существует', 'id': section_id}
    elif edited == 405:
        ret = {'message': 'Попытка редактировать чужую секцию', 'id': section_id}
    else:
        ret = {'message': 'Секция редактирована', 'id': section_id}

    return make_response(jsonify(ret), edited)
