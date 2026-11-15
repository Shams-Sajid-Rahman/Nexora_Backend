"""Standard error shape (docs/06): {"error": {"code", "message", "details"}}."""
from typing import Any


class AppError(Exception):
    status_code = 400
    code = "APP_ERROR"

    def __init__(self, message: str, code: str | None = None,
                 status_code: int | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationAppError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
