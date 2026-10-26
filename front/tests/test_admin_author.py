"""Regression tests for admin records losing their author (issue #542).

A blank ``created_by_user`` relation field in a flask-admin create form is
written to the model by ``populate_obj`` and, on flush, overwrites the
``created_by_id`` set in ``on_model_change`` with NULL. ``created_by_formatter``
then raised for such rows and the whole list page answered 500.
"""

from types import SimpleNamespace

import pytest

from app import app as flask_app
from miminet_admin import AnswerView, created_by_formatter
from miminet_admin import TestView as AdminTestView
from miminet_model import db
from quiz.entity.entity import Answer
from quiz.entity.entity import Test as QuizTest


@pytest.mark.parametrize(
    "view_cls, model",
    [(AdminTestView, QuizTest), (AnswerView, Answer)],
    ids=["test", "answer"],
)
def test_author_fields_are_not_in_create_form(view_cls, model):
    with flask_app.app_context():
        form_cls = view_cls(
            model, db.session, endpoint=f"t542_{model.__name__}"
        ).get_create_form()

    assert not hasattr(form_cls, "created_by_user")
    assert not hasattr(form_cls, "created_by_id")


def test_created_by_formatter_returns_nick(mocker):
    user_model = mocker.patch("miminet_admin.User")
    user_model.query.get.return_value = SimpleNamespace(nick="teacher")

    row = SimpleNamespace(id=1, created_by_id=7)

    assert created_by_formatter(None, None, row, "created_by_id") == "teacher"
    user_model.query.get.assert_called_once_with(7)


def test_created_by_formatter_tolerates_missing_author(mocker):
    user_model = mocker.patch("miminet_admin.User")

    row = SimpleNamespace(id=1, created_by_id=None)

    assert created_by_formatter(None, None, row, "created_by_id") == "—"
    user_model.query.get.assert_not_called()


def test_created_by_formatter_tolerates_deleted_user(mocker):
    user_model = mocker.patch("miminet_admin.User")
    user_model.query.get.return_value = None

    row = SimpleNamespace(id=1, created_by_id=42)

    assert created_by_formatter(None, None, row, "created_by_id") == "—"
