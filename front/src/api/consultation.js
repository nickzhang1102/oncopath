// front/src/api/consultation.js
import request from './request'

function createUuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  const bytes = new Uint8Array(16)
  globalThis.crypto.getRandomValues(bytes)
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export const consultationApi = {
  // 会话管理
  getConversations(limit, offset, patientId = null) {
    return request.get('/consultation/conversations', {
      params: { limit, offset, patient_id: patientId || undefined },
    })
  },

  createConversation(patientId) {
    return request.post('/consultation/conversations', { patient_id: patientId })
  },

  deleteConversation(id) {
    return request.delete(`/consultation/conversations/${id}`)
  },

  // 会诊会话
  getSession(conversationId) {
    return request.get(`/consultation/session/${conversationId}`)
  },

  stopSession(sessionId) {
    return request.post(`/consultation/session/${sessionId}/stop`)
  },

  submitAnswer(sessionId, answers) {
    return request.post(`/consultation/session/${sessionId}/answer`, { answers })
  },

  // 分享
  getSharedSession(token) {
    return request.get(`/consultation/session/share/${token}`)
  },

  generateShareToken(conversationId, params = {}) {
    return request.post(`/consultation/conversations/${conversationId}/share`, params)
  },

  verifySharePassword(token, password) {
    return request.post(`/consultation/share/${token}/verify`, { password })
  },

  getConversationById(id) {
    return request.get(`/consultation/session/${id}`)
  },

  getAgentTeamsAvailability() {
    return request.get('/consultation/agentteams/availability')
  },

  async startAgentTeamsConsultation(patientId) {
    return request.post('/consultation/agentteams/start', {
      patient_id: patientId,
      request_id: createUuid(),
    }, { silentError: true })
  },

  getActiveAgentTeamsLaunchIntent(patientId) {
    return request.get('/consultation/agentteams/launch-intents/active', {
      params: { patient_id: patientId },
      silentError: true,
    })
  },

  getAgentTeamsExternalSession(conversationId, patientId) {
    return request.get(`/consultation/agentteams/sessions/${conversationId}`, {
      params: { patient_id: patientId },
      silentError: true,
    })
  },

  updateAgentTeamsExternalStatus(conversationId, patientId, status) {
    return request.patch(`/consultation/agentteams/sessions/${conversationId}/status`, {
      status,
    }, {
      params: { patient_id: patientId },
      silentError: true,
    })
  },

  refreshAgentTeamsEmbed(conversationId, patientId) {
    return request.post(`/consultation/agentteams/sessions/${conversationId}/embed/refresh`, {}, {
      params: { patient_id: patientId },
      silentError: true,
    })
  },
}
