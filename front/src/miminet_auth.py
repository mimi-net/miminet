import hmac
import os
import pathlib
import time
import requests
import json

from google.oauth2 import id_token
import google.auth.transport.requests
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol

from flask_login import login_user
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import TokenExpiredError
import hashlib

from sqlalchemy.exc import SQLAlchemyError

from flask_login import login_user, login_required, logout_user, current_user, LoginManager
from flask import app, session, request, flash, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from miminet_model import User, db

# Global variables
UPLOAD_FOLDER = 'static/avatar/'
UPLOAD_TMP_FOLDER = 'static/tmp/avatar/'
ALLOWED_EXTENSIONS = {'bmp', 'png', 'jpg', 'jpeg'}

login_manager = LoginManager()
login_manager.login_view = "login_index"

# create an alias of login_required decorator
login_required = login_required

# Google auth (https://github.com/code-specialist/flask_google_login/blob/main/app.py)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = "698442891298-ursgc8b93lrr09i38vphoqnpg89urpcg.apps.googleusercontent.com"
client_secrets_file = os.path.join(
    pathlib.Path(__file__).parent, "client_google.json")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def handle_needs_login():
    flash("Для выполнения этого действия необходимо войти.")
    return redirect(url_for('login_index', next=request.endpoint))


def redirect_next_url(fallback):

    if 'next_url' not in session:
        redirect(fallback)
    try:
        dest_url = url_for(session['next_url'])
        return redirect(dest_url)
    except:
        return redirect(fallback)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_index():

    if current_user.is_authenticated:
        return redirect(url_for('user_profile'))

    next_url = request.args.get("next")

    if next_url:
        session['next_url'] = next_url
    else:
        session.pop('next_url', None)

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password_hash, password):
                login_user(user, remember=True)
                return redirect_next_url(fallback=url_for('user_profile'))
            else:
                flash('Пара логин и пароль указаны неверно', category='error')
                return render_template('auth/login.html', user=current_user)
        else:
            flash('Пользователя с таким почтовым адресом нет', category='error')
            return render_template('auth/login.html', user=current_user)

    return render_template('auth/login.html', user=current_user)


@login_required
def user_profile():
    user = User.query.filter_by(id=current_user.id).first()

    if request.method == 'POST':
        last_name = request.form.get('last_name').strip()
        first_name = request.form.get('first_name').strip()
        middle_name = request.form.get('middle_name').strip()
        how_to_contact = request.form.get('how_to_contact').strip()

        if first_name:
            user.first_name = first_name
            user.middle_name = middle_name
            user.last_name = last_name
            user.how_to_contact = how_to_contact
            db.session.commit()

    return render_template('auth/profile.html', user=user)


def password_recovery():
    return render_template("auth/password_recovery.html")


@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


def google_login():

    flow = Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=["https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid"]
    )

    flow.redirect_uri = url_for('google_callback', _external=True)
    authorization_url, state = flow.authorization_url(access_type='offline',
                                                      include_granted_scopes='true')
    session["state"] = state
    return redirect(authorization_url)


def vk_login():
    authorization_link = "https://oauth.vk.com/authorize"
    authorization_url = f"{authorization_link}?client_id={VK_CLIENT_ID}&display=page&redirect_uri={VK_REDIRECT_URI}&scope=friends,email&response_type=code&v=5.130"
    return redirect(authorization_url)


def google_callback():

    state = session["state"]
    print(request.args.get('state'), session)

    if not state:
        redirect(url_for('login_index'))

    flow = Flow.from_client_secrets_file(
        client_secrets_file=client_secrets_file,
        scopes=["https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/userinfo.email",
                "openid"]
    )

    flow.redirect_uri = url_for('google_callback', _external=True)
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(
        session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=60
    )

    user = User.query.filter_by(google_id=id_info.get('sub')).first()

    # New user?
    if user is None:
        # Yes
        try:
            avatar_uri = os.urandom(16).hex()
            avatar_uri = avatar_uri + ".jpg"

            if 'picture' in id_info:
                r = requests.get(id_info.get('picture'), allow_redirects=True)
                open('static/avatar/' + avatar_uri, 'wb').write(r.content)

            f = id_info.get('family_name', '')
            n = id_info.get('given_name', '')

            new_user = User(nick=f + n,
                            avatar_uri=avatar_uri,
                            google_id=id_info.get('sub'),
                            email=id_info.get('email'))
            db.session.add(new_user)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.__dict__['orig'])
            print(error)
            print("Can't add new user to Database")
            flash(error, category='error')
            return redirect(url_for('login_index'))

        user = User.query.filter_by(google_id=id_info.get('sub')).first()

    login_user(user, remember=True)
    return redirect_next_url(fallback=url_for('home'))

# https://vk.com/dev/authcode_flow_user


def vk_callback():

    user_code = request.args.get('code')

    if not user_code:
        return redirect(url_for('login_index'))

    # Get access token
    response = requests.get(
        'https://oauth.vk.com/access_token?client_id=51544060&client_secret=5G1LOaa0ty0zFDmH5cPw&redirect_uri=https://miminet.ru/auth/vk_callback&code=' + user_code)
    access_token_json = json.loads(response.text)

    if "error" in access_token_json:
        return redirect(url_for('login_index'))

    print(access_token_json)

    vk_id = access_token_json.get('user_id')
    access_token = access_token_json.get('access_token')
    vk_email = access_token_json.get('email')

    # Get user name
    response = requests.get('https://api.vk.com/method/users.get?user_ids=' + str(
        vk_id) + '&fields=photo_100&access_token=' + str(access_token) + '&v=5.130')
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

            if 'photo_100' in vk_user['response'][0]:
                r = requests.get(vk_user['response'][0]
                                 ['photo_100'], allow_redirects=True)
                open('static/avatar/' + avatar_uri, 'wb').write(r.content)

            new_user = User(nick=vk_user['response'][0]['first_name'] + vk_user['response'][0]['last_name'],
                            avatar_uri=avatar_uri,
                            vk_id=vk_id,
                            email=vk_email)
            db.session.add(new_user)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.__dict__['orig'])
            print(error)
            print("Can't add new user to the Database")
            flash(error, category='error')
            return redirect(url_for('login_index'))

        user = User.query.filter_by(vk_id=vk_id).first()

    login_user(user, remember=True)
    return redirect_next_url(fallback=url_for('home'))


# Чтение данных из файла конфигурации
config_path = os.environ.get('CLIENT_YANDEX_PATH', 'front/src/client_yandex.json')
with open(config_path) as config_file:
    config_data = json.load(config_file)

# Чтение данных из файла конфигурации
# config_path = pathlib.Path(__file__).parent / 'client_yandex.json'
# with open(config_path) as config_file:
# config_data = json.load(config_file)

# Определение переменных
oauthQueryParams = {
    'client_id': config_data['web']['client_id'],
    'response_type': 'token',
    'redirect_uri': config_data['web']['redirect_uris'][0],
}

tokenPageOrigin = config_data['web']['redirect_uris'][0]


def yandex_login():
    client_id = oauthQueryParams['client_id']
    client_secret = config_data['web']['client_secret']
    redirect_uri = oauthQueryParams['redirect_uri']
    scope = ["login:email", "login:avatar"]

    yandex_session = OAuth2Session(
        client_id,
        redirect_uri=redirect_uri,
        scope=scope
    )

    yandex_session.redirect_uri = url_for('yandex_callback', _external=True)

    authorization_url, state = yandex_session.authorization_url(
        config_data['web']['auth_uri'],
        access_type='offline',
        prompt='consent',
    )

    session["state"] = state

    print("Redirecting to Yandex for authentication.")
    print("Authorization URL:", authorization_url)

    return redirect(authorization_url)


def yandex_callback():
    state = session.get("state")
    if not state:
        print("State not found. Redirecting to login page.")
        return redirect(url_for('login_index'))

    try:
        client_id = oauthQueryParams['client_id']
        client_secret = config_data['web']['client_secret']
        redirect_uri = oauthQueryParams['redirect_uri']

        yandex_session = OAuth2Session(
            client_id, redirect_uri=redirect_uri, state=state)

        token = yandex_session.fetch_token(
            config_data['web']['token_uri'],
            authorization_response=request.url,
            client_secret=client_secret,
        )

        print("Token:", token)

        user_info_response = yandex_session.get('https://login.yandex.ru/info')
        user_info_response.raise_for_status()

        id_info = user_info_response.json()

        print("Yandex callback:")
        print("User information:", id_info)

        user = User.query.filter_by(yandex_id=id_info.get('id')).first()

        if user is None:
            avatar_uri = id_info.get('default_avatar_id', '')
            if avatar_uri:
                avatar_uri = avatar_uri.replace('/', '-')
                avatar_uri += ".jpg"
                avatar_url = f'https://avatars.yandex.net/get-yapic/{avatar_uri}/islands-200'

                r = requests.get(avatar_url, allow_redirects=True)
                r.raise_for_status()

                avatar_path = 'static/avatar/'
                os.makedirs(avatar_path, exist_ok=True)

                with open(os.path.join(avatar_path, avatar_uri), 'wb') as f:
                    f.write(r.content)

                new_user = User(
                    nick=id_info.get('login', ''),
                    avatar_uri=avatar_uri,
                    yandex_id=id_info.get('id'),
                    email=id_info.get('default_email', '')
                )
                db.session.add(new_user)
                db.session.commit()

        user = User.query.filter_by(yandex_id=id_info.get('id')).first()

        login_user(user, remember=True)
        return redirect_next_url(fallback=url_for('home'))

    except TokenExpiredError:
        print("Token expired. Redirecting to login page.")
        flash("Token expired. Please log in again.", category='error')
        return redirect(url_for('login_index'))

    except Exception as e:
        print(f"Unexpected error occurred during callback processing: {e}")
        flash(
            f"Unexpected error occurred during callback processing: {e}", category='error')
        return redirect(url_for('login_index'))
    

def check_tg_authorization(auth_data):
    BOT_TOKEN = '6039516169:AAGg9G9rhZpUJAyAe_dG21vMb6wnnLhwHvA'
    try:
        check_hash = auth_data['hash']
        del auth_data['hash']

        data_check_arr = [f"{key}={value}" for key, value in auth_data.items()]
        data_check_arr.sort()
        
        data_check_string = "\n".join(data_check_arr)

        secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
        hash_result = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        print(f"Expected Hash: {check_hash}")
        print(f"Calculated Hash: {hash_result}")

        if hash_result != check_hash:
            raise Exception('Data is NOT from Telegram')

        if (time.time() - int(auth_data['auth_date'])) > 86400:
            raise Exception('Data is outdated')

        print("Authorization successful")
        return auth_data

    except Exception as e:
        print(f"Authorization failed: {str(e)}")
        raise


def tg_callback():
    user_json = request.args.get('user')

    if not user_json:
        flash("Invalid Telegram user data", category='error')
        return redirect(url_for('login_index'))
    
    try:
        user_data = json.loads(user_json)
        check_tg_authorization(user_data)
    except Exception as e:
        flash(str(e), category='error')
        return redirect(url_for('login_index'))

    telegram_user_id = str(user_data.get('id', ''))

    user = User.query.filter((User.telegram_id == telegram_user_id) | (User.email == user_data.get('username', ''))).first()

    if user is None:
        try:
            avatar_uri = os.urandom(16).hex() + ".jpg"

            photo_url = user_data.get('photo_url', '')

            if photo_url:
                r = requests.get(photo_url, allow_redirects=True)
                open('static/avatar/' + avatar_uri, 'wb').write(r.content)

            last_name = user_data.get('last_name', '')
            first_name = user_data.get('first_name', '')

            username = user_data.get('username', '')

            new_user = User(
                nick=last_name + first_name,
                avatar_uri=avatar_uri,
                telegram_id=telegram_user_id,
                email=username  
            )

            db.session.add(new_user)
            db.session.commit()

            user = User.query.filter((User.telegram_id == telegram_user_id) | (User.email == user_data.get('username', ''))).first()

        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.__dict__['orig'])
            print(error)
            print("Can't add new user to Database")
            flash(error, category='error')
            return redirect(url_for('login_index'))

    login_user(user, remember=True)
    return redirect_next_url(fallback=url_for('home'))

@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
