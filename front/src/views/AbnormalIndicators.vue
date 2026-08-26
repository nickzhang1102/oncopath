<template>
  <div class="abnormal-indicators">
    <!-- 统一页面抬头（标题 + 解释性副标题） -->
    <BackButton title="异常指标" subtitle="追踪偏离参考范围的指标变化" />

    <!-- 日期范围过滤 -->
    <div class="date-filter-section">
      <div class="date-chips">
        <span
          v-for="opt in dateOptions"
          :key="opt.key"
          class="date-chip"
          :class="{ active: activeDateKey === opt.key }"
          @click="onDateChange(opt.key)"
        >{{ opt.label }}</span>
      </div>
      <!-- 自定义日期触发 -->
      <div v-if="activeDateKey === 'custom'" class="custom-date-trigger">
        <span class="date-field" @click="showStartPicker = true">
          {{ customStart || '开始日期' }}
        </span>
        <span class="date-separator">至</span>
        <span class="date-field" @click="showEndPicker = true">
          {{ customEnd || '结束日期' }}
        </span>
        <span v-if="customStart && customEnd" class="apply-btn" @click="applyCustomDate">应用</span>
      </div>
    </div>

    <!-- 自定义日期弹出选择器 -->
    <van-popup
      v-model:show="showStartPicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="customStartDate"
        title="开始日期"
        :min-date="new Date(2000, 0, 1)"
        :max-date="new Date()"
        @confirm="onStartPickerConfirm"
        @cancel="showStartPicker = false"
      />
    </van-popup>
    <van-popup
      v-model:show="showEndPicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="customEndDate"
        title="结束日期"
        :min-date="new Date(2000, 0, 1)"
        :max-date="new Date()"
        @confirm="onEndPickerConfirm"
        @cancel="showEndPicker = false"
      />
    </van-popup>

    <van-loading v-if="loading" class="loading-center" />

    <van-empty v-else-if="!hasData" description="暂无异常指标" />

    <div v-else class="indicator-groups">
      <div
        v-for="group in groupedByDate"
        :key="group.medical_id"
        class="date-group"
      >
        <!-- 日期和医院 -->
        <div class="group-header">
          <span class="group-date">{{ formatDate(group.medical_date) }}</span>
          <span v-if="group.hospital" class="group-hospital">
            <van-icon name="location-o" />
            {{ group.hospital }}
          </span>
        </div>

        <!-- 该日期下的异常指标列表 -->
        <div class="group-items">
          <div
            v-for="indicator in group.items"
            :key="indicator.detail_id || indicator.medical_detail_id"
            class="indicator-item"
            @click="viewHistory(indicator)"
          >
            <div class="indicator-left">
              <span class="indicator-name">{{ indicator.index_name }}</span>
              <span class="indicator-ref">参考: {{ indicator.reference_value }}</span>
            </div>
            <div class="indicator-right">
              <span class="indicator-value" :class="getValueClass(indicator)">
                {{ indicator.index_value }}
              </span>
              <span v-if="indicator.index_unit" class="indicator-unit">{{ indicator.index_unit }}</span>
              <van-tag
                :type="indicator.index_status === 'high' ? 'danger' : 'warning'"
                size="small"
                round
              >
                {{ indicator.index_status === 'high' ? '偏高' : '偏低' }}
              </van-tag>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { useMedicalStore } from '@/stores/medical'
import { useResponsive } from '@/composables/useResponsive'
import BackButton from '@/components/index-detail/BackButton.vue'
import dayjs from 'dayjs'

const { isDesktop } = useResponsive()

const router = useRouter()
const patientStore = usePatientStore()
const medicalStore = useMedicalStore()

const loading = ref(false)

// 日期过滤
const activeDateKey = ref('3m')
const customStart = ref(null)
const customEnd = ref(null)
const customStartDate = ref([])
const customEndDate = ref([])
const showStartPicker = ref(false)
const showEndPicker = ref(false)

const dateOptions = [
  { key: 'all', label: '全部' },
  { key: '1m', label: '1月' },
  { key: '3m', label: '3月' },
  { key: '6m', label: '6月' },
  { key: '1y', label: '1年' },
  { key: 'custom', label: '自定义' },
]

function getDateRange(key) {
  const now = dayjs()
  switch (key) {
    case '1m': return { start: now.subtract(1, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '3m': return { start: now.subtract(3, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '6m': return { start: now.subtract(6, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '1y': return { start: now.subtract(1, 'year').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case 'custom': return { start: customStart.value, end: customEnd.value }
    default: return { start: null, end: null }
  }
}

function onDateChange(key) {
  activeDateKey.value = key
  if (key !== 'custom') {
    loadAbnormalIndicators()
  }
}

function onStartPickerConfirm({ selectedValues }) {
  if (selectedValues?.length === 3) {
    customStart.value = selectedValues.join('-')
  }
  showStartPicker.value = false
}

function onEndPickerConfirm({ selectedValues }) {
  if (selectedValues?.length === 3) {
    customEnd.value = selectedValues.join('-')
  }
  showEndPicker.value = false
}

function applyCustomDate() {
  if (customStart.value && customEnd.value) {
    loadAbnormalIndicators()
  }
}

const hasData = computed(() => medicalStore.abnormalCount > 0)

// 按医疗记录分组（同一次检查的异常指标归为一组）
const groupedByDate = computed(() => {
  const groups = new Map()

  for (const indicator of medicalStore.abnormalIndicators) {
    const key = `${indicator.medical_id}_${indicator.medical_date}`
    if (!groups.has(key)) {
      groups.set(key, {
        medical_id: indicator.medical_id,
        medical_date: indicator.medical_date,
        hospital: indicator.hospital,
        items: []
      })
    }
    groups.get(key).items.push(indicator)
  }

  // 按日期降序
  return [...groups.values()].sort((a, b) =>
    new Date(b.medical_date) - new Date(a.medical_date)
  )
})

function formatDate(dateStr) {
  return dayjs(dateStr).format('YYYY年MM月DD日')
}

function getValueClass(indicator) {
  return {
    'value--high': indicator.index_status === 'high',
    'value--low': indicator.index_status === 'low'
  }
}

function viewHistory(indicator) {
  if (!indicator.index_id) {
    showToast('该指标未关联标准库，无法查看历史')
    return
  }
  router.push({
    path: '/home/indicator/history',
    query: {
      index_id: indicator.index_id,
      index_name: indicator.indicator_name || indicator.name || indicator.index_name
    }
  })
}

async function loadAbnormalIndicators() {
  if (patientStore.currentPatient) {
    loading.value = true
    try {
      const dateRange = getDateRange(activeDateKey.value)
      await medicalStore.fetchAbnormalIndicators(patientStore.currentPatient.patient_id, {
        start_date: dateRange.start,
        end_date: dateRange.end
      })
    } finally {
      loading.value = false
    }
  }
}

onMounted(loadAbnormalIndicators)

watch(() => patientStore.currentPatient?.patient_id, (newId) => {
  if (newId) loadAbnormalIndicators()
})
</script>

<style scoped>
.abnormal-indicators {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: var(--space-8);
}

/* 日期过滤 */
.date-filter-section {
  margin: 16px;
  margin-top: 8px;
}

.date-chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 0;
}

.date-chip {
  flex-shrink: 0;
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--primary-alpha-15);
}

.date-chip.active {
  background: var(--primary-color);
  color: var(--color-white);
  border-color: var(--primary-color);
}

.custom-date-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.date-field {
  padding: 4px 10px;
  border-radius: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--primary-alpha-15);
  cursor: pointer;
}

.date-separator {
  color: var(--text-tertiary);
}

.apply-btn {
  padding: 4px 10px;
  border-radius: 8px;
  background: var(--primary-color);
  color: var(--color-white);
  cursor: pointer;
}

.indicator-groups {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* 日期分组 */
.date-group {
  background: var(--bg-surface-alpha);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--primary-alpha-5);
  border-bottom: 1px solid var(--primary-alpha-8);
}

.group-date {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
}

.group-hospital {
  font-size: 12px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 指标列表 */
.group-items {
  padding: 4px 0;
}

.indicator-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.indicator-item:hover {
  background: var(--primary-alpha-5);
}

.indicator-item:active {
  background: var(--primary-alpha-10);
}

.indicator-item + .indicator-item {
  border-top: 1px solid var(--primary-alpha-5);
}

.indicator-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.indicator-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.indicator-ref {
  font-size: 12px;
  color: var(--text-tertiary);
}

.indicator-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  margin-left: 12px;
}

.indicator-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.indicator-value.value--high {
  color: var(--danger-color);
}

.indicator-value.value--low {
  color: var(--warning-color);
}

.indicator-unit {
  font-size: 12px;
  color: var(--text-secondary);
}

@media (min-width: 768px) {
  .abnormal-indicators {
    padding: 0 var(--space-6) var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
  }
  .indicator-groups {
    padding: 0;
  }
}
</style>