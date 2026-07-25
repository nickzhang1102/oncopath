import request from './request'

export const patientApi = {
  // 获取患者列表
  getPatientList(params) {
    return request.get('/patients', { params })
  },

  // 获取单个患者
  getPatient(patientId) {
    return request.get(`/patients/${patientId}`)
  },

  // 获取患者编辑信息（敏感字段明文返回）
  getPatientForEdit(patientId) {
    return request.get(`/patients/${patientId}/edit`)
  },

  // 创建患者
  createPatient(data) {
    return request.post('/patients', data)
  },

  // 更新患者
  updatePatient(patientId, data) {
    return request.put(`/patients/${patientId}`, data)
  },

  // 删除患者
  deletePatient(patientId) {
    return request.delete(`/patients/${patientId}`)
  },

  // 获取患者统计
  getPatientStats(patientId) {
    return request.get(`/patients/${patientId}/stats`)
  },

  // 切换当前患者 - 后端路径是 /{patient_id}/switch
  switchPatient(patientId) {
    return request.post(`/patients/${patientId}/switch`)
  },

  // 根据身份证号查找患者 - 暂不支持，返回空结果
  findByIdCard(idCard) {
    // 该接口后端暂未实现，返回空结果
    return Promise.resolve({ patients: [] })
  },

  // 获取主患者信息
  getPrimaryPatient() {
    return request.get('/patients/primary')
  },

  // 设置主患者
  setPrimaryPatient(patientId) {
    return request.put(`/patients/${patientId}/primary`)
  },
}