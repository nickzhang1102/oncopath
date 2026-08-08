// front/src/api/consultation.js
import request from './request'

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

  startAgentTeamsConsultation(patientId, conversationId = null) {
    return request.post('/consultation/agentteams/start', {
      patient_id: patientId,
      conversation_id: conversationId,
    }, { silentError: true })
  },

  getAgentTeamsExternalSession(conversationId, patientId) {
    return request.get(`/consultation/agentteams/sessions/${conversationId}`, {
      params: { patient_id: patientId },
      silentError: true,
    })
  },
}
