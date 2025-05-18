import sys
from datetime import datetime

from flask import Flask, make_response, render_template
from flask_admin import Admin
from flask_login import current_user, login_required
from flask_migrate import Migrate

from miminet_admin import (
    MiminetAdminIndexView,
    TestView,
    SectionView,
    QuestionView,
    AnswerView,
    QuestionCategoryView,
    SessionQuestionView,
    CreateCheckTaskView,
)
from miminet_auth import (
    google_callback,
    google_login,
    insert_test_user,
    login_index,
    login_manager,
    logout,
    remove_test_user,
    user_profile,
    vk_callback,
    vk_login,
    yandex_login,
    yandex_callback,
    tg_callback,
)
from miminet_config import SECRET_KEY
from miminet_host import (
    delete_job,
    save_host_config,
    save_hub_config,
    save_router_config,
    save_server_config,
    save_switch_config,
)
from miminet_model import Network, db, init_db
from miminet_network import (
    copy_network,
    create_network,
    delete_network,
    move_nodes,
    post_nodes,
    post_nodes_edges,
    update_network_config,
    upload_network_picture,
    web_network,
    web_network_shared,
    get_emulation_queue_size,
    get_last_emulation_time,
)
from miminet_shark import mimishark_page
from miminet_simulation import check_simulation, run_simulation
from quiz.controller.question_controller import (
    get_questions_by_section_endpoint,
    create_question_endpoint,
    delete_question_endpoint,
)
from quiz.controller.image_controller import upload_image_endpoint
from quiz.controller.quiz_session_controller import (
    start_session_endpoint,
    get_question_by_session_question_id_endpoint,
    finish_session_endpoint,
    answer_on_session_question_endpoint,
    session_result_endpoint,
    get_result_by_session_guid_endpoint,
    check_network_task_endpoint,
    finish_old_session_endpoint,
    get_session_question_json,
)
from quiz.controller.section_controller import (
    get_sections_by_test_endpoint,
)
from quiz.controller.test_controller import (
    get_all_tests_endpoint,
    get_tests_by_owner_endpoint,
    get_test_endpoint,
)
from quiz.entity.entity import (
    Section,
    Test,
    Question,
    Answer,
    QuestionCategory,
    SessionQuestion,
)

from quiz.controller.image_controller import image_routes

app = Flask(
    __name__, static_url_path="", static_folder="static", template_folder="templates"
)

# SQLAlchimy config
POSTGRES_HOST = "172.18.0.4"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "my_postgres"
POSTGRES_DB_NAME = "miminet"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config["SECRET_KEY"] = SECRET_KEY
app.config["SESSION_COOKIE_NAME"] = "mimi_session"

# Init Databases
db.init_app(app)

# Init Flask-Migrate
migrate = Migrate(app, db)

# Init LoginManager
login_manager.init_app(app)

# Init Sitemap
zero_days_ago = (datetime.now()).date().isoformat()

# App add_url_rule
# Login
app.add_url_rule("/auth/login.html", methods=["GET", "POST"], view_func=login_index)
app.add_url_rule("/auth/google_login", methods=["GET"], view_func=google_login)
app.add_url_rule("/auth/vk_login", methods=["GET"], view_func=vk_login)
app.add_url_rule("/auth/yandex_login", methods=["GET"], view_func=yandex_login)
app.add_url_rule("/auth/vk_callback", methods=["GET"], view_func=vk_callback)
app.add_url_rule("/auth/google_callback", methods=["GET"], view_func=google_callback)
app.add_url_rule("/auth/yandex_callback", methods=["GET"], view_func=yandex_callback)
app.add_url_rule("/auth/tg_callback", methods=["GET"], view_func=tg_callback)
app.add_url_rule("/user/profile.html", methods=["GET", "POST"], view_func=user_profile)
app.add_url_rule("/auth/logout", methods=["GET"], view_func=logout)

# Network
app.add_url_rule("/create_network", methods=["GET"], view_func=create_network)
app.add_url_rule("/web_network", methods=["GET"], view_func=web_network)
app.add_url_rule("/web_network_shared", methods=["GET"], view_func=web_network_shared)
app.add_url_rule(
    "/network/update_network_config",
    methods=["GET", "POST"],
    view_func=update_network_config,
)
app.add_url_rule("/delete_network", methods=["GET", "POST"], view_func=delete_network)
app.add_url_rule("/post_network_nodes", methods=["GET", "POST"], view_func=post_nodes)
app.add_url_rule("/post_nodes_edges", methods=["POST"], view_func=post_nodes_edges)
app.add_url_rule("/move_network_nodes", methods=["POST"], view_func=move_nodes)
app.add_url_rule(
    "/network/upload_network_picture",
    methods=["GET", "POST"],
    view_func=upload_network_picture,
)
app.add_url_rule("/network/copy_network", methods=["POST"], view_func=copy_network)

# Simulation
app.add_url_rule("/run_simulation", methods=["POST"], view_func=run_simulation)
app.add_url_rule("/check_simulation", methods=["GET"], view_func=check_simulation)

# Emulation queue
app.add_url_rule(
    "/emulation_queue/size", methods=["GET"], view_func=get_emulation_queue_size
)
app.add_url_rule(
    "/emulation_queue/time", methods=["GET"], view_func=get_last_emulation_time
)


# Hosts
app.add_url_rule(
    "/host/save_config", methods=["GET", "POST"], view_func=save_host_config
)
app.add_url_rule(
    "/host/router_save_config", methods=["GET", "POST"], view_func=save_router_config
)
app.add_url_rule(
    "/host/server_save_config", methods=["GET", "POST"], view_func=save_server_config
)
app.add_url_rule("/host/delete_job", methods=["GET", "POST"], view_func=delete_job)
app.add_url_rule(
    "/host/hub_save_config", methods=["GET", "POST"], view_func=save_hub_config
)
app.add_url_rule(
    "/host/switch_save_config", methods=["GET", "POST"], view_func=save_switch_config
)

# MimiShark
app.add_url_rule("/host/mimishark", methods=["GET"], view_func=mimishark_page)
app.add_url_rule("/router/mimishark", methods=["GET"], view_func=mimishark_page)
app.add_url_rule("/server/mimishark", methods=["GET"], view_func=mimishark_page)
app.add_url_rule("/hub/mimishark", methods=["GET"], view_func=mimishark_page)
app.add_url_rule("/switch/mimishark", methods=["GET"], view_func=mimishark_page)

# Quiz
app.add_url_rule(
    "/quiz/test/owner", methods=["GET"], view_func=get_tests_by_owner_endpoint
)
app.add_url_rule("/quiz/test/all", methods=["GET"], view_func=get_all_tests_endpoint)
app.add_url_rule("/quiz/test/get", methods=["GET"], view_func=get_test_endpoint)

app.add_url_rule(
    "/quiz/section/test/all", methods=["GET"], view_func=get_sections_by_test_endpoint
)

app.add_url_rule(
    "/quiz/question/create", methods=["POST"], view_func=create_question_endpoint
)

app.add_url_rule(
    "/quiz/question/delete", methods=["DELETE"], view_func=delete_question_endpoint
)

app.add_url_rule(
    "/quiz/question/all", methods=["GET"], view_func=get_questions_by_section_endpoint
)

app.add_url_rule(
    "/quiz/session/question/json", methods=["GET"], view_func=get_session_question_json
)

app.add_url_rule(
    "/quiz/session/start", methods=["POST"], view_func=start_session_endpoint
)
app.add_url_rule(
    "/quiz/session/question",
    methods=["GET"],
    view_func=get_question_by_session_question_id_endpoint,
)
app.add_url_rule(
    "/quiz/session/answer",
    methods=["POST"],
    view_func=answer_on_session_question_endpoint,
)

app.add_url_rule(
    "/quiz/session/check_network_task",
    methods=["POST"],
    view_func=check_network_task_endpoint,
)

app.add_url_rule(
    "/quiz/session/finish", methods=["PUT"], view_func=finish_session_endpoint
)
app.add_url_rule(
    "/quiz/session/finishold", methods=["PUT"], view_func=finish_old_session_endpoint
)
app.add_url_rule(
    "/quiz/session/result", methods=["GET"], view_func=session_result_endpoint
)
app.add_url_rule(
    "/quiz/user/session/result",
    methods=["GET"],
    view_func=get_result_by_session_guid_endpoint,
)
app.add_url_rule(
    "/quiz/images/upload", methods=["POST"], view_func=upload_image_endpoint
)

app.register_blueprint(image_routes)

# Init Flask-admin
admin = Admin(
    app,
    index_view=MiminetAdminIndexView(),
    name="Miminet Admin",
    template_mode="bootstrap4",
)

admin.add_view(TestView(Test, db.session))
admin.add_view(SectionView(Section, db.session))
admin.add_view(QuestionView(Question, db.session))
admin.add_view(AnswerView(Answer, db.session))
admin.add_view(QuestionCategoryView(QuestionCategory, db.session))
admin.add_view(SessionQuestionView(SessionQuestion, db.session))
admin.add_view(
    CreateCheckTaskView(
        Network,
        db.session,
        name="Создать задачу проверки",
        endpoint="create_check_task",
    )
)


@app.route("/")
def index():  # put application's code here
    return render_template("index.html")


@app.route("/home")
@login_required
def home():
    user = current_user
    networks = (
        Network.query.filter(Network.author_id == user.id)
        .filter(Network.is_task.is_(False))
        .order_by(Network.id.desc())
        .all()
    )
    return render_template("home.html", networks=networks)


@app.route("/course")
def course():
    return render_template("course.html")


@app.route("/examples")
def examples():
    guids = [
        "d5eb566d-402e-442f-a98a-d5341568a5c9",
        "385ccc51-9a6e-4b9a-8e90-fbf27ae73186",
        "0a1be702-d7fb-4e97-a8ae-fe9cb75fcf32",
        "7509b963-d190-4aad-8d90-9be42f302bbb",
        "19e7c6b6-9541-4602-8c78-d0c64c069b41",
        "076f1ae4-1a6d-42fd-b8f5-9c09cdc4f930",
        "d35bcad2-b2be-4c2a-9902-26d4edd0bb1d",
        "4fc0fafb-2a16-4244-a664-3f1e8f788a63",
        "6994b921-cc0f-4cbd-b209-7f30784027d7",
        "1646e111-1a47-4d98-a253-c396904e5351",
        "1ccd87d4-a74f-485e-a95e-e1111c041fc7",
        "fe1fc02f-6bb4-421d-94cb-6902f826e30d",
        "993e2d62-ae6c-4b62-9ec4-6d90f768b56a",
    ]
    networks = (
        Network.query.filter(Network.guid.in_(guids)).order_by(Network.id.asc()).all()
    )
    return render_template("examples.html", networks=networks)


@app.route("/sitemap.xml", methods=["GET"])
@app.route("/Sitemap.xml", methods=["GET"])
def sitemap():
    """Generate sitemap.xml. Makes a list of urls and date modified."""
    pages = []
    skip_pages = [
        "/nooffer.html",
        "/Sitemap.xml",
        "/sitemap.xml",
        "/404.html",
        "/auth/google_login",
        "/auth/google_callback",
        "/auth/vk_callback",
        "/auth/yandex_login",
        "/auth/yandex_callback",
        "/auth/tg_callback",
        "/auth/logout",
        "/run_simulation",
        "/check_simulation",
        "/network/update_network_config",
        "/host/save_config",
        "/host/delete_job",
        "/host/hub_save_config",
        "/host/switch_save_config",
        "/user/profile.html",
        "/delete_network",
        "/post_network_nodes",
        "/network/upload_network_picture",
        "/home",
    ]

    # static pages
    for rule in app.url_map.iter_rules():
        if rule.rule in skip_pages:
            continue

        # Skip admin URL
        if "admin/" in rule.rule:
            continue

        if "GET" in rule.methods and len(rule.arguments) == 0:
            pages.append(["https://miminet.ru" + str(rule.rule), zero_days_ago])

    sitemap_xml = render_template("sitemap_template.xml", pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"
    return response


if __name__ == "__main__":
    init_db(app)

    if len(sys.argv) > 1:
        if sys.argv[1] == "dev":
            insert_test_user(app)
        elif sys.argv[1] == "prod":
            remove_test_user(app)
    else:
        app.run()
