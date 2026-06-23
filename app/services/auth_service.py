"""
Authentication Service - Business Logic for User Authentication

Handles JWT token generation, password hashing, and user authentication flows.
"""
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import CONFIDENCE_MIN
from app.exceptions import AuthenticationError, AuthorizationError, ValidationError
from app.models.auth import (
    Token,
    TokenPayload,
    TokenType,
    UserCreate,
    UserLogin,
    UserResponse,
    UserRole,
)
from app.repositories.user_repository import UserRepository


class AuthService:
    """
    Service for authentication and authorization operations.

    Handles:
    - User registration and login
    - JWT token generation and validation
    - Password hashing and verification
    - Authorization checks
    """

    # JWT Configuration
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    ALGORITHM = "HS256"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = UserRepository(session)

    # Password Hashing

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches
        """
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )

    # User Registration

    async def register(self, user_data: UserCreate) -> UserResponse:
        """
        Register a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user response

        Raises:
            ConflictError: If email or username exists
            ValidationError: If password doesn't meet requirements
        """
        # Hash password
        hashed_password = self.hash_password(user_data.password)

        # Create user
        return await self.repository.create(user_data, hashed_password)

    # User Authentication

    async def login(self, login_data: UserLogin) -> Token:
        """
        Authenticate user and generate tokens.

        Args:
            login_data: Login credentials

        Returns:
            JWT tokens (access + refresh)

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Get user by email
        user = await self.repository.get_for_auth(login_data.email)

        if not user:
            raise AuthenticationError(
                "Invalid email or password",
                details={"field": "email"}
            )

        # Verify password
        if not self.verify_password(login_data.password, user.hashed_password):
            raise AuthenticationError(
                "Invalid email or password",
                details={"field": "password"}
            )

        # Check if user is disabled
        if user.disabled:
            raise AuthenticationError(
                "Account is disabled",
                details={"email": user.email}
            )

        # Update last login
        await self.repository.update_last_login(user.user_id)

        # Generate tokens
        return self.generate_tokens(user.user_id, user.email, UserRole(user.role))

    async def refresh_token(self, refresh_token: str) -> Token:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New JWT tokens

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            # Decode refresh token
            payload = jwt.decode(
                refresh_token,
                settings.secret_key,
                algorithms=[self.ALGORITHM],
            )

            # Verify token type
            if payload.get("type") != TokenType.REFRESH:
                raise AuthenticationError(
                    "Invalid token type",
                    details={"expected": TokenType.REFRESH}
                )

            # Extract user info
            user_id = payload.get("sub")
            email = payload.get("email")
            role = UserRole(payload.get("role"))

            # Verify user still exists and is active
            user = await self.repository.get_for_auth(email)
            if not user or str(user.user_id) != user_id:
                raise AuthenticationError("User not found")

            if user.disabled:
                raise AuthenticationError("Account is disabled")

            # Generate new tokens
            return self.generate_tokens(user_id, email, role)

        except jwt.PyJWTError as e:
            raise AuthenticationError(
                "Invalid refresh token",
                details={"error": str(e)}
            )

    def generate_tokens(
        self,
        user_id: str,
        email: str,
        role: UserRole
    ) -> Token:
        """
        Generate access and refresh tokens.

        Args:
            user_id: User UUID
            email: User email
            role: User role

        Returns:
            Token pair
        """
        now = datetime.utcnow()

        # Access token (short-lived)
        access_payload = {
            "sub": user_id,
            "email": email,
            "role": role.value,
            "iat": now,
            "exp": now + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES),
            "type": TokenType.ACCESS,
        }
        access_token = jwt.encode(
            access_payload,
            settings.secret_key,
            algorithm=self.ALGORITHM,
        )

        # Refresh token (long-lived)
        refresh_payload = {
            "sub": user_id,
            "email": email,
            "role": role.value,
            "iat": now,
            "exp": now + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS),
            "type": TokenType.REFRESH,
        }
        refresh_token = jwt.encode(
            refresh_payload,
            settings.secret_key,
            algorithm=self.ALGORITHM,
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=TokenType.ACCESS,
            expires_in=self.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        )

    def verify_token(self, token: str, token_type: TokenType = TokenType.ACCESS) -> TokenPayload:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token
            token_type: Expected token type

        Returns:
            Token payload

        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[self.ALGORITHM],
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise AuthenticationError(
                    f"Expected {token_type} token",
                    details={"expected": token_type, "got": payload.get("type")}
                )

            return TokenPayload(**payload)

        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(
                "Invalid token",
                details={"error": str(e)}
            )

    # Authorization

    def check_permission(self, role: UserRole, required_permission: str) -> bool:
        """
        Check if a role has a specific permission.

        Args:
            role: User role
            required_permission: Required permission

        Returns:
            True if authorized

        Raises:
            AuthorizationError: If not authorized
        """
        from app.models.auth import has_permission, Permission

        # Convert string to Permission enum
        try:
            permission = Permission(required_permission)
        except ValueError:
            raise ValidationError(
                f"Unknown permission: {required_permission}",
                details={"permission": required_permission}
            )

        if not has_permission(role, permission):
            raise AuthorizationError(
                f"Role '{role}' does not have permission '{required_permission}'",
                details={
                    "role": role.value,
                    "required_permission": required_permission
                }
            )

        return True

    def require_role(self, user_role: UserRole, required_roles: list[UserRole]) -> bool:
        """
        Check if user has one of the required roles.

        Args:
            user_role: User's current role
            required_roles: List of acceptable roles

        Returns:
            True if authorized

        Raises:
            AuthorizationError: If not authorized
        """
        if user_role not in required_roles and user_role != UserRole.ADMIN:
            raise AuthorizationError(
                f"Role '{user_role}' not in required roles: {required_roles}",
                details={
                    "user_role": user_role.value,
                    "required_roles": [r.value for r in required_roles]
                }
            )

        return True

    # User Management

    async def get_current_user(self, user_id: UUID | str) -> UserResponse:
        """
        Get current authenticated user.

        Args:
            user_id: User UUID

        Returns:
            User response

        Raises:
            NotFoundError: If user doesn't exist
        """
        from app.exceptions import NotFoundError

        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(
                f"User with ID '{user_id}' not found",
                details={"user_id": str(user_id)}
            )

        return user

    async def update_user(
        self,
        user_id: UUID | str,
        update_data: dict
    ) -> UserResponse:
        """
        Update user information.

        Args:
            user_id: User UUID
            update_data: Update data

        Returns:
            Updated user response
        """
        from app.models.auth import UserUpdate

        user_update = UserUpdate(**update_data)
        return await self.repository.update(user_id, user_update)
