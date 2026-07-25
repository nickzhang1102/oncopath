"""集成测试 - 患者流程"""
import pytest
from httpx import AsyncClient


class TestPatientFlow:
    """患者流程集成测试"""

    @pytest.mark.asyncio
    async def test_create_and_query_patient(self, client: AsyncClient, auth_headers):
        """测试创建和查询患者"""
        # 1. 创建患者
        create_response = await client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "patient_name": "测试患者",
                "patient_phone": "13812345678",
                "gender": "male"
            }
        )
        assert create_response.status_code == 200
        patient_data = create_response.json()
        assert patient_data["patient_name"] == "测试患者"
        patient_id = patient_data["patient_id"]

        # 2. 查询患者列表
        list_response = await client.get(
            "/api/v1/patients",
            headers=auth_headers
        )
        assert list_response.status_code == 200
        patients = list_response.json()
        assert isinstance(patients, list)
        assert len(patients) > 0

        # 3. 查询患者详情
        detail_response = await client.get(
            f"/api/v1/patients/{patient_id}",
            headers=auth_headers
        )
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["patient_name"] == "测试患者"

    @pytest.mark.asyncio
    async def test_patient_data_isolation(self, client: AsyncClient, auth_headers):
        """测试患者数据隔离"""
        # 创建患者
        create_response = await client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "patient_name": "隔离测试患者",
                "gender": "female"
            }
        )
        assert create_response.status_code == 200
        patient_id = create_response.json()["patient_id"]

        # 未认证访问应该失败
        unauth_response = await client.get(f"/api/v1/patients/{patient_id}")
        assert unauth_response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_patient(self, client: AsyncClient, auth_headers):
        """测试更新患者信息"""
        # 创建患者
        create_response = await client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "patient_name": "更新测试患者",
                "gender": "male"
            }
        )
        patient_id = create_response.json()["patient_id"]

        # 更新患者信息
        update_response = await client.put(
            f"/api/v1/patients/{patient_id}",
            headers=auth_headers,
            json={
                "patient_name": "更新后患者名",
                "patient_phone": "13987654321"
            }
        )
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["patient_name"] == "更新后患者名"

    @pytest.mark.asyncio
    async def test_delete_patient(self, client: AsyncClient, auth_headers):
        """测试删除患者"""
        # 创建患者
        create_response = await client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "patient_name": "待删除患者",
                "gender": "male"
            }
        )
        patient_id = create_response.json()["patient_id"]

        # 删除患者
        delete_response = await client.delete(
            f"/api/v1/patients/{patient_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200

        # 确认已删除
        detail_response = await client.get(
            f"/api/v1/patients/{patient_id}",
            headers=auth_headers
        )
        assert detail_response.status_code == 404

    @pytest.mark.asyncio
    async def test_patient_name_desensitization(self, client: AsyncClient, auth_headers):
        """测试患者姓名脱敏"""
        # 创建患者
        create_response = await client.post(
            "/api/v1/patients",
            headers=auth_headers,
            json={
                "patient_name": "张三李四",
                "gender": "male"
            }
        )
        assert create_response.status_code == 200
        patient_data = create_response.json()

        # 验证返回的是脱敏后的姓名（不再返回明文）
        assert "patient_name" in patient_data
        masked_name = patient_data["patient_name"]
        # 脱敏格式: 张***
        assert masked_name != "张三李四"
