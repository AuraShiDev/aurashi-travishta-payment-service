from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import GlobalException
from app.core.errors import ErrorCode
from app.core.messages import ErrorMessage
from app.utils.response import ApiResponse, ErrorDetail


def register_exception_handlers(app: FastAPI):
    # ---------- Custom Domain Errors ----------
    @app.exception_handler(GlobalException)
    async def handle_global_exception(
        request: Request, exc: GlobalException
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResponse(
                success=False,
                statusCode=exc.status_code,
                message=exc.message,
                data=None,
                errors=[
                    ErrorDetail(
                        code=exc.error_code,
                        message=exc.message,
                    )
                ],
            ).dict(),
        )

    # ---------- Database Errors ----------
    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        request: Request, exc: SQLAlchemyError
    ):
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                statusCode=500,
                message=ErrorMessage.DATABASE_FAILURE,
                data=None,
                errors=[
                    ErrorDetail(
                        code=ErrorCode.DATABASE_ERROR,
                        message=str(exc),
                    )
                ],
            ).dict(),
        )

    # ---------- Catch-all (500) ----------
    @app.exception_handler(Exception)
    async def handle_unhandled_exception(
        request: Request, exc: Exception
    ):
        return JSONResponse(
            status_code=500,
            content=ApiResponse(
                success=False,
                statusCode=500,
                message=ErrorMessage.SERVER_ERROR,
                data=None,
                errors=[
                    ErrorDetail(
                        code=ErrorCode.INTERNAL_SERVER_ERROR,
                        message=str(exc),
                    )
                ],
            ).dict(),
        )
