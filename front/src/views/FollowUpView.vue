<template>
  <div class="follow-up-view">
    <BackButton v-if="!isDesktop" title="随访提醒" />

    <header v-if="isDesktop" class="desktop-header">
      <div class="header-content">
        <h1 class="page-title">随访提醒</h1>
        <div class="header-actions">
          <van-button type="primary" icon="plus" @click="openAddForm">新建提醒</van-button>
        </div>
      </div>
    </header>

    <!-- 筛选Tab -->
    <van-tabs v-model:active="activeTab" @change="loadReminders" class="filter-tabs">
      <van-tab title="待处理" name="pending" />
      <van-tab title="已确认" name="confirmed" />
      <van-tab title="已过期" name="expired" />
      <van-tab title="全部" name="" />
    </van-tabs>

    <van-loading v-if="loading" class="loading-center" />

    <div v-else-if="reminders.length === 0" class="empty-state">
      <van-empty description="暂无提醒" />
    </div>

    <div v-else class="reminder-list">
      <div
        v-for="item in reminders"
        :key="item.id"
        class="reminder-card"
      >
        <div class="card-header">
          <div class="card-title">{{ item.title }}</div>
          <van-tag :type="statusTagType(item.status)">{{ statusLabel(item.status) }}</van-tag>
        </div>
        <div class="card-body">
          <div class="card-info">
            <van-icon name="calendar-o" /> {{ item.reminder_date }}
          </div>
          <div v-if="item.description" class="card-desc">{{ item.description }}</div>
          <div v-if="item.source_type" class="card-source">
            来源：{{ sourceLabel(item.source_type) }}
          </div>
        </div>
        <div class="card-actions">
          <van-button
            v-if="item.status === 'pending' || item.status === 'sent'"
            size="small"
            type="success"
            @click="handleConfirm(item)"
          >
            已复查
          </van-button>
          <van-button size="small" plain @click="handleDelete(item)">删除</van-button>
        </div>
      </div>
    </div>

    <van-floating-bubble
      v-if="!isDesktop && hasPatient"
      axis="xy"
      icon="plus"
      @click="openAddForm"
      :gap="floatingBubbleGap"
    />

    <!-- 新建弹窗 -->
    <van-popup
      v-model:show="showForm"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-md' : ''"
      :style="!isDesktop ? { height: '70%' } : ''"
    >
      <div class="form-popup">
        <van-nav-bar
          title="新建提醒"
          :left-text="!isDesktop ? '取消' : ''"
          @click-left="showForm = false"
        >
          <template v-if="!isDesktop" #right>
            <van-button type="primary" size="small" :loading="saving" @click="handleSave">保存</van-button>
          </template>
        </van-nav-bar>
        <div class="form-content">
          <van-cell-group inset>
            <van-field v-model="form.title" label="标题" placeholder="如：复查CT" required />
            <van-field
              v-model="form.reminder_date"
              label="提醒日期"
              placeholder="点击选择"
              readonly
              clickable
              required
              @click="showDatePicker = true"
            />
            <van-field v-model="form.description" label="备注" type="textarea" rows="2" />
          </van-cell-group>
        </div>

        <!-- 桌面端底部按钮 -->
        <div v-if="isDesktop" class="form-footer">
          <van-button @click="showForm = false">取消</van-button>
          <van-button type="primary" :loading="saving" @click="handleSave">保存</van-button>
        </div>
      </div>
    </van-popup>

    <van-popup
      v-model:show="showDatePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker title="选择日期" @confirm="onDateConfirm" @cancel="showDatePicker = false" />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import dayjs from 'dayjs'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'
import followUpApi from '@/api/followUp'
import BackButton from '@/components/index-detail/BackButton.vue'

const { isDesktop, floatingBubbleGap } = useResponsive()
const patientStore = usePatientStore()
const hasPatient = computed(() => !!patientStore.currentPatient)

const loading = ref(false)
const saving = ref(false)
const reminders = ref([])
const activeTab = ref('pending')
const showForm = ref(false)
const showDatePicker = ref(false)
const form = ref({ title: '', reminder_date: '', description: '' })

function statusLabel(s) {
  return { pending: '待处理', sent: '已发送', confirmed: '已确认', expired: '已过期' }[s] || s
}

function statusTagType(s) {
  return { pending: 'primary', sent: 'warning', confirmed: 'success', expired: 'default' }[s] || 'default'
}

function sourceLabel(s) {
  return { manual: '手动创建', interpretation: 'AI解读', consultation: 'AI会诊' }[s] || s
}

function openAddForm() {
  form.value = { title: '', reminder_date: dayjs().format('YYYY-MM-DD'), description: '' }
  showForm.value = true
}

function onDateConfirm({ selectedValues }) {
  form.value.reminder_date = selectedValues.join('-')
  showDatePicker.value = false
}

async function loadReminders() {
  if (!patientStore.currentPatient) return
  loading.value = true
  try {
    const params = { patient_id: patientStore.currentPatient.patient_id }
    if (activeTab.value) params.status = activeTab.value
    const res = await followUpApi.getReminders(params)
    reminders.value = Array.isArray(res?.items) ? res.items : (Array.isArray(res) ? res : [])
  } catch (e) {
    console.error('加载提醒失败:', e)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!form.value.title) { showToast('请输入标题'); return }
  if (!form.value.reminder_date) { showToast('请选择日期'); return }
  saving.value = true
  try {
    await followUpApi.createReminder({
      ...form.value,
      patient_id: patientStore.currentPatient.patient_id,
    })
    showToast('创建成功')
    showForm.value = false
    await loadReminders()
  } catch (e) {
    console.error('创建失败:', e)
  } finally {
    saving.value = false
  }
}

async function handleConfirm(item) {
  try {
    await showConfirmDialog({ title: '确认已复查？', message: `提醒：${item.title}` })
    await followUpApi.confirmReminder(item.id)
    showToast('已确认')
    await loadReminders()
  } catch { /* 取消 */ }
}

async function handleDelete(item) {
  try {
    await showConfirmDialog({ title: '确认删除？', message: item.title })
    await followUpApi.deleteReminder(item.id)
    showToast('已删除')
    await loadReminders()
  } catch { /* 取消 */ }
}

onMounted(() => { loadReminders() })
watch(() => patientStore.currentPatient?.patient_id, (n, o) => { if (n && n !== o) loadReminders() })
</script>

<style scoped>
.follow-up-view {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
}

.filter-tabs { background: var(--bg-surface); }

.loading-center { display: flex; justify-content: center; padding: 60px; }

.empty-state { display: flex; align-items: center; justify-content: center; min-height: 40vh; }

.reminder-list { padding: 16px; }

.reminder-card {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
}

.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }

.card-title { font-size: 16px; font-weight: 600; color: var(--text-primary); }

.card-info { font-size: 13px; color: var(--text-secondary); display: flex; align-items: center; gap: 4px; }

.card-desc { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }

.card-source { font-size: 12px; color: var(--text-tertiary); margin-top: 2px; }

.card-actions { display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end; }

.form-popup { height: 100%; display: flex; flex-direction: column; background: var(--bg-elevated); }

.form-content { flex: 1; overflow-y: auto; padding: 16px; }

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-elevated);
}

/* 桌面端页面头部（对齐 StatusView/ConsultationList） */
.desktop-header {
  margin-bottom: var(--space-4);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

@media (min-width: 768px) {
  .follow-up-view { max-width: 800px; margin: 0 auto; }
}
</style>