from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from flask import session
from flask_login import login_user
from pylti1p3.contrib.flask import FlaskMessageLaunch
from miminet_model import User, db
import uuid

class BaseActionHandler(ABC):
    def __init__(self, message_launch: FlaskMessageLaunch):
        self.message_launch = message_launch
        self.launch_data = message_launch.get_launch_data()
        
    def handle(self):
        session["launch_id"] = self.message_launch.get_launch_id()
        
        self._handle_user()
        
        return self._process()
    
    def _handle_user(self):
        platform_user = User.query.filter(
            User.platformUserId == self.launch_data.get("sub"),
            User.platform == self.launch_data.get("iss")
        ).first()
        
        if platform_user is None:
            platform_user = User(
                nick=self.launch_data.get("name", f"platformUser_{uuid.uuid4().hex[:8]}"),
                platform=self.launch_data.get("iss"),
                platformUserId=self.launch_data.get("sub")
            )
            db.session.add(platform_user)
            db.session.commit()
        
        login_user(platform_user)
        
        return platform_user
    
    @abstractmethod
    def _process(self):
        pass



T = TypeVar('T')
class BaseActionResultSender(Generic[T], ABC):
    def __init__(self, message_launch: FlaskMessageLaunch):
        self.message_launch = message_launch
        self.launch_data = message_launch.get_launch_data()

    def send(self, result):
        session["launch_id"] = self.message_launch.get_launch_id()
        
        return self._send(result)
        
    @abstractmethod
    def _send(self, result: T) -> bool:
        pass