from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    field: str | None = None
    details: dict = Field(default_factory=dict)


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    pages: int


class ApiResponse[T](BaseModel):
    success: bool = True
    data: T | None = None
    message: str = "OK"


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody


class ApiListResponse[T](BaseModel):
    success: bool = True
    data: list[T]
    pagination: Pagination
