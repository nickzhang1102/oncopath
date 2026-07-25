import request from './request'

export const medicationApi = {
  // 获取用药记录列表
  listMedications(params) {
    return request.get('/medications', { params })
  },

  // 创建用药记录
  createMedication(data) {
    return request.post('/medications', data)
  },

  // 获取单条用药记录
  getMedication(id) {
    return request.get(`/medications/${id}`)
  },

  // 更新用药记录
  updateMedication(id, data) {
    return request.put(`/medications/${id}`, data)
  },

  // 删除用药记录
  deleteMedication(id) {
    return request.delete(`/medications/${id}`)
  },

  // 停药操作
  discontinueMedication(id, params) {
    return request.put(`/medications/${id}/discontinue`, null, { params })
  }
}

export const medicationLogApi = {
  // 创建/更新服药打卡（支持 time_slot 多次打卡）
  createLog(data) {
    return request.post('/medication-logs', data)
  },

  // 获取今日服药任务（按 time_slot 展开）
  getTodayTasks(patientId) {
    return request.get(`/medication-logs/today/${patientId}`)
  },

  // 获取依从性统计（按 slot 粒度）
  getAdherenceStats(patientId, days = 30) {
    return request.get(`/medication-logs/adherence/${patientId}`, { params: { days } })
  }
}
