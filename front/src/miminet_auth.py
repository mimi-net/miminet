import hashlib
import hmac
import json
import logging
import os
import pathlib
import time
import uuid

import google.auth.transport.requests
import requests
from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from miminet_config import make_example_net_switch_and_hub
from miminet_model import Network, User, db
from oauthlib.oauth2 import TokenExpiredError
from pip._vendor import cachecontrol
from requests_oauthlib import OAuth2Session
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

DEFAULT_USER_CONFIG = {
    "hideARP": False,
    "hideSTP": False,
    "hideSYN": False,
}

# Global variables
AVATAR_UPLOAD_FOLDER = "/app/static/avatar"
ALLOWED_EXTENSIONS = {"bmp", "png", "jpg", "jpeg"}
MAX_AVATAR_SIZE = 1 * 1024 * 1024
PROFILE_VIEWER_MIN_ROLE = 1
SOCIAL_LINK_PROVIDER_SESSION_KEY = "social_link_provider"
SOCIAL_LINK_USER_ID_SESSION_KEY = "social_link_user_id"
SOCIAL_LINK_REDIRECT_SESSION_KEY = "social_link_redirect"

login_manager = LoginManager()
login_manager.login_view = "login_index"

# create an alias of login_required decorator
login_required = login_required


def generate_avatar_uri(extension=".jpg"):
    avatar_hash = os.urandom(16).hex()
    return os.path.join(avatar_hash[0], avatar_hash[1], avatar_hash + extension)


def get_avatar_path(avatar_uri):
    return os.path.join(AVATAR_UPLOAD_FOLDER, avatar_uri)


def save_avatar_blob(avatar_uri, blob):
    avatar_path = get_avatar_path(avatar_uri)
    os.makedirs(os.path.dirname(avatar_path), exist_ok=True)
    with open(avatar_path, "wb") as avatar_file:
        avatar_file.write(blob)

    return avatar_path


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

yandex_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_yandex.json")
yandex_json = None

if os.path.exists(yandex_secrets_file):
    with open(yandex_secrets_file, "r") as file:
        yandex_json = json.loads(file.read())

tg_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_tg.json")
tg_json = None

if os.path.exists(tg_secrets_file):
    with open(tg_secrets_file, "r") as file:
        tg_json = json.loads(file.read())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("miminet_auth")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def handle_needs_login():
    flash("Для выполнения этого действия необходимо войти.")
    return redirect(url_for("login_index", next=request.endpoint))


def redirect_next_url(fallback):
    if "next_url" not in session:
        return redirect(fallback)
    try:
        dest_url = url_for(session["next_url"])
        return redirect(dest_url)
    except Exception:
        return redirect(fallback)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _start_social_link(provider_name, redirect_endpoint="user_profile"):
    if not current_user.is_authenticated:
        return

    session[SOCIAL_LINK_PROVIDER_SESSION_KEY] = provider_name
    session[SOCIAL_LINK_USER_ID_SESSION_KEY] = current_user.id
    session[SOCIAL_LINK_REDIRECT_SESSION_KEY] = redirect_endpoint
    session["next_url"] = redirect_endpoint


def _clear_social_link(provider_name=None):
    if (
        provider_name is not None
        and session.get(SOCIAL_LINK_PROVIDER_SESSION_KEY) != provider_name
    ):
        return

    session.pop(SOCIAL_LINK_PROVIDER_SESSION_KEY, None)
    session.pop(SOCIAL_LINK_USER_ID_SESSION_KEY, None)
    session.pop(SOCIAL_LINK_REDIRECT_SESSION_KEY, None)


def _redirect_after_social_link(default_endpoint="user_profile"):
    redirect_endpoint = (
        session.get(SOCIAL_LINK_REDIRECT_SESSION_KEY) or default_endpoint
    )
    _clear_social_link()
    session.pop("next_url", None)
    return redirect(url_for(redirect_endpoint))


def _get_social_link_user(provider_name):
    if session.get(SOCIAL_LINK_PROVIDER_SESSION_KEY) != provider_name:
        return None

    user_id = session.get(SOCIAL_LINK_USER_ID_SESSION_KEY)
    if not user_id:
        return None

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    if not current_user.is_authenticated or current_user.id != user_id:
        return None

    return User.query.get(user_id)


def _bind_social_account(provider_name, field_name, field_value):
    if (
        session.get(SOCIAL_LINK_PROVIDER_SESSION_KEY) != provider_name
        or not current_user.is_authenticated
    ):
        return None

    link_user = _get_social_link_user(provider_name)
    if not link_user:
        flash("Не удалось найти профиль для привязки соцсети.", category="error")
        return _redirect_after_social_link()

    existing_user = User.query.filter_by(**{field_name: field_value}).first()
    if existing_user and existing_user.id != link_user.id:
        flash("Этот аккаунт соцсети уже привязан к другому профилю.", category="error")
        return _redirect_after_social_link()

    setattr(link_user, field_name, field_value)
    db.session.commit()
    return _redirect_after_social_link()


def login_index():
    next_url = request.args.get("next")

    link_provider = request.args.get("link_provider", type=str)
    telegram_link_mode = current_user.is_authenticated and link_provider == "tg"

    if current_user.is_authenticated:
        access_token = create_access_token(identity=str(current_user.id))
        refresh_token = create_refresh_token(identity=str(current_user.id))

        # if current_user.is_authenticated and not telegram_link_mode:
        #     return redirect(url_for("user_profile"))
        response = redirect_next_url(fallback=url_for("home"))
        if next_url:
            response = redirect_next_url(fallback=next_url)
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response

    if next_url:
        session["next_url"] = next_url
    else:
        session.pop("next_url", None)

    if telegram_link_mode:
        _start_social_link("tg", redirect_endpoint=next_url or "user_profile")
        return render_template("auth/login.html", user=current_user)

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password_hash, password):
                login_user(user, remember=True)
                access_token = create_access_token(identity=str(user.id))
                refresh_token = create_refresh_token(identity=str(user.id))

                response = redirect_next_url(fallback=url_for("user_profile"))
                set_access_cookies(response, access_token)
                set_refresh_cookies(response, refresh_token)
                return response
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
    nick_parts = (user.nick or "").strip().split(maxsplit=1)
    first_name = nick_parts[0] if nick_parts else ""
    last_name = nick_parts[1] if len(nick_parts) > 1 else ""

    if request.method == "POST":
        submitted_first_name = request.form.get("first_name")
        submitted_last_name = request.form.get("last_name")
        first_name = (
            submitted_first_name.strip()
            if submitted_first_name is not None
            else first_name
        )
        last_name = (
            submitted_last_name.strip()
            if submitted_last_name is not None
            else last_name
        )
        avatar = request.files.get("avatar")
        has_updates = False

        if len(first_name) < 1 or len(first_name) > 50:
            flash("Имя должно быть от 1 до 50 символов.", category="error")
            return render_template(
                "auth/profile.html",
                user=user,
                first_name=first_name,
                last_name=last_name,
            )
        if not all(c.isalpha() or c in " -'" for c in first_name):
            flash(
                "Имя содержит недопустимые символы (только буквы, пробелы, дефисы и апострофы).",
                category="error",
            )
            return render_template(
                "auth/profile.html",
                user=user,
                first_name=first_name,
                last_name=last_name,
            )

        if len(last_name) > 50:
            flash("Фамилия должна быть до 50 символов.", category="error")
            return render_template(
                "auth/profile.html",
                user=user,
                first_name=first_name,
                last_name=last_name,
            )
        if last_name and not all(c.isalpha() or c in " -'" for c in last_name):
            flash(
                "Фамилия содержит недопустимые символы (только буквы, пробелы, дефисы и апострофы).",
                category="error",
            )
            return render_template(
                "auth/profile.html",
                user=user,
                first_name=first_name,
                last_name=last_name,
            )

        if avatar and avatar.filename:
            avatar.seek(0, os.SEEK_END)
            file_size = avatar.tell()
            avatar.seek(0)

            if file_size > MAX_AVATAR_SIZE:
                flash("Размер файла не должен превышать 1 МБ", category="error")
                return redirect(url_for("user_profile"))

            if not allowed_file(avatar.filename):
                flash("Допустимые форматы: bmp, png, jpg, jpeg", category="error")
                return render_template(
                    "auth/profile.html",
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                )

            ext = (
                os.path.splitext(secure_filename(avatar.filename))[1].lower() or ".jpg"
            )
            avatar_uri = generate_avatar_uri(ext)

            try:
                logger.info(
                    f"Attempting to save avatar: filename={avatar.filename}, size={file_size}, uri={avatar_uri}"
                )
                save_avatar_blob(avatar_uri, avatar.read())
                user.avatar_uri = avatar_uri
                has_updates = True
                logger.info(f"Avatar uploaded for user {current_user.id}")
            except Exception as e:
                logger.error(f"Failed to save avatar: {e}", exc_info=True)
                flash("Ошибка загрузки аватара", category="error")
                return render_template(
                    "auth/profile.html",
                    user=user,
                    first_name=first_name,
                    last_name=last_name,
                )

        new_nick = f"{first_name} {last_name}".strip()
        if new_nick != user.nick:
            user.nick = new_nick
            has_updates = True

        if has_updates:
            db.session.commit()
            return redirect(url_for("user_profile"))

    return render_template(
        "auth/profile.html", user=user, first_name=first_name, last_name=last_name
    )


@login_required
def user_profile_view(user_id: int):
    if (
        current_user.id != user_id
        and (current_user.role or 0) < PROFILE_VIEWER_MIN_ROLE
    ):
        abort(403)

    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)

    nick_parts = (user.nick or "").strip().split(maxsplit=1)
    first_name = nick_parts[0] if nick_parts else ""
    last_name = nick_parts[1] if len(nick_parts) > 1 else ""

    return render_template(
        "auth/profile_readonly.html",
        user=user,
        first_name=first_name,
        last_name=last_name,
    )


def _load_user_config(user: User) -> dict:
    try:
        parsed = json.loads(user.config) if user.config else {}
    except (TypeError, ValueError):
        parsed = {}

    return parsed if isinstance(parsed, dict) else {}


@login_required
def animation_filters():
    user = current_user
    user_config = _load_user_config(user)

    # Ensure defaults are present
    merged_config = {**DEFAULT_USER_CONFIG, **user_config}
    merged_config["hideARP"] = bool(merged_config.get("hideARP", False))
    merged_config["hideSTP"] = bool(merged_config.get("hideSTP", False))
    merged_config["hideSYN"] = bool(merged_config.get("hideSYN", False))

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}

        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid payload"}), 400

        for key in ("hideARP", "hideSTP", "hideSYN"):
            if key in payload:
                merged_config[key] = bool(payload.get(key, False))

        user.config = json.dumps(merged_config)
        db.session.commit()

        return jsonify(merged_config), 200

    return jsonify({"error": "Invalid request"}), 405


def password_recovery():
    return render_template("auth/password_recovery.html")


@login_required
def logout():
    _clear_social_link()
    session.pop("next_url", None)
    logout_user()
    response = redirect(url_for("index"))
    unset_jwt_cookies(response)
    return response


def google_login():
    _start_social_link("google")
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


def vk_login():
    _start_social_link("vk")
    authorization_link = "https://oauth.vk.com/authorize"
    authorization_url = f"{authorization_link}?client_id={VK_CLIENT_ID}&display=page&redirect_uri={VK_REDIRECT_URI}&scope=friends,email&response_type=code&v=5.130"
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

    google_id = id_info.get("sub")
    social_link_response = _bind_social_account("google", "google_id", google_id)
    if social_link_response is not None:
        return social_link_response

    user = User.query.filter_by(google_id=google_id).first()

    # New user?
    if user is None:
        # Yes
        try:
            avatar_uri = "empty.jpg"

            photo_uri = id_info.get("picture")
            if photo_uri:
                generated_avatar_uri = generate_avatar_uri()
                try:
                    r = requests.get(photo_uri, allow_redirects=True, timeout=10)
                    r.raise_for_status()  # Проверяет HTTP-ошибки (например, 404)
                    save_avatar_blob(generated_avatar_uri, r.content)
                    avatar_uri = generated_avatar_uri
                except requests.RequestException as e:
                    logger.error(
                        f"Failed to download avatar from Google for user {id_info.get('sub')}: {e}"
                    )
                    avatar_uri = "empty.jpg"  # Дефолтный аватар при ошибке
                except (IOError, PermissionError) as e:
                    logger.error(
                        f"Failed to save avatar file for user {id_info.get('sub')}: {e}"
                    )
                    avatar_uri = "empty.jpg"

            f = id_info.get("family_name", "")
            n = id_info.get("given_name", "")

            new_user = User(
                nick=f + n,
                avatar_uri=avatar_uri,
                google_id=google_id,
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

        user = User.query.filter_by(google_id=google_id).first()

    login_user(user, remember=True)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    response = redirect_next_url(fallback=url_for("home"))
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

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

    return response


# https://vk.com/dev/authcode_flow_user
def vk_callback():
    user_code = request.args.get("code")
    user_is_new = False

    if not user_code:
        return redirect(url_for("login_index"))

    # Get access token
    response = requests.get(
        "https://oauth.vk.com/access_token",
        params={
            "client_id": VK_CLIENT_ID,
            "client_secret": VK_CLIENT_SECRET,
            "redirect_uri": VK_REDIRECT_URI,
            "code": user_code,
        },
        timeout=10,
    )
    access_token_json = response.json()

    if "error" in access_token_json:
        return redirect(url_for("login_index"))

    access_token = access_token_json.get("access_token")
    vk_email = access_token_json.get("email")

    try:
        vk_id = str(int(access_token_json["user_id"]))
    except (KeyError, ValueError, TypeError):
        return redirect(url_for("login_index"))

    social_link_response = _bind_social_account("vk", "vk_id", vk_id)
    if social_link_response is not None:
        return social_link_response

    # Get user name
    response = requests.get(
        "https://api.vk.com/method/users.get",
        params={
            "user_ids": vk_id,
            "fields": "photo_100",
            "access_token": str(access_token),
            "v": "5.130",
        },
        timeout=10,
    )
    vk_user = response.json()

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
            avatar_uri = "empty.jpg"

            photo_uri = vk_user.get("response", [{}])[0].get("photo_100")
            if photo_uri:
                generated_avatar_uri = generate_avatar_uri()
                try:
                    r = requests.get(photo_uri, allow_redirects=True, timeout=10)
                    r.raise_for_status()
                    save_avatar_blob(generated_avatar_uri, r.content)
                    avatar_uri = generated_avatar_uri
                except requests.RequestException as e:
                    logger.error(
                        f"Failed to download avatar from VK for user {vk_id}: {e}"
                    )
                    avatar_uri = "empty.jpg"
                except (IOError, PermissionError) as e:
                    logger.error(f"Failed to save avatar file for user {vk_id}: {e}")
                    avatar_uri = "empty.jpg"

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
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    response = redirect_next_url(fallback=url_for("home"))
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)

    print(f"access_token: {access_token}; refresh_token: {refresh_token}")

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

    return response


def yandex_login(yandex_json=yandex_json):
    _start_social_link("yandex")
    yandex_session = OAuth2Session(
        yandex_json["web"]["client_id"],
        redirect_uri=yandex_json["web"]["redirect_uris"][0],
    )

    authorization_url, state = yandex_session.authorization_url(
        yandex_json["web"]["auth_uri"], access_type="offline", prompt="consent"
    )

    session["state"] = state

    return redirect(authorization_url)


def yandex_callback(yandex_json=yandex_json):
    state = session.get("state")
    if not state:
        return redirect(url_for("login_index"))

    try:
        yandex_session = OAuth2Session(
            yandex_json["web"]["client_id"],
            redirect_uri=yandex_json["web"]["redirect_uris"][0],
            state=state,
        )

        yandex_session.fetch_token(
            yandex_json["web"]["token_uri"],
            authorization_response=request.url,
            client_secret=yandex_json["web"]["client_secret"],
        )

        user_info_response = yandex_session.get("https://login.yandex.ru/info")
        user_info_response.raise_for_status()
        id_info = user_info_response.json()

        yandex_id = id_info.get("id")
        social_link_response = _bind_social_account("yandex", "yandex_id", yandex_id)
        if social_link_response is not None:
            return social_link_response

        user = User.query.filter_by(yandex_id=yandex_id).first()

        if user is None:
            try:
                new_user = User(
                    nick=id_info.get("login", ""),
                    yandex_id=yandex_id,
                    email=id_info.get("default_email", ""),
                )
                db.session.add(new_user)
                db.session.commit()

            except SQLAlchemyError as e:
                db.session.rollback()
                error = str(e.__dict__["orig"])
                logger.error("Error while adding new Yandex user: %s", e)
                flash(error, category="error")
                return redirect(url_for("login_index"))

            user = User.query.filter_by(yandex_id=yandex_id).first()

        login_user(user, remember=True)
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        response = redirect_next_url(fallback=url_for("home"))
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response

    except TokenExpiredError as e:
        logger.error("Token expired: %s", e)
        flash("Token expired. Please log in again.", category="error")
        return redirect(url_for("login_index"))


def check_tg_authorization(auth_data, tg_json=tg_json):
    BOT_TOKEN = tg_json["token"]["BOT_TOKEN"]
    check_hash = auth_data["hash"]
    del auth_data["hash"]

    data_check_arr = [f"{key}={value}" for key, value in auth_data.items()]
    data_check_arr.sort()

    data_check_string = "\n".join(data_check_arr)

    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    hash_result = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if hash_result != check_hash:
        raise Exception("Data is NOT from Telegram")

    if (time.time() - int(auth_data["auth_date"])) > 86400:
        raise Exception("Data is outdated")

    return auth_data


def tg_callback():
    user_json = request.args.get("user")

    if not user_json:
        flash("Invalid Telegram user data", category="error")
        return redirect(url_for("login_index"))

    user_data = json.loads(user_json)
    try:
        check_tg_authorization(user_data)
    except Exception as e:
        logger.error("Error while processing Telegram callback: %s", e)
        flash(str(e), category="error")
        return redirect(url_for("login_index"))

    tg_id = str(user_data.get("id", ""))
    social_link_response = _bind_social_account("tg", "tg_id", tg_id)
    if social_link_response is not None:
        return social_link_response

    user = User.query.filter(
        (User.tg_id == tg_id) | (User.email == user_data.get("username", ""))
    ).first()

    if user is None:
        try:
            new_user = User(
                nick=user_data.get("first_name", ""),
                tg_id=tg_id,
                email=user_data.get("username", ""),
            )
            db.session.add(new_user)
            db.session.commit()

        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.__dict__["orig"])
            logger.error("Error while adding new Telegram user: %s", e)
            flash(error, category="error")
            return redirect(url_for("login_index"))

        user = User.query.filter(
            (User.tg_id == tg_id) | (User.email == user_data.get("username", ""))
        ).first()

    login_user(user, remember=True)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    response = redirect_next_url(fallback=url_for("home"))
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


class TestUserData:
    """Data for test user initializing."""

    nick = "test_user"
    email = "selenium"
    password = "password"
    password_hash = generate_password_hash(password)


def insert_test_user(app):
    with app.app_context():
        try:
            test_user = User(
                nick=TestUserData.nick,
                email=TestUserData.email,
                password_hash=TestUserData.password_hash,
            )

            db.session.add(test_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred while adding the test user: {e}")


def remove_test_user(app):
    with app.app_context():
        try:
            user_to_remove = User.query.filter_by(email=TestUserData.email).first()

            if user_to_remove:
                db.session.delete(user_to_remove)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred while removing the test user: {e}")
