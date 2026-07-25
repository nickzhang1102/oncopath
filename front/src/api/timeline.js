import request from './request'

export const timelineApi = {
  // 查询时间线事件
  queryTimeline(data) {
    return request.post('/timeline/events/query', data)
  },

  // 获取时间线（兼容旧接口）
  getTimeline(patientId, params = {}) {
    return request.post('/timeline/events/query', {
      patient_id: patientId,
      ...params
    })
  },

  // 查询统一时间线（聚合时间线事件 + 检验报告 + 检查报告 + 病理报告）
  queryUnifiedTimeline(data) {
    return request.post('/timeline/unified/query', data)
  },

  // 获取统一时间线统计
  getUnifiedStats(patientId) {
    return request.get(`/timeline/unified/stats/${patientId}`)
  },

  // 添加时间线事件
  addTimelineItem(data) {
    return request.post('/timeline/events', data)
  },

  // 更新时间线事件
  updateTimelineItem(eventId, data) {
    return request.put(`/timeline/events/${eventId}`, data)
  },

  // 删除时间线事件
  deleteTimelineItem(eventId) {
    return request.delete(`/timeline/events/${eventId}`)
  },

  // 获取时间线统计
  getStats(patientId) {
    return request.get(`/timeline/stats/${patientId}`)
  }
}