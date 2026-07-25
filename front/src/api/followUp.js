import request from './request'

export default {
  /** 获取随访提醒列表 */
  getReminders(params) {
    return request.get('/reminders', { params })
  },

  /** 获取待处理提醒 */
  getPendingReminders(patientId) {
    return request.get('/reminders/pending', { params: { patient_id: patientId } })
  },

  /** 创建随访提醒 */
  createReminder(data) {
    return request.post('/reminders', data)
  },

  /** 更新随访提醒 */
  updateReminder(id, data) {
    return request.put(`/reminders/${id}`, data)
  },

  /** 删除随访提醒 */
  deleteReminder(id) {
    return request.delete(`/reminders/${id}`)
  },

  /** 标记提醒为已确认 */
  confirmReminder(id) {
    return request.put(`/reminders/${id}/confirm`)
  },
}