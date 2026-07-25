import { defineStore } from 'pinia'
import { ref } from 'vue'
import notificationApi from '@/api/notification'
import { useUserStore } from '@/stores/user'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const pollingTimer = ref(null)
  const eventSource = ref(null)
  const sseConnected = ref(false)
  const retryCount = ref(0)
  const MAX_RETRY = 3
  const RETRY_DELAY = 5000

  async function fetchNotifications(params = {}) {
    try {
      loading.value = true
      const result = await notificationApi.getNotifications(params)
      notifications.value = result.items || []
      unreadCount.value = result.unread_count || 0
    } catch (err) {
      console.error('获取通知失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchUnreadCount() {
    try {
      const result = await notificationApi.getNotifications({ limit: 1 })
      unreadCount.value = result.unread_count || 0
    } catch {
      // 静默失败
    }
  }

  async function markRead(notificationId) {
    await notificationApi.markRead(notificationId)
    const item = notifications.value.find(n => n.notification_id === notificationId)
    if (item && !item.is_read) {
      item.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  async function markAllRead() {
    await notificationApi.markAllRead()
    notifications.value.forEach(n => { n.is_read = true })
    unreadCount.value = 0
  }

  async function deleteNotification(notificationId) {
    await notificationApi.deleteNotification(notificationId)
    const idx = notifications.value.findIndex(n => n.notification_id === notificationId)
    if (idx >= 0) {
      const wasUnread = !notifications.value[idx].is_read
      notifications.value.splice(idx, 1)
      if (wasUnread) unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  // ---- SSE 实时推送（使用 fetch + ReadableStream，避免 Token 在 URL 中传递）----

  function handleSSENotification(data) {
    try {
      const notification = typeof data === 'string' ? JSON.parse(data) : data
      // 更新未读数
      unreadCount.value += 1
      // 插入列表头部
      notifications.value.unshift(notification)
    } catch (e) {
      console.error('SSE 通知解析失败:', e)
    }
  }

  async function connectSSE() {
    const userStore = useUserStore()
    if (!userStore.token) return
    if (eventSource.value) return // 已连接

    const base = '/api/v1/accounts/notifications/stream'
    retryCount.value = 0

    try {
      const response = await fetch(base, {
        method: 'GET',
        headers: {
          'Accept': 'text/event-stream',
          'Authorization': `Bearer ${userStore.token}`,
        },
      })

      if (!response.ok) {
        if (response.status === 401) {
          // 认证失败，停止 SSE，恢复轮询
          console.warn('SSE 认证失败，恢复轮询')
          startPolling()
          return
        }
        throw new Error(`SSE 连接失败: ${response.status}`)
      }

      sseConnected.value = true
      stopPolling()

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      eventSource.value = { reader, abortController: new AbortController() }

      // 读取流
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 解析 SSE 格式：event: xxx\ndata: xxx\n\n
        const lines = buffer.split('\n')
        buffer = ''

        let currentEvent = ''
        let currentData = ''

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim()
          } else if (line.startsWith('data:')) {
            currentData = line.slice(5).trim()
          } else if (line === '' && currentEvent && currentData) {
            // 事件结束，处理
            if (currentEvent === 'notification') {
              handleSSENotification(currentData)
            }
            currentEvent = ''
            currentData = ''
          } else if (line !== '') {
            // 不完整的行，放回 buffer
            buffer += line + '\n'
          }
        }
      }

      // 流结束，恢复轮询
      sseConnected.value = false
      eventSource.value = null
      startPolling()

    } catch (err) {
      sseConnected.value = false
      eventSource.value = null
      console.error('SSE 连接错误:', err)

      // 重试
      if (retryCount.value < MAX_RETRY) {
        retryCount.value += 1
        setTimeout(connectSSE, RETRY_DELAY)
      } else {
        // 重试耗尽，恢复轮询
        startPolling()
      }
    }
  }

  function disconnectSSE() {
    if (eventSource.value) {
      if (eventSource.value.abortController) {
        eventSource.value.abortController.abort()
      }
      if (eventSource.value.reader) {
        eventSource.value.reader.cancel()
      }
      eventSource.value = null
    }
    sseConnected.value = false
    retryCount.value = 0
  }

  // ---- 轮询（降级方案）----

  function startPolling() {
    stopPolling()
    pollingTimer.value = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchUnreadCount()
      }
    }, 120000) // 120s 间隔
  }

  function stopPolling() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  return {
    notifications,
    unreadCount,
    loading,
    sseConnected,
    fetchNotifications,
    fetchUnreadCount,
    markRead,
    markAllRead,
    deleteNotification,
    connectSSE,
    disconnectSSE,
    startPolling,
    stopPolling,
  }
})