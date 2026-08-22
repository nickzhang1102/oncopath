import request from './request'

export const adminApi = {
  // 仪表盘统计
  getAdminStats() {
    return request.get('/admin/stats')
  },

  // 健康检查（验证 admin 鉴权）
  healthCheck() {
    return request.get('/admin/health')
  },

  // 用户管理
  getAdminUsers(params) {
    return request.get('/admin/users', { params })
  },
  getAdminUserDetail(id) {
    return request.get(`/admin/users/${id}`)
  },
  updateUserStatus(id, data) {
    return request.put(`/admin/users/${id}/status`, data)
  },
  resetUserPassword(id, data) {
    return request.post(`/admin/users/${id}/reset-password`, data)
  },

  // 指标库管理
  getAdminIndices(params) {
    return request.get('/admin/indices', { params })
  },
  createIndex(data) {
    return request.post('/admin/indices', data)
  },
  updateIndex(id, data) {
    return request.put(`/admin/indices/${id}`, data)
  },
  updateIndexStatus(id, data) {
    return request.put(`/admin/indices/${id}/status`, data)
  },
  deleteIndex(id) {
    return request.delete(`/admin/indices/${id}`)
  },
  updateIndicesSort(data) {
    return request.put('/admin/indices/sort', data)
  },
  importIndices(data) {
    return request.post('/admin/indices/import', data)
  },

  // 指标分类管理
  getIndexCategories() {
    return request.get('/admin/indices/categories')
  },
  createIndexCategory(data) {
    return request.post('/admin/indices/categories', data)
  },
  updateIndexCategory(key, data) {
    return request.put(`/admin/indices/categories/${key}`, data)
  },
  deleteIndexCategory(key) {
    return request.delete(`/admin/indices/categories/${key}`)
  },

  // AgentTeams 集成配置
  getAgentTeamsConfig() {
    return request.get('/admin/agentteams-config')
  },
  updateAgentTeamsConfig(data) {
    return request.put('/admin/agentteams-config', data)
  },

  // AgentTeams 启动意图人工复核
  getAgentTeamsLaunchIntents(params = { status: 'manual_review' }) {
    return request.get('/admin/agentteams-launch-intents', { params })
  },
  getAgentTeamsLaunchIntent(id) {
    return request.get(`/admin/agentteams-launch-intents/${id}`)
  },
  reconcileAgentTeamsLaunchIntent(id) {
    return request.post(`/admin/agentteams-launch-intents/${id}/reconcile`)
  },
  resolveAgentTeamsLaunchIntent(id, data) {
    return request.post(`/admin/agentteams-launch-intents/${id}/resolve`, data)
  }
}
