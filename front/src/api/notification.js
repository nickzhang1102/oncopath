import request from './request'

export default {
  /** 获取通知列表 */
  getNotifications(params) {
    return request.get('/accounts/notifications', { params })
  },

  /** 创建通知 */
  createNotification(data) {
    return request.post('/accounts/notifications', data)
  },

  /** 标记单条通知已读 */
  markRead(notificationId) {
    return request.put(`/accounts/notifications/${notificationId}/read`)
  },

  /** 标记所有通知已读 */
  markAllRead() {
    return request.put('/accounts/notifications/read-all')
  },

  /** 删除通知 */
  deleteNotification(notificationId) {
    return request.delete(`/accounts/notifications/${notificationId}`)
  },
}