import datetime
from functools import wraps
import os
import pathlib
import uuid

from flask_login import login_user, logout_user

from flask import jsonify, request, session, redirect, url_for
from flask_caching import Cache
from werkzeug.exceptions import Forbidden
from pylti1p3.contrib.flask import FlaskOIDCLogin, FlaskMessageLaunch, FlaskRequest, FlaskCacheDataStorage
from pylti1p3.deep_link_resource import DeepLinkResource
from pylti1p3.grade import Grade
from pylti1p3.lineitem import LineItem
from pylti1p3.tool_config import ToolConfJsonFile
from pylti1p3.registration import Registration

from miminet_model import User, db

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
    message_launch_data = message_launch.get_launch_data()
    
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

    login_user(platformUser)

    launchSectionId = message_launch_data.get("https://purl.imsglobal.org/spec/lti/claim/custom").get('task')

    return redirect(url_for('get_section_endpoint', section=launchSectionId))

def score(score):
    if ("launch_id" in session):
        tool_conf = ToolConfJsonFile(get_lti_config_path())
        flask_request = FlaskRequest()
        launch_data_storage = get_launch_data_storage()
        message_launch = ExtendedFlaskMessageLaunch.from_cache(session.get("launch_id"), flask_request, tool_conf,
                                                            launch_data_storage=launch_data_storage)
        
        resource_link_id = message_launch.get_launch_data() \
            .get('https://purl.imsglobal.org/spec/lti/claim/resource_link', {}).get('id')

        if not message_launch.has_ags():
            raise Forbidden("Don't have grades!")

        sub = message_launch.get_launch_data().get('sub')
        timestamp = datetime.datetime.utcnow().isoformat() + 'Z'

        grades = message_launch.get_ags()
        sc = Grade().set_score_given(score) \
            .set_timestamp(timestamp) \
            .set_user_id(sub)
        sc_line_item = LineItem().set_tag('score').set_resource_id(resource_link_id)
        grades.put_grade(sc, sc_line_item)

        if "returnToLtiPlatformUrl" in session: session.pop("returnToLtiPlatformUrl")

def get_jwks():
    tool_conf = ToolConfJsonFile(get_lti_config_path())
    return jsonify({'keys': tool_conf.get_jwks()})

def get_lti_config_path():
    return os.path.join(pathlib.Path(__file__).parent, "config", "lti_config.json")

def get_launch_data_storage():
    return FlaskCacheDataStorage(cache)