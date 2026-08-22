import request from './request'

/**
 * LLM 配置 API（仅管理员或首个账号可用）
 * 三组配置：consultation(会诊) / interpretation(解读) / ocr
 */
export const llmConfigApi = {
  // 获取所有 LLM 配置
  getLLMConfigs() {
    return request.get('/llm-configs')
  },

  // 整组更新配置（单事务，保存后自动生效）
  updateLLMConfigGroup(group, updates) {
    return request.put(`/llm-configs/group/${group}`, { updates })
  },

  // 测试指定配置组的 LLM 连通性
  testLLMConfig(group) {
    return request.post('/llm-configs/test', { group })
  },

  // 获取配置状态（LLM 是否已配置，首启弹窗判定用）
  getLLMConfigStatus() {
    return request.get('/llm-configs/status')
  },
}
