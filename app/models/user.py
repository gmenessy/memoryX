"""
User Database Model.

SQLAlchemy model for user authentication and authorization.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.auth import UserRole


class User(Base):
    """
    User model for authentication and authorization.

    Stores user credentials and role information for RBAC.
    """

    __tablename__ = "users"

    # Primary key
    user_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
        index=True,
    )

    # User identifiers
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # Authentication
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Authorization
    role: Mapped[UserRole] = mapped_column(
        String(20),
        default=UserRole.USER,
        nullable=False,
    )

    # Status
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<User(user_id={self.user_id}, email={self.email}, role={self.role})>"
