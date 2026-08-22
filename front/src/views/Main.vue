<template>
  <div class="main-view" :class="{ 'has-sidebar': isDesktop }">
    <!-- 动态背景动画 -->
    <BackgroundAnimation />

    <!-- 内容区域 -->
    <div class="content-section">
      <!-- 新用户引导 -->
      <OnboardingGuide />

      <!-- LLM 未配置提醒 -->
      <LLMConfigPrompt />

      <!-- 桌面端患者切换器 -->
      <PatientSwitcher v-if="isDesktop" />

      <!-- 桌面端仪表盘布局 -->
      <template v-if="isDesktop">
        <!-- 桌面端搜索入口 -->
        <div class="desktop-search-entry" data-tour="search" @click="router.push('/home/search')">
          <van-icon name="search" size="20" />
          <span>搜索指标、药品、报告...</span>
        </div>
        <div v-if="dashboardData" class="dashboard-grid">
          <DashboardPatientOverview :data="dashboardData" />
          <DashboardStatsGrid :data="dashboardData" data-tour="stats" @go="handleGo" />
          <DashboardAbnormalSummary :data="dashboardData" @go-abnormal="handleGoAbnormal" />
          <DashboardTodoList
            :data="dashboardData"
            @go-pending-review="handleGoPendingReview"
            @go-consultation="handleGoConsultation"
            @go-reminders="handleGoReminders"
          />
        </div>
        <IndicatorSection data-tour="indicators" />
      </template>

      <!-- 移动端布局 -->
      <template v-if="!isDesktop">
        <QuickActionBar data-tour="quick-actions" @action="handleAction" />
        <template v-if="dashboardData">
          <MobilePatientBanner :data="dashboardData" />
          <MobileStatsRow :data="dashboardData" data-tour="stats" @go="handleGo" />
          <MobileTodoBanner
            :data="dashboardData"
            @go-pending-review="handleGoPendingReview"
            @go-consultation="handleGoConsultation"
            @go-reminders="handleGoReminders"
          />
          <MobileAbnormalPreview :data="dashboardData" @go-abnormal="handleGoAbnormal" />
        </template>
        <IndicatorSection data-tour="indicators" />
        <FeatureGrid title="医疗管理" :items="medicalItems" data-tour="features" />
        <FeatureGrid title="智能工具" :items="toolItems" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, onActivated, watch, nextTick, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import { dashboardApi } from '@/api/dashboard'
import { useResponsive } from '@/composables/useResponsive'
import {
  MEDICAL_NAV_ITEMS, AI_NAV_ITEMS,
  MANAGEMENT_NAV_ITEMS, OTHER_NAV_ITEMS,
} from '@/styles/navigation'

const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import QuickActionBar from '@/components/home/QuickActionBar.vue'
import FeatureGrid from '@/components/home/FeatureGrid.vue'
import IndicatorSection from '@/components/home/IndicatorSection.vue'
import PatientSwitcher from '@/components/PatientSwitcher.vue'
import MobilePatientBanner from '@/components/home/MobilePatientBanner.vue'
import MobileStatsRow from '@/components/home/MobileStatsRow.vue'
import MobileTodoBanner from '@/components/home/MobileTodoBanner.vue'
import MobileAbnormalPreview from '@/components/home/MobileAbnormalPreview.vue'
import DashboardPatientOverview from '@/components/dashboard/DashboardPatientOverview.vue'
import DashboardStatsGrid from '@/components/dashboard/DashboardStatsGrid.vue'
import DashboardAbnormalSummary from '@/components/dashboard/DashboardAbnormalSummary.vue'
import DashboardTodoList from '@/components/dashboard/DashboardTodoList.vue'
import OnboardingGuide from '@/components/home/OnboardingGuide.vue'
import LLMConfigPrompt from '@/components/home/LLMConfigPrompt.vue'

const router = useRouter()
const patientStore = usePatientStore()
const { isDesktop } = useResponsive()

// 移动端FeatureGrid: 医疗管理（与桌面侧边栏完全一致）
const medicalItems = MEDICAL_NAV_ITEMS

// 移动端FeatureGrid: 智能工具+管理工具+其他（合并展示）
const toolItems = [...AI_NAV_ITEMS, ...MANAGEMENT_NAV_ITEMS, ...OTHER_NAV_ITEMS]

const dashboardData = ref(null)
let lastRefreshTime = 0
const REFRESH_THROTTLE_MS = 30000 // 30秒节流

// 处理操作栏点击
function handleAction(action) {
  // action 已通过 router.push 处理
}

function handleGo(path) {
  router.push(path)
}

function handleGoAbnormal() {
  router.push('/home/abnormal-indicators')
}

function handleGoPendingReview() {
  router.push('/home/image-report?tab=list&ocr_status=pending_review')
}

function handleGoConsultation() {
  router.push('/home/consultation')
}

function handleGoReminders() {
  router.push('/home/profile/notifications?tab=reminders')
}

// 刷新数据（桌面端和移动端统一加载）
async function refreshData() {
  if (!patientStore.currentPatient) return

  try {
    dashboardData.value = await dashboardApi.getDashboard(
      patientStore.currentPatient.patient_id
    )
  } catch (err) {
    console.error('加载仪表盘数据失败:', err)
  }
}

// 监听患者变化
watch(() => patientStore.currentPatient?.patient_id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    await nextTick()
    refreshData()
  }
})

// 页面激活时刷新
onMounted(async () => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
  await refreshData()
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

// keep-alive 页面重新激活时刷新数据
onActivated(async () => {
  await refreshData()
})

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    const now = Date.now()
    if (now - lastRefreshTime > REFRESH_THROTTLE_MS) {
      lastRefreshTime = now
      refreshData()
    }
  }
}
</script>

<style scoped>
.main-view {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 16px;
  position: relative;
  padding-bottom: var(--safe-bottom);
  box-sizing: border-box;
}

.content-section {
  position: relative;
  z-index: 2;
  padding-bottom: 20px;
}

/* 移动端垂直布局间距 */
.content-section > :not(:first-child) {
  margin-top: var(--space-4);
}

/* 仪表盘网格 */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  margin-top: var(--space-4);
}

/* 桌面端搜索入口 */
.desktop-search-entry {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-4);
  padding: 12px 16px;
  background: var(--bg-surface-alpha);
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-tertiary);
}

.desktop-search-entry:hover {
  background: var(--primary-alpha-5);
  box-shadow: 0 4px 12px var(--primary-alpha-12);
}

.desktop-search-entry span {
  font-size: var(--text-sm);
}

/* 响应式调整 */
@media (max-width: 480px) {
  .main-view {
    padding: 12px;
  }
}

@media (min-width: 768px) {
  .main-view {
    padding: var(--space-6);
    padding-bottom: var(--space-6);
    max-width: 1280px;
    margin: 0 auto;
  }

  .content-section {
    /* 桌面端单列流式，仅 dashboard-grid 负责 grid 布局 */
  }

  .dashboard-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (min-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr 1fr 1fr;
  }
}
</style>