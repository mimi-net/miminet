from flask import redirect, url_for, session
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_login import current_user

from miminet_model import User

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


class TestView(MiminetAdminModelView):
    # Remove columns from list view
    column_exclude_list = ["is_deleted", "updated_on"]
    # Remove fields
    form_excluded_columns = ["is_deleted", "updated_on"]
    # column_display_pk = False
    # can_delete = False

    column_list = ("name", "description", "is_ready", "is_retakeable", "created_on", "created_by_id")
    column_sortable_list = ("name", "created_on", "created_by_id")
    column_searchable_list = ("name", "created_by_id")

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "is_ready": "Тест готов",
        "is_retakeable": "Можно перепроходить",
        "created_on": "Дата создания",
        "created_by_id": "Автор"
    }

    def _column_formatter(view, context, model, name, **kwargs):
        user_nick = User.query.get(model.created_by_id).nick
        if user_nick:
            return user_nick
        raise Exception("Error occurred while retrieving user nickname")

    column_formatters = {
        "created_by_id": _column_formatter
    }

    def on_model_change(self, form, model, is_created, **kwargs):
        if model.created_by_id != current_user.id:
            raise Exception("You are not allowed to edit this record.")

    # def get_query(self):
    #     return self.session.query(self.model).filter(self.model.created_by_id == current_user.id)

    pass

# class SectionView(MiminetAdminModelView):

