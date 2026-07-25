from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, Numeric, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class MedicalIndex(Base):
    """医疗指标表 - 统一标准库"""
    __tablename__ = "medical_index"

    # ===== 原有字段 =====
    index_id = Column(Integer, primary_key=True, index=True)
    index_name = Column(String(100), nullable=False, comment="指标名称")
    index_unit = Column(String(20), nullable=True, comment="单位")
    reference_min = Column(Numeric(10, 2), nullable=True, comment="参考值最小值")
    reference_max = Column(Numeric(10, 2), nullable=True, comment="参考值最大值")
    index_type = Column(String(50), nullable=True, comment="指标类型")
    is_chart = Column(Boolean, default=True, comment="是否图表展示")
    description = Column(Text, nullable=True, comment="描述")
    sort = Column(Integer, default=0, comment="排序")
    is_edit = Column(Boolean, default=True, comment="是否可编辑")

    # ===== 新增字段（从StandardIndicator合并） =====
    index_code = Column(String(50), unique=True, nullable=True, comment="指标编码: WBC, RBC, GLU")
    index_name_en = Column(String(100), nullable=True, comment="英文名称: White Blood Cell")
    category = Column(String(50), nullable=True, comment="指标分类，关联 image_category.category_key")
    sub_category = Column(String(50), nullable=True, comment="子分类: 红细胞系、白细胞系")
    unit_type = Column(String(20), nullable=True, comment="单位类型: concentration, ratio")
    reference_range = Column(JSONB, default=dict, comment='{"adult": {"min": 4, "max": 10}}')
    match_count = Column(Integer, default=0, comment="成功匹配次数")
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_system = Column(Boolean, default=False, comment="系统内置指标不可删除")

    # 新增索引
    __table_args__ = (
        Index('idx_medical_index_category', 'category'),
        Index('idx_medical_index_code', 'index_code'),
        Index('idx_medical_index_active', 'is_active'),
    )

    # 关系
    check_details = relationship("MedicalCheckDetail", back_populates="standard_index")


class MedicalCheck(Base):
    """医疗检查表"""
    __tablename__ = "medical_check"

    medical_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False)
    medical_date = Column(Date, nullable=False, comment="检查日期")
    hospital = Column(String(100), nullable=True, comment="医院")
    comment = Column(Text, nullable=True, comment="备注")
    status = Column(String(20), default="active", nullable=False, comment="状态")
    category = Column(String(50), nullable=True, comment="报告分类，关联 image_category.category_key")
    created_at = Column(DateTime, default=get_utc_now)

    # AI 解读
    interpretation = Column(Text, nullable=True, comment="AI解读内容(Markdown)")
    interpretation_at = Column(DateTime, nullable=True, comment="AI解读时间")

    # 索引
    __table_args__ = (
        Index('idx_medical_check_patient_date', 'patient_id', 'medical_date'),
    )

    # 关系
    patient = relationship("Patient", back_populates="medical_checks")
    details = relationship("MedicalCheckDetail", back_populates="medical_check", cascade="all, delete-orphan")


class MedicalCheckDetail(Base):
    """医疗检查明细表"""
    __tablename__ = "medical_check_detail"

    medical_detail_id = Column(Integer, primary_key=True, index=True)
    medical_id = Column(Integer, ForeignKey("medical_check.medical_id"), nullable=False)

    # 关联标准指标库
    index_id = Column(Integer, ForeignKey("medical_index.index_id"), nullable=True, comment="关联标准指标ID")

    # 保留原有字段（用于显示原始数据）
    index_name = Column(String(100), nullable=False, comment="指标名称")
    index_value = Column(String(50), nullable=True, comment="指标值")
    index_unit = Column(String(20), nullable=True, comment="单位")
    reference_value = Column(String(50), nullable=True, comment="参考值")
    index_status = Column(String(20), nullable=True, comment="状态: normal/abnormal")

    # 索引
    __table_args__ = (
        Index('idx_medical_check_detail_medical_id', 'medical_id'),
        Index('idx_medical_check_detail_index_id', 'index_id'),
        Index('ix_medical_check_detail_status', 'index_status'),
    )

    # 关系
    medical_check = relationship("MedicalCheck", back_populates="details")
    standard_index = relationship("MedicalIndex", back_populates="check_details")


class MedicalExam(Base):
    """检查报告表"""
    __tablename__ = "medical_exam"

    exam_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False)
    medical_date = Column(Date, nullable=True, comment="检查日期")
    hospital = Column(String(100), nullable=True, comment="医院")
    title = Column(String(200), nullable=True, comment="报告标题")
    exam_type = Column(String(50), nullable=True, comment="检查类型")
    exam_info = Column(Text, nullable=True, comment="检查所见")
    exam_diag = Column(Text, nullable=True, comment="诊断意见")
    comment = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=get_utc_now)

    # AI 解读
    interpretation = Column(Text, nullable=True, comment="AI解读内容(Markdown)")
    interpretation_at = Column(DateTime, nullable=True, comment="AI解读时间")

    # 索引
    __table_args__ = (
        Index('idx_medical_exam_patient_date', 'patient_id', 'medical_date'),
    )

    # 关系
    patient = relationship("Patient", back_populates="medical_exams")


class PathologyReport(Base):
    """病理报告表"""
    __tablename__ = "pathology_report"

    report_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False, index=True)
    report_title = Column(String(200), nullable=True, comment="报告标题")
    report_date = Column(Date, nullable=True, comment="报告日期")
    hospital = Column(String(100), nullable=True, comment="医院")
    comment = Column(Text, nullable=True, comment="备注")
    image_path = Column(String(500), nullable=True, comment="图片文件存储路径")
    image_type = Column(String(20), nullable=True, comment="文件类型: jpeg, png, pdf")
    created_at = Column(DateTime, default=get_utc_now)

    # 病理诊断相关字段（会诊提示词必需）
    diagnosis = Column(Text, nullable=True, comment="病理诊断")
    cancer_type = Column(String(100), nullable=True, comment="癌种/肿瘤类型")
    stage = Column(String(50), nullable=True, comment="临床分期(如 IIIA期)")
    histology_type = Column(String(100), nullable=True, comment="组织学类型(如 腺癌/鳞癌)")
    immunohistochemistry = Column(Text, nullable=True, comment="免疫组化结果")
    gene_testing = Column(Text, nullable=True, comment="基因检测信息")

    # AI 解读
    interpretation = Column(Text, nullable=True, comment="AI解读内容(Markdown)")
    interpretation_at = Column(DateTime, nullable=True, comment="AI解读时间")

    # 关系
    patient = relationship("Patient", back_populates="pathology_reports")
    ihc_markers = relationship("PathologyIHC", back_populates="pathology_report", cascade="all, delete-orphan")


class PathologyIHC(Base):
    """免疫组化标记物结构化存储"""
    __tablename__ = "pathology_ihc"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("pathology_report.report_id", ondelete="CASCADE"), nullable=False)
    marker_name = Column(String(100), nullable=False, comment="标记物名称: ER, PR, HER2, Ki-67, TTF-1 等")
    result = Column(String(50), nullable=True, comment="结果: 阳性/阴性/弱阳性/强阳性 等")
    intensity = Column(String(20), nullable=True, comment="染色强度: +/++/+++")
    percentage = Column(String(20), nullable=True, comment="阳性细胞百分比: 30%, >90%")

    __table_args__ = (
        Index('ix_pathology_ihc_report_id', 'report_id'),
        Index('ix_pathology_ihc_marker_name', 'marker_name'),
    )

    pathology_report = relationship("PathologyReport", back_populates="ihc_markers")


class UserFavoriteIndex(Base):
    """用户收藏的指标"""
    __tablename__ = "user_favorite_index"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False)
    index_id = Column(Integer, ForeignKey("medical_index.index_id"), nullable=False)
    sort = Column(Integer, default=0, comment="自定义排序")
    created_at = Column(DateTime, default=get_utc_now)

    # 唯一约束
    __table_args__ = (
        Index('idx_user_favorite_unique', 'account_id', 'index_id', unique=True),
    )


class UserIndexGroup(Base):
    """用户保存的指标组合（按患者隔离）"""
    __tablename__ = "user_index_group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False)
    group_name = Column(String(50), nullable=False, comment="组合名称")
    index_ids = Column(JSONB, nullable=False, comment="有序指标ID数组，如 [3, 7, 12]")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 唯一约束：同一用户同一患者下组合名不重复
    __table_args__ = (
        Index('idx_user_index_group_unique', 'account_id', 'patient_id', 'group_name', unique=True),
    )


class MedicalRecord(Base):
    """病情记录表"""
    __tablename__ = "medical_record"

    record_id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False, index=True)
    record_name = Column(String(100), nullable=True, comment="记录名称")
    record_date = Column(Date, nullable=True, comment="记录日期")
    record_info = Column(Text, nullable=True, comment="记录内容")
    record_type = Column(String(50), nullable=True, comment="记录类型")
    patient_status = Column(String(50), nullable=True, comment="患者状态")
    comment = Column(Text, nullable=True, comment="备注")
    record_drug = Column(Text, nullable=True, comment="用药记录")
    hospital = Column(String(100), nullable=True, comment="医院")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    patient = relationship("Patient", back_populates="medical_records")