# app/core/exceptions.py
from app.core.messages import ErrorMessage

class GlobalException(Exception):
    status_code: int
    error_code: str
    message: str

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


class AccessTokenRequired(GlobalException):
    status_code = 401
    error_code = "access_token_required"
    message = "Please provide a valid access token"


class ResourceNotFound(GlobalException):
    status_code = 404
    error_code = "not_found"
    message = "Requested resource not found"


class ValidationException(GlobalException):
    status_code = 400
    error_code = "validation_error"
    message = "Validation failed"

class AccessDenied(GlobalException):
    status_code = 403
    error_code = "access_denied"
    message = ErrorMessage.ACCESS_DENIED

class UserNotFound(GlobalException):
    status_code = 404
    error_code = "user_not_found"
    message = ErrorMessage.USER_NOT_FOUND

class UserAlreadyExists(GlobalException):
    status_code = 400
    error_code = "user_already_exists"
    message = ErrorMessage.USER_ALREADY_EXISTS

class InvalidCredentials(GlobalException):
    status_code = 401
    error_code = "invalid_credentials"
    message = ErrorMessage.INVALID_CREDENTIALS

class InvalidOTP(GlobalException):
    status_code = 400
    error_code = "invalid_otp"
    message = ErrorMessage.OTP_INVALID

class BadRequest(GlobalException):
    status_code = 400
    error_code = "bad_request"
    message = "Bad request"
class ExternalServiceError(GlobalException):
    status_code = 502
    error_code = "external_service_error"
    message = "External service request failed"