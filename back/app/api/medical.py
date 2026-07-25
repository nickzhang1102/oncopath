"""医疗数据 API 路由聚合入口

原 medical.py (1935行/65端点) 已拆分为 8 个独立模块：
- medical_index.py: 标准指标库 CRUD + 收藏管理
- medical_check.py: 检验报告 CRUD + AI解读 + 明细操作
- medical_exam.py: 检查报告 CRUD + AI解读
- pathology.py: 病理报告 CRUD + 图片管理 + AI解读
- medical_record.py: 病情记录 CRUD
- indicator_query.py: 指标历史/异常/对比查询
- indicator_group.py: 用户指标组合 CRUD
- indicator_legacy.py: 原版UI兼容接口

本文件仅保留空路由器，供 routers.py 统一注册。
实际端点已全部迁移至上述子模块。
"""
from fastapi import APIRouter

router = APIRouter()