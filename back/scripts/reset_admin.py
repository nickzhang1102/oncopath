"""
清理 login_account 表并创建 admin 用户
独立脚本，不依赖 app 模块
"""
import asyncio
import sys
import os

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import asyncpg
import bcrypt

# 密码加密
def hash_password(password: str) -> str:
    """使用 bcrypt 加密密码"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


async def reset_admin():
    """清理所有用户并创建admin用户"""
    # 从环境变量获取数据库配置
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "medical_report")

    conn = await asyncpg.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name
    )

    try:
        print("=" * 60)
        print("清理 login_account 表并创建 admin 用户")
        print("=" * 60)

        # 1. 查看当前用户
        rows = await conn.fetch("SELECT account_id, username, account_type FROM login_account")
        print(f"\n当前用户数量: {len(rows)}")
        for row in rows:
            print(f"  - ID:{row['account_id']}, 用户名:{row['username']}, 类型:{row['account_type']}")

        # 2. 清空 login_account 表（CASCADE 级联删除关联数据）
        print("\n正在清空 login_account 表（CASCADE）...")
        await conn.execute("DELETE FROM login_account CASCADE")
        print("[OK] login_account 表已清空")

        # 3. 创建 admin 用户
        print("\n正在创建 admin 用户...")
        admin_password = os.environ.get("ADMIN_INITIAL_PASSWORD", "admin123")
        hashed_password = hash_password(admin_password)

        await conn.execute("""
            INSERT INTO login_account (username, password, account_name, account_type, status)
            VALUES ($1, $2, $3, $4, $5)
        """, 'admin', hashed_password, '管理员', 'admin', 'active')

        print("[OK] admin 用户创建成功")

        # 4. 验证
        row = await conn.fetchrow("SELECT account_id, username, account_type, status FROM login_account WHERE username = 'admin'")
        if row:
            print(f"\n验证成功:")
            print(f"  账号ID: {row['account_id']}")
            print(f"  用户名: {row['username']}")
            print(f"  账号类型: {row['account_type']}")
            print(f"  状态: {row['status']}")
            print(f"  密码: {'**** (从环境变量)' if os.environ.get('ADMIN_INITIAL_PASSWORD') else 'admin123 (默认)'}")

        print("\n" + "=" * 60)
        print("[完成] admin 用户已就绪")
        print("=" * 60)

    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(reset_admin())
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()