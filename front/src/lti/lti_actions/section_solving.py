from .base import BaseActionHandler, BaseActionResultSender
from flask import redirect, url_for
from datetime import datetime
from pylti1p3.grade import Grade
from pylti1p3.lineitem import LineItem

class SectionSolvingHandler(BaseActionHandler):

    def _process(self):
        resource_link = self.launch_data.get("https://purl.imsglobal.org/spec/lti/claim/resource_link")
        launch_section_id = resource_link.get('id')

        return redirect(url_for('get_section_endpoint', section=launch_section_id))


class SectionSolvingResultSender(BaseActionResultSender[float]):
    
    def send(self, score: float) -> bool:
        if not self.message_launch.has_ags():
            raise Exception("LTI launch doesn't have AGS permissions")
        
        resource_link = self.launch_data.get(
            "https://purl.imsglobal.org/spec/lti/claim/resource_link"
        )
        resource_link_id = resource_link.get('id') if resource_link else None
        
        sub = self.launch_data.get('sub')
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        grades = self.message_launch.get_ags()
        
        grade = Grade() \
            .set_score_given(score) \
            .set_timestamp(timestamp) \
            .set_user_id(sub)
        
        line_item = LineItem() \
            .set_tag('score') \
            .set_resource_id(resource_link_id)
        
        grades.put_grade(grade, line_item)
        return True
