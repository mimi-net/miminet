from flask import redirect, session, url_for
from .base import BaseActionHandler

class QuizSessionRetrievalHandler(BaseActionHandler):
    
    def _process(self):
        custom = self.launch_data.get("https://purl.imsglobal.org/spec/lti/claim/custom")

        quiz_session_id = custom.get('submission_id')

        return redirect(url_for('session_result_endpoint', id=quiz_session_id))
