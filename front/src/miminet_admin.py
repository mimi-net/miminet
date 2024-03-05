from datetime import date

from flask import redirect, url_for, session
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_admin.model import typefmt
from flask_login import current_user

from miminet_model import User, db
from quiz.entity.entity import Test

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


# Base model view with access and inaccess methods
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

    def date_format(view, value):
        return value.strftime('%d.%m.%Y')

    MY_DEFAULT_FORMATTERS = dict(typefmt.BASE_FORMATTERS)
    MY_DEFAULT_FORMATTERS.update({
        type(None): typefmt.null_formatter,
        date: date_format
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
    # column_display_pk = False
    # can_delete = False

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

    # def get_query(self):
    #     return self.session.query(self.model).filter(self.model.created_by_id == current_user.id)

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
        "test_id": get_test_name
    }

    form_extra_fields = {"test_id": QuerySelectField(
        "Раздел теста",
        query_factory=lambda: Test.query.all(),
        get_pk=lambda test: test.id,
        get_label=lambda test: test.name
                               + (", " + test.description if test.description else "")
                               + (", " + User.query.get(test.created_by_id).nick) if test.created_by_id else "")
    }

    pass
