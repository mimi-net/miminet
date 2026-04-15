from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from flask import session
from flask_login import login_user
from pylti1p3.contrib.flask import FlaskMessageLaunch
from miminet_model import User, db

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

class BaseActionHandler(ABC):
    def __init__(self, message_launch: FlaskMessageLaunch):
        self.message_launch = message_launch
        self.launch_data = message_launch.get_launch_data()
        
    def handle(self):
        if "https://purl.imsglobal.org/spec/lti/claim/launch_presentation" in self.launch_data:
            launch_presentation = self.launch_data.get("https://purl.imsglobal.org/spec/lti/claim/launch_presentation")
            session["returnToLtiPlatformUrl"] = launch_presentation.get("return_url", self.message_launch.get_iss())

        self._handle_user()
        return self._process()
    
    def _handle_user(self):
        platform_user = User.query.filter(
            User.platform_client_id == self.message_launch.get_client_id(),
            User.platform_user_id == self.launch_data.get("sub")
        ).first()
        
        if platform_user is None:
            platform_user = User(
                nick=self.launch_data.get("name", ""),
                platform_client_id=self.message_launch.get_client_id(),
                platform_user_id=self.launch_data.get("sub")
            )
            db.session.add(platform_user)
            db.session.commit()
        
        login_user(platform_user, remember=True)
        return platform_user
    
    @abstractmethod
    def _process(self):
        pass



T = TypeVar('T')
class BaseResultSender(Generic[T], ABC):
    def __init__(self, message_launch: FlaskMessageLaunch):
        self.message_launch = message_launch
        self.launch_data = message_launch.get_launch_data()

    def send(self, result):
        if "returnToLtiPlatformUrl" in session: session.pop("returnToLtiPlatformUrl")

        return self._send(result)
        
    @abstractmethod
    def _send(self, result: T) -> bool:
        pass