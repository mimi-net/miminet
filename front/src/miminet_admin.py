from datetime import date, datetime

from flask import redirect, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_admin.form import TimeField
from flask_admin.model import typefmt, InlineFormAdmin
from flask_login import current_user

from miminet_model import User
from quiz.entity.entity import Test, Section, TextQuestion

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
    MY_DEFAULT_FORMATTERS.update({
        type(None): typefmt.null_formatter,
        date: lambda view, value: value.strftime('%d.%m.%Y')
    })

    column_type_formatters = MY_DEFAULT_FORMATTERS


def created_by_formatter(view, context, model, name, **kwargs):
    user = User.query.get(model.created_by_id)
    if user and user.nick:
        return user.nick
    raise Exception("Error occurred while retrieving user nickname")


class TestView(MiminetAdminModelView):
    # Remove columns from list view
    column_exclude_list = ["is_deleted", "updated_on"]
    # Remove fields
    form_excluded_columns = ["is_deleted", "updated_on"]

    column_list = ("name", "description", "is_ready", "is_retakeable", "created_on", "created_by_id")
    column_sortable_list = ("name", "created_on", "created_by_id")

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "is_ready": "Тест готов",
        "is_retakeable": "Можно перепроходить",
        "created_on": "Дата создания",
        "created_by_id": "Автор"
    }

    column_formatters = {
        "created_by_id": created_by_formatter
    }

    pass


def get_test_name(view, context, model, name, **kwargs):
    test = Test.query.get(model.test_id)
    if test and test.name:
        return test.name
    raise Exception("Error occurred while retrieving test name")


class SectionView(MiminetAdminModelView):
    column_exclude_list = ["is_deleted", "updated_on"]
    form_excluded_columns = ["is_deleted", "updated_on"]

    column_list = ("test_id", "name", "description", "timer", "created_on", "created_by_id")
    column_sortable_list = ("name", "created_on", "created_by_id")

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "timer": "Время на прохождение",
        "test_id": "Раздел теста",
        "created_on": "Дата создания",
        "created_by_id": "Автор"
    }

    column_formatters = {
        "created_by_id": created_by_formatter,
        "test_id": get_test_name,
        "timer": lambda v, c, model, n, **kwargs: model.timer.strftime("%H:%M")
    }

    form_overrides = {
        "timer": TimeField
    }

    form_extra_fields = {"test_id": QuerySelectField(
        "Раздел теста",
        query_factory=lambda: Test.query.filter(Test.created_by_id == current_user.id).all(),
        get_pk=lambda test: test.id,
        get_label=lambda test: test.name
                               + (", " + test.description if test.description else "")
                               + (", " + User.query.get(test.created_by_id).nick) if test.created_by_id else "")
    }

    def on_model_change(self, form, model, is_created, **kwargs):
        # Call base class functionality
        super().on_model_change(form, model, is_created)

        model.test_id = str(model.test_id).removeprefix("<Test ")
        model.test_id = str(model.test_id).removesuffix(">")

        model.timer = datetime.strptime(str(model.timer), "%H:%M:%S")

    pass


def get_section_name(view, context, model, name, **kwargs):
    section = Section.query.get(model.section_id)
    if section and section.name:
        return section.name
    raise Exception("Error occurred while retrieving section name")


class TextQuestionInline(InlineFormAdmin):
    form_columns = ('id', 'text_type')
    form_choices = {
        "text_type": [
            ("matching", "matching"),
            ("sorting", "sorting"),
            ("variable", "variable"),
        ]
    }


class QuestionView(MiminetAdminModelView):
    column_exclude_list = ["is_deleted", "updated_on"]
    form_excluded_columns = ["is_deleted", "updated_on", "practice_question", "session_questions", "created_by_user",
                             "section", "question_type"]

    column_list = ("section_id", "text_question", "question_text", "created_on", "created_by_id")
    column_sortable_list = ("created_on", "created_by_id")

    column_labels = {
        "section_id": "Вопрос раздела",
        "created_on": "Дата создания",
        "created_by_id": "Автор",
        "question_text": "Текст вопроса"
    }

    column_formatters = {
        "created_by_id": created_by_formatter,
        "section_id": get_section_name
    }

    form_extra_fields = {"section_id": QuerySelectField(
        "Вопрос раздела",
        query_factory=lambda: Section.query.filter(Section.created_by_id == current_user.id).all(),
        get_pk=lambda section: section.id,
        get_label=lambda section: section.name +
                                  (", " + User.query.get(section.created_by_id).nick) if section.created_by_id else "")
    }

    inline_models = (TextQuestionInline(TextQuestion),)

    def on_model_change(self, form, model, is_created, **kwargs):
        # Call base class functionality
        super().on_model_change(form, model, is_created)

        model.section_id = str(model.section_id).removeprefix("<Section ")
        model.section_id = str(model.section_id).removesuffix(">")

        model.question_type = "text"
    pass
