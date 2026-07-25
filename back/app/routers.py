from fastapi import APIRouter

from app.api import (
    auth, user, patient, medical, medical_index, medical_record, indicator_group,
    medical_check, medical_exam, pathology, indicator_query, indicator_legacy,
    timeline, upload, prompt,
    image_report, knowledge, knowledge_preview, conversation, medication, dashboard,
    export, follow_up, files, medication_log,
    indicator_history, share, search, admin, admin_agentteams,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(user.router, prefix="/accounts", tags=["用户"])
api_router.include_router(patient.router, prefix="/patients", tags=["患者"])
api_router.include_router(medical.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(medical_index.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(medical_record.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(indicator_group.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(medical_check.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(medical_exam.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(pathology.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(indicator_query.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(indicator_legacy.router, prefix="/medical", tags=["医疗数据"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["时间线"])
api_router.include_router(upload.router, tags=["图片上传"])
api_router.include_router(prompt.router, prefix="/prompt", tags=["提示词配置"])
api_router.include_router(image_report.router, tags=["上传报告"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(knowledge_preview.router, prefix="/knowledge", tags=["知识库预览"])
api_router.include_router(conversation.router, prefix="/consultation", tags=["会诊对话"])
api_router.include_router(medication.router, prefix="/medications", tags=["用药记录"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(export.router, tags=["数据导出"])
api_router.include_router(follow_up.router, tags=["随访提醒"])
api_router.include_router(files.router, tags=["文件服务"])
api_router.include_router(medication_log.router, prefix="/medication-logs", tags=["服药记录"])
api_router.include_router(indicator_history.router, prefix="/indicator-history", tags=["指标历史"])
api_router.include_router(share.router, tags=["报告分享"])
api_router.include_router(search.router, tags=["全局搜索"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理后台"])
api_router.include_router(admin_agentteams.router, prefix="/admin", tags=["管理后台"])
