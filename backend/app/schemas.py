from datetime import date, datetime
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


class AccountUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class AgentTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TransactionRowRead(BaseModel):
    id: UUID
    submission_id: UUID
    date: date
    entry_group: int
    entry_line: int
    sub_account: str
    details: str
    account_code: str
    debit_amount: float | None = None
    credit_amount: float | None = None
    account_class: str
    sub_class: str
    country: str
    region: str

class UploadVersionRead(BaseModel):
    id: UUID
    filename: str
    status: str
    version_number: int
    created_at: datetime
    reviewed_at: datetime | None = None


class UploadPreview(BaseModel):
    upload_id: UUID
    filename: str
    status: str
    version_number: int = 1
    parent_submission_id: UUID | None = None
    total_rows: int
    total_columns: int
    created_at: datetime | None = None
    reviewed_at: datetime | None = None
    columns: list[str]
    detected_types: dict = Field(default_factory=dict)
    validation: dict = Field(default_factory=dict)
    preview_rows: list[dict]
    version_history: list[UploadVersionRead] = Field(default_factory=list)


class UploadSummary(BaseModel):
    id: UUID
    filename: str
    status: str
    version_number: int = 1
    parent_submission_id: UUID | None = None
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
    pass


class ReuploadRequest(RejectRequest):
    pass


class RejectActionRequest(RejectRequest):
    upload_id: UUID


class ReuploadActionRequest(ReuploadRequest):
    upload_id: UUID


class SubmissionCommentCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class SubmissionCommentRead(BaseModel):
    id: UUID
    submission_id: UUID
    user_id: UUID
    user_name: str
    user_role: str
    message: str
    created_at: datetime
