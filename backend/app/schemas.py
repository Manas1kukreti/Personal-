from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="employee", pattern="^(employee|manager)$")


class UserRead(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    manager_id: UUID | None = None
    manager_name: str | None = None


class AdminUserRead(UserRead):
    assigned_employee_count: int = 0


class AdminEmployeeRead(UserRead):
    assignment_status: str


class AssignmentRequest(BaseModel):
    employee_id: UUID
    manager_id: UUID


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
    created_at: datetime | None = None
    reviewed_at: datetime | None = None
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
    reviewed_at: datetime | None = None


class ApprovalRequest(BaseModel):
    manager_id: UUID | None = None
    comment: str | None = Field(default=None, max_length=2000)


class ApprovalActionRequest(ApprovalRequest):
    upload_id: UUID


class RejectRequest(ApprovalRequest):
    comment: str = Field(min_length=1, max_length=2000)


class ReuploadRequest(RejectRequest):
    pass


class RejectActionRequest(RejectRequest):
    upload_id: UUID


class ReuploadActionRequest(ReuploadRequest):
    upload_id: UUID
