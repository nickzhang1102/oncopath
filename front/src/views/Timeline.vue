<template>
  <div class="timeline-view">
    <!-- 统一页面抬头 -->
    <BackButton title="治疗时间线" />

    <!-- 过滤器区域 -->
    <div class="filter-section">
      <!-- 日期范围快捷按钮 -->
      <div class="date-range-bar">
        <div class="date-shortcuts">
          <span
            v-for="opt in dateShortcuts"
            :key="opt.label"
            class="shortcut-btn"
            :class="{ active: isActiveShortcut(opt) }"
            @click="onDateShortcut(opt)"
          >{{ opt.label }}</span>
        </div>
        <span class="custom-date-btn" @click="showDatePicker = true">
          <van-icon name="calendar-o" size="14" />
          {{ dateRangeLabel }}
        </span>
      </div>

      <FilterChips
        :groups="timelineStore.filterGroups"
        @toggle="timelineStore.toggleFilter"
        @reset-group="onResetGroup"
      />

      <!-- 导出按钮 -->
      <div class="export-bar">
        <van-button
          class="export-btn"
          size="small"
          plain
          round
          icon="description"
          :loading="exporting"
          @click="handleExportTimeline"
        >
          导出 PDF
        </van-button>
      </div>
    </div>

    <!-- 过滤提示条（有排除项或日期范围时显示） -->
    <div v-if="hasDisabledFilters || timelineStore.dateRange" class="filter-hint">
      <span class="hint-text">
        <template v-if="timelineStore.dateRange">
          {{ dateRangeDisplay }} ·
        </template>
        已隐藏 {{ disabledCount }} 项，
        共 {{ timelineStore.filteredItems.length }} / {{ timelineStore.timelineItems.length }} 条
      </span>
      <span class="hint-action" @click="clearAllFilters">清除筛选</span>
    </div>

    <!-- 日期选择器 -->
    <van-popup
      v-model:show="showDatePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="pickerStartDate"
        title="开始日期"
        :min-date="minDate"
        :max-date="maxDate"
        @confirm="onStartDateConfirm"
        @cancel="showDatePicker = false"
      />
    </van-popup>
    <van-popup
      v-model:show="showEndDatePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="pickerEndDate"
        title="结束日期"
        :min-date="minDate"
        :max-date="maxDate"
        @confirm="onEndDateConfirm"
        @cancel="showEndDatePicker = false"
      />
    </van-popup>

    <!-- 加载状态 -->
    <van-loading v-if="loading" class="loading-center" />

    <!-- 空状态 -->
    <van-empty v-else-if="timelineStore.filteredItems.length === 0 && !loading" description="暂无记录" />

    <!-- 时间线列表 -->
    <van-pull-refresh v-else v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loadingMore"
        :finished="!timelineStore.hasMore"
        finished-text="没有更多了"
        @load="onLoadMore"
      >
        <div class="timeline-list">
          <template v-for="(item, index) in timelineStore.filteredItems" :key="item.id">
            <!-- 日期分组头 -->
            <div v-if="isFirstInMonth(item, index)" class="date-group-header">
              <span class="date-line"></span>
              <span class="date-text">{{ formatDateGroup(item.event_date) }}</span>
              <span class="date-line"></span>
            </div>

            <!-- 按类型分发卡片 -->
            <TimelineEventCard
              v-if="item.source_type === 'timeline_event'"
              :item="item"
              @click="handleItemClick"
            />
            <MedicalCheckCard
              v-else-if="item.source_type === 'medical_check'"
              :item="item"
              @click="handleItemClick"
            />
            <MedicalExamCard
              v-else-if="item.source_type === 'medical_exam'"
              :item="item"
              @click="handleItemClick"
            />
            <PathologyReportCard
              v-else-if="item.source_type === 'pathology_report'"
              :item="item"
              @click="handleItemClick"
            />
            <MedicationCard
              v-else-if="item.source_type === 'medication'"
              :item="item"
              @click="handleItemClick"
            />
          </template>
        </div>
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { useTimelineStore } from '@/stores/timeline'
import { useResponsive } from '@/composables/useResponsive'
import { exportApi } from '@/api/export'
import { downloadBlob } from '@/utils/export'
import { getNavigationTarget } from '@/utils/timelineNavigation'
import FilterChips from '@/components/timeline/FilterChips.vue'
import BackButton from '@/components/index-detail/BackButton.vue'
import TimelineEventCard from '@/components/timeline/TimelineEventCard.vue'
import MedicalCheckCard from '@/components/timeline/MedicalCheckCard.vue'
import MedicalExamCard from '@/components/timeline/MedicalExamCard.vue'
import PathologyReportCard from '@/components/timeline/PathologyReportCard.vue'
import MedicationCard from '@/components/timeline/MedicationCard.vue'
import dayjs from 'dayjs'

const router = useRouter()
const patientStore = usePatientStore()
const timelineStore = useTimelineStore()
const { isDesktop } = useResponsive()

const loading = ref(false)
const refreshing = ref(false)
const loadingMore = ref(false)

// ===== 日期范围筛选 =====
const showDatePicker = ref(false)
const showEndDatePicker = ref(false)
const pendingStartDate = ref(null)
const exporting = ref(false)

const minDate = new Date(2020, 0, 1)
const maxDate = new Date()

const pickerStartDate = ref(['2024', '01', '01'])
const pickerEndDate = ref(dayjs().format('YYYY-MM-DD').split('-'))

const dateShortcuts = [
  { label: '全部', months: 0 },
  { label: '1月', months: 1 },
  { label: '3月', months: 3 },
  { label: '6月', months: 6 },
  { label: '1年', months: 12 },
]

const dateRangeLabel = computed(() => {
  if (timelineStore.dateRange) {
    return `${timelineStore.dateRange.start} ~ ${timelineStore.dateRange.end}`
  }
  return '自定义'
})

const dateRangeDisplay = computed(() => {
  if (!timelineStore.dateRange) return ''
  const { start, end } = timelineStore.dateRange
  return `${start} ~ ${end}`
})

function isActiveShortcut(opt) {
  if (!timelineStore.dateRange && opt.months === 0) return true
  if (!timelineStore.dateRange) return false
  if (opt.months === 0) return false
  const expectedStart = dayjs().subtract(opt.months, 'month').format('YYYY-MM-DD')
  const expectedEnd = dayjs().format('YYYY-MM-DD')
  return timelineStore.dateRange.start === expectedStart && timelineStore.dateRange.end === expectedEnd
}

function onDateShortcut(opt) {
  if (opt.months === 0) {
    timelineStore.clearDateRange()
  } else {
    const end = dayjs().format('YYYY-MM-DD')
    const start = dayjs().subtract(opt.months, 'month').format('YYYY-MM-DD')
    timelineStore.setDateRange(start, end)
  }
  loadData()
}

function onStartDateConfirm({ selectedValues }) {
  pendingStartDate.value = selectedValues.join('-')
  showDatePicker.value = false
  showEndDatePicker.value = true
}

function onEndDateConfirm({ selectedValues }) {
  const end = selectedValues.join('-')
  if (pendingStartDate.value && end) {
    // 确保 start <= end
    const [s, e] = pendingStartDate.value <= end
      ? [pendingStartDate.value, end]
      : [end, pendingStartDate.value]
    timelineStore.setDateRange(s, e)
    loadData()
  }
  showEndDatePicker.value = false
  pendingStartDate.value = null
}

// 过滤状态计算
const hasDisabledFilters = computed(() => timelineStore.disabledFilters.size > 0)

const disabledCount = computed(() => {
  const total = timelineStore.timelineItems.length
  const filtered = timelineStore.filteredItems.length
  return total - filtered
})

function clearAllFilters() {
  timelineStore.selectAll()
  timelineStore.clearDateRange()
  loadData()
}

async function handleExportTimeline() {
  const patientId = patientStore.currentPatient?.patient_id
  if (!patientId) {
    showToast('请先选择患者')
    return
  }

  exporting.value = true
  try {
    const blob = await exportApi.exportTimeline(patientId)
    const ok = await downloadBlob(blob, `timeline_${patientId}.pdf`)
    if (ok) showToast('导出成功')
  } catch {
    showToast('导出失败')
  } finally {
    exporting.value = false
  }
}

// 重置分组
function onResetGroup(group) {
  for (const item of group.items) {
    if (item.disabled) {
      timelineStore.toggleFilter(item.key)
    }
  }
}

function handleItemClick(item) {
  const target = getNavigationTarget(item)
  if (target) {
    router.push(target)
  }
}

// 日期分组判断
function isFirstInMonth(item, index) {
  if (index === 0) return true
  const prevItem = timelineStore.filteredItems[index - 1]
  return getMonthKey(item.event_date) !== getMonthKey(prevItem.event_date)
}

function getMonthKey(dateStr) {
  if (!dateStr) return ''
  return dateStr.substring(0, 7) // YYYY-MM
}

function formatDateGroup(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getFullYear()}年${d.getMonth() + 1}月`
}

// 数据加载
async function loadData() {
  if (!patientStore.currentPatient) return
  loading.value = true
  try {
    await timelineStore.fetchTimeline(patientStore.currentPatient.patient_id)
  } finally {
    loading.value = false
  }
}

async function onRefresh() {
  try {
    await loadData()
  } finally {
    refreshing.value = false
  }
}

async function onLoadMore() {
  if (!patientStore.currentPatient || !timelineStore.hasMore) {
    loadingMore.value = false
    return
  }
  try {
    await timelineStore.fetchTimeline(patientStore.currentPatient.patient_id, { loadMore: true })
  } catch (error) {
    console.error('加载更多失败:', error)
  } finally {
    loadingMore.value = false
  }
}

// 生命周期
onMounted(async () => {
  await loadData()
})

// 监听患者变化
watch(() => patientStore.currentPatient?.patient_id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    await loadData()
  }
})
</script>

<style scoped>
.timeline-view {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
  box-sizing: border-box;
}

/* 过滤器区域 */
.filter-section {
  padding: 12px 16px;
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--bg-primary);
}

/* 日期范围栏 */
.date-range-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.date-shortcuts {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.shortcut-btn {
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.shortcut-btn:active {
  transform: scale(0.95);
}

.shortcut-btn.active {
  color: var(--primary-color);
  background: var(--primary-alpha-10);
  border-color: var(--primary-alpha-20);
  font-weight: 500;
}

.custom-date-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.custom-date-btn:active {
  transform: scale(0.95);
}

/* 导出按钮 */
.export-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

.export-btn {
  font-size: 12px;
}

/* 过滤提示条 */
.filter-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 20px;
  background: var(--primary-alpha-6);
  font-size: 12px;
}

.hint-text {
  color: var(--text-secondary);
}

.hint-action {
  color: var(--primary-color);
  font-weight: 500;
  cursor: pointer;
}

.hint-action:active {
  opacity: 0.7;
}

/* 加载状态 */
.loading-center {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}

/* 时间线列表 */
.timeline-list {
  padding: 0 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 日期分组头 */
.date-group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0 4px;
}

.date-line {
  flex: 1;
  height: 1px;
  background: var(--primary-alpha-15);
}

.date-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--primary-color);
  white-space: nowrap;
}

/* 响应式 */
@media (min-width: 768px) {
  .timeline-view {
    padding-bottom: var(--space-6);
  }

  .filter-section {
    max-width: 900px;
    margin: 0 auto;
  }

  .timeline-list {
    max-width: 900px;
    margin: 0 auto;
    padding: 0 24px 24px;
  }
}
</style>
