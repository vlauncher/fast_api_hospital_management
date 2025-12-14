import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.auth.models import User, Role
from app.core.security import verify_password, get_password_hash


@pytest.mark.auth
@pytest.mark.integration
class TestAuthentication:
    """Test authentication endpoints and functionality."""

    async def test_register_user_success(self, client: AsyncClient) -> None:
        """Test successful user registration."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "full_name": "New User",
            "phone_number": "+1234567890"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "password" not in data
        assert "id" in data

    async def test_register_user_duplicate_username(self, client: AsyncClient, test_user: User) -> None:
        """Test registration with duplicate username."""
        user_data = {
            "username": test_user.username,
            "email": "different@example.com",
            "password": "password123",
            "full_name": "Different User"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_register_user_duplicate_email(self, client: AsyncClient, test_user: User) -> None:
        """Test registration with duplicate email."""
        user_data = {
            "username": "differentuser",
            "email": test_user.email,
            "password": "password123",
            "full_name": "Different User"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_login_success(self, client: AsyncClient, test_user: User) -> None:
        """Test successful user login."""
        login_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_credentials(self, client: AsyncClient) -> None:
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/v1/auth/login", data=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    async def test_get_current_user(self, authenticated_client: AsyncClient, test_user: User) -> None:
        """Test getting current user information."""
        response = await authenticated_client.get("/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert "password" not in data

    async def test_get_current_user_unauthorized(self, client: AsyncClient) -> None:
        """Test getting current user without authentication."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401

    async def test_refresh_token(self, authenticated_client: AsyncClient) -> None:
        """Test refreshing access token."""
        # First login to get refresh token
        login_data = {
            "username": "testuser",
            "password": "testpassword123"
        }
        response = await authenticated_client.post("/api/v1/auth/login", data=login_data)
        refresh_token = response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        response = await authenticated_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_change_password_success(self, authenticated_client: AsyncClient) -> None:
        """Test successful password change."""
        password_data = {
            "current_password": "testpassword123",
            "new_password": "newpassword123"
        }
        
        response = await authenticated_client.post("/api/v1/auth/change-password", json=password_data)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

    async def test_change_password_wrong_current(self, authenticated_client: AsyncClient) -> None:
        """Test password change with wrong current password."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }
        
        response = await authenticated_client.post("/api/v1/auth/change-password", json=password_data)
        
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    async def test_logout_success(self, authenticated_client: AsyncClient) -> None:
        """Test successful logout."""
        response = await authenticated_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"


@pytest.mark.auth
@pytest.mark.unit
class TestSecurityUtilities:
    """Test security utility functions."""

    def test_password_hashing(self) -> None:
        """Test password hashing and verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_password_hash_uniqueness(self) -> None:
        """Test that same password produces different hashes."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.auth
@pytest.mark.integration
class TestUserManagement:
    """Test user management endpoints."""

    async def test_get_users_admin_only(self, admin_client: AsyncClient) -> None:
        """Test getting all users (admin only)."""
        response = await admin_client.get("/api/v1/auth/users")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_users_unauthorized(self, authenticated_client: AsyncClient) -> None:
        """Test getting all users without admin privileges."""
        response = await authenticated_client.get("/api/v1/auth/users")
        
        assert response.status_code == 403

    async def test_update_user_success(self, authenticated_client: AsyncClient, test_user: User) -> None:
        """Test updating user information."""
        update_data = {
            "full_name": "Updated Name",
            "phone_number": "+9876543210"
        }
        
        response = await authenticated_client.put(f"/api/v1/auth/users/{test_user.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["phone_number"] == update_data["phone_number"]

    async def test_deactivate_user_admin_only(self, admin_client: AsyncClient, test_user: User) -> None:
        """Test deactivating a user (admin only)."""
        response = await admin_client.patch(f"/api/v1/auth/users/{test_user.id}/deactivate")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    async def test_create_role_admin_only(self, admin_client: AsyncClient) -> None:
        """Test creating a new role (admin only)."""
        role_data = {
            "name": "new_role",
            "description": "A new test role",
            "permissions": ["read:patients"]
        }
        
        response = await admin_client.post("/api/v1/auth/roles", json=role_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == role_data["name"]
        assert data["description"] == role_data["description"]

    async def test_assign_role_admin_only(self, admin_client: AsyncClient, test_user: User) -> None:
        """Test assigning a role to a user (admin only)."""
        # First create a role
        role_data = {
            "name": "test_assignment_role",
            "description": "Role for assignment test",
            "permissions": ["read:patients"]
        }
        response = await admin_client.post("/api/v1/auth/roles", json=role_data)
        role_id = response.json()["id"]
        
        # Assign role to user
        assignment_data = {
            "user_id": str(test_user.id),
            "role_id": role_id
        }
        
        response = await admin_client.post("/api/v1/auth/assign-role", json=assignment_data)
        
        assert response.status_code == 200
        assert response.json()["message"] == "Role assigned successfully"


@pytest.mark.auth
@pytest.mark.integration
@pytest.mark.slow
class TestAuthenticationFlow:
    """Test complete authentication workflows."""

    async def test_complete_user_lifecycle(self, client: AsyncClient) -> None:
        """Test complete user lifecycle: register, login, access protected resource, logout."""
        # Register user
        user_data = {
            "username": "lifecycle_user",
            "email": "lifecycle@example.com",
            "password": "password123",
            "full_name": "Lifecycle User"
        }
        
        register_response = await client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201
        user_id = register_response.json()["id"]
        
        # Login
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        tokens = login_response.json()
        
        # Access protected resource
        client.headers.update({"Authorization": f"Bearer {tokens['access_token']}"})
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["username"] == user_data["username"]
        
        # Change password
        password_data = {
            "current_password": user_data["password"],
            "new_password": "newpassword123"
        }
        
        change_response = await client.post("/api/v1/auth/change-password", json=password_data)
        assert change_response.status_code == 200
        
        # Logout
        logout_response = await client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200
        
        # Try to access protected resource after logout
        me_response_after_logout = await client.get("/api/v1/auth/me")
        assert me_response_after_logout.status_code == 401

    async def test_token_refresh_flow(self, client: AsyncClient, test_user: User) -> None:
        """Test token refresh flow with expired access token."""
        # Login
        login_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }
        
        login_response = await client.post("/api/v1/auth/login", data=login_data)
        tokens = login_response.json()
        
        # Use refresh token to get new access token
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        
        # Verify new token works
        client.headers.update({"Authorization": f"Bearer {new_tokens['access_token']}"})
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
