/**
 * 上传报告 API
 */
import request from './request'
import { useSSEStream } from '@/composables/useSSEStream'
import { useUserStore } from '@/stores/user'

/**
 * 获取图片分类列表
 */
export function getImageCategories() {
  return request({
    url: '/image_reports/categories',
    method: 'get'
  })
}

/**
 * 检查报告是否重复
 * @param {Object} params - 查询参数
 * @param {number} params.patient_id - 患者ID
 * @param {string} params.category - 分类key
 * @param {string} params.content_hash - 文件内容SHA-256哈希
 */
export function checkDuplicate(params) {
  return request({
    url: '/image_reports/check-duplicate',
    method: 'post',
    params
  })
}

/**
 * 上传报告
 * @param {Object} data - 报告数据
 * @param {number} data.patient_id - 患者ID
 * @param {string} data.title - 报告标题
 * @param {string} data.category - 分类key
 * @param {string} data.image_data - Base64编码的图片/PDF数据
 * @param {string} data.image_type - 文件类型 (jpeg, png, pdf)
 * @param {string} [data.hospital] - 医院代码
 * @param {string} [data.department] - 科室代码
 * @param {string} [data.capture_date] - 检查日期 (YYYY-MM-DD)
 * @param {string[]} [data.tags] - 标签列表
 * @param {string} [data.description] - 描述
 * @param {string} [data.notes] - 备注
 * @param {boolean} [data.is_private=true] - 是否私有
 * @param {boolean} [data.is_important=false] - 是否重要
 */
export function uploadImageReport(data) {
  return request({
    url: '/image_reports',
    method: 'post',
    data
  })
}

/**
 * 上传报告（SSE流式响应）
 * 使用 useSSEStream composable 统一处理重试、心跳、超时、取消
 *
 * @param {Object} data - 报告数据
 * @param {Function} onProgress - 进度回调函数 (status, message, data)
 * @param {Function} onError - 错误回调函数 (message, event?)
 * @param {Function} onComplete - 完成回调函数
 * @returns {Function} 取消函数
 */
export function uploadImageReportStream(data, { onProgress, onError, onComplete }) {
  const baseURL = import.meta.env.VITE_API_BASE_URL || ''
  const token = useUserStore().token

  // 报告上传 SSE 事件用 'status' 字段标识类型（非 'type'）
  const { startStream, abort } = useSSEStream(
    (event) => {
      if (event.status === 'error') {
        onError?.(event.message, event)
      } else if (event.status === 'completed') {
        onComplete?.(event.data, event.message)
      } else {
        onProgress?.(event.status, event.message)
      }
    },
    {
      eventTypeField: 'status',
      maxRetries: 3,
      totalTimeout: 5 * 60 * 1000  // OCR 处理可能较长，5 分钟总超时
    }
  )

  startStream(`${baseURL}/api/v1/image_reports/upload-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  }).catch(error => {
    if (error.name !== 'AbortError') {
      onError?.(error.message || '上传失败')
    }
  })

  return abort
}

/**
 * 获取报告列表
 * @param {Object} params - 查询参数
 * @param {number} [params.patient_id] - 患者ID
 * @param {string} [params.category] - 分类
 * @param {string} [params.hospital] - 医院
 * @param {string} [params.start_date] - 开始日期
 * @param {string} [params.end_date] - 结束日期
 * @param {string} [params.search] - 搜索关键词
 * @param {number} [params.page=1] - 页码
 * @param {number} [params.per_page=20] - 每页数量
 */
export function getImageReports(params) {
  return request({
    url: '/image_reports',
    method: 'get',
    params
  })
}

/**
 * 获取报告详情
 * @param {number} reportId - 报告ID
 */
export function getImageReportDetail(reportId) {
  return request({
    url: `/image_reports/${reportId}`,
    method: 'get'
  })
}

/**
 * 更新报告
 * @param {number} reportId - 报告ID
 * @param {Object} data - 更新数据
 */
export function updateImageReport(reportId, data) {
  return request({
    url: `/image_reports/${reportId}`,
    method: 'put',
    data
  })
}

/**
 * 删除报告
 * @param {number} reportId - 报告ID
 */
export function deleteImageReport(reportId) {
  return request({
    url: `/image_reports/${reportId}`,
    method: 'delete'
  })
}

/**
 * 获取图片数据
 * @param {number} reportId - 报告ID
 */
export function getImageData(reportId) {
  return request({
    url: `/image_reports/${reportId}/image`,
    method: 'get'
  })
}

/**
 * 获取报告统计
 * @param {Object} [params] - 查询参数
 * @param {number} [params.patient_id] - 患者ID
 */
export function getImageReportStats(params = {}) {
  return request({
    url: '/image_reports/stats',
    method: 'get',
    params
  })
}

/**
 * 提交OCR审查修正
 * @param {number} reportId - 报告ID
 * @param {Object} data - 审查数据
 * @param {string} data.report_type - 报告类型: lab/exam/pathology
 * @param {Array} data.corrections - 修正列表
 * @param {string} data.corrections[].field_name - 字段名
 * @param {string} [data.corrections[].original_value] - 原始值
 * @param {string} [data.corrections[].corrected_value] - 修正值
 */
export function submitOCRReview(reportId, data) {
  return request({
    url: `/image_reports/${reportId}/review`,
    method: 'post',
    data: {
      report_id: reportId,
      ...data
    }
  })
}

/**
 * 获取OCR审查记录
 * @param {number} reportId - 报告ID
 */
export function getOCRReviews(reportId) {
  return request({
    url: `/image_reports/${reportId}/reviews`,
    method: 'get'
  })
}