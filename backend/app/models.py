import enum
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
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
    pending = "pending"
    approved = "approved"
    declined = "declined"
    reupload_requested = "reupload_requested"


class ReviewAction(str, enum.Enum):
    approved = "approved"
    declined = "declined"
    reupload_requested = "reupload_requested"


class TransactionType(str, enum.Enum):
    Payment = "Payment"
    Debit = "Debit"
    Credit = "Credit"
    Transfer = "Transfer"
    Refund = "Refund"


class PaymentMethod(str, enum.Enum):
    NEFT = "NEFT"
    UPI = "UPI"
    CreditCard = "Credit Card"
    DebitCard = "Debit Card"
    NetBanking = "Net Banking"


class TransactionStatus(str, enum.Enum):
    Initiated = "Initiated"
    Pending = "Pending"
    Successful = "Successful"
    Failed = "Failed"


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
    manager: Mapped["User | None"] = relationship(remote_side=[id], back_populates="employees", foreign_keys=[manager_id])
    employees: Mapped[list["User"]] = relationship(back_populates="manager", foreign_keys=[manager_id])

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


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_reviews_submission_id"),
        CheckConstraint(
            "(action = 'approved') OR (comment IS NOT NULL AND length(trim(comment)) > 0)",
            name="ck_reviews_comment_required",
        ),
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


class TransactionRow(Base):
    __tablename__ = "transaction_rows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_number: Mapped[str] = mapped_column(String(80), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(120), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type", values_callable=enum_values),
        nullable=False,
    )
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", values_callable=enum_values),
        nullable=False,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status", values_callable=enum_values),
        nullable=False,
    )

    submission: Mapped[Submission] = relationship(back_populates="transaction_rows")
