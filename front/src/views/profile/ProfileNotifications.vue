<template>
  <div class="profile-notifications">
    <van-nav-bar
      title="消息通知"
      left-text="返回"
      left-arrow
      @click-left="$router.back()"
      fixed
      placeholder
      :safe-area-inset-top="true"
    >
      <template #right>
        <span class="read-all-btn" @click="handleReadAll">全部已读</span>
      </template>
    </van-nav-bar>

    <!-- 筛选标签 -->
    <van-tabs v-model:active="activeTab" @change="handleTabChange">
      <van-tab title="全部" name="all" />
      <van-tab title="未读" name="unread" />
    </van-tabs>

    <!-- 通知列表 -->
    <van-pull-refresh v-model:loading="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <div v-if="notifications.length === 0 && !loading" class="empty-state">
          <van-empty description="暂无通知" />
        </div>
        <div
          v-for="item in notifications"
          :key="item.notification_id"
          class="notification-item"
          :class="{ unread: !item.is_read }"
          @click="handleItemClick(item)"
        >
          <div class="item-header">
            <span class="item-type" :class="item.type">{{ getTypeName(item.type) }}</span>
            <span class="item-time">{{ formatTime(item.created_at) }}</span>
          </div>
          <div class="item-title">{{ item.title }}</div>
          <div v-if="item.content" class="item-content">{{ item.content }}</div>
        </div>
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { useRouter } from 'vue-router'
import { userApi } from '@/api/user'
import { useNotificationStore } from '@/stores/notification'
import { useUserStore } from '@/stores/user'

const router = useRouter()
// 未读数与全局通知 store 同步，保证底部导航「我的」按钮角标与列表一致
const notificationStore = useNotificationStore()
// 判定管理员身份，用于「会诊启动需人工复核」通知跳转管理后台复核页
const userStore = useUserStore()

// 通知列表
const activeTab = ref('all')
const notifications = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)
const limit = 20

onMounted(() => {
  onLoad()
})

async function onLoad() {
  if (refreshing.value) return

  try {
    const params = { page: page.value, limit }
    if (activeTab.value === 'unread') {
      params.is_read = false
    }

    const res = await userApi.getNotifications(params)

    if (page.value === 1) {
      notifications.value = res.items
    } else {
      notifications.value.push(...res.items)
    }

    // 同步全局未读数（底部导航角标数据源）
    notificationStore.unreadCount = res.unread_count || 0

    if (notifications.value.length >= res.total) {
      finished.value = true
    } else {
      page.value++
    }
  } catch (error) {
    showToast('加载失败')
    finished.value = true
  } finally {
    loading.value = false
  }
}

async function onRefresh() {
  page.value = 1
  finished.value = false
  notifications.value = []
  await onLoad()
  refreshing.value = false
}

function handleTabChange() {
  page.value = 1
  finished.value = false
  notifications.value = []
  onLoad()
}

async function handleItemClick(item) {
  if (!item.is_read) {
    try {
      await userApi.markNotificationRead(item.notification_id)
      item.is_read = true
      notificationStore.unreadCount = Math.max(0, notificationStore.unreadCount - 1)
    } catch (error) {
      console.error('标记已读失败', error)
    }
  }

  // 根据通知类型跳转。
  // 会诊消息通知会随会诊删除被后端同步清理；对仍存在的通知统一跳转会诊列表
  // （嵌入页需要患者上下文，通知体里没有），避免指向无效页面 404。
  // 例外：管理员的「会诊启动需人工复核」通知（带 intent_id）跳管理后台复核页。
  const extra = item.extra_data || {}
  let target = null
  if (item.type === 'consultation') {
    if (extra.intent_id && userStore.userInfo?.account_type === 'admin') {
      target = '/admin/agentteams-launch-reviews'
    } else {
      target = '/home/consultation'
    }
  } else if (item.type === 'report') {
    const relatedId = item.related_id || extra.related_id || extra.report_id
    target = relatedId ? `/home/report/${relatedId}` : '/home/reports'
  }
  if (target) {
    router.push(target)
  }
}

async function handleReadAll() {
  try {
    const res = await userApi.markAllNotificationsRead()
    showSuccessToast(`已标记 ${res.updated_count} 条通知为已读`)
    notifications.value.forEach(item => { item.is_read = true })
    // 同步全局未读数（底部导航角标数据源）
    notificationStore.unreadCount = 0
  } catch (error) {
    showToast('操作失败')
  }
}

function getTypeName(type) {
  const typeMap = {
    system: '系统',
    consultation: '会诊',
    report: '报告',
    reminder: '提醒',
  }
  return typeMap[type] || '通知'
}

function formatTime(time) {
  const date = new Date(time)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`

  return `${date.getMonth() + 1}/${date.getDate()}`
}
</script>

<style scoped>
.profile-notifications {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
}

:deep(.van-nav-bar) {
  background: var(--bg-surface-alpha);
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  z-index: 10;
}

:deep(.van-nav-bar__title) {
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
}

:deep(.van-nav-bar__text) {
  color: var(--primary-color);
}

:deep(.van-icon-arrow-left) {
  color: var(--primary-color);
}

.read-all-btn {
  font-size: var(--text-sm);
  color: var(--primary-color);
}

.notification-item {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-surface);
  margin-bottom: 1px;
}

.notification-item.unread {
  background: var(--bg-surface);
  border-left: 3px solid var(--primary-color);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.item-type {
  font-size: var(--text-xs);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.item-type.system {
  background: var(--status-info-bg);
  color: var(--primary-color);
}

.item-type.consultation {
  background: var(--status-normal-bg);
  color: var(--success-color);
}

.item-type.report {
  background: var(--status-warning-bg);
  color: var(--warning-color);
}

.item-type.reminder {
  background: var(--status-danger-bg);
  color: var(--danger-color);
}

.item-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.item-title {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.item-content {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.5;
}

.empty-state {
  padding: var(--space-8) 0;
}

@media (min-width: 768px) {
  .profile-notifications {
    max-width: 800px;
    margin: 0 auto;
  }
}
</style>
