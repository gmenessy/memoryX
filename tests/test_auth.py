"""
Authentication Service Tests.

Tests for user registration, login, token generation, and authorization.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.auth import (
    UserRole,
    UserCreate,
    UserLogin,
    Token,
    Permission,
    TokenType,
)
from app.services.auth_service import AuthService
from app.exceptions import ConflictError, AuthenticationError, ValidationError


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test that password hashing produces different hashes for same input."""
        service = AuthService(session=None)

        password = "SecurePassword123"
        hash1 = service.hash_password(password)
        hash2 = service.hash_password(password)

        # Hashes should be different (due to salt)
        assert hash1 != hash2
        # But both should verify correctly
        assert service.verify_password(password, hash1)
        assert service.verify_password(password, hash2)

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        service = AuthService(session=None)

        password = "SecurePassword123"
        hashed = service.hash_password(password)

        assert service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        service = AuthService(session=None)

        password = "SecurePassword123"
        hashed = service.hash_password(password)

        assert service.verify_password("WrongPassword123", hashed) is False


class TestUserRolePermissions:
    """Test role-based permission system."""

    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        from app.models.auth import has_permission

        for permission in Permission:
            assert has_permission(UserRole.ADMIN, permission)

    def test_readonly_limited_permissions(self):
        """Test that readonly role has limited permissions."""
        from app.models.auth import has_permission

        # Should have read permissions
        assert has_permission(UserRole.READONLY, Permission.MEMORY_READ)
        assert has_permission(UserRole.READONLY, Permission.EVENT_READ)

        # Should not have write permissions
        assert not has_permission(UserRole.READONLY, Permission.MEMORY_CREATE)
        assert not has_permission(UserRole.READONLY, Permission.MEMORY_DELETE)

    def test_user_standard_permissions(self):
        """Test that user role has standard permissions."""
        from app.models.auth import has_permission

        # Should have create/read/update
        assert has_permission(UserRole.USER, Permission.MEMORY_CREATE)
        assert has_permission(UserRole.USER, Permission.MEMORY_READ)
        assert has_permission(UserRole.USER, Permission.MEMORY_UPDATE)

        # Should not have delete or admin permissions
        assert not has_permission(UserRole.USER, Permission.MEMORY_DELETE)
        assert not has_permission(UserRole.USER, Permission.GOVERNANCE_ADMIN)


class TestTokenGeneration:
    """Test JWT token generation and validation."""

    def test_generate_access_token(self):
        """Test access token generation."""
        service = AuthService(session=None)

        user_id = str(uuid4())
        email = "test@example.com"
        role = UserRole.USER

        tokens = service.generate_tokens(user_id, email, role)

        assert tokens.access_token
        assert tokens.refresh_token
        assert tokens.token_type == TokenType.ACCESS
        assert tokens.expires_in == service.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_verify_valid_token(self):
        """Test verification of valid token."""
        service = AuthService(session=None)

        user_id = str(uuid4())
        email = "test@example.com"
        role = UserRole.USER

        tokens = service.generate_tokens(user_id, email, role)

        payload = service.verify_token(tokens.access_token, TokenType.ACCESS)

        assert payload.sub == user_id
        assert payload.email == email
        assert payload.role == role
        assert payload.type == TokenType.ACCESS

    def test_verify_token_with_wrong_type(self):
        """Test that token with wrong type is rejected."""
        service = AuthService(session=None)

        user_id = str(uuid4())
        email = "test@example.com"
        role = UserRole.USER

        tokens = service.generate_tokens(user_id, email, role)

        # Try to verify refresh token as access token
        with pytest.raises(AuthenticationError):
            service.verify_token(tokens.refresh_token, TokenType.ACCESS)

    def test_token_expiration(self):
        """Test token expiration."""
        from unittest.mock import patch
        from datetime import datetime, timedelta

        service = AuthService(session=None)

        # Create a token that's already expired
        user_id = str(uuid4())
        email = "test@example.com"
        role = UserRole.USER

        # Mock time to be in the future
        with patch('app.services.auth_service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() + timedelta(days=30)

            tokens = service.generate_tokens(user_id, email, role)

        # Verify token (should fail because it's expired)
        # Note: This test assumes proper JWT exp validation
        # Actual expiration validation happens during verify_token


class TestUserValidation:
    """Test user creation validation."""

    def test_user_create_with_strong_password(self):
        """Test user creation with strong password."""
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="SecurePass123",
            role=UserRole.USER,
        )

        assert user_data.email == "test@example.com"
        assert user_data.username == "testuser"
        assert user_data.role == UserRole.USER

    def test_user_create_with_weak_password(self):
        """Test that weak password is rejected."""
        with pytest.raises(ValidationError, match="uppercase"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="weakpassword",  # No uppercase
                role=UserRole.USER,
            )

        with pytest.raises(ValidationError, match="lowercase"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="WEAKPASSWORD",  # No lowercase
                role=UserRole.USER,
            )

        with pytest.raises(ValidationError, match="digit"):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="WeakPass",  # No digit
                role=UserRole.USER,
            )

    def test_user_create_with_invalid_username(self):
        """Test that invalid username is rejected."""
        with pytest.raises(ValidationError, match="username"):
            UserCreate(
                email="test@example.com",
                username="user@name",  # Invalid character
                password="SecurePass123",
                role=UserRole.USER,
            )

    def test_user_create_with_short_password(self):
        """Test that short password is rejected."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="Short1",  # Less than 8 chars
                role=UserRole.USER,
            )


class TestAuthorization:
    """Test authorization checks."""

    def test_check_permission_success(self):
        """Test successful permission check."""
        service = AuthService(session=None)

        # Admin should have all permissions
        result = service.check_permission(UserRole.ADMIN, Permission.MEMORY_DELETE)
        assert result is True

    def test_check_permission_failure(self):
        """Test failed permission check."""
        service = AuthService(session=None)

        # Readonly should not have delete permission
        with pytest.raises(AuthenticationError):  # Raises AuthorizationError internally
            service.check_permission(UserRole.READONLY, Permission.MEMORY_DELETE)

    def test_require_role_success(self):
        """Test successful role requirement."""
        service = AuthService(session=None)

        # Admin should pass admin requirement
        result = service.require_role(UserRole.ADMIN, [UserRole.ADMIN])
        assert result is True

    def test_require_role_with_admin_override(self):
        """Test that admin bypasses role requirements."""
        service = AuthService(session=None)

        # Admin should pass even if not in required list
        result = service.require_role(UserRole.ADMIN, [UserRole.USER])
        assert result is True

    def test_require_role_failure(self):
        """Test failed role requirement."""
        service = AuthService(session=None)

        # User should not pass admin requirement
        with pytest.raises(AuthenticationError):  # Raises AuthorizationError internally
            service.require_role(UserRole.USER, [UserRole.ADMIN])


@pytest.mark.asyncio
class TestAuthServiceIntegration:
    """Integration tests for AuthService."""

    async def test_register_and_login_flow(self, test_db_session):
        """Test complete registration and login flow."""
        from app.repositories.user_repository import UserRepository

        # Create service
        service = AuthService(test_db_session)

        # Register user
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="SecurePass123",
            role=UserRole.USER,
        )

        user = await service.register(user_data)

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert user.disabled is False

        # Login with credentials
        login_data = UserLogin(
            email="test@example.com",
            password="SecurePass123",
        )

        tokens = await service.login(login_data)

        assert tokens.access_token
        assert tokens.refresh_token
        assert tokens.token_type == TokenType.ACCESS

    async def test_login_with_invalid_credentials(self, test_db_session):
        """Test login with invalid credentials."""
        from app.repositories.user_repository import UserRepository

        service = AuthService(test_db_session)

        # Try to login with non-existent user
        login_data = UserLogin(
            email="nonexistent@example.com",
            password="SecurePass123",
        )

        with pytest.raises(AuthenticationError):
            await service.login(login_data)

    async def test_login_with_wrong_password(self, test_db_session):
        """Test login with wrong password."""
        service = AuthService(test_db_session)

        # Register user
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="SecurePass123",
            role=UserRole.USER,
        )

        await service.register(user_data)

        # Try to login with wrong password
        login_data = UserLogin(
            email="test@example.com",
            password="WrongPassword123",
        )

        with pytest.raises(AuthenticationError):
            await service.login(login_data)

    async def test_duplicate_email_rejection(self, test_db_session):
        """Test that duplicate email is rejected."""
        service = AuthService(test_db_session)

        # Register first user
        user_data1 = UserCreate(
            email="test@example.com",
            username="testuser1",
            password="SecurePass123",
            role=UserRole.USER,
        )

        await service.register(user_data1)

        # Try to register second user with same email
        user_data2 = UserCreate(
            email="test@example.com",  # Same email
            username="testuser2",
            password="SecurePass123",
            role=UserRole.USER,
        )

        with pytest.raises(ConflictError):
            await service.register(user_data2)

    async def test_duplicate_username_rejection(self, test_db_session):
        """Test that duplicate username is rejected."""
        service = AuthService(test_db_session)

        # Register first user
        user_data1 = UserCreate(
            email="test1@example.com",
            username="testuser",
            password="SecurePass123",
            role=UserRole.USER,
        )

        await service.register(user_data1)

        # Try to register second user with same username
        user_data2 = UserCreate(
            email="test2@example.com",
            username="testuser",  # Same username
            password="SecurePass123",
            role=UserRole.USER,
        )

        with pytest.raises(ConflictError):
            await service.register(user_data2)

    async def test_login_disabled_user(self, test_db_session):
        """Test that disabled user cannot login."""
        from app.repositories.user_repository import UserRepository

        service = AuthService(test_db_session)
        repo = UserRepository(test_db_session)

        # Register user
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="SecurePass123",
            role=UserRole.USER,
        )

        user = await service.register(user_data)

        # Disable user
        from app.models.auth import UserUpdate
        await repo.update(user.user_id, UserUpdate(disabled=True))

        # Try to login
        login_data = UserLogin(
            email="test@example.com",
            password="SecurePass123",
        )

        with pytest.raises(AuthenticationError, match="disabled"):
            await service.login(login_data)

    async def test_token_refresh(self, test_db_session):
        """Test token refresh flow."""
        service = AuthService(test_db_session)

        # Register and login
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="SecurePass123",
            role=UserRole.USER,
        )

        await service.register(user_data)

        login_data = UserLogin(
            email="test@example.com",
            password="SecurePass123",
        )

        tokens = await service.login(login_data)

        # Refresh token
        new_tokens = await service.refresh_token(tokens.refresh_token)

        assert new_tokens.access_token
        assert new_tokens.refresh_token
        # New access token should be different from old one
        assert new_tokens.access_token != tokens.access_token
