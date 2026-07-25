"""集成测试 - 认证流程"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestAuthFlow:
    """认证流程集成测试"""

    @pytest.mark.asyncio
    async def test_register_login_flow(self, client: AsyncClient):
        """测试注册登录完整流程"""
        import uuid
        username = f"newuser_{uuid.uuid4().hex[:8]}"

        # 1. 注册新用户
        register_response = await client.post("/api/v1/auth/register", json={
            "username": username,
            "password": "newpass123",
            "account_name": "新用户"
        })
        assert register_response.status_code == 200
        data = register_response.json()
        assert data["username"] == username
        assert data["account_name"] == "新用户"

        # 2. 使用新用户登录
        login_response = await client.post("/api/v1/auth/login", json={
            "username": username,
            "password": "newpass123"
        })
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data

        token = login_data["access_token"]

        # 3. 使用token访问受保护资源
        profile_response = await client.get(
            "/api/v1/user/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["username"] == username

    @pytest.mark.asyncio
    async def test_login_with_wrong_password(self, client: AsyncClient, test_user):
        """测试错误密码登录"""
        response = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_resource_without_token(self, client: AsyncClient):
        """测试无token访问受保护资源"""
        response = await client.get("/api/v1/accounts/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_resource_with_invalid_token(self, client: AsyncClient):
        """测试无效token访问受保护资源"""
        response = await client.get(
            "/api/v1/accounts/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user):
        """测试注册重复用户名"""
        response = await client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "anotherpass",
            "account_name": "另一个用户"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_token_refresh(self, client: AsyncClient, test_user):
        """测试Token刷新"""
        # 登录获取refresh token
        login_response = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass123"
        })
        refresh_token = login_response.json()["refresh_token"]

        # 使用refresh token刷新
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()
        assert "access_token" in refresh_data

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient, auth_headers):
        """测试登出"""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        assert response.status_code == 200
