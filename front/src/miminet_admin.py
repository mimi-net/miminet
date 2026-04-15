import json
from datetime import date

from flask import flash, redirect, request, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.fields import QuerySelectField
from flask_admin.form import DateTimePickerWidget, Select2Widget
from flask_admin.model import typefmt
from flask_login import current_user
from markupsafe import Markup
from miminet_model import Network, User, db
from quiz.entity.entity import (
    Question,
    QuestionCategory,
    QuizSession,
    Section,
    SessionQuestion,
    Test,
)
from quiz.service.network_upload_service import (
    create_check_task,
    create_check_task_json,
)
from quiz.util.dto import calculate_question_count
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from wtforms import DateTimeField, Form, SelectField, SubmitField, TextAreaField

ADMIN_ROLE_LEVEL = 1


def _pluralize_ru(value, forms):
    remainder_hundred = value % 100
    remainder_ten = value % 10

    if 11 <= remainder_hundred <= 14:
        return forms[2]
    if remainder_ten == 1:
        return forms[0]
    if 2 <= remainder_ten <= 4:
        return forms[1]
    return forms[2]


def _format_count(value, forms):
    return f"{value} {_pluralize_ru(value, forms)}"


def _build_test_cards(tests):
    cards = []

    for test in tests:
        sections = [section for section in test.sections if not section.is_deleted]
        question_count = sum(calculate_question_count(section) for section in sections)
        finished_sessions = sum(
            1
            for section in sections
            for session in section.quiz_sessions
            if not session.is_deleted and session.finished_at is not None
        )
        preview_sections = sections[:3]

        cards.append(
            {
                "name": test.name,
                "description": test.description,
                "status_label": ("Опубликован" if test.is_ready else "Черновик"),
                "retakeable_label": (
                    "Можно перепроходить"
                    if test.is_retakeable
                    else "Одна попытка на раздел"
                ),
                "section_label": _format_count(
                    len(sections), ("раздел", "раздела", "разделов")
                ),
                "question_label": _format_count(
                    question_count, ("задание", "задания", "заданий")
                ),
                "attempts_label": _format_count(
                    finished_sessions,
                    (
                        "завершенное прохождение",
                        "завершенных прохождения",
                        "завершенных прохождений",
                    ),
                ),
                "section_names": [section.name for section in preview_sections],
                "hidden_section_count": max(len(sections) - len(preview_sections), 0),
            }
        )

    return cards


def _get_admin_tests(user_id):
    return (
        Test.query.filter(
            Test.created_by_id == user_id,
            Test.is_deleted.is_(False),
        )
        .options(
            selectinload(Test.sections).selectinload(Section.quiz_sessions),
            selectinload(Test.sections).selectinload(Section.questions),
        )
        .order_by(Test.created_on.desc())
        .all()
    )


def _calculate_session_score(quiz_session):
    score = 0
    max_score = 0

    for session_question in quiz_session.sessions:
        if session_question.is_deleted:
            continue

        question = session_question.question
        is_practice = question is not None and question.question_type == 0

        if is_practice:
            score += session_question.score or 0
            max_score += session_question.max_score or 0
        else:
            score += 1 if session_question.is_correct else 0
            max_score += 1

    return score, max_score


def _build_statistics_groups(section_columns):
    groups = []

    for section in section_columns:
        if not groups or groups[-1]["test_id"] != section["test_id"]:
            groups.append(
                {
                    "test_id": section["test_id"],
                    "test_name": section["test_name"],
                    "colspan": 1,
                }
            )
        else:
            groups[-1]["colspan"] += 1

    return groups


def _build_statistics_data(tests):
    section_columns = []

    for test in tests:
        sections = [section for section in test.sections if not section.is_deleted]
        sections.sort(key=lambda section: section.id or 0)

        for section in sections:
            section_columns.append(
                {
                    "id": section.id,
                    "test_id": test.id,
                    "test_name": test.name,
                    "section_name": section.name,
                }
            )

    if not section_columns:
        return section_columns, []

    section_ids = [section["id"] for section in section_columns]
    latest_sessions_subquery = (
        db.session.query(
            QuizSession.id.label("session_id"),
            func.row_number()
            .over(
                partition_by=(QuizSession.created_by_id, QuizSession.section_id),
                order_by=(QuizSession.finished_at.desc(), QuizSession.id.desc()),
            )
            .label("row_num"),
        )
        .filter(
            QuizSession.section_id.in_(section_ids),
            QuizSession.is_deleted.is_(False),
            QuizSession.finished_at.isnot(None),
            QuizSession.created_by_id.isnot(None),
        )
        .subquery()
    )

    sessions = (
        db.session.query(QuizSession)
        .join(
            latest_sessions_subquery,
            latest_sessions_subquery.c.session_id == QuizSession.id,
        )
        .filter(latest_sessions_subquery.c.row_num == 1)
        .options(
            selectinload(QuizSession.sessions).selectinload(SessionQuestion.question),
            selectinload(QuizSession.created_by_user),
        )
        .all()
    )

    latest_session_by_user_section = {}
    users_by_id = {}

    for session in sessions:
        key = (session.created_by_id, session.section_id)
        if key in latest_session_by_user_section:
            continue

        latest_session_by_user_section[key] = session
        users_by_id[session.created_by_id] = session.created_by_user

    rows = []

    for user_id, user in users_by_id.items():
        cells = []
        total_score = 0
        completed_sections = 0

        for section in section_columns:
            session = latest_session_by_user_section.get((user_id, section["id"]))

            if session is None:
                cells.append({"has_result": False})
                continue

            score, max_score = _calculate_session_score(session)
            total_score += score
            completed_sections += 1
            cells.append(
                {
                    "has_result": True,
                    "score": score,
                    "max_score": max_score,
                    "guid": session.guid,
                }
            )

        if user and user.nick:
            user_name = user.nick
        elif user and user.email:
            user_name = user.email
        else:
            user_name = f"Пользователь {user_id}"

        rows.append(
            {
                "user_id": user_id,
                "user_name": user_name,
                "can_open_profile": user is not None,
                "total_score": total_score,
                "completed_sections": completed_sections,
                "cells": cells,
            }
        )

    rows.sort(
        key=lambda row: (
            -row["total_score"],
            -row["completed_sections"],
            row["user_name"].casefold(),
        )
    )

    for position, row in enumerate(rows, start=1):
        row["position"] = position

    return section_columns, rows


class MiminetAdminIndexView(AdminIndexView):
    @expose("/")
    def index(self):
        tests = _get_admin_tests(current_user.id)
        return self.render(
            "admin/index.html",
            test_cards=_build_test_cards(tests),
            statistics_url=url_for("admin.statistics"),
        )

    @expose("/statistics")
    def statistics(self):
        tests = _get_admin_tests(current_user.id)
        section_columns, user_rows = _build_statistics_data(tests)
        return self.render(
            "admin/statistics.html",
            section_columns=section_columns,
            test_groups=_build_statistics_groups(section_columns),
            user_rows=user_rows,
        )

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
        if hasattr(model, "created_by_id"):
            if not is_created and model.created_by_id != current_user.id:
                raise Exception("You are not allowed to edit this record.")
            if is_created:
                model.created_by_id = current_user.id
        else:
            pass

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
        "is_exam",
        "results_available_from",
        "created_on",
        "created_by_id",
        "meta",
    )
    column_sortable_list = ("name", "created_on", "created_by_id", "test_id")

    column_labels = {
        "name": "Название",
        "description": "Описание",
        "timer": "Время на прохождение (в минутах)",
        "test_id": "Раздел теста",
        "is_exam": "Контрольная работа",
        "results_available_from": "Открыть результаты с",
        "created_on": "Дата создания",
        "created_by_id": "Автор",
        "meta": "Мета раздел",
    }

    column_formatters = {
        "created_by_id": created_by_formatter,
        "test_id": get_test_name,
    }

    form_excluded_columns = [
        "created_by_id",
        "created_by_user",
        "created_on",
        "updated_on",
    ]

    # form_extra_fields = {
    #     "is_exam": BooleanField(default=False),
    #     # "results_available_from": DateTimeField(
    #     #     label="Дата открытия результатов",
    #     #     format="%d-%m-%Y %H:%M",
    #     #     description="Формат: d-m-Y, H:M. Время в мск. Обратите внимание, что без is_exam, ответы будут доступны в любом случае.",
    #     # ),
    #     "test_id": QuerySelectField(
    #         "Раздел теста",
    #         query_factory=lambda: Test.query.filter(
    #             Test.created_by_id == current_user.id
    #         ).all(),
    #         get_pk=lambda test: test.id,
    #         get_label=lambda test: (
    #             test.name
    #             + (", " + test.description if test.description else "")
    #             + (" (" + User.query.get(test.created_by_id).nick)
    #             + ")"
    #             if test.created_by_id
    #             else ""
    #         ),
    #     ),
    # }

    form_overrides = {"results_available_from": DateTimeField}

    form_args = {
        "results_available_from": {
            "widget": DateTimePickerWidget(),
            # 'format': '%d-%m-%Y %H:%M:%S',
            "label": "Дата открытия результатов",
            "description": "Формат: d-m-Y H:M:S. Время в мск. Обратите внимание, что без is_exam ответы будут доступны в любом случае.",
        }
    }

    # form_args = {
    #     'results_available_from': {
    #         'widget': DateTimePickerWidget(),
    #         'format': '%d-%m-%Y %H:%M:%S',
    #         'label': 'Дата открытия результатов',
    #         'description': 'Формат: d-m-Y H:M:S. Время в мск. Обратите внимание, что без is_exam ответы будут доступны в любом случае.'
    #     }
    # }

    def on_model_change(self, form, model, is_created, **kwargs):
        if is_created:
            if current_user.is_authenticated:
                model.created_by_id = current_user.id

        super().on_model_change(form, model, is_created)

        # model.test_id = model.test_id.get_id()

    pass


def get_section_name(view, context, model, name, **kwargs):
    if model.section_id is None:
        return "Без раздела"

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
                section.name + (" (" + User.query.get(section.created_by_id).nick + ")")
                if section.created_by_id
                else ""
            ),
            allow_blank=True,
            blank_text="Без раздела",
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
        super().on_model_change(form, model, is_created)

        if model.section_id:
            model.section_id = model.section_id.get_id()
        else:
            model.section_id = None

        model.category_id = model.category_id.get_id()
        model.text = Markup.escape(Markup.unescape(model.text))


def get_question_text(view, context, model, name, **kwargs):
    if not model.question_id:
        return "Вопрос не установлен"
    question = Question.query.get(model.question_id)
    return question.text if question and question.text else "Вопрос не найден"


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


class CheckByQuestionForm(Form):
    question_id = SelectField("Вопрос", coerce=int)
    requirements = TextAreaField("Requirements JSON")


class SessionQuestionView(MiminetAdminModelView):
    list_template = "admin/sessionQuestionList.html"

    can_create = False
    can_delete = False

    column_list = (
        "id",
        "quiz_session_id",
        "question_id",
        "question_text",
        "is_correct",
        "score",
        "max_score",
    )

    column_labels = {
        "id": "ID записи",
        "quiz_session_id": "Сессия",
        "question_id": "Вопрос (ID)",
        "question_text": "Текст вопроса",
        "is_correct": "Ответ верный",
        "score": "Набрано баллов",
        "max_score": "Максимум",
    }

    @staticmethod
    def fmt_question_text(view, context, model, name):
        q = Question.query.get(model.question_id)
        return q.text if q else "<вопрос не найден>"

    column_formatters = {
        "question_text": fmt_question_text,
    }

    @expose("/")
    def index_view(self, **kwargs):
        return super().index_view(**kwargs)

    @action("check_by_question", "Проверить по вопросу", None)
    def action_dummy(self, ids):
        return redirect(url_for(".check_by_question_view"))

    @expose("/check-by-question/", methods=["GET", "POST"])
    def check_by_question_view(self, **kwargs):
        all_q = db.session.query(Question.id, Question.text).distinct().all()
        choices = [
            (q.id, q.text[:50] + "…" if len(q.text) > 50 else q.text) for q in all_q
        ]

        form = CheckByQuestionForm(request.form)
        form.question_id.choices = choices

        if request.method == "POST" and form.validate():
            try:
                requirements = json.loads(form.requirements.data)
            except json.JSONDecodeError:
                flash("Некорректный JSON в requirements.", "error")
                return self.render("admin/check_by_question.html", form=form)

            sq_entries = (
                db.session.query(SessionQuestion)
                .filter(
                    SessionQuestion.question_id == form.question_id.data,
                    SessionQuestion.max_score == 0,
                    SessionQuestion.quiz_session_id.isnot(None),
                )
                .all()
            )
            if not sq_entries:
                flash("Нет новых записей для этого вопроса.", "warning")
                return self.render("admin/check_by_question.html", form=form)

            for sq in sq_entries:
                nm = Network.query.filter_by(guid=sq.network_guid).first()
                if not nm:
                    flash(f"Сеть с GUID {sq.network_guid} не найдена.", "error")
                    continue

                raw_data = nm.network
                if isinstance(raw_data, dict):
                    network = raw_data
                else:
                    try:
                        network = json.loads(raw_data)
                    except json.JSONDecodeError:
                        flash(
                            f"Сеть для записи {sq.id} не может быть прочитана.", "error"
                        )
                        continue

                try:
                    create_check_task(network, requirements, sq.id)
                except Exception as e:
                    flash(f"Ошибка при проверке записи {sq.id}: {e}", "error")

            flash(
                f"Запросы на проверку отправлены для {len(sq_entries)} записей.",
                "success",
            )
            return redirect(url_for(".index_view"))

        return self.render("admin/check_by_question.html", form=form)


class CreateCheckTaskForm(Form):
    guids = TextAreaField("GUID-ы сетей (по одному на строку)")
    requirements = TextAreaField("Requirements (JSON)")
    submit = SubmitField("Создать задачу проверки")


class CreateCheckTaskView(MiminetAdminModelView):
    @expose("/", methods=["GET", "POST"])
    def index(self):
        form = CreateCheckTaskForm(request.form)
        if request.method == "POST" and form.validate():
            try:
                guids = [
                    line.strip()
                    for line in form.guids.data.strip().splitlines()
                    if line.strip()
                ]

                networks = []
                for guid in guids:
                    network = Network.query.filter(Network.guid == guid).first()
                    if not network:
                        raise ValueError(f"Сеть с GUID {guid} не найдена.")
                    networks.append((json.loads(network.network), guid))

                reqs = json.loads(form.requirements.data)
                create_check_task_json(networks, reqs)
                flash("Задача проверки успешно создана.", "success")
                return redirect(url_for(".index"))
            except Exception as e:
                flash(f"Ошибка: {str(e)}", "error")

        return self.render("admin/create_check_task.html", form=form)
