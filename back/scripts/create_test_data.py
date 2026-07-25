"""
创建测试数据脚本 - 修正版

用于快速创建首页UI测试所需的数据
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
from app.core.database import AsyncSessionLocal
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalType, MedicalIndex, MedicalCheck, MedicalCheckDetail
from app.core.security import get_password_hash


async def create_test_data():
    """创建测试数据"""
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("开始创建测试数据...")
        print("=" * 60)

        # 1. 创建测试用户
        print("\n[1/6] 检查测试用户...")
        from sqlalchemy import select

        # 先检查用户是否存在
        user_result = await db.execute(
            select(LoginAccount).where(LoginAccount.username == "testuser")
        )
        user = user_result.scalar_one_or_none()

        if not user:
            print("[创建] 用户不存在，正在创建...")
            user = LoginAccount(
                username="testuser",
                password=get_password_hash("Test123456"),
                phone="13800138000",
                account_name="测试用户",
                account_type="user"
            )
            db.add(user)
            await db.flush()
            print(f"[OK] 用户创建成功: {user.username} (ID: {user.account_id})")
        else:
            print(f"[OK] 使用现有用户: {user.username} (ID: {user.account_id})")

        # 2. 创建测试患者
        print("\n[2/6] 检查测试患者...")

        # 先检查患者是否存在
        patient_result = await db.execute(
            select(Patient).where(
                Patient.account_id == user.account_id,
                Patient.patient_name == "张三"
            )
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            print("[创建] 患者不存在，正在创建...")
            patient = Patient(
                patient_name="张三",
                account_id=user.account_id,
                gender="男",
                birth_date=date(1985, 5, 15),
                patient_phone="13800138000",
                id_card="110101198505150011"
            )
            db.add(patient)
            await db.flush()
            print(f"[OK] 患者创建成功: {patient.patient_name} (ID: {patient.patient_id})")
        else:
            print(f"[OK] 使用现有患者: {patient.patient_name} (ID: {patient.patient_id})")

        # 3. 获取或创建医疗类型
        print("\n[3/6] 获取医疗类型...")

        from sqlalchemy import select

        # 直接通过ID获取（假设数据库已有标准类型）
        # ID=2: 血常规, ID=3: 肿瘤标志物
        blood_type_result = await db.execute(
            select(MedicalType).where(MedicalType.type_id == 2)
        )
        blood_type = blood_type_result.scalar_one_or_none()

        tumor_type_result = await db.execute(
            select(MedicalType).where(MedicalType.type_id == 3)
        )
        tumor_type = tumor_type_result.scalar_one_or_none()

        if not blood_type or not tumor_type:
            # 如果没有，查询所有类型看看有什么
            all_types = await db.execute(select(MedicalType))
            types_list = all_types.scalars().all()

            print(f"[警告] 未找到标准医疗类型，现有类型: {[(t.type_id, t.type_name) for t in types_list]}")

            # 尝试通过名称获取
            for t in types_list:
                if '血常规' in t.type_name or '血' in t.type_name:
                    blood_type = t
                if '肿瘤' in t.type_name or '标志物' in t.type_name:
                    tumor_type = t

        print(f"[OK] 医疗类型: 血常规(ID={blood_type.type_id if blood_type else 'None'}), 肿瘤标志物(ID={tumor_type.type_id if tumor_type else 'None'})")

        # 4. 创建标准指标库
        print("\n[4/6] 准备标准指标库...")

        # 获取血常规指标
        blood_indices_result = await db.execute(
            select(MedicalIndex).where(MedicalIndex.medical_type == blood_type.type_id).limit(6)
        )
        blood_indices = list(blood_indices_result.scalars().all())

        # 获取肿瘤标志物指标
        tumor_indices_result = await db.execute(
            select(MedicalIndex).where(MedicalIndex.medical_type == tumor_type.type_id).limit(6)
        )
        tumor_indices = list(tumor_indices_result.scalars().all())

        # 如果肿瘤标志物指标不足，创建新的
        if len(tumor_indices) < 6:
            print(f"[创建] 肿瘤标志物指标不足({len(tumor_indices)}/6)，正在创建...")

            new_tumor_indices = [
                MedicalIndex(
                    index_name="甲胎蛋白",
                    index_code="AFP",
                    index_unit="ng/mL",
                    reference_min=0,
                    reference_max=20,
                    medical_type=tumor_type.type_id,
                    category="肿瘤标志物",
                    is_active=True,
                    is_chart=True
                ),
                MedicalIndex(
                    index_name="癌胚抗原",
                    index_code="CEA",
                    index_unit="ng/mL",
                    reference_min=0,
                    reference_max=5,
                    medical_type=tumor_type.type_id,
                    category="肿瘤标志物",
                    is_active=True,
                    is_chart=True
                ),
                MedicalIndex(
                    index_name="糖类抗原125",
                    index_code="CA125",
                    index_unit="U/mL",
                    reference_min=0,
                    reference_max=35,
                    medical_type=tumor_type.type_id,
                    category="肿瘤标志物",
                    is_active=True,
                    is_chart=True
                ),
                MedicalIndex(
                    index_name="糖类抗原19-9",
                    index_code="CA19-9",
                    index_unit="U/mL",
                    reference_min=0,
                    reference_max=37,
                    medical_type=tumor_type.type_id,
                    category="肿瘤标志物",
                    is_active=True,
                    is_chart=True
                ),
                MedicalIndex(
                    index_name="前列腺特异性抗原",
                    index_code="PSA",
                    index_unit="ng/mL",
                    reference_min=0,
                    reference_max=4,
                    medical_type=tumor_type.type_id,
                    category="肿瘤标志物",
                    is_active=True,
                    is_chart=True
                ),
                MedicalIndex(
                    index_name="糖类抗原15-3",
                    index_code="CA15-3",
                    index_unit="U/mL",
                    reference_min=0,
                    reference_max=25,
                    medical_type=tumor_type.type_id,
                    category="肿瘤标志物",
                    is_active=True,
                    is_chart=True
                ),
            ]

            db.add_all(new_tumor_indices)
            await db.flush()

            # 重新获取肿瘤标志物指标
            tumor_indices_result = await db.execute(
                select(MedicalIndex).where(MedicalIndex.medical_type == tumor_type.type_id).limit(6)
            )
            tumor_indices = list(tumor_indices_result.scalars().all())

        # 如果血常规指标不足，也创建新的
        if len(blood_indices) < 4:
            print(f"[创建] 血常规指标不足({len(blood_indices)}/4)，正在创建...")

            new_blood_indices = [
                MedicalIndex(
                    index_name="白细胞计数",
                    index_code="WBC",
                    index_unit="10^9/L",
                    reference_min=4.0,
                    reference_max=10.0,
                    medical_type=blood_type.type_id,
                    category="血常规",
                    sub_category="白细胞系",
                    is_active=True,
                    is_chart=True
                ),
                MedicalIndex(
                    index_name="红细胞计数",
                    index_code="RBC",
                    index_unit="10^12/L",
                    reference_min=3.5,
                    reference_max=5.5,
                    medical_type=blood_type.type_id,
                    category="血常规",
                    sub_category="红细胞系",
                    is_active=True,
                    is_chart=True
                ),
                MedicalIndex(
                    index_name="血红蛋白",
                    index_code="HGB",
                    index_unit="g/L",
                    reference_min=120,
                    reference_max=160,
                    medical_type=blood_type.type_id,
                    category="血常规",
                    sub_category="红细胞系",
                    is_active=True,
                    is_chart=True
                ),
                MedicalIndex(
                    index_name="血小板计数",
                    index_code="PLT",
                    index_unit="10^9/L",
                    reference_min=100,
                    reference_max=300,
                    medical_type=blood_type.type_id,
                    category="血常规",
                    sub_category="血小板系",
                    is_active=True,
                    is_chart=True
                ),
            ]

            db.add_all(new_blood_indices)
            await db.flush()

            # 重新获取血常规指标
            blood_indices_result = await db.execute(
                select(MedicalIndex).where(MedicalIndex.medical_type == blood_type.type_id).limit(6)
            )
            blood_indices = list(blood_indices_result.scalars().all())

        print(f"[OK] 标准指标库: 血常规 {len(blood_indices)} 个, 肿瘤标志物 {len(tumor_indices)} 个")

        # 5. 创建检验记录（最近3个月的数据）
        print("\n[5/6] 创建检验记录...")

        check_records = []
        detail_records = []

        # 创建3个月的血常规数据
        for i in range(3):
            check_date = date.today() - timedelta(days=i * 30)
            check = MedicalCheck(
                patient_id=patient.patient_id,
                medical_date=check_date,
                hospital="北京协和医院",
                medical_type=blood_type.type_id,  # 使用整数字段
                comment="定期检查"
            )
            db.add(check)
            await db.flush()
            check_records.append(check)

            # 为每次检验创建明细
            details = [
                MedicalCheckDetail(
                    medical_id=check.medical_id,
                    index_id=blood_indices[0].index_id,
                    index_name="白细胞计数",
                    index_value=f"{6.5 + i * 0.5:.1f}",
                    index_unit="10^9/L",
                    reference_value="4.0-10.0",
                    index_status="normal"
                ),
                MedicalCheckDetail(
                    medical_id=check.medical_id,
                    index_id=blood_indices[1].index_id,
                    index_name="红细胞计数",
                    index_value=f"{4.2 + i * 0.1:.1f}",
                    index_unit="10^12/L",
                    reference_value="3.5-5.5",
                    index_status="normal"
                ),
                MedicalCheckDetail(
                    medical_id=check.medical_id,
                    index_id=blood_indices[2].index_id,
                    index_name="血红蛋白",
                    index_value=f"{135 + i * 2}",
                    index_unit="g/L",
                    reference_value="120-160",
                    index_status="normal"
                ),
                MedicalCheckDetail(
                    medical_id=check.medical_id,
                    index_id=blood_indices[3].index_id,
                    index_name="血小板计数",
                    index_value=f"{180 + i * 10}",
                    index_unit="10^9/L",
                    reference_value="100-300",
                    index_status="normal"
                ),
            ]
            detail_records.extend(details)

        # 创建肿瘤标志物数据
        for i in range(3):
            check_date = date.today() - timedelta(days=i * 30)
            check = MedicalCheck(
                patient_id=patient.patient_id,
                medical_date=check_date,
                hospital="北京协和医院",
                medical_type=tumor_type.type_id,
                comment="肿瘤筛查"
            )
            db.add(check)
            await db.flush()
            check_records.append(check)

            # 添加一个异常指标用于测试异常提醒
            details = [
                MedicalCheckDetail(
                    medical_id=check.medical_id,
                    index_id=tumor_indices[0].index_id,
                    index_name="甲胎蛋白",
                    index_value=f"{15 + i * 2}",
                    index_unit="ng/mL",
                    reference_value="0-20",
                    index_status="high" if i == 0 else "normal"
                ),
                MedicalCheckDetail(
                    medical_id=check.medical_id,
                    index_id=tumor_indices[1].index_id,
                    index_name="癌胚抗原",
                    index_value=f"{3.5 + i * 0.3:.1f}",
                    index_unit="ng/mL",
                    reference_value="0-5",
                    index_status="normal"
                ),
                MedicalCheckDetail(
                    medical_id=check.medical_id,
                    index_id=tumor_indices[2].index_id,
                    index_name="糖类抗原125",
                    index_value=f"{25 + i * 2}",
                    index_unit="U/mL",
                    reference_value="0-35",
                    index_status="normal"
                ),
            ]
            detail_records.extend(details)

        db.add_all(detail_records)
        print(f"[OK] 检验记录创建成功: {len(check_records)} 条")
        print(f"[OK] 检验明细创建成功: {len(detail_records)} 条")

        # 6. 提交事务
        print("\n[6/6] 提交数据...")
        await db.commit()

        print("\n" + "=" * 60)
        print("[OK] 测试数据创建完成！")
        print("=" * 60)
        print("\n测试账号信息:")
        print(f"  用户名: {user.username}")
        print(f"  密码: Test123456")
        print(f"\n患者信息:")
        print(f"  姓名: {patient.patient_name}")
        print(f"  患者ID: {patient.patient_id}")
        print(f"\n数据统计:")
        print(f"  血常规记录: 3 次")
        print(f"  肿瘤标志物记录: 3 次")
        print(f"  异常指标: 1 个 (甲胎蛋白)")
        print("\n可以使用此账号登录测试首页UI功能。")
        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(create_test_data())
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
