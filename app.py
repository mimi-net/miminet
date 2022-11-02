import sys
from flask import Flask, render_template, request

from miminet_config import SQLITE_DATABASE_NAME, SECRET_KEY
from miminet_model import db, init_db
from miminet_auth import login_manager, login_index, google_login, google_callback, user_profile

app = Flask(__name__,  static_url_path='', static_folder='static', template_folder="templates")

# SQLAlchimy config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + SQLITE_DATABASE_NAME
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_NAME'] = "mimi_session"

# Init Database
db.app = app
db.init_app(app)

# Init LoginManager
login_manager.init_app(app)


# App add_url_rule
# Login
app.add_url_rule('/login.html', methods=['GET', 'POST'], view_func=login_index)
app.add_url_rule('/google_login', methods=['GET'], view_func=google_login)
app.add_url_rule('/google_callback', methods=['GET'], view_func=google_callback)
app.add_url_rule('/profile.html', methods=['GET', 'POST'], view_func=user_profile)

@app.route('/')
def index():  # put application's code here
    return render_template("index.html")


@app.route('/home')
def home():
    return render_template("home.html")


@app.route('/edge')
def edge():  # put application's code here
    return render_template("edge.html")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            init_db(app)
    else:
        app.run()
