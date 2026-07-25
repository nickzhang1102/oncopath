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
      <van-tab title="随访提醒" name="reminders" />
    </van-tabs>

    <!-- 通知列表 -->
    <van-pull-refresh v-model:loading="refreshing" @refresh="onRefresh">
      <van-list
        v-if="activeTab !== 'reminders'"
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

      <!-- 随访提醒列表 -->
      <div v-if="activeTab === 'reminders'" class="reminder-section">
        <div class="reminder-actions">
          <van-button size="small" type="primary" plain icon="plus" @click="showCreateReminder = true">
            添加提醒
          </van-button>
        </div>
        <div v-if="reminders.length === 0 && !reminderLoading" class="empty-state">
          <van-empty description="暂无随访提醒" />
        </div>
        <div
          v-for="item in reminders"
          :key="item.id"
          class="reminder-item"
          :class="'status-' + item.status"
        >
          <div class="reminder-header">
            <span class="reminder-status" :class="item.status">{{ getStatusLabel(item.status) }}</span>
            <span class="reminder-date">{{ item.reminder_date }}</span>
          </div>
          <div class="reminder-title">{{ item.title }}</div>
          <div v-if="item.description" class="reminder-desc">{{ item.description }}</div>
          <div class="reminder-footer">
            <van-button
              v-if="item.status === 'pending' || item.status === 'sent'"
              size="mini"
              type="success"
              plain
              @click="handleConfirmReminder(item)"
            >
              已复查
            </van-button>
            <van-button
              size="mini"
              type="danger"
              plain
              @click="handleDeleteReminder(item)"
            >
              删除
            </van-button>
          </div>
        </div>
      </div>
    </van-pull-refresh>

    <!-- 创建提醒弹窗 -->
    <van-dialog
      v-model:show="showCreateReminder"
      title="添加随访提醒"
      show-cancel-button
      :before-close="handleCreateReminder"
    >
      <div class="create-form">
        <van-field v-model="newReminder.title" label="提醒标题" placeholder="如：血常规复查" required />
        <van-field v-model="newReminder.description" label="备注" type="textarea" rows="2" placeholder="可选" />
        <van-field
          v-model="newReminder.reminder_date"
          label="提醒日期"
          placeholder="点击选择"
          readonly
          clickable
          required
          @click="showNotifDatePicker = true"
        />
      </div>
    </van-dialog>

    <!-- 提醒日期选择器 -->
    <van-popup
      v-model:show="showNotifDatePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="notifDatePickerValue"
        title="选择提醒日期"
        :min-date="new Date()"
        :max-date="new Date(2030, 11, 31)"
        @confirm="onNotifDateConfirm"
        @cancel="showNotifDatePicker = false"
      />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast, showSuccessToast, showConfirmDialog } from 'vant'
import { useRoute, useRouter } from 'vue-router'
import { userApi } from '@/api/user'
import followUpApi from '@/api/followUp'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'

const route = useRoute()
const router = useRouter()
const patientStore = usePatientStore()
const { isDesktop } = useResponsive()

// 通知列表
const activeTab = ref(route.query.tab === 'reminders' ? 'reminders' : 'all')
const notifications = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)
const limit = 20

// 随访提醒
const reminders = ref([])
const reminderLoading = ref(false)
const showCreateReminder = ref(false)
const showNotifDatePicker = ref(false)
const notifDatePickerValue = ref([])
const newReminder = ref({ title: '', description: '', reminder_date: '' })

function onNotifDateConfirm({ selectedValues }) {
  if (selectedValues?.length === 3) {
    newReminder.value.reminder_date = selectedValues.join('-')
  }
  showNotifDatePicker.value = false
}

onMounted(() => {
  if (activeTab.value === 'reminders') {
    loadReminders()
  } else {
    onLoad()
  }
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
  if (activeTab.value === 'reminders') {
    await loadReminders()
    refreshing.value = false
    return
  }
  page.value = 1
  finished.value = false
  notifications.value = []
  await onLoad()
  refreshing.value = false
}

async function handleTabChange() {
  if (activeTab.value === 'reminders') {
    await loadReminders()
  } else {
    page.value = 1
    finished.value = false
    notifications.value = []
    onLoad()
  }
}

async function loadReminders() {
  const patientId = patientStore.currentPatient?.patient_id
  if (!patientId) {
    reminders.value = []
    return
  }
  reminderLoading.value = true
  try {
    const res = await followUpApi.getReminders({ patient_id: patientId })
    reminders.value = res.items || res.data || res || []
  } catch (error) {
    showToast('加载提醒失败')
  } finally {
    reminderLoading.value = false
  }
}

async function handleConfirmReminder(item) {
  try {
    await showConfirmDialog({ title: '确认', message: '确认已复查？' })
    await followUpApi.confirmReminder(item.id)
    showSuccessToast('已确认复查')
    await loadReminders()
  } catch {
    // 取消或失败
  }
}

async function handleDeleteReminder(item) {
  try {
    await showConfirmDialog({ title: '确认删除', message: '确定删除此提醒？' })
    await followUpApi.deleteReminder(item.id)
    showSuccessToast('已删除')
    await loadReminders()
  } catch {
    // 取消或失败
  }
}

async function handleCreateReminder(action) {
  if (action !== 'confirm') {
    newReminder.value = { title: '', description: '', reminder_date: '' }
    return true
  }
  if (!newReminder.value.title || !newReminder.value.reminder_date) {
    showToast('请填写标题和日期')
    return false
  }
  const patientId = patientStore.currentPatient?.patient_id
  if (!patientId) {
    showToast('请先选择患者')
    return false
  }
  try {
    await followUpApi.createReminder({
      patient_id: patientId,
      ...newReminder.value,
    })
    showSuccessToast('提醒已创建')
    newReminder.value = { title: '', description: '', reminder_date: '' }
    await loadReminders()
    return true
  } catch {
    showToast('创建失败')
    return false
  }
}

async function handleItemClick(item) {
  if (!item.is_read) {
    try {
      await userApi.markNotificationRead(item.notification_id)
      item.is_read = true
    } catch (error) {
      console.error('标记已读失败', error)
    }
  }

  // 根据通知类型跳转
  const routeMap = {
    consultation: item.related_id ? `/conversation/${item.related_id}` : '/consultation/list',
    report: item.related_id ? `/report/${item.related_id}` : '/home/reports',
    reminder: '/home/follow-up',
  }
  const target = routeMap[item.type]
  if (target) {
    router.push(target)
  }
}

async function handleReadAll() {
  try {
    const res = await userApi.markAllNotificationsRead()
    showSuccessToast(`已标记 ${res.updated_count} 条通知为已读`)
    notifications.value.forEach(item => { item.is_read = true })
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

function getStatusLabel(status) {
  const map = { pending: '待处理', sent: '已通知', confirmed: '已复查', expired: '已过期' }
  return map[status] || status
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

/* 随访提醒 */
.reminder-section {
  padding: var(--space-3) var(--space-4);
}

.reminder-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-3);
}

.reminder-item {
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  margin-bottom: var(--space-3);
  border: 1px solid var(--border-color);
}

.reminder-item.status-expired {
  opacity: 0.6;
}

.reminder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.reminder-status {
  font-size: var(--text-xs);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.reminder-status.pending {
  background: var(--status-warning-bg);
  color: var(--warning-color);
}

.reminder-status.sent {
  background: var(--status-info-bg);
  color: var(--primary-color);
}

.reminder-status.confirmed {
  background: var(--status-normal-bg);
  color: var(--success-color);
}

.reminder-status.expired {
  background: var(--bg-secondary);
  color: var(--text-tertiary);
}

.reminder-date {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.reminder-title {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-1);
}

.reminder-desc {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: var(--space-2);
}

.reminder-footer {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}

.create-form {
  padding: var(--space-3) var(--space-4);
}

@media (min-width: 768px) {
  .profile-notifications {
    max-width: 800px;
    margin: 0 auto;
  }
}
</style>