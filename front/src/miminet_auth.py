import json
import os
import pathlib
import uuid

import google.auth.transport.requests
import requests
from flask import flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from miminet_model import Network, User, db
from miminet_config import make_example_net_switch_and_hub
from pip._vendor import cachecontrol
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash

# Global variables
UPLOAD_FOLDER = "static/avatar/"
UPLOAD_TMP_FOLDER = "static/tmp/avatar/"
ALLOWED_EXTENSIONS = {"bmp", "png", "jpg", "jpeg"}

login_manager = LoginManager()
login_manager.login_view = "login_index"

# create an alias of login_required decorator
login_required = login_required

# Google auth (https://github.com/code-specialist/flask_google_login/blob/main/app.py)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_google.json")

GOOGLE_CLIENT_ID = ""
VK_CLIENT_ID = ""
VK_CLIENT_SECRET = ""
VK_REDIRECT_URI = ""

if os.path.exists(client_secrets_file):
    with open(client_secrets_file, "r") as file:
        google_json = json.loads(file.read())

    GOOGLE_CLIENT_ID = google_json["web"]["client_id"]

vk_secrets_file = os.path.join(pathlib.Path(__file__).parent, "vk_auth.json")

if os.path.exists(vk_secrets_file):
    with open(vk_secrets_file, "r") as file:
        vk_json = json.loads(file.read())
    VK_CLIENT_ID = vk_json["web"]["client_id"]
    VK_CLIENT_SECRET = vk_json["web"]["client_secret"]
    VK_REDIRECT_URI = vk_json["web"]["redirect_uri"]


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def handle_needs_login():
    flash("Для выполнения этого действия необходимо войти.")
    return redirect(url_for("login_index", next=request.endpoint))


def redirect_next_url(fallback):
    if "next_url" not in session:
        redirect(fallback)
    try:
        dest_url = url_for(session["next_url"])
        return redirect(dest_url)
    except Exception:
        return redirect(fallback)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_index():
    if current_user.is_authenticated:
        return redirect(url_for("user_profile"))

    next_url = request.args.get("next")

    if next_url:
        session["next_url"] = next_url
    else:
        session.pop("next_url", None)

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password_hash, password):
                login_user(user, remember=True)
                return redirect_next_url(fallback=url_for("user_profile"))
            else:
                flash("Пара логин и пароль указаны неверно", category="error")
                return render_template("auth/login.html", user=current_user)
        else:
            flash("Пользователя с таким почтовым адресом нет", category="error")
            return render_template("auth/login.html", user=current_user)

    return render_template("auth/login.html", user=current_user)


@login_required
def user_profile():
    user = User.query.filter_by(id=current_user.id).first()

    if request.method == "POST":
        last_name = request.form.get("last_name").strip()
        first_name = request.form.get("first_name").strip()
        middle_name = request.form.get("middle_name").strip()
        how_to_contact = request.form.get("how_to_contact").strip()

        if first_name:
            user.first_name = first_name
            user.middle_name = middle_name
            user.last_name = last_name
            user.how_to_contact = how_to_contact
            db.session.commit()

    return render_template("auth/profile.html", user=user)


def password_recovery():
    return render_template("auth/password_recovery.html")


@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


def google_login():
    flow = Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
    )

    flow.redirect_uri = url_for("google_callback", _external=True)
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true"
    )
    session["state"] = state
    return redirect(authorization_url)


def google_callback():
    state = session["state"]
    print(request.args.get("state"), session)
    user_is_new = False

    if not state:
        redirect(url_for("login_index"))

    flow = Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=[
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ],
    )

    flow.redirect_uri = url_for("google_callback", _external=True)
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=60,
    )

    user = User.query.filter_by(google_id=id_info.get("sub")).first()

    # New user?
    if user is None:
        # Yes
        try:
            avatar_uri = os.urandom(16).hex()
            avatar_uri = avatar_uri + ".jpg"

            if "picture" in id_info:
                r = requests.get(id_info.get("picture"), allow_redirects=True)
                open("static/avatar/" + avatar_uri, "wb").write(r.content)

            f = id_info.get("family_name", "")
            n = id_info.get("given_name", "")

            new_user = User(
                nick=f + n,
                avatar_uri=avatar_uri,
                google_id=id_info.get("sub"),
                email=id_info.get("email"),
            )
            db.session.add(new_user)
            db.session.commit()
            user_is_new = True
        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.__dict__["orig"])
            print(error)
            print("Can't add new user to Database")
            flash(error, category="error")
            return redirect(url_for("login_index"))

        user = User.query.filter_by(google_id=id_info.get("sub")).first()

    login_user(user, remember=True)

    if user_is_new:
        u = uuid.uuid4()
        n = Network(
            author_id=user.id,
            network=make_example_net_switch_and_hub(),
            title="Свитч и хаб (пример сети)",
            guid=str(u),
            preview_uri="switch_and_hub.png",
        )
        db.session.add(n)
        db.session.commit()

    return redirect_next_url(fallback=url_for("home"))


# https://vk.com/dev/authcode_flow_user
def vk_callback():
    user_code = request.args.get("code")
    user_is_new = False

    if not user_code:
        return redirect(url_for("login_index"))

    # Get access token
    response = requests.get(
        f"https://oauth.vk.com/access_token?client_id={VK_CLIENT_ID}&client_secret={VK_CLIENT_SECRET}&redirect_uri={VK_REDIRECT_URI}&code="
        + user_code
    )
    access_token_json = json.loads(response.text)

    if "error" in access_token_json:
        return redirect(url_for("login_index"))

    vk_id = access_token_json.get("user_id")
    access_token = access_token_json.get("access_token")
    vk_email = access_token_json.get("email")

    # Get user name
    response = requests.get(
        "https://api.vk.com/method/users.get?user_ids="
        + str(vk_id)
        + "&fields=photo_100&access_token="
        + str(access_token)
        + "&v=5.130"
    )
    vk_user = json.loads(response.text)

    if vk_email:
        user = User.query.filter_by(email=vk_email).first()

        if user:
            user.vk_id = vk_id
            db.session.commit()

    user = User.query.filter_by(vk_id=vk_id).first()

    # New user?
    if user is None:
        # Yes
        try:
            avatar_uri = os.urandom(16).hex()
            avatar_uri = avatar_uri + ".jpg"

            # if "photo_100" in vk_user["response"][0]:
            # r = requests.get(
            #   vk_user["response"][0]["photo_100"], allow_redirects=True
            # )
            # open('static/avatar/' + avatar_uri, 'wb').write(r.content)

            new_user = User(
                nick=vk_user["response"][0]["first_name"]
                + vk_user["response"][0]["last_name"],
                avatar_uri=avatar_uri,
                vk_id=vk_id,
                email=vk_email,
            )
            db.session.add(new_user)
            db.session.commit()

            user_is_new = True

        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.__dict__["orig"])
            print(error)
            print("Can't add new user to the Database")
            flash(error, category="error")
            return redirect(url_for("login_index"))

        user = User.query.filter_by(vk_id=vk_id).first()

    login_user(user, remember=True)

    if user_is_new:
        u = uuid.uuid4()
        n = Network(
            author_id=user.id,
            network=make_example_net_switch_and_hub(),
            title="Свитч и хаб (пример сети)",
            guid=str(u),
            preview_uri="switch_and_hub.png",
        )
        db.session.add(n)
        db.session.commit()

    return redirect_next_url(fallback=url_for("home"))
