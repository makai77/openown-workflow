class WorkflowError(Exception):
    code = "workflow_error"
    status_code = 400

    def __init__(self, message: str, *, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class InvalidTransition(WorkflowError):
    code = "invalid_transition"


class CommentRequired(WorkflowError):
    code = "comment_required"


class WorkflowPermissionDenied(WorkflowError):
    code = "permission_denied"
    status_code = 403
