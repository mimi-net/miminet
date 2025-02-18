from datetime import date

from flask import redirect, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_admin.form import Select2Widget
from flask_admin.model import typefmt
from flask_login import current_user
from markupsafe import Markup
from wtforms import SelectField, TextAreaField

from miminet_model import db, User, QuestionCategory
from quiz.entity.entity import Test, Section, Question

ADMIN_ROLE_LEVEL = 1


class MiminetAdminIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        return self.render("admin/index.html")

    def is_accessible(self):
        if current_user.is_authenticated:
            if current_user.role >= ADMIN_ROLE_LEVEL:
                return True
        else:
            return False

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login_index"))


# Base model view
class MiminetAdminModelView(ModelView):
    # Remove columns from list view
    column_exclude_list = ["is_deleted", "updated_on"]
    # Remove fields
    form_excluded_columns = ["is_deleted", "updated_on", "created_on"]

    can_set_page_size = True

    def is_accessible(self):
        if current_user.is_authenticated:
            if current_user.role >= ADMIN_ROLE_LEVEL:
                return True
        else:
            return False

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login_index"))

    def on_model_change(self, form, model, is_created, **kwargs):
        if not is_created and model.created_by_id != current_user.id:
            raise Exception("You are not allowed to edit this record.")
        if is_created:
            model.created_by_id = current_user.id

    MY_DEFAULT_FORMATTERS = dict(typefmt.BASE_FORMATTERS)
    MY_DEFAULT_FORMATTERS.update(
        {
            type(None): typefmt.null_formatter,
            date: lambda view, value: value.strftime("%d.%m.%Y"),
        }
    )

    column_type_formatters = MY_DEFAULT_FORMATTERS


def created_by_formatter(view, context, model, name, **kwargs):
    user = User.query.get(model.created_by_id)
    if user and user.nick:
        return user.nick
    raise Exception("Error occurred while retrieving user nickname")


class TestView(MiminetAdminModelView):
    column_list = (
        "name",
        "description",
        "is_ready",
        "is_retakeable",
        "created_on",
        "created_by_id",
    )
    column_sortable_list = ("name", "created_on", "created_by_id")

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "is_ready": "Тест готов",
        "is_retakeable": "Можно перепроходить",
        "created_on": "Дата создания",
        "created_by_id": "Автор",
    }

    column_formatters = {"created_by_id": created_by_formatter}

    pass


def get_test_name(view, context, model, name, **kwargs):
    test = Test.query.get(model.test_id)
    if test and test.name:
        return test.name
    raise Exception("Error occurred while retrieving test name")


class SectionView(MiminetAdminModelView):
    column_list = (
        "test_id",
        "name",
        "description",
        "timer",
        "created_on",
        "created_by_id",
    )
    column_sortable_list = ("name", "created_on", "created_by_id", "test_id")

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "timer": "Время на прохождение (в минутах)",
        "test_id": "Раздел теста",
        "created_on": "Дата создания",
        "created_by_id": "Автор",
    }

    column_formatters = {
        "created_by_id": created_by_formatter,
        "test_id": get_test_name,
    }

    form_extra_fields = {
        "test_id": QuerySelectField(
            "Раздел теста",
            query_factory=lambda: Test.query.filter(
                Test.created_by_id == current_user.id
            ).all(),
            get_pk=lambda test: test.id,
            get_label=lambda test: (
                test.name
                + (", " + test.description if test.description else "")
                + (" (" + User.query.get(test.created_by_id).nick)
                + ")"
                if test.created_by_id
                else ""
            ),
        )
    }

    def on_model_change(self, form, model, is_created, **kwargs):
        # Call base class functionality
        super().on_model_change(form, model, is_created)

        model.test_id = model.test_id.get_id()

    pass


def get_section_name(view, context, model, name, **kwargs):
    section = Section.query.get(model.section_id)
    if section and section.name:
        return section.name
    raise Exception("Error occurred while retrieving section name")


def get_question_type(view, context, model, name, **kwargs):
    types = {
        0: "Практическое задание",
        1: "С вариантами ответов",
        2: "На сортировку",
        3: "На сопоставление",
    }
    return types.get(model.question_type, "")


class QuestionView(MiminetAdminModelView):
    form_excluded_columns = MiminetAdminModelView.form_excluded_columns + [
        "practice_question",
        "session_questions",
        "created_by_user",
        "section",
    ]

    form_overrides = {
        "text": TextAreaField,
    }

    form_widget_args = {
        "text": {"rows": 4, "style": "font-family: monospace; width: 680px;"},
    }

    column_list = (
        "section_id",
        "text",
        "explanation",
        "question_type",
        "created_on",
        "created_by_id",
        "category_id",
    )
    column_sortable_list = ("created_on", "created_by_id", "section_id")

    column_labels = {
        "section_id": "Вопрос раздела",
        "created_on": "Дата создания",
        "explanation": "Пояснение",
        "created_by_id": "Автор",
        "question_type": "Тип вопроса",
        "text": "Текст вопроса",
        "category_id": "Категория",
    }

    column_formatters = {
        "created_by_id": created_by_formatter,  # type: ignore
        "section_id": get_section_name,  # type: ignore
        "question_type": get_question_type,  # type: ignore
        "text": lambda v, c, model, n, **kwargs: Markup.unescape(model.text),
    }

    form_extra_fields = {
        "section_id": QuerySelectField(
            "Вопрос раздела",
            query_factory=lambda: Section.query.filter(
                Section.created_by_id == current_user.id
            ).all(),
            get_pk=lambda section: section.id,
            get_label=lambda section: (
                section.name + (" (" + User.query.get(section.created_by_id).nick) + ")"
                if section.created_by_id
                else ""
            ),
        ),
        "question_type": SelectField(
            "Тип вопроса",
            choices=[
                (0, "Практическое задание"),
                (1, "С вариантами ответов"),
                (2, "На сортировку"),
                (3, "На сопоставление"),
            ],
            widget=Select2Widget(),
        ),
        "category_id": QuerySelectField(
            "Категория вопроса",
            query_factory=lambda: db.session.query(QuestionCategory),
            get_pk=lambda question_category: question_category.id,
            get_label=lambda question_category: question_category.name,
        ),
    }

    def on_model_change(self, form, model, is_created, **kwargs):
        # Call base class functionality
        super().on_model_change(form, model, is_created)

        model.section_id = model.section_id.get_id()
        model.category_id = model.category_id.get_id()

        model.text = Markup.escape(Markup.unescape(model.text))

    pass


def get_question_text(view, context, model, name, **kwargs):
    question = Question.query.get(model.question_id)
    if question and question.text:
        return question.text
    raise Exception("Error occurred while retrieving question text")


class AnswerView(MiminetAdminModelView):
    column_list = (
        "question_id",
        "variant",
        "is_correct",
        "position",
        "left",
        "right",
        "created_by_id",
    )
    column_sortable_list = ("created_by_id", "question_id")

    column_labels = {
        "question_id": "Вопрос",
        "variant": "Вариант ответа",
        "position": "Позиция ответа",
        "left": "Левая часть",
        "right": "Правая часть",
        "created_by_id": "Автор",
    }

    column_formatters = {
        "question_id": get_question_text,
        "created_by_id": created_by_formatter,
    }

    form_extra_fields = {
        "question_id": QuerySelectField(
            "Вопрос",
            query_factory=lambda: Question.query.all(),
            get_pk=lambda question: question.id,
            get_label=lambda question: (
                question.text
                + (" (" + User.query.get(question.created_by_id).nick)
                + ")"
                if question.created_by_id
                else ""
            ),
        )
    }

    def on_model_change(self, form, model, is_created, **kwargs):
        # Call base class functionality
        super().on_model_change(form, model, is_created)

        model.question_id = str(model.question_id).removeprefix("<Question ")
        model.question_id = str(model.question_id).removesuffix(">")

        if model.variant:
            model.variant = Markup.escape(Markup.unescape(model.variant))

        if model.left:
            model.left = Markup.escape(Markup.unescape(model.left))

        if model.right:
            model.right = Markup.escape(Markup.unescape(model.right))

    pass


class QuestionCategoryView(MiminetAdminModelView):
    column_list = ("name",)

    column_labels = {
        "name": "Название",
    }

    pass
