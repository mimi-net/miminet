from quiz.entity.entity import Section, SessionQuestion
from .base import BaseActionHandler, BaseResultSender
from flask import redirect, url_for
from datetime import datetime
from pylti1p3.grade import Grade

class SectionRetrievalHandler(BaseActionHandler):

    def _process(self):
        custom = self.launch_data.get("https://purl.imsglobal.org/spec/lti/claim/custom")
        
        section = Section.query.filter_by(id=custom.get('section_id')).first()
        roles = self.launch_data.get("https://purl.imsglobal.org/spec/lti/claim/roles")

        print(roles[0])

        if roles[0] == "http://purl.imsglobal.org/vocab/lis/v2/membership#Learner":
            return redirect(url_for('get_section_endpoint', section=section.id))
        elif roles[0] == "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor":
            return redirect(url_for('web_network', guid=section.questions[0].practice_question.start_configuration))
        else:
            launch_presentation = self.launch_data.get("https://purl.imsglobal.org/spec/lti/claim/launch_presentation")
            return redirect(launch_presentation.get("return_url", self.message_launch.get_iss()))
    

class QuizSessionSender(BaseResultSender[SessionQuestion]):
    
    def _send(self, session_question: SessionQuestion) -> bool:
        if not self.message_launch.has_ags(): raise Exception("LTI launch doesn't have AGS permissions")
        
        sub = self.launch_data.get('sub')
        timestamp = datetime.now().isoformat() + 'Z'
        
        grades = self.message_launch.get_ags()
        
        grade = Grade() \
            .set_user_id(sub) \
            .set_timestamp(timestamp) \
            .set_activity_progress("Completed") \
            .set_grading_progress("Pending") \
            .set_extra_claims({"submissionId": f"{session_question.quiz_session_id}"})
        
        return grades.put_grade(grade)


class QuizSessionScoreSender(BaseResultSender[SessionQuestion]):
    
    def _send(self, session_question: SessionQuestion) -> bool:
        if not self.message_launch.has_ags(): raise Exception("LTI launch doesn't have AGS permissions")
        
        sub = self.launch_data.get('sub')
        timestamp = datetime.now().isoformat() + 'Z'
        
        grades = self.message_launch.get_ags()
        
        grade = Grade() \
            .set_user_id(sub) \
            .set_timestamp(timestamp) \
            .set_activity_progress("Completed") \
            .set_grading_progress("FullyGraded") \
            .set_score_given(session_question.score) \
            .set_extra_claims({"submissionId": f"{session_question.quiz_session_id}"})
        
        return grades.put_grade(grade)
