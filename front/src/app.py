import sys
from datetime import datetime

from flask import Flask, make_response, render_template
from flask_login import current_user, login_required
from flask_migrate import Migrate
from miminet_auth import (
    google_callback,
    google_login,
    login_index,
    login_manager,
    logout,
    user_profile,
    vk_callback,
)
from miminet_config import SECRET_KEY, SQLITE_DATABASE_NAME
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
)
from miminet_shark import mimishark_page
from miminet_simulation import check_simulation, run_simulation
from quiz.controller.question_controller import (
    create_question_endpoint,
    get_questions_by_section_endpoint,
    delete_question_endpoint,
)
from quiz.controller.quiz_session_controller import (
    start_session_endpoint,
    get_question_by_session_question_id_endpoint,
    finish_session_endpoint,
    answer_on_session_question_endpoint,
    session_result_endpoint,
    get_results_by_user_endpoint,
)
from quiz.controller.section_controller import (
    create_section_endpoint,
    get_sections_by_test_endpoint,
)
from quiz.controller.test_controller import (
    create_test_endpoint,
    get_all_tests_endpoint,
    get_tests_by_owner_endpoint,
    get_deleted_tests_by_owner_endpoint,
    delete_test_endpoint,
    edit_test_endpoint,
    get_test_endpoint,
    publish_or_unpublish_test_endpoint,
)

app = Flask(
    __name__, static_url_path="", static_folder="static", template_folder="templates"
)

# SQLAlchimy config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + SQLITE_DATABASE_NAME
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
app.add_url_rule("/auth/vk_callback", methods=["GET"], view_func=vk_callback)
app.add_url_rule("/auth/google_callback", methods=["GET"], view_func=google_callback)
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

# Quiz
app.add_url_rule("/quiz/test/create", methods=["POST"], view_func=create_test_endpoint)
app.add_url_rule(
    "/quiz/test/owner", methods=["GET"], view_func=get_tests_by_owner_endpoint
)
app.add_url_rule("/quiz/test/all", methods=["GET"], view_func=get_all_tests_endpoint)
app.add_url_rule(
    "/quiz/test/owner/deleted",
    methods=["GET"],
    view_func=get_deleted_tests_by_owner_endpoint,
)
app.add_url_rule(
    "/quiz/test/delete", methods=["DELETE"], view_func=delete_test_endpoint
)
app.add_url_rule("/quiz/test/edit", methods=["PUT"], view_func=edit_test_endpoint)
app.add_url_rule("/quiz/test/get", methods=["GET"], view_func=get_test_endpoint)
app.add_url_rule(
    "/quiz/test/publish", methods=["PUT"], view_func=publish_or_unpublish_test_endpoint
)

app.add_url_rule(
    "/quiz/section/create", methods=["POST"], view_func=create_section_endpoint
)
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
    "/quiz/session/finish", methods=["PUT"], view_func=finish_session_endpoint
)
app.add_url_rule(
    "/quiz/session/result", methods=["GET"], view_func=session_result_endpoint
)
app.add_url_rule(
    "/quiz/session/results", methods=["GET"], view_func=get_results_by_user_endpoint
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
        .filter(Network.is_task == False)
        .order_by(Network.id.desc())
        .all()
    )
    return render_template("home.html", networks=networks)


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
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            init_db(app)
    else:
        app.run()
