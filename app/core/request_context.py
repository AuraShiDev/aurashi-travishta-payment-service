from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.common.constants import Roles
from app.core.exceptions import AccessDenied
from app.core.messages import ErrorMessage
from app.utils.response import ApiResponse, ErrorDetail
from app.core.errors import ErrorCode

from typing import Optional
from pydantic import BaseModel
from enum import Enum

class AuthStatus(str, Enum):
    AUTHENTICATED = "AUTHENTICATED"
    ANONYMOUS = "ANONYMOUS"


class UserContext(BaseModel):
    auth_status: AuthStatus
    user_id: Optional[str] = None
    type: Optional[str] = None
    session_id: Optional[str] = None


class GatewayAuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        auth_status = request.headers.get("AuthStatus")
        user_id = request.headers.get("UserId")
        roles = request.headers.get("UserRoles")
        user_type = request.headers.get("UserType")
        session_id = request.headers.get("X-Session-Id")
        print(request.headers)
        # 🔐 Enforce gateway presence
        if not auth_status:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ApiResponse(
                    success=False,
                    statusCode=401,
                    message=ErrorMessage.AUTH_CONTEXT_MISSING,
                    data=None,
                    errors=[
                        ErrorDetail(
                            code=ErrorCode.ACCESS_TOKEN_REQUIRED,
                            message="Request must pass through gateway",
                        )
                    ],
                ).model_dump(),
            )

        # 🔍 Validate auth status
        if auth_status not in AuthStatus.__members__:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=ApiResponse(
                    success=False,
                    statusCode=401,
                    message=ErrorMessage.AUTH_CONTEXT_MISSING,
                    data=None,
                    errors=[
                        ErrorDetail(
                            code=ErrorCode.ACCESS_TOKEN_REQUIRED,
                            message="Invalid X-Auth-Status header",
                        )
                    ],
                ).model_dump(),
            )

        # 🧠 Build context
        request.state.user_context = UserContext(
            auth_status=AuthStatus[auth_status],
            user_id=user_id,
            type=user_type,
            session_id=session_id,
        )

        return await call_next(request)

def _get_user_context(request: Request) -> UserContext:
    user_ctx = getattr(request.state, "user_context", None)

    if not user_ctx:
        raise AccessDenied(ErrorMessage.AUTH_CONTEXT_MISSING)

    return user_ctx



def is_valid_user(request: Request) -> None:
    user_ctx = _get_user_context(request)

    if user_ctx.auth_status != AuthStatus.AUTHENTICATED:
        raise AccessDenied(ErrorMessage.USER_NOT_AUTHENTICATED)

    if not user_ctx.user_id:
        raise AccessDenied(ErrorMessage.USER_ID_MISSING)


def is_admin_user(request: Request) -> None:
    is_valid_user(request)

    user_ctx = _get_user_context(request)

    if user_ctx.type != Roles.ADMIN:
        raise AccessDenied(ErrorMessage.ADMIN_ACCESS_REQUIRED)

def is_public_user(request: Request) -> None:
    user_ctx = _get_user_context(request)

    if user_ctx.auth_status != AuthStatus.ANONYMOUS:
        raise AccessDenied(ErrorMessage.DRIVER_ACCESS_REQUIRED)

def is_end_user(request: Request) -> None:
    is_valid_user(request)

    user_ctx = _get_user_context(request)

    if user_ctx.type != Roles.USER:
        raise AccessDenied(ErrorMessage.END_USER_ACCESS_REQUIRED)

def get_idempotency_key(request: Request) -> Optional[str]:
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        return None

    idempotency_key = idempotency_key.strip()
    return idempotency_key or None

def get_razorpay_signature_key(request: Request) -> Optional[str]:
    razorpay_signature = request.headers.get("Razorpay-Signature")
    if not razorpay_signature:
        return None

    razorpay_signature = razorpay_signature.strip()
    return razorpay_signature or None

