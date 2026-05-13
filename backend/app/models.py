import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UploadStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    reupload_requested = "reupload_requested"


class UserRole(str, enum.Enum):
    employee = "employee"
    manager = "manager"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.employee, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    uploads: Mapped[list["Upload"]] = relationship(back_populates="uploaded_by", foreign_keys="Upload.uploaded_by_id")


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[UploadStatus] = mapped_column(Enum(UploadStatus, name="upload_status"), default=UploadStatus.pending, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    total_columns: Mapped[int] = mapped_column(Integer, default=0)
    columns: Mapped[list] = mapped_column(JSONB, default=list)
    detected_types: Mapped[dict] = mapped_column(JSONB, default=dict)
    preview_rows: Mapped[list] = mapped_column(JSONB, default=list)
    validation_summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_path: Mapped[str | None] = mapped_column(String(500))
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    uploaded_by: Mapped[User | None] = relationship(foreign_keys=[uploaded_by_id], back_populates="uploads")
    comments: Mapped[list["ManagerComment"]] = relationship(back_populates="upload", cascade="all, delete-orphan")
    staged_rows: Mapped[list["PendingUploadRow"]] = relationship(back_populates="upload", cascade="all, delete-orphan")


class PendingUploadRow(Base):
    __tablename__ = "pending_upload_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"))
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    upload: Mapped[Upload] = relationship(back_populates="staged_rows")


class ApprovedTransaction(Base):
    __tablename__ = "approved_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id"))
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    department: Mapped[str | None] = mapped_column(String(120))
    employee_name: Mapped[str | None] = mapped_column(String(120))
    kpi_name: Mapped[str | None] = mapped_column(String(160))
    target_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    actual_value: Mapped[float | None] = mapped_column(Numeric(14, 2))
    attainment_pct: Mapped[float | None] = mapped_column(Numeric(8, 2))
    transaction_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ManagerComment(Base):
    __tablename__ = "manager_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="CASCADE"))
    manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    upload: Mapped[Upload] = relationship(back_populates="comments")


class KpiSnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
