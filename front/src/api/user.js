import request from './request'

export const userApi = {
  // 登录
  login(data) {
    return request.post('/auth/login', data)
  },

  // 注册
  register(data) {
    return request.post('/auth/register', data)
  },

  // 获取用户信息
  getProfile() {
    return request.get('/accounts/me')
  },

  updateUserProfile(data) {
    return request.put('/accounts/me', data)
  },

  // 修改密码（已登录）
  changePassword(data) {
    return request.put('/accounts/password', data)
  },

  // 忘记密码 - 获取重置令牌
  forgotPassword(data) {
    return request.post('/auth/forgot-password', data)
  },

  // 重置密码
  resetPassword(data) {
    return request.post('/auth/reset-password', data)
  },

  // 隐私设置
  getPrivacySettings() {
    return request.get('/accounts/privacy')
  },

  updatePrivacySettings(data) {
    return request.put('/accounts/privacy', data)
  },

  // 通知
  getNotifications(params) {
    return request.get('/accounts/notifications', { params })
  },

  markNotificationRead(id) {
    return request.put(`/accounts/notifications/${id}/read`)
  },

  markAllNotificationsRead() {
    return request.put('/accounts/notifications/read-all')
  },

  deleteNotification(id) {
    return request.delete(`/accounts/notifications/${id}`)
  },

  // 登出（撤销后端会话）
  logout() {
    return request.post('/auth/logout').catch(() => {
      // 即使后端登出失败，也继续本地清理
    })
  }
}