import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import LoginAccount

class TestAuth:
    @pytest.mark.asyncio
    async def test_register(self, client):
        """测试用户注册"""
        import uuid
        unique_username = f"testuser_{uuid.uuid4().hex[:8]}"
        response = await client.post("/api/v1/auth/register", json={
            "username": unique_username,
            "password": "testpass123",
            "account_name": "Test User"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == unique_username
        assert data["account_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client, db_session):
        """测试重复用户名注册"""
        import uuid
        username = f"duplicate_{uuid.uuid4().hex[:8]}"

        # 创建第一个用户
        user = LoginAccount(
            username=username,
            password=get_password_hash("pass123"[:72])
        )
        db_session.add(user)
        await db_session.commit()

        # 尝试注册相同用户名
        response = await client.post("/api/v1/auth/register", json={
            "username": username,
            "password": "pass456"
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success(self, client, db_session):
        """测试登录成功"""
        import uuid
        # 创建用户
        user = LoginAccount(
            username=f"loginuser_{uuid.uuid4().hex[:8]}",
            password=get_password_hash("password123"[:72])
        )
        db_session.add(user)
        await db_session.commit()

        # 登录
        response = await client.post("/api/v1/auth/login", json={
            "username": user.username,
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, db_session):
        """测试密码错误"""
        import uuid
        username = f"wrongpass_{uuid.uuid4().hex[:8]}"

        user = LoginAccount(
            username=username,
            password=get_password_hash("correctpass"[:72])
        )
        db_session.add(user)
        await db_session.commit()

        response = await client.post("/api/v1/auth/login", json={
            "username": username,
            "password": "wrongpass"
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_with_invalid_phone(self, client):
        """测试无效手机号注册"""
        response = await client.post("/api/v1/auth/register", json={
            "username": "invalidphone",
            "password": "testpass123",
            "account_name": "Invalid Phone User",
            "phone": "invalid-phone-format"
        })
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """测试登录不存在的用户"""
        response = await client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "anypassword"
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_token_refresh_success(self, client, db_session):
        """测试Token刷新成功"""
        import uuid
        username = f"refreshuser_{uuid.uuid4().hex[:8]}"

        # 创建用户
        user = LoginAccount(
            username=username,
            password=get_password_hash("password123"[:72])
        )
        db_session.add(user)
        await db_session.commit()

        # 登录获取refresh token
        login_response = await client.post("/api/v1/auth/login", json={
            "username": username,
            "password": "password123"
        })
        refresh_token = login_response.json()["refresh_token"]

        # 刷新token
        response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_token_refresh_invalid(self, client):
        """测试无效refresh token"""
        response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_without_token(self, client):
        """测试未授权访问受保护路由"""
        response = await client.get("/api/v1/accounts/me")
        assert response.status_code == 401  # Unauthorized

    @pytest.mark.asyncio
    async def test_protected_route_with_valid_token(self, client, db_session):
        """测试有效Token访问受保护路由"""
        import uuid
        username = f"protecteduser_{uuid.uuid4().hex[:8]}"

        # 创建用户
        user = LoginAccount(
            username=username,
            password=get_password_hash("password123"[:72])
        )
        db_session.add(user)
        await db_session.commit()

        # 登录
        login_response = await client.post("/api/v1/auth/login", json={
            "username": username,
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # 访问受保护路由
        response = await client.get(
            "/api/v1/accounts/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logout_success(self, client, db_session):
        """测试登出成功"""
        import uuid
        username = f"logoutuser_{uuid.uuid4().hex[:8]}"

        # 创建用户
        user = LoginAccount(
            username=username,
            password=get_password_hash("password123"[:72])
        )
        db_session.add(user)
        await db_session.commit()

        # 登录
        login_response = await client.post("/api/v1/auth/login", json={
            "username": username,
            "password": "password123"
        })
        token = login_response.json()["access_token"]

        # 登出
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # 尝试使用已登出的token（取决于实现，可能返回401）
        # protected_response = await client.get(
        #     "/api/v1/accounts/profile",
        #     headers={"Authorization": f"Bearer {token}"}
        # )
        # assert protected_response.status_code == 401
