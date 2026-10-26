"""Regression test for the slow admin section form (issue #543).

The questions/quiz_sessions relation selects listed every question and quiz
session of the section, so editing a section that many users had taken took
seconds to render.
"""

from app import app as flask_app
from miminet_admin import SectionView
from miminet_model import db
from quiz.entity.entity import Section


def test_section_form_has_no_relation_selects():
    with flask_app.app_context():
        form_cls = SectionView(
            Section, db.session, endpoint="t543_section"
        ).get_create_form()

    assert not hasattr(form_cls, "questions")
    assert not hasattr(form_cls, "quiz_sessions")
    # The fields the admin actually edits are still there.
    assert hasattr(form_cls, "name")
    assert hasattr(form_cls, "test")
