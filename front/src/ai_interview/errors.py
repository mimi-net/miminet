class InterviewError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class InterviewUnavailable(InterviewError):
    status_code = 403


class InterviewConflict(InterviewError):
    status_code = 409


class InterviewNotFound(InterviewError):
    status_code = 404
