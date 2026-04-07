import os
import pathlib

from flask import jsonify, session
from flask_caching import Cache
from pylti1p3.contrib.flask import FlaskOIDCLogin, FlaskRequest, FlaskCacheDataStorage
from pylti1p3.tool_config import ToolConfJsonFile
from lti_provider.lti_actions.base import ExtendedFlaskMessageLaunch

from lti_provider.lti_actions.factory import ActionHandlerFactory, ActionResultSenderFactory

cache = Cache()

def login():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    launch_data_storage = get_launch_data_storage()

    flask_request = FlaskRequest()
    target_link_uri = flask_request.get_param('target_link_uri')
    if not target_link_uri: raise Exception('Missing "target_link_uri" param')

    oidc_login = FlaskOIDCLogin(flask_request, tool_conf, launch_data_storage=launch_data_storage)
    return oidc_login\
        .enable_check_cookies()\
        .redirect(target_link_uri)


def launch():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    flask_request = FlaskRequest()
    launch_data_storage = get_launch_data_storage()

    message_launch = ExtendedFlaskMessageLaunch(flask_request, tool_conf, launch_data_storage=launch_data_storage)
    session["launch_id"] = message_launch.get_launch_id()
    
    handler = ActionHandlerFactory.create_handler(message_launch)
    return handler.handle()


def send(result, result_type: str = None):
    if "launch_id" not in session: raise Exception("No active LTI launch")

    tool_conf = ToolConfJsonFile(get_lti_config_path())
    flask_request = FlaskRequest()
    launch_data_storage = get_launch_data_storage()

    message_launch = ExtendedFlaskMessageLaunch.from_cache(session["launch_id"], flask_request, tool_conf, launch_data_storage=launch_data_storage)
    
    result_sender = ActionResultSenderFactory.create_sender(message_launch, result_type)
    return result_sender.send(result)


def get_jwks():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    return jsonify(tool_conf.get_jwks())

def get_lti_config_path():
    return os.path.join(pathlib.Path(__file__).parent, "config", "lti_config.json")

def get_launch_data_storage():
    return FlaskCacheDataStorage(cache)
