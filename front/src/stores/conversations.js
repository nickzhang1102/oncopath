// front/src/stores/conversations.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { consultationApi } from '@/api/consultation'

export const useConversationsStore = defineStore('conversations', () => {
  const conversations = ref([])
  const currentConversation = ref(null)
  const recentConversations = ref([])
  const total = ref(0)

  const finished = computed(() => conversations.value.length >= total.value)

  function appendConversations(newItems) {
    newItems.forEach(item => {
      if (!conversations.value.some(c => c.id === item.id)) {
        conversations.value.push(item)
      }
    })
  }

  async function fetchConversations(limit = 20, offset = 0, append = false) {
    try {
      const response = await consultationApi.getConversations(limit, offset)
      total.value = response.total || 0
      if (append) {
        appendConversations(response.conversations || [])
      } else {
        conversations.value = response.conversations || []
      }
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '获取会诊列表失败'
      }
    }
  }

  async function fetchRecentConversations(limit = 10) {
    try {
      const response = await consultationApi.getConversations(limit, 0)
      recentConversations.value = response.conversations || []
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '获取最近会诊失败'
      }
    }
  }

  async function createConversation(patientId) {
    try {
      const response = await consultationApi.createConversation(patientId)
      const newConversation = response

      conversations.value.unshift(newConversation)
      recentConversations.value.unshift(newConversation)
      currentConversation.value = newConversation

      return { success: true, conversation: newConversation }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '创建会诊失败'
      }
    }
  }

  async function deleteConversation(id) {
    try {
      await consultationApi.deleteConversation(id)
      conversations.value = conversations.value.filter(c => c.id !== id)
      recentConversations.value = recentConversations.value.filter(c => c.id !== id)
      if (currentConversation.value?.id === id) {
        currentConversation.value = null
      }
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '删除会诊失败'
      }
    }
  }

  async function fetchConversationByToken(token) {
    try {
      const response = await consultationApi.getSharedSession(token)
      return { success: true, data: response }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '会诊不存在或链接已失效'
      }
    }
  }

  async function generateShareToken(conversationId, params = {}) {
    try {
      const response = await consultationApi.generateShareToken(conversationId, params)
      return { success: true, data: response }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '生成分享链接失败'
      }
    }
  }

  async function verifySharePassword(token, password) {
    try {
      const response = await consultationApi.verifySharePassword(token, password)
      return { success: true, data: response }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '密码验证失败'
      }
    }
  }

  async function fetchConversationById(id) {
    try {
      const response = await consultationApi.getConversationById(id)
      return { success: true, data: response }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || '会诊不存在'
      }
    }
  }

  function clearCurrentConversation() {
    currentConversation.value = null
  }

  return {
    conversations,
    currentConversation,
    recentConversations,
    total,
    finished,
    fetchConversations,
    fetchRecentConversations,
    createConversation,
    deleteConversation,
    fetchConversationByToken,
    fetchConversationById,
    generateShareToken,
    verifySharePassword,
    clearCurrentConversation
  }
})