"""
Authentication API Endpoints.

Provides REST endpoints for user registration, login, and token management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request

from app.api.deps import get_auth_service, get_current_user, require_admin
from app.api.rate_limit import limiter, rate_limit_auth, rate_limit_admin, rate_limit_read
from app.exceptions import AuthenticationError, AuthorizationError, ValidationError
from app.models.auth import Token, TokenPayload, TokenRefresh, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Endpoints

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Stricter limit for registration
async def register(
    user_data: UserCreate,
    request: Request,  # Required for rate limiting
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.

    - **email**: User email address (must be unique)
    - **username**: Username (3-50 chars, alphanumeric + underscore/hyphen)
    - **password**: Password (min 8 chars, must contain uppercase, lowercase, digit)
    - **role**: User role (default: 'user')
    """
    try:
        return await auth_service.register(user_data)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # Login rate limit
async def login(
    login_data: UserLogin,
    request: Request,  # Required for rate limiting
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate user and receive JWT tokens.

    Returns both access_token (short-lived) and refresh_token (long-lived).
    Use access_token in Authorization header for authenticated requests.
    Use refresh_token to obtain new access_token when it expires.

    - **email**: User email address
    - **password**: User password
    """
    try:
        return await auth_service.login(login_data)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")  # Refresh rate limit
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Long-lived refresh token from login

    Returns new token pair.
    """
    try:
        return await auth_service.refresh_token(token_data.refresh_token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
@limiter.limit("100/minute")  # Read endpoint
async def get_current_user_info(
    request: Request,
    current_user: TokenPayload = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Get current user information.

    Requires valid access token.
    """
    try:
        return await auth_service.get_current_user(current_user.sub)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.post("/logout")
async def logout():
    """
    Logout user (token invalidation on client side).

    Note: JWT tokens are stateless. To properly implement logout,
    consider maintaining a token blacklist or using refresh token rotation.
    """
    return {"message": "Successfully logged out"}


# Admin endpoints

@router.get("/users", response_model=list[UserResponse])
@limiter.limit("50/minute")  # Admin endpoint
async def list_users(
    request: Request,
    current_admin: TokenPayload = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    List all users (Admin only).

    Requires admin role.
    """
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(auth_service.session)
    return await repo.list_users()
