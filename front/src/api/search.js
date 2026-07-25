import request from './request'

export default {
  /** 全局搜索 */
  search(params) {
    return request.get('/search', { params })
  }
}