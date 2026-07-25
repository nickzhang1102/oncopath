import request from './request'

export const shareApi = {
  // 生成分享令牌
  createShareToken(data) {
    return request.post('/share', data)
  },

  // 通过令牌获取分享的报告（无需认证）
  getSharedReport(token) {
    return request.get(`/share/report/${token}`)
  },
}
