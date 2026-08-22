/**
 * 提示词配置 API
 * 用于AI诊断提示词的获取和保存
 */

import request from './request'

/**
 * 获取提示词配置
 * @param {number} patientId - 患者ID
 * @returns {Promise} 配置数据
 */
export function getPromptConfig(patientId) {
  return request({
    url: `/prompt/config/${patientId}`,
    method: 'get'
  })
}

/**
 * 保存提示词配置
 * @param {Object} config - 配置数据
 * @param {number} config.patient_id - 患者ID
 * @param {number} config.time_range_days - 数据时间范围（天）
 * @param {Array} config.user_content_config - 用户内容配置
 * @returns {Promise} 保存结果
 */
export function savePromptConfig(config) {
  return request({
    url: '/prompt/config',
    method: 'post',
    data: config
  })
}

/**
 * 获取默认提示词配置
 * @returns {Promise} 默认配置数据
 */
export function getDefaultPromptConfig() {
  return request({
    url: '/prompt/default',
    method: 'get'
  })
}

/**
 * 预览提示词
 * @param {Object} config - 配置数据
 * @param {number} config.patient_id - 患者ID
 * @param {number} config.time_range_days - 数据时间范围（天）
 * @param {Array} config.user_content_config - 用户内容配置
 * @returns {Promise} 预览结果
 */
export function previewPromptConfig(config) {
  return request({
    url: '/prompt/preview',
    method: 'post',
    data: config
  })
}

// ========== 记录概要摘要 API ==========

/**
 * 获取患者概要列表
 * @param {number} patientId - 患者ID
 * @param {Object} params - 查询参数
 * @param {string} [params.summary_type] - 概要类型筛选
 * @param {string} [params.status] - 状态筛选
 * @returns {Promise} 概要列表
 */
export function listSummaries(patientId, params = {}) {
  return request({
    url: `/prompt/summaries/${patientId}`,
    method: 'get',
    params
  })
}

/**
 * 生成概要（规则模板 / LLM）
 * @param {Object} data - 生成参数
 * @param {number} data.patient_id - 患者ID
 * @param {string} data.summary_type - 概要类型 (treatment/medication_record/status)
 * @param {string} data.period_start - 时段起始 (YYYY-MM-DD)
 * @param {string} data.period_end - 时段结束 (YYYY-MM-DD)
 * @param {string} [data.source=rule_template] - 来源 (rule_template/llm_generated)
 * @returns {Promise} 生成的概要
 */
export function generateSummary(data) {
  return request({
    url: '/prompt/summaries/generate',
    method: 'post',
    data
  })
}

/**
 * 编辑/确认概要
 * @param {number} summaryId - 概要ID
 * @param {Object} data - 更新数据
 * @param {string} [data.summary_text] - 概要文本
 * @param {string} [data.status] - 状态 (draft/confirmed)
 * @returns {Promise} 更新后的概要
 */
export function updateSummary(summaryId, data) {
  return request({
    url: `/prompt/summaries/${summaryId}`,
    method: 'put',
    data
  })
}

/**
 * 删除概要
 * @param {number} summaryId - 概要ID
 * @returns {Promise} 删除结果
 */
export function deleteSummary(summaryId) {
  return request({
    url: `/prompt/summaries/${summaryId}`,
    method: 'delete'
  })
}