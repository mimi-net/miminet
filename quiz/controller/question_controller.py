import json

from flask import request, abort, make_response
from flask_login import login_required

from quiz.service.question_service import get_questions_by_section
from quiz.util.encoder import UUIDEncoder


@login_required
def get_questions_by_section_endpoint():
    res = get_questions_by_section(request.args.get('section_id', type=str))
    if res[1] == 404 or res[1] == 405:
        abort(res[1])
    else:
        return make_response(json.dumps([obj.__dict__ for obj in res[0]], cls=UUIDEncoder), res[1])