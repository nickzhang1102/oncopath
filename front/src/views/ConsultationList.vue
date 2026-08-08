<!-- front/src/views/ConsultationList.vue -->
<template>
  <div class="consultation-list" :class="{ 'is-desktop': isDesktop }">
    <!-- 移动端顶部导航 -->
    <van-nav-bar
      v-if="!isDesktop"
      title="虚拟会诊"
      left-text="返回"
      left-arrow
      @click-left="handleBack"
      fixed
      placeholder
      :safe-area-inset-top="true"
    >
      <template #right>
        <van-button size="mini" type="primary" plain icon="setting-o" @click="router.push('/home/consultation/prompt-config')">提示词</van-button>
      </template>
    </van-nav-bar>

    <!-- 桌面端页面头部 -->
    <header v-if="isDesktop" class="desktop-header">
      <div class="header-content">
        <h1 class="page-title">虚拟会诊</h1>
        <div class="header-actions">
          <van-button plain icon="setting-o" @click="router.push('/home/consultation/prompt-config')">提示词配置</van-button>
          <van-button
            type="primary"
            icon="add-o"
            :loading="agentTeamsAvailabilityLoading"
            @click="handleStartConsultation"
          >开始会诊</van-button>
        </div>
      </div>
    </header>

    <!-- 移动端搜索栏 -->
    <van-search
      v-if="!isDesktop"
      v-model="searchQuery"
      placeholder="搜索会诊记录"
      shape="round"
      @search="onSearch"
    />

    <div v-if="!isDesktop && currentPatient" class="mobile-patient-context">
      <span><van-icon name="user-o" />{{ currentPatientName }}</span>
      <button type="button" @click="showHistoryPatientPicker = true">切换患者</button>
    </div>

    <!-- 桌面端搜索+筛选栏 -->
    <div v-if="isDesktop" class="desktop-toolbar">
      <van-search
        v-model="searchQuery"
        placeholder="搜索会诊记录"
        shape="round"
        @search="onSearch"
        class="desktop-search"
      />
      <button
        v-if="currentPatient"
        type="button"
        class="patient-filter-button"
        @click="showHistoryPatientPicker = true"
      >
        <van-icon name="user-o" />
        <span>{{ currentPatientName }}</span>
        <van-icon name="arrow-down" />
      </button>
      <div class="filter-tabs">
        <button
          v-for="tab in statusTabs"
          :key="tab.value"
          :class="['filter-tab', { active: activeTab === tab.value }]"
          @click="activeTab = tab.value"
        >{{ tab.label }}</button>
      </div>
    </div>

    <!-- 会诊列表 -->
    <van-pull-refresh v-if="!isDesktop" v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loadingMore"
        :finished="finished"
        finished-text="没有更多了"
        @load="onLoad"
      >
        <template v-if="conversations.length > 0">
          <van-swipe-cell v-for="conv in filteredConversations" :key="conv.id">
            <div
              :class="['consultation-card', getStatusClass(getConversationStatus(conv))]"
              @click="handleOpenConversation(conv)"
            >
              <div class="card-header">
                <span class="card-title">{{ conv.title || '虚拟会诊' }}</span>
                <span :class="['status-tag', getStatusClass(getConversationStatus(conv))]">
                  {{ getStatusText(getConversationStatus(conv)) }}
                </span>
              </div>
              <div class="card-body" v-if="conv.preview">
                <span class="card-preview">{{ conv.preview }}</span>
              </div>
              <div class="card-footer">
                <span class="card-patient"><van-icon name="user-o" />{{ currentPatientName }}</span>
                <span class="card-time">{{ formatTime(conv.updated_at || conv.created_at) }}</span>
              </div>
            </div>
            <template #right>
              <van-button square type="danger" text="删除" class="delete-button" @click="handleDelete(conv)" />
            </template>
          </van-swipe-cell>
        </template>
        <van-empty v-else-if="!loadingMore" description="暂无会诊记录" image="search">
          <van-button
            type="primary"
            class="empty-button"
            :loading="agentTeamsAvailabilityLoading"
            @click="handleStartConsultation"
          >开始会诊</van-button>
        </van-empty>
      </van-list>
    </van-pull-refresh>

    <!-- 桌面端列表 -->
    <div v-if="isDesktop" class="desktop-list">
      <div v-if="filteredConversations.length > 0" class="conversation-grid">
        <div
          v-for="conv in filteredConversations"
          :key="conv.id"
          :class="['desktop-card', getStatusClass(getConversationStatus(conv))]"
          @click="handleOpenConversation(conv)"
        >
          <div class="desktop-card-header">
            <span class="desktop-card-title">{{ conv.title || '虚拟会诊' }}</span>
            <span :class="['status-tag', getStatusClass(getConversationStatus(conv))]">
              {{ getStatusText(getConversationStatus(conv)) }}
            </span>
          </div>
          <div class="desktop-card-body" v-if="conv.preview">
            {{ conv.preview }}
          </div>
          <div class="desktop-card-footer">
            <span class="card-time">{{ formatTime(conv.updated_at || conv.created_at) }}</span>
            <div class="card-actions">
              <span class="detail-link">查看明细 <van-icon name="arrow" /></span>
              <van-button size="mini" type="danger" plain @click.stop="handleDelete(conv)">删除</van-button>
            </div>
          </div>
        </div>
      </div>
      <van-empty v-else-if="!loadingMore" description="暂无会诊记录" image="search">
        <van-button
          type="primary"
          :loading="agentTeamsAvailabilityLoading"
          @click="handleStartConsultation"
        >开始会诊</van-button>
      </van-empty>

      <!-- 加载更多 -->
      <div v-if="filteredConversations.length > 0" class="load-more-area">
        <van-button
          v-if="!finished"
          :loading="loadingMore"
          plain
          round
          size="small"
          @click="onLoad"
        >加载更多</van-button>
        <span v-else class="no-more">没有更多了</span>
      </div>
    </div>

    <!-- 移动端浮动按钮 -->
    <van-button
      v-if="!isDesktop && conversations.length > 0"
      class="start-button"
      type="primary"
      icon="add-o"
      round
      :loading="agentTeamsAvailabilityLoading"
      @click="handleStartConsultation"
    >开始会诊</van-button>

    <van-action-sheet v-model:show="showHistoryPatientPicker" title="选择历史患者">
      <div class="patient-picker history-patient-picker">
        <button
          v-for="patient in patientStore.patientList"
          :key="patient.patient_id"
          type="button"
          :class="['patient-item', { active: currentPatientId === patient.patient_id }]"
          @click="selectHistoryPatient(patient)"
        >
          <van-icon name="user-o" />
          <span>{{ patient.patient_name || `患者${patient.patient_id}` }}</span>
          <van-icon v-if="currentPatientId === patient.patient_id" name="success" color="var(--primary-color)" />
        </button>
      </div>
    </van-action-sheet>

    <!-- 开始会诊时选择患者 -->
    <van-action-sheet
      v-model:show="showPatientPicker"
      title="选择患者"
    >
      <div class="patient-picker">
        <div
          v-for="patient in patientStore.patientList"
          :key="patient.patient_id"
          :class="['patient-item', { active: selectedPatientId === patient.patient_id }]"
          @click="selectedPatientId = patient.patient_id"
        >
          <van-icon name="user-o" />
          <span>{{ patient.patient_name || `患者${patient.patient_id}` }}</span>
          <van-icon v-if="selectedPatientId === patient.patient_id" name="success" color="var(--primary-color)" />
        </div>
        <van-empty v-if="patientStore.patientList.length === 0" description="暂无患者" />
        <div class="picker-footer">
          <van-button
            block
            type="primary"
            :disabled="!selectedPatientId"
            :loading="agentTeamsStartLoading"
            @click="confirmStartConsultation"
          >
            确认开始
          </van-button>
        </div>
      </div>
    </van-action-sheet>

    <AgentTeamsUpsellDialog
      v-model:show="showAgentTeamsUpsell"
      :upsell="agentTeamsUpsell"
      @cta="handleAgentTeamsUpsellCta"
    />

    <AgentTeamsErrorDialog
      v-model:show="showAgentTeamsError"
      :error="agentTeamsError"
      @cta="handleAgentTeamsUpsellCta"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showDialog } from 'vant'
import { useConversationsStore } from '@/stores/conversations'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'
import { consultationApi } from '@/api/consultation'
import AgentTeamsUpsellDialog from '@/components/consultation/AgentTeamsUpsellDialog.vue'
import AgentTeamsErrorDialog from '@/components/consultation/AgentTeamsErrorDialog.vue'
import { getAgentTeamsErrorUx, isAgentTeamsError } from '@/utils/agentteamsErrorUx'
import dayjs from 'dayjs'

const router = useRouter()
const { isDesktop } = useResponsive()
const conversationsStore = useConversationsStore()
const patientStore = usePatientStore()

// 状态
const searchQuery = ref('')
const refreshing = ref(false)
const loadingMore = ref(false)
const showPatientPicker = ref(false)
const showHistoryPatientPicker = ref(false)
const showAgentTeamsUpsell = ref(false)
const showAgentTeamsError = ref(false)
const agentTeamsUpsell = ref({})
const agentTeamsError = ref({})
const agentTeamsCtaUrl = ref('')
const agentTeamsAvailabilityLoading = ref(false)
const agentTeamsStartLoading = ref(false)
const selectedPatientId = ref(null)
const currentPage = ref(0)
const pageSize = 20
const activeTab = ref('all')

const statusTabs = [
  { label: '全部', value: 'all' },
  { label: '进行中', value: 'active' },
  { label: '已完成', value: 'completed' },
]

// 计算属性
const conversations = computed(() => conversationsStore.conversations)
const finished = computed(() => conversationsStore.finished)
const currentPatient = computed(() => patientStore.currentPatient)
const currentPatientId = computed(() => currentPatient.value?.patient_id || null)
const currentPatientName = computed(() => currentPatient.value?.patient_name || '当前患者')

const filteredConversations = computed(() => {
  let list = conversations.value

  // 状态筛选
  if (activeTab.value === 'active') {
    list = list.filter(c => ['new', 'created', 'running', 'idle', 'assessing', 'forming_team', 'monitoring', 'summarizing', 'analyzing'].includes(getConversationStatus(c)))
  } else if (activeTab.value === 'completed') {
    list = list.filter(c => ['completed', 'stopped', 'failed', 'error'].includes(getConversationStatus(c)))
  }

  // 搜索筛选
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(c =>
      (c.title || '').toLowerCase().includes(q) ||
      (c.preview || '').toLowerCase().includes(q)
    )
  }

  return list
})

// 方法
function handleBack() {
  router.push('/home/news')
}

function getConversationStatus(conv) {
  return conv?.external_session_status || conv?.status || 'new'
}

function getStatusClass(status) {
  const map = {
    'new': 'status-new',
    'created': 'status-new',
    'running': 'status-analyzing',
    'analyzing': 'status-analyzing',
    'completed': 'status-completed',
    'error': 'status-error',
    'idle': 'status-new',
    'assessing': 'status-analyzing',
    'forming_team': 'status-analyzing',
    'monitoring': 'status-analyzing',
    'summarizing': 'status-analyzing',
    'failed': 'status-error',
    'stopped': 'status-error'
  }
  return map[status] || 'status-new'
}

function getStatusText(status) {
  const map = {
    'new': '新建',
    'created': '新建',
    'running': '分析中',
    'analyzing': '分析中',
    'completed': '已完成',
    'error': '异常',
    'idle': '新建',
    'assessing': '评估中',
    'forming_team': '组队中',
    'monitoring': '执行中',
    'summarizing': '汇总中',
    'failed': '失败',
    'stopped': '已停止'
  }
  return map[status] || '新建'
}

function formatTime(time) {
  if (!time) return ''
  // 后端存储 naive UTC 时间（无时区标记），需手动加偏移
  return dayjs(time).add(8, 'hour').format('MM-DD HH:mm')
}

async function onRefresh() {
  await loadFirstPage()
  refreshing.value = false
}

async function loadFirstPage() {
  const patientId = currentPatientId.value
  currentPage.value = 0
  conversationsStore.clearConversations()
  if (!patientId) return

  loadingMore.value = true
  try {
    const result = await conversationsStore.fetchConversations(
      pageSize,
      0,
      false,
      patientId,
    )
    if (result.success && currentPatientId.value === patientId) {
      currentPage.value = 1
    }
  } finally {
    if (currentPatientId.value === patientId) {
      loadingMore.value = false
    }
  }
}

async function onLoad() {
  const patientId = currentPatientId.value
  if (!patientId) {
    loadingMore.value = false
    return
  }
  const result = await conversationsStore.fetchConversations(
    pageSize,
    currentPage.value * pageSize,
    true,
    patientId,
  )
  if (result.success && currentPatientId.value === patientId) {
    currentPage.value++
  }
  if (currentPatientId.value === patientId) {
    loadingMore.value = false
  }
}

function onSearch() {
  // 搜索由 computed 属性过滤
}

function handleOpenConversation(conv) {
  router.push({
    path: `/home/consultation/${conv.id}`,
    query: { patient_id: conv.patient_id || currentPatientId.value },
  })
}

async function selectHistoryPatient(patient) {
  showHistoryPatientPicker.value = false
  if (patient.patient_id === currentPatientId.value) return
  try {
    await patientStore.switchPatient(patient.patient_id)
  } catch {
    showToast('切换患者失败，请稍后重试')
  }
}

async function handleDelete(conv) {
  try {
    await showDialog({
      title: '确认删除',
      message: '仅删除 OncoPath 本地会诊记录，AgentTeams 中的远端分析仍会保留。确定删除吗？',
      showCancelButton: true,
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      confirmButtonColor: 'var(--danger-color)'
    })
    const result = await conversationsStore.deleteConversation(conv.id)
    if (result.success) {
      showToast('已删除')
    } else {
      showToast(result.error || '删除失败')
    }
  } catch {
    // 用户取消对话框
  }
}

async function handleStartConsultation() {
  if (agentTeamsAvailabilityLoading.value) return

  agentTeamsAvailabilityLoading.value = true
  try {
    const availability = await consultationApi.getAgentTeamsAvailability()
    agentTeamsCtaUrl.value = availability.upsell?.cta_url || ''
    if (!availability.configured || !availability.enabled) {
      agentTeamsUpsell.value = availability.upsell || {}
      showAgentTeamsUpsell.value = true
      return
    }
  } catch {
    showToast('无法检查 AgentTeams 配置，请稍后重试')
    return
  } finally {
    agentTeamsAvailabilityLoading.value = false
  }

  // 确保有患者列表
  if (patientStore.patientList.length === 0) {
    await patientStore.fetchPatientList()
  }

  // 优先使用当前已选中患者直接开始
  if (patientStore.currentPatient) {
    selectedPatientId.value = patientStore.currentPatient.patient_id || patientStore.currentPatient.id
    await confirmStartConsultation()
    return
  }

  // 没有当前患者但只有一个患者，直接选择
  if (patientStore.patientList.length === 1) {
    selectedPatientId.value = patientStore.patientList[0].patient_id || patientStore.patientList[0].id
    await confirmStartConsultation()
    return
  }

  // 多个患者且无当前选中，弹出选择
  selectedPatientId.value = null
  showPatientPicker.value = true
}

function handleAgentTeamsUpsellCta(url) {
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function confirmStartConsultation() {
  if (!selectedPatientId.value) {
    showToast('请选择患者')
    return
  }
  if (agentTeamsStartLoading.value) return

  showPatientPicker.value = false
  agentTeamsStartLoading.value = true

  try {
    const result = await consultationApi.startAgentTeamsConsultation(selectedPatientId.value)
    await conversationsStore.fetchConversations(pageSize, 0, false, selectedPatientId.value)
    currentPage.value = 1
    router.push({
      path: `/home/consultation/${result.conversation_id}`,
      query: { patient_id: selectedPatientId.value },
    })
  } catch (error) {
    if (isAgentTeamsError(error)) {
      agentTeamsError.value = getAgentTeamsErrorUx(error, { ctaUrl: agentTeamsCtaUrl.value })
      showAgentTeamsError.value = true
    } else if (!error?.handled) {
      showToast('启动 AgentTeams 会诊失败，请稍后重试')
    }
  } finally {
    agentTeamsStartLoading.value = false
  }
}

onMounted(async () => {
  if (!patientStore.loaded) {
    await patientStore.fetchPatientList()
  }
  await loadFirstPage()
})

watch(currentPatientId, async (patientId, previousPatientId) => {
  if (patientId === previousPatientId) return
  if (!patientId) {
    // 当前患者被清空（如删除最后一个患者），清空会诊列表
    conversationsStore.clearConversations()
    currentPage.value = 0
    return
  }
  if (!previousPatientId) return  // 从无到有，由 onMounted 负责首次加载
  await loadFirstPage()
})
</script>

<style scoped>
.consultation-list {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
}

.consultation-list :deep(.van-nav-bar) {
  background: var(--bg-surface-alpha);
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  z-index: 10;
}

.consultation-list :deep(.van-nav-bar__title) {
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
}

.consultation-list :deep(.van-nav-bar__text) {
  color: var(--primary-color);
}

.consultation-list :deep(.van-icon-arrow-left) {
  color: var(--primary-color);
}

.consultation-list.is-desktop {
  padding-bottom: 0;
}

.mobile-patient-context {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin: 0 var(--space-3) var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.mobile-patient-context span,
.patient-filter-button {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.mobile-patient-context button {
  border: 0;
  background: transparent;
  color: var(--primary-color);
  font-size: var(--text-sm);
  cursor: pointer;
}

/* ===== 移动端卡片 ===== */
.consultation-card {
  padding: var(--space-3) var(--space-4);
  padding-left: calc(var(--space-4) + var(--category-bar-width));
  margin: var(--space-2) var(--space-3);
  background: var(--glass-bg);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: var(--card-transition);
  position: relative;
  overflow: hidden;
}

.consultation-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--category-bar-width);
  background: var(--primary-color);
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}

.consultation-card.status-completed::before { background: var(--success-color); }
.consultation-card.status-error::before { background: var(--danger-color); }
.consultation-card.status-analyzing::before { background: var(--warning-color); }

.consultation-card:active {
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.card-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.status-tag {
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: 10px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
}

.status-tag.status-new { background: var(--primary-alpha-10); color: var(--primary-color); }

.status-tag.status-analyzing {
  background: var(--status-info-bg);
  color: var(--info-color);
}

.status-tag.status-analyzing::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  margin-right: 4px;
  animation: statusPulse 1.5s ease-in-out infinite;
}

.status-tag.status-completed { background: var(--status-normal-bg); color: var(--success-color); }
.status-tag.status-error { background: var(--status-danger-bg); color: var(--danger-color); }

.card-body {
  margin-top: var(--space-1);
}

.card-preview {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  margin-top: var(--space-1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.card-patient,
.detail-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
}

.card-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.start-button {
  position: fixed;
  bottom: calc(90px + env(safe-area-inset-bottom, 0px));
  right: var(--space-4);
  z-index: var(--z-float);
}

.empty-button {
  min-width: 160px;
  padding: 12px 24px;
}

.patient-picker {
  padding: var(--space-3);
  max-height: 60vh;
  overflow-y: auto;
}

.patient-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s;
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--text-primary);
  text-align: left;
}

.patient-item:active,
.patient-item.active {
  background: var(--bg-elevated);
}

.patient-item span {
  flex: 1;
  font-size: var(--text-sm);
}

.picker-footer {
  padding: var(--space-3) 0 0;
}

.delete-button {
  height: 100%;
}

/* ===== 桌面端头部（与其他视图统一） ===== */
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
  gap: var(--space-4);
}

/* ===== 桌面端工具栏 ===== */
.desktop-toolbar {
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-3) var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.desktop-search {
  flex: 0 1 320px;
}

.patient-filter-button {
  min-width: 140px;
  max-width: 220px;
  height: 36px;
  padding: 0 var(--space-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--text-primary);
  cursor: pointer;
}

.patient-filter-button span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.desktop-search :deep(.van-search__content) {
  background: var(--bg-elevated);
}

.filter-tabs {
  display: flex;
  gap: var(--space-1);
}

.filter-tab {
  padding: var(--space-1) var(--space-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.filter-tab:hover {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.filter-tab.active {
  background: var(--primary-color);
  color: var(--bg-surface);
  border-color: var(--primary-color);
}

/* ===== 桌面端列表 ===== */
.desktop-list {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 var(--space-6);
}

.conversation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-3);
}

.desktop-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  padding-left: calc(var(--space-4) + var(--category-bar-width));
  cursor: pointer;
  transition: var(--card-transition);
  position: relative;
  overflow: hidden;
}

.desktop-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--category-bar-width);
  background: var(--primary-color);
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}

.desktop-card.status-completed::before { background: var(--success-color); }
.desktop-card.status-error::before { background: var(--danger-color); }
.desktop-card.status-analyzing::before { background: var(--warning-color); }

.desktop-card:hover {
  transform: translateY(var(--card-hover-lift));
  box-shadow: var(--card-hover-shadow);
  border-color: transparent;
}

.desktop-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2);
}

.desktop-card-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.desktop-card-body {
  margin-top: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.desktop-card-footer {
  margin-top: var(--space-3);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.detail-link {
  color: var(--primary-color);
}

.card-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.load-more-area {
  display: flex;
  justify-content: center;
  padding: var(--space-4) 0;
}

.no-more {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}
</style>
