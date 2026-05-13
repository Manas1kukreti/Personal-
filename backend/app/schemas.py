from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="employee", pattern="^(employee|manager|admin)$")


class UserRead(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class UploadPreview(BaseModel):
    upload_id: UUID
    filename: str
    status: str
    total_rows: int
    total_columns: int
    columns: list[str]
    detected_types: dict = Field(default_factory=dict)
    validation: dict = Field(default_factory=dict)
    preview_rows: list[dict]


class UploadSummary(BaseModel):
    id: UUID
    filename: str
    status: str
    total_rows: int
    total_columns: int
    uploader_name: str | None = None
    validation_passed: bool = True
    created_at: datetime


class ApprovalRequest(BaseModel):
    manager_id: UUID | None = None
    comment: str | None = Field(default=None, max_length=2000)


class RejectRequest(ApprovalRequest):
    comment: str = Field(min_length=1, max_length=2000)


class ReuploadRequest(RejectRequest):
    pass
