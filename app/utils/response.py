from typing import Generic, TypeVar, List, Optional, Dict
from pydantic import BaseModel

T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: str
    field: Optional[str] = None
    message: str

class PaginationMeta(BaseModel):
    page: int
    pageSize: int
    totalRecords: int
    totalPages: int

class MetaData(BaseModel):
    pagination: Optional[PaginationMeta] = None
    filters: Optional[Dict] = None
    sort: Optional[Dict] = None

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    statusCode: int
    message: str
    data: Optional[T]
    meta: Optional[MetaData] = None
    errors: Optional[List[ErrorDetail]] = None
    traceId: Optional[str] = None


def success_response(data, message="Success", meta=None, status_code=200, trace_id=None):
    return ApiResponse(
        success=True,
        statusCode=status_code,
        message=message,
        data=data,
        meta=meta,
        errors=None,
        traceId=trace_id
    )

def error_response(message, errors, status_code=400, trace_id=None):
    return ApiResponse(
        success=False,
        statusCode=status_code,
        message=message,
        data=None,
        meta=None,
        errors=errors,
        traceId=trace_id
    )
