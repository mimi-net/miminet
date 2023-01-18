import sys

from flask import Flask, render_template, request
from flask_login import login_required, current_user
from flask_migrate import Migrate

from miminet_config import SQLITE_DATABASE_NAME, SECRET_KEY
from miminet_model import db, init_db, Network
from miminet_auth import login_manager, login_index, google_login, google_callback, user_profile
from miminet_network import create_network, web_network, update_network_config,\
    delete_network, post_nodes, post_edges, post_nodes_edges, move_nodes
from miminet_simulation import run_simulation, check_simulation
from miminet_host import save_host_config

app = Flask(__name__,  static_url_path='', static_folder='static', template_folder="templates")

# SQLAlchimy config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + SQLITE_DATABASE_NAME
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_COOKIE_NAME'] = "mimi_session"

# Init Database
db.app = app
db.init_app(app)

# Init Flask-Migrate
migrate = Migrate(app, db)

# Init LoginManager
login_manager.init_app(app)


# App add_url_rule
# Login
app.add_url_rule('/login.html', methods=['GET', 'POST'], view_func=login_index)
app.add_url_rule('/google_login', methods=['GET'], view_func=google_login)
app.add_url_rule('/google_callback', methods=['GET'], view_func=google_callback)
app.add_url_rule('/profile.html', methods=['GET', 'POST'], view_func=user_profile)

# Network
app.add_url_rule('/create_network', methods=['GET'], view_func=create_network)
app.add_url_rule('/web_network', methods=['GET'], view_func=web_network)
app.add_url_rule('/update_network_config', methods=['GET', 'POST'], view_func=update_network_config)
app.add_url_rule('/delete_network', methods=['GET', 'POST'], view_func=delete_network)
app.add_url_rule('/post_network_nodes', methods=['GET', 'POST'], view_func=post_nodes)
app.add_url_rule('/post_network_edges', methods=['GET', 'POST'], view_func=post_edges)
app.add_url_rule('/post_nodes_edges', methods=['POST'], view_func=post_nodes_edges)
app.add_url_rule('/move_network_nodes', methods=['POST'], view_func=move_nodes)

# Simulation
app.add_url_rule('/run_simulation', methods=['POST'], view_func=run_simulation)
app.add_url_rule('/check_simulation', methods=['GET'], view_func=check_simulation)

# Hosts
app.add_url_rule('/host/save_config', methods=['GET', 'POST'], view_func=save_host_config)


@app.route('/')
def index():  # put application's code here
    return render_template("index.html")


@app.route('/home')
@login_required
def home():
    user = current_user

    networks = Network.query.filter(Network.author_id == user.id).all()

    return render_template("home.html", networks = networks)


@app.route('/edge')
def edge():  # put application's code here
    return render_template("edge.html")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            init_db(app)
    else:
        app.run()
