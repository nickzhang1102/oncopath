"""识别公开迁移启用前最后一个私有部署版本。

版本 ID：drop_billing_appointment
父版本：public_schema_baseline
创建日期：2026-08-08

公开基线是删除本地计费表和预约表之后的静态结构快照。现有私有部署在完成
该变更后，已经记录了 ``drop_billing_appointment``；全新公开部署则通过基线
到达相同结构。这个无操作标记让两条路径汇入同一条受版本控制且自包含的迁移图。
"""
from typing import Sequence, Union


revision: str = "drop_billing_appointment"
down_revision: Union[str, Sequence[str], None] = "public_schema_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """公开基线已经包含删除相关业务表后的数据库结构。"""
    pass


def downgrade() -> None:
    """兼容标记没有需要反向执行的结构操作。"""
    pass
