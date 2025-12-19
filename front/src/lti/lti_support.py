import os
import pathlib
import uuid

from flask import jsonify, request, session
from flask_caching import Cache
from pylti1p3.contrib.flask import FlaskOIDCLogin, FlaskMessageLaunch, FlaskRequest, FlaskCacheDataStorage
from pylti1p3.tool_config import ToolConfJsonFile

from front.src.lti.lti_actions import ActionHandlerFactory, ActionResultSenderFactory

cache = Cache()

class ExtendedFlaskMessageLaunch(FlaskMessageLaunch):

    def validate_nonce(self):
        """
        Probably it is bug on "https://lti-ri.imsglobal.org":
        site passes invalid "nonce" value during deep links launch.
        Because of this in case of iss == http://imsglobal.org just skip nonce validation.

        """
        iss = self.get_iss()
        if iss == "https://lti-ri.imsglobal.org":
            return self
        return super().validate_nonce()


def login():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    launch_data_storage = get_launch_data_storage()

    flask_request = FlaskRequest()
    target_link_uri = flask_request.get_param('target_link_uri')
    if not target_link_uri:
        raise Exception('Missing "target_link_uri" param')

    oidc_login = FlaskOIDCLogin(flask_request, tool_conf, launch_data_storage=launch_data_storage)
    return oidc_login\
        .enable_check_cookies()\
        .redirect(target_link_uri)


def launch():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    flask_request = FlaskRequest()
    launch_data_storage = get_launch_data_storage()
    message_launch = ExtendedFlaskMessageLaunch(flask_request, tool_conf, launch_data_storage=launch_data_storage)
    
<<<<<<< HEAD
    if request.args.get("returnUrl"):
        session["returnToLtiPlatformUrl"] = request.args.get("returnUrl")
    
    handler = ActionHandlerFactory.create_handler(message_launch)
    return handler.handle()
=======
    if request.args.get("returnUrl") != None: session["returnToLtiPlatformUrl"] = request.args.get("returnUrl")
    session["launch_id"] = message_launch.get_launch_id()

    platformUser = User.query.filter(
        User.platformUserId == message_launch_data.get("sub"),
        User.platform == message_launch_data.get("iss")
    ).first()
    
    if platformUser is None:
        platformUser = User(nick=message_launch_data.get("name", f"platformUser_{uuid.uuid4().hex[:8]}"), platform=message_launch_data.get("iss"), platformUserId=message_launch_data.get("sub"))
        db.session.add(platformUser)
        db.session.commit()
>>>>>>> 6a9640608554e0231ba0d7654048cabac9b37878


<<<<<<< HEAD
def send(result):
    if "launch_id" not in session:
        raise Exception("No active LTI launch")
    
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    flask_request = FlaskRequest()
    launch_data_storage = get_launch_data_storage()
    
    message_launch = ExtendedFlaskMessageLaunch.from_cache(
        session.get("launch_id"), flask_request, tool_conf,
        launch_data_storage=launch_data_storage
    )
    
    result_sender = ActionResultSenderFactory.create_sender(message_launch)
    result_sender.send(result)
    
    if "returnToLtiPlatformUrl" in session: session.pop("returnToLtiPlatformUrl")
=======
    launchSectionId = message_launch_data.get("https://purl.imsglobal.org/spec/lti/claim/custom").get('task')
>>>>>>> 6a9640608554e0231ba0d7654048cabac9b37878


def get_jwks():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    return jsonify(tool_conf.get_jwks())

def get_lti_config_path():
    return os.path.join(pathlib.Path(__file__).parent, "config", "lti_config.json")

def get_launch_data_storage():
    return FlaskCacheDataStorage(cache)