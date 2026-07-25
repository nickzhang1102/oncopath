<template>
  <div class="timeline-section">
    <!-- 标题和配置按钮 -->
    <div class="section-header">
      <h3 class="section-title">治疗时间线</h3>
      <div class="header-actions">
        <span class="time-range-label">{{ timeRangeLabel }}</span>
        <van-icon name="bars" class="config-btn" @click="showConfig = true" />
      </div>
    </div>

    <!-- 加载状态 -->
    <van-loading v-if="loading" class="loading-center" />

    <!-- 空状态 -->
    <div v-else-if="timelineItems.length === 0" class="empty-state">
      <div class="empty-icon"><van-icon name="todo-list-o" /></div>
      <div class="empty-text">暂无治疗记录</div>
      <div class="empty-hint">点击上方"添加治疗"开始记录</div>
    </div>

    <!-- 时间线内容 -->
    <div v-else class="timeline-content">
      <!-- 按年份分组 -->
      <div v-for="(yearGroup, year) in groupedByYear" :key="year" class="year-group">
        <div class="year-label">{{ year }}年</div>
        
        <!-- 时间线项目 -->
        <div class="timeline-items">
          <div
            v-for="item in yearGroup"
            :key="item.event_id"
            class="timeline-item"
            :class="`timeline-item--${item.category}`"
            @click="handleItemClick(item)"
          >
            <div class="item-dot">
              <span class="item-icon"><van-icon :name="getCategoryIcon(item.category)" /></span>
            </div>
            <div class="item-content">
              <div class="item-header">
                <span class="item-date">{{ formatDate(item.event_date) }}</span>
                <span class="item-title">{{ item.category === 'daily_status' ? getDailyStatusTitle(item) : item.title }}</span>
              </div>
              <div v-if="item.description && item.category !== 'daily_status'" class="item-description">
                {{ item.description }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 时间范围配置弹窗 -->
    <van-popup
      v-model:show="showConfig"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :style="isDesktop ? 'width: 400px; border-radius: var(--radius-lg); overflow: hidden; padding: 20px;' : { padding: '20px' }"
    >
      <div class="config-popup">
        <div class="config-title">选择时间范围</div>
        <van-radio-group v-model="selectedRange">
          <van-cell-group inset>
            <van-cell
              v-for="option in timeRangeOptions"
              :key="option.value"
              :title="option.label"
              clickable
              @click="selectTimeRange(option.value)"
            >
              <template #right-icon>
                <van-radio :name="option.value" />
              </template>
            </van-cell>
          </van-cell-group>
        </van-radio-group>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import { useTimelineStore } from '@/stores/timeline'
import { getNavigationTarget } from '@/utils/timelineNavigation'
import { useResponsive } from '@/composables/useResponsive'
import dayjs from 'dayjs'

const { isDesktop } = useResponsive()

const router = useRouter()
const patientStore = usePatientStore()
const timelineStore = useTimelineStore()

// 状态
const loading = ref(false)
const showConfig = ref(false)
const selectedRange = ref(30) // 默认1个月

// 时间范围选项
const timeRangeOptions = [
  { label: '最近1周', value: 7 },
  { label: '最近2周', value: 14 },
  { label: '最近1个月', value: 30 },
  { label: '最近3个月', value: 90 },
  { label: '最近6个月', value: 180 },
  { label: '最近1年', value: 365 }
]

// 计算属性
const timeRangeLabel = computed(() => {
  const option = timeRangeOptions.find(o => o.value === selectedRange.value)
  return option ? option.label : '最近1个月'
})

const timelineItems = computed(() => {
  return timelineStore.timelineItems || []
})

// 按年份分组
const groupedByYear = computed(() => {
  const groups = {}
  const sortedItems = [...timelineItems.value].sort((a, b) => 
    new Date(b.event_date) - new Date(a.event_date)
  )
  
  sortedItems.forEach(item => {
    const year = new Date(item.event_date).getFullYear()
    if (!groups[year]) {
      groups[year] = []
    }
    groups[year].push(item)
  })
  
  return groups
})

// 方法
function getCategoryIcon(category) {
  const iconMap = {
    chemotherapy: 'gem-o',
    radiation: 'fire-o',
    surgery: 'certificate',
    targeted: 'aim',
    immunotherapy: 'shield-o',
    adc: 'aim',
    car_t: 'shield-o',
    other: 'medical',
    pain: 'warning-o',
    mood: 'smile-o',
    status: 'chart-trending-o',
    diet: 'gift-o',
    sleep: 'closed-eye',
    stool: 'records',
    diagnosis: 'hospital',
    medical: 'hospital',
    life: 'flower-o',
    daily_status: 'todo-list-o'
  }
  return iconMap[category] || 'todo-list-o'
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

// 点击时间线条目跳转
function handleItemClick(item) {
  const target = getNavigationTarget(item)
  if (target) {
    router.push(target)
  }
}

function getDailyStatusTitle(item) {
  if (!item.life_details) return '状态记录'
  const parts = []
  const ld = item.life_details
  parts.push(`疼痛${ld.pain?.score ?? 0}`)
  parts.push(`心情${ld.mood?.score ?? 5}`)
  parts.push(`睡眠${ld.sleep?.score ?? 5}`)
  parts.push(`饮食${ld.diet?.score ?? 5}`)
  const stoolLabels = { normal: '正常', loose: '稀便', constipation: '便秘' }
  parts.push(`大便${stoolLabels[ld.stool?.status] || '正常'}`)
  return parts.join('/')
}

async function selectTimeRange(value) {
  selectedRange.value = value
  showConfig.value = false
  await loadTimeline()
}

async function loadTimeline() {
  if (!patientStore.currentPatient) return
  
  loading.value = true
  try {
    const endDate = dayjs().format('YYYY-MM-DD')
    const startDate = dayjs().subtract(selectedRange.value, 'day').format('YYYY-MM-DD')
    
    await timelineStore.fetchTimeline(patientStore.currentPatient.patient_id, {
      start_date: startDate,
      end_date: endDate
    })
  } finally {
    loading.value = false
  }
}

// 暴露刷新方法
defineExpose({
  refresh: loadTimeline
})

// 生命周期
onMounted(async () => {
  await loadTimeline()
})

// keep-alive 页面重新激活时刷新数据
onActivated(async () => {
  await loadTimeline()
})

// 监听患者变化
watch(() => patientStore.currentPatient?.patient_id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    await loadTimeline()
  }
})
</script>

<style scoped>
.timeline-section {
  background: var(--bg-surface-alpha);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 16px var(--primary-alpha-10);
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--primary-alpha-10);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-range-label {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--primary-alpha-8);
  padding: 4px 8px;
  border-radius: 6px;
}

.config-btn {
  font-size: 18px;
  color: var(--primary-color);
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: background 0.2s;
}

.config-btn:hover {
  background: var(--primary-alpha-10);
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 16px;
  color: var(--primary-color);
  font-weight: 500;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 时间线内容 */
.timeline-content {
  max-height: 400px;
  overflow-y: auto;
}

.year-group {
  margin-bottom: 16px;
}

.year-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 3px solid var(--primary-color);
}

.timeline-items {
  position: relative;
  padding-left: 24px;
}

/* 时间线竖线 */
.timeline-items::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--primary-alpha-20);
}

.timeline-item {
  position: relative;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--primary-alpha-8);
  cursor: pointer;
  transition: background 0.2s;
  border-radius: 8px;
}

.timeline-item:hover {
  background: var(--primary-alpha-5);
}

.timeline-item:active {
  background: var(--primary-alpha-10);
}

.timeline-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.item-dot {
  position: absolute;
  left: -24px;
  top: 4px;
  width: 24px;
  height: 24px;
  background: var(--bg-surface);
  border: 2px solid var(--primary-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.item-icon {
  font-size: 12px;
}

.item-content {
  padding-left: 8px;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.item-date {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--primary-alpha-8);
  padding: 2px 6px;
  border-radius: 4px;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.item-description {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 4px;
}

.item-extra {
  font-size: 12px;
  color: var(--primary-color);
  background: var(--primary-alpha-5);
  padding: 4px 8px;
  border-radius: 6px;
  display: inline-block;
}

/* 配置弹窗 */
.config-popup {
  padding-bottom: 20px;
}

.config-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  text-align: center;
  margin-bottom: 16px;
}

/* 不同类别的样式 */
.timeline-item--chemotherapy .item-dot {
  border-color: var(--color-purple);
}

.timeline-item--radiation .item-dot {
  border-color: var(--warning-color);
}

.timeline-item--surgery .item-dot {
  border-color: var(--danger-color);
}

.timeline-item--mood .item-dot {
  border-color: var(--success-color);
}

.timeline-item--pain .item-dot {
  border-color: var(--danger-color);
}

/* 滚动条样式 */
.timeline-content::-webkit-scrollbar {
  width: 4px;
}

.timeline-content::-webkit-scrollbar-track {
  background: transparent;
}

.timeline-content::-webkit-scrollbar-thumb {
  background: var(--primary-alpha-30);
  border-radius: 2px;
}
</style>