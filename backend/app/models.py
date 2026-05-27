import enum
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def enum_values(enum_type: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_type]


class UserRole(str, enum.Enum):
    employee = "employee"
    manager = "manager"
    admin = "admin"


class ReviewStatus(str, enum.Enum):
    processing = "processing"
    pending = "pending"
    approved = "approved"
    declined = "declined"
    parse_failed = "parse_failed"
    reupload_requested = "reupload_requested"


class ReviewAction(str, enum.Enum):
    approved = "approved"
    declined = "declined"
    reupload_requested = "reupload_requested"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=enum_values),
        default=UserRole.employee,
        nullable=False,
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submissions: Mapped[list["Submission"]] = relationship(back_populates="user", foreign_keys="Submission.user_id")
    reviews: Mapped[list["Review"]] = relationship(back_populates="manager", foreign_keys="Review.manager_id")
    comments: Mapped[list["SubmissionComment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    manager: Mapped["User | None"] = relationship(remote_side=[id], back_populates="employees", foreign_keys=[manager_id])
    employees: Mapped[list["User"]] = relationship(back_populates="manager", foreign_keys=[manager_id])
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def name(self) -> str:
        return self.full_name


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_submission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id"))
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, name="review_status", values_callable=enum_values),
        default=ReviewStatus.pending,
        nullable=False,
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="submissions", foreign_keys=[user_id])
    parent_submission: Mapped["Submission | None"] = relationship(remote_side=[id])
    review: Mapped["Review | None"] = relationship(back_populates="submission", cascade="all, delete-orphan")
    transaction_rows: Mapped[list["TransactionRow"]] = relationship(back_populates="submission", cascade="all, delete-orphan")
    comments: Mapped[list["SubmissionComment"]] = relationship(back_populates="submission", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_reviews_submission_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    manager_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action: Mapped[ReviewAction] = mapped_column(
        Enum(ReviewAction, name="review_action", values_callable=enum_values),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped[Submission] = relationship(back_populates="review")
    manager: Mapped[User] = relationship(back_populates="reviews")


class SubmissionComment(Base):
    __tablename__ = "submission_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    submission: Mapped[Submission] = relationship(back_populates="comments")
    user: Mapped[User] = relationship(back_populates="comments")


class TransactionRow(Base):
    __tablename__ = "transaction_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)

    # Date
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Entry split — entry_group ties the two legs together, entry_line distinguishes them
    entry_group: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_line: Mapped[int] = mapped_column(Integer, nullable=False)

    # Account info
    sub_account: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str] = mapped_column(String(255), nullable=False)
    account_code: Mapped[str] = mapped_column(String(80), nullable=False)

    # Amounts — one side will be null on each leg (standard double-entry)
    debit_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    credit_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Classification — 'class' is a Python reserved word so stored as account_class
    account_class: Mapped[str] = mapped_column(String(120), nullable=False)
    sub_class: Mapped[str] = mapped_column(String(120), nullable=False)

    # Geography
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)

    submission: Mapped["Submission"] = relationship(back_populates="transaction_rows")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class AuditAction(str, enum.Enum):
    upload_created = "upload_created"
    upload_approved = "upload_approved"
    upload_declined = "upload_declined"
    reupload_requested = "reupload_requested"
    reupload_submitted = "reupload_submitted"
    comment_added = "comment_added"
    user_assigned = "user_assigned"
    user_reassigned = "user_reassigned"
    login = "login"
    logout = "logout"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", values_callable=enum_values),
        nullable=False,
    )
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    actor: Mapped["User | None"] = relationship(foreign_keys=[actor_id])