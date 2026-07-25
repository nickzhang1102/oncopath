"""时间工具函数

提供统一的 UTC 时间获取方法，确保数据库存储的时间一致且无时区信息。
提供日期计算辅助函数。
提供 UTC ISO 8601 字符串格式化函数，统一返回带 Z 后缀的时区标识，
避免前端按本地时区误读，造成时间显示偏差。
"""

from datetime import datetime, date, timezone
from typing import Optional


def get_utc_now() -> datetime:
    """获取当前 UTC 时间（无时区信息，用于数据库存储）

    使用 datetime.now(timezone.utc) 替代已过期的 datetime.utcnow()，
    并通过 .replace(tzinfo=None) 移除时区信息，确保与数据库兼容。

    Returns:
        datetime: 当前 UTC 时间，无时区信息
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_isoformat(dt: Optional[datetime]) -> Optional[str]:
    """将 datetime 序列化为带 Z 后缀的 ISO 8601 字符串

    项目约定：所有 DateTime 字段在数据库中均以 UTC naive datetime 存储。
    在 API 响应序列化时，必须显式带上时区标识（Z 或 +00:00），
    否则前端 dayjs / new Date() 会将无时区字符串按本地时区（UTC+8）解析，
    导致显示时间与实际时间相差 8 小时。

    Args:
        dt: 任意 datetime 对象（naive 或 aware）

    Returns:
        ISO 8601 字符串（带 Z 后缀），如 "2026-06-03T12:43:00.123456Z"
        如果 dt 为 None 则返回 None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 数据库中存的是 UTC naive datetime，序列化为 UTC
        dt = dt.replace(tzinfo=timezone.utc)
    # 统一使用 Z 后缀（RFC 3339 / ISO 8601 推荐的 UTC 表示法）
    return dt.isoformat().replace("+00:00", "Z")


def calculate_age(birth_date: date) -> Optional[int]:
    """根据出生日期计算年龄

    Args:
        birth_date: 出生日期

    Returns:
        年龄（整数），如果 birth_date 为 None 则返回 None
    """
    if not birth_date:
        return None
    today = date.today()
    age = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age
