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

    // AbortController 必须在发请求前创建并绑定 signal，
    // 否则 disconnectSSE 无法中断已挂起的连接（含 TCP 半开场景）
    const abortController = new AbortController()
    // 心跳超时：超过时限未收到任何数据即判定连接半开，主动断开走重试/降级
    let heartbeatTimer = null
    const HEARTBEAT_TIMEOUT = 90000
    const resetHeartbeat = () => {
      if (heartbeatTimer) clearTimeout(heartbeatTimer)
      heartbeatTimer = setTimeout(() => {
        console.warn('通知 SSE 心跳超时，主动断开')
        abortController.abort(new Error('通知 SSE 心跳超时'))
      }, HEARTBEAT_TIMEOUT)
    }

    try {
      const response = await fetch(base, {
        method: 'GET',
        headers: {
          'Accept': 'text/event-stream',
          'Authorization': `Bearer ${userStore.token}`,
        },
        signal: abortController.signal,
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

      eventSource.value = { reader, abortController }

      resetHeartbeat()
      // 读取流
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        resetHeartbeat()

        buffer += decoder.decode(value, { stream: true })

        // 解析 SSE 格式：event: xxx\ndata: xxx\n\n
        // 最后一段可能被 chunk 截断，必须留在 buffer 等下一个 chunk 拼全
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

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
          }
        }
      }

      // 流正常结束，恢复轮询
      sseConnected.value = false
      eventSource.value = null
      startPolling()

    } catch (err) {
      sseConnected.value = false
      eventSource.value = null

      // 用户主动断开（无 reason 的 abort），静默退出不重试
      if (err?.name === 'AbortError') return

      console.error('SSE 连接错误:', err)

      // 心跳超时或网络异常：有限重试，耗尽后恢复轮询
      if (retryCount.value < MAX_RETRY) {
        retryCount.value += 1
        setTimeout(connectSSE, RETRY_DELAY)
      } else {
        startPolling()
      }
    } finally {
      if (heartbeatTimer) clearTimeout(heartbeatTimer)
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