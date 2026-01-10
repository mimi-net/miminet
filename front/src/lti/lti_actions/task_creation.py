from .base import BaseActionHandler
from flask import render_template, session

class TaskCreationHandler(BaseActionHandler):
    
    def _process(self):
        dl_settings = self.launch_data.get("https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings")
        
        if "deep_link_return_url" in dl_settings:
            session["deep_link_return_url"] = dl_settings["deep_link_return_url"]
        
        return render_template("lti/deep_link_selector.html", launch_data=self.launch_data)