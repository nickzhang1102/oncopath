import request from './request'

export default {
  /** 查询某指标的历史趋势 */
  getHistory(params) {
    return request.get('/indicator-history', { params })
  },
}