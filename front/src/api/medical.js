import request from './request'

export const medicalApi = {
  // 获取医疗报告列表（检验报告）
  getMedicalReportList(patientId, params = {}) {
    return request.post('/medical/checks/query', {
      patient_id: patientId,
      ...params
    })
  },

  // 获取单个医疗报告
  getMedicalReport(reportId) {
    return request.get(`/medical/checks/${reportId}`)
  },

  // 获取报告指标（从检验报告详情中获取）
  getIndicators(reportId) {
    return request.get(`/medical/checks/${reportId}`)
  },

  // 获取指标历史（按index_id查询）
  getIndicatorHistory(indexId, params = {}) {
    return request.get(`/medical/indices/history`, {
      params: {
        index_id: indexId,
        ...params
      }
    })
  },

  // 别名：与getIndicatorHistory相同
  getIndexHistoryById: function(indexId, params = {}) {
    return this.getIndicatorHistory(indexId, params)
  },

  // 获取异常指标（支持日期过滤）
  getAbnormalIndicators(patientId, params = {}) {
    return request.get(`/medical/patients/${patientId}/indicators/abnormal`, {
      params: { limit: params.limit || 100, start_date: params.start_date, end_date: params.end_date }
    })
  },

  // 更新指标备注（通过更新检验备注接口）
  updateIndicatorNote(medicalId, note) {
    return request.put(`/medical/checks/${medicalId}/comment`, { comment: note })
  },

  // ===== 新增接口：支持原版UI功能 =====

  // 获取最新检验数据（按分类）
  getLatestCheckData(patientId, category, params = {}) {
    return request.get(`/medical/checks/latest`, {
      params: {
        patient_id: patientId,
        category: category,
        ...params
      }
    })
  },

  // 按分类获取最新指标数据（从image_report获取）
  getLatestIndicatorsByCategory(patientId, category, params = {}) {
    return request.get(`/medical/indicators/latest`, {
      params: {
        patient_id: patientId,
        category: category,
        ...params
      }
    })
  },

  // 获取指标列表（按分类）
  getIndexes(patientId, category) {
    return request.get(`/medical/indices`, {
      params: {
        patient_id: patientId,
        category: category
      }
    })
  },

  // 获取指标分类列表
  getIndexCategories() {
    return request.get('/medical/indices/categories')
  },

  // 按分类获取指标列表
  getIndicesByCategory(category) {
    return request.get('/medical/indices/by-category', {
      params: { category }
    })
  },

  // 收藏指标
  addFavoriteIndex(indexId) {
    return request.post(`/medical/indices/${indexId}/favorite`)
  },

  // 取消收藏
  removeFavoriteIndex(indexId) {
    return request.delete(`/medical/indices/${indexId}/favorite`)
  },

  // 获取最新检查报告（CT等）
  getLatestExamReport(patientId, examType, params = {}) {
    return request.get(`/medical/exams/latest`, {
      params: {
        patient_id: patientId,
        exam_type: examType,
        ...params
      }
    })
  },

  // ===== 检查报告相关 =====

  // 获取检查报告列表
  getExamReports(patientId, params = {}) {
    return request.post(`/medical/exams/query`, {
      patient_id: patientId,
      ...params
    })
  },

  // 获取检查报告详情
  getExamReport(examId) {
    return request.get(`/medical/exams/${examId}`)
  },

  // 更新检查报告
  updateExamReport(examId, data) {
    return request.put(`/medical/exams/${examId}`, data)
  },

  // ===== 病理报告相关 =====

  // 获取病理报告列表
  getPathologyReports(patientId, params = {}) {
    return request.post(`/medical/pathology/query`, {
      patient_id: patientId,
      ...params
    })
  },

  // 获取病理报告详情
  getPathologyReport(reportId) {
    return request.get(`/medical/pathology/${reportId}`)
  },

  // 更新病理报告
  updatePathologyReport(reportId, data) {
    return request.put(`/medical/pathology/${reportId}`, data)
  },

  // 获取病理报告图片
  getPathologyImage(reportId) {
    return request.get(`/medical/pathology/${reportId}/image`)
  },

  // ===== 病情记录相关 =====

  // 获取病情记录列表
  getMedicalRecords(patientId, params = {}) {
    return request.post(`/medical/records/query`, {
      patient_id: patientId,
      ...params
    })
  },

  // 创建病情记录
  createMedicalRecord(data) {
    return request.post(`/medical/records`, data)
  },

  // 获取病情记录详情
  getMedicalRecord(recordId) {
    return request.get(`/medical/records/${recordId}`)
  },

  // 更新病情记录
  updateMedicalRecord(recordId, data) {
    return request.put(`/medical/records/${recordId}`, data)
  },

  // 删除病情记录
  deleteMedicalRecord(recordId) {
    return request.delete(`/medical/records/${recordId}`)
  },

  // ===== 指标明细操作相关 =====

  // 添加检验明细（支持用户手动添加指标数据）
  addMedicalCheckDetail(data) {
    return request.post('/medical/checks/detail', data)
  },

  // 更新检验备注
  updateMedicalCheckComment(medicalId, data) {
    return request.put(`/medical/checks/${medicalId}/comment`, data)
  },

  // 删除检验明细
  deleteMedicalCheckDetail(detailId) {
    return request.delete(`/medical/checks/details/${detailId}`)
  },

  // 删除检验报告
  deleteMedicalCheck(medicalId) {
    return request.delete(`/medical/checks/${medicalId}`)
  },

  // 删除检查报告
  deleteExamReport(examId) {
    return request.delete(`/medical/exams/${examId}`)
  },

  // 删除病理报告
  deletePathologyReport(reportId) {
    return request.delete(`/medical/pathology/${reportId}`)
  },

  // ===== AI 解读相关 =====

  // 生成 AI 解读
  interpretMedicalCheck(medicalId) {
    return request.post(`/medical/checks/${medicalId}/interpret`)
  },

  // 获取已有 AI 解读
  getInterpretation(medicalId) {
    return request.get(`/medical/checks/${medicalId}/interpretation`)
  },

  // ===== 检查报告 AI 解读 =====

  // 生成检查报告 AI 解读
  interpretExam(examId) {
    return request.post(`/medical/exams/${examId}/interpret`)
  },

  // 获取检查报告已有 AI 解读
  getExamInterpretation(examId) {
    return request.get(`/medical/exams/${examId}/interpretation`)
  },

  // ===== 病理报告 AI 解读 =====

  // 生成病理报告 AI 解读
  interpretPathology(reportId) {
    return request.post(`/medical/pathology/${reportId}/interpret`)
  },

  // 获取病理报告已有 AI 解读
  getPathologyInterpretation(reportId) {
    return request.get(`/medical/pathology/${reportId}/interpretation`)
  },

  // ===== 指标对比 =====

  // 批量对比多个指标（日期对齐）
  compareIndices(data) {
    return request.post('/medical/indices/compare', data)
  },

  // ===== 指标组合 =====

  // 创建指标组合
  createIndexGroup(data) {
    return request.post('/medical/indices/groups', data)
  },

  // 获取指标组合列表（按患者）
  getIndexGroups(patientId) {
    return request.get('/medical/indices/groups', {
      params: { patient_id: patientId }
    })
  },

  // 删除指标组合
  deleteIndexGroup(groupId) {
    return request.delete(`/medical/indices/groups/${groupId}`)
  },
}
