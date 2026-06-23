"""
User Repository - Data Access Layer for User authentication.

Handles all database operations for user management.
"""
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import DeclarativeMeta

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.auth import UserCreate, UserUpdate, UserResponse, UserRole
from app.models.user import User


class UserRepository:
    """
    Repository for User model database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_data: UserCreate, hashed_password: str) -> UserResponse:
        """
        Create a new user.

        Args:
            user_data: User creation data
            hashed_password: Pre-hashed password

        Returns:
            Created user response

        Raises:
            ConflictError: If email or username already exists
        """
        # Check for existing email
        existing_email = await self.get_by_email(user_data.email)
        if existing_email:
            raise ConflictError(
                f"User with email '{user_data.email}' already exists",
                details={"field": "email", "value": user_data.email}
            )

        # Check for existing username
        existing_username = await self.get_by_username(user_data.username)
        if existing_username:
            raise ConflictError(
                f"User with username '{user_data.username}' already exists",
                details={"field": "username", "value": user_data.username}
            )

        # Create user
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            role=user_data.role.value,
        )

        self.session.add(db_user)
        await self.session.flush()
        await self.session.refresh(db_user)

        return self._to_response(db_user)

    async def get_by_id(self, user_id: UUID | str) -> UserResponse | None:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User response or None
        """
        result = await self.session.execute(
            select(User).where(User.user_id == str(user_id))
        )
        user = result.scalar_one_or_none()
        return self._to_response(user) if user else None

    async def get_by_email(self, email: str) -> UserResponse | None:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            User response or None
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        return self._to_response(user) if user else None

    async def get_by_username(self, username: str) -> UserResponse | None:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            User response or None
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        return self._to_response(user) if user else None

    async def get_for_auth(self, email: str) -> User | None:
        """
        Get user model (not response) for authentication.

        Includes hashed_password for login verification.

        Args:
            email: User email

        Returns:
            User model or None
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        role: UserRole | None = None,
        disabled: bool | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[UserResponse]:
        """
        List users with optional filtering.

        Args:
            role: Filter by role
            disabled: Filter by disabled status
            limit: Max results
            offset: Pagination offset

        Returns:
            List of user responses
        """
        from app.constants import MAX_LIMIT, MIN_LIMIT, MIN_OFFSET

        # Validate pagination
        if limit > MAX_LIMIT:
            raise ValidationError(
                f"Limit cannot exceed {MAX_LIMIT}",
                details={"limit": limit, "max_limit": MAX_LIMIT}
            )
        if limit < MIN_LIMIT:
            raise ValidationError(
                f"Limit must be at least {MIN_LIMIT}",
                details={"limit": limit, "min_limit": MIN_LIMIT}
            )
        if offset < MIN_OFFSET:
            raise ValidationError(
                "Offset cannot be negative",
                details={"offset": offset}
            )

        # Build query
        query = select(User)

        if role:
            query = query.where(User.role == role.value)

        if disabled is not None:
            query = query.where(User.disabled == disabled)

        query = query.order_by(User.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        users = result.scalars().all()

        return [self._to_response(user) for user in users]

    async def update(self, user_id: UUID | str, update_data: UserUpdate) -> UserResponse | None:
        """
        Update a user.

        Args:
            user_id: User UUID
            update_data: Update data

        Returns:
            Updated user response or None

        Raises:
            NotFoundError: If user doesn't exist
            ConflictError: If email/username conflict
        """
        # Check if user exists
        existing = await self.get_by_id(user_id)
        if not existing:
            raise NotFoundError(
                f"User with ID '{user_id}' not found",
                details={"user_id": str(user_id)}
            )

        # Build update dict
        update_dict = {}
        if update_data.email is not None:
            # Check for email conflict
            email_check = await self.get_by_email(update_data.email)
            if email_check and str(email_check.user_id) != str(user_id):
                raise ConflictError(
                    f"Email '{update_data.email}' already in use",
                    details={"field": "email", "value": update_data.email}
                )
            update_dict["email"] = update_data.email

        if update_data.username is not None:
            # Check for username conflict
            username_check = await self.get_by_username(update_data.username)
            if username_check and str(username_check.user_id) != str(user_id):
                raise ConflictError(
                    f"Username '{update_data.username}' already in use",
                    details={"field": "username", "value": update_data.username}
                )
            update_dict["username"] = update_data.username

        if update_data.role is not None:
            update_dict["role"] = update_data.role.value

        if update_data.disabled is not None:
            update_dict["disabled"] = update_data.disabled

        if not update_dict:
            return existing

        # Perform update
        stmt = (
            update(User)
            .where(User.user_id == str(user_id))
            .values(**update_dict)
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Return updated user
        return await self.get_by_id(user_id)

    async def update_last_login(self, user_id: UUID | str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User UUID
        """
        stmt = (
            update(User)
            .where(User.user_id == str(user_id))
            .values(last_login=datetime.utcnow())
        )
        await self.session.execute(stmt)

    async def delete(self, user_id: UUID | str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if not found
        """
        # Check if user exists
        existing = await self.get_by_id(user_id)
        if not existing:
            return False

        # Delete user
        stmt = (
            update(User)
            .where(User.user_id == str(user_id))
            .values(disabled=True)  # Soft delete
        )
        await self.session.execute(stmt)
        return True

    async def count_users(
        self,
        role: UserRole | None = None,
        disabled: bool | None = None
    ) -> int:
        """
        Count users matching filters.

        Args:
            role: Filter by role
            disabled: Filter by disabled status

        Returns:
            User count
        """
        from sqlalchemy import func

        query = select(func.count()).select_from(User)

        if role:
            query = query.where(User.role == role.value)

        if disabled is not None:
            query = query.where(User.disabled == disabled)

        result = await self.session.execute(query)
        return result.scalar() or 0

    def _to_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse."""
        return UserResponse(
            user_id=UUID(user.user_id),
            email=user.email,
            username=user.username,
            role=UserRole(user.role),
            disabled=user.disabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
