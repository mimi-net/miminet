from pylti1p3.contrib.flask import FlaskMessageLaunch

from .quiz_session_retrieval import QuizSessionRetrievalHandler
from .section_creation import SectionCreationHandler, SectionSender
from .section_retrieval import QuizSessionScoreSender, QuizSessionSender, SectionRetrievalHandler

class ActionHandlerFactory:
    @staticmethod
    def create_handler(message_launch: FlaskMessageLaunch):
        launch_data = message_launch.get_launch_data()
        
        message_type = launch_data.get(
            "https://purl.imsglobal.org/spec/lti/claim/message_type"
        )
        
        if message_type == "LtiResourceLinkRequest":
            return SectionRetrievalHandler(message_launch)
        elif message_type == "LtiDeepLinkingRequest":
            return SectionCreationHandler(message_launch)
        elif message_type == "LtiSubmissionReviewRequest":
            return QuizSessionRetrievalHandler(message_launch)
        else:
            raise Exception("Unknown lti message type")
        
class ActionResultSenderFactory:
    @staticmethod
    def create_sender(message_launch: FlaskMessageLaunch, result_type: str = None):
        launch_data = message_launch.get_launch_data()
        
        message_type = launch_data.get("https://purl.imsglobal.org/spec/lti/claim/message_type")

        if result_type is None:
            if message_type == "LtiResourceLinkRequest":
                raise Exception("Specify result_type when send results from LtiResourceLinkRequest")
            elif message_type == "LtiDeepLinkingRequest":
                return SectionSender(message_launch)
        elif result_type == "section" and message_type == "LtiDeepLinkingRequest":
            return SectionSender(message_launch)
        elif result_type == "solution" and message_type == "LtiResourceLinkRequest":
            return QuizSessionSender(message_launch)
        elif result_type == "solution_score" and message_type == "LtiResourceLinkRequest":
            return QuizSessionScoreSender(message_launch)
        else:
            raise NotImplementedError()