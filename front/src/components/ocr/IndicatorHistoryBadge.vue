<template>
  <div v-if="history" class="indicator-history-badge" @click.stop="showPopup = true">
    <span class="trend-icon" :class="`trend-${history.trend}`">
      {{ trendIcon }}
    </span>
    <span v-if="lastValue" class="last-value">{{ lastValue }}</span>

    <van-popup
      v-model:show="showPopup"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :closeable="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <div class="history-popup">
        <div class="popup-title">{{ history.index_name }} 历史趋势</div>
        <div class="history-list">
          <div v-for="(item, i) in history.history" :key="i" class="history-item">
            <span class="history-date">{{ item.medical_date }}</span>
            <span class="history-value" :class="`status-${item.index_status}`">
              {{ item.index_value }} {{ item.index_unit }}
            </span>
            <span class="history-hospital">{{ item.hospital }}</span>
          </div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import indicatorHistoryApi from '@/api/indicatorHistory'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop } = useResponsive()

const props = defineProps({
  indexName: { type: String, required: true },
  patientId: { type: Number, required: true },
})

const history = ref(null)
const showPopup = ref(false)

const trendIcon = computed(() => {
  return { up: '↑', down: '↓', stable: '→', unknown: '' }[history.value?.trend] || ''
})

const lastValue = computed(() => {
  const h = history.value?.history
  if (!h || h.length === 0) return ''
  return `${h[0].index_value}${h[0].index_unit || ''}`
})

onMounted(async () => {
  try {
    history.value = await indicatorHistoryApi.getHistory({
      patient_id: props.patientId,
      index_name: props.indexName,
      limit: 5,
    })
    if (!history.value?.history?.length) history.value = null
  } catch {
    // 静默失败
  }
})
</script>

<style scoped>
.indicator-history-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--primary-alpha-8);
  cursor: pointer;
  font-size: 12px;
}

.trend-icon { font-weight: 700; }
.trend-up { color: var(--danger-color); }
.trend-down { color: var(--info-color); }
.trend-stable { color: var(--success-color); }
.last-value { color: var(--text-secondary); }

.history-popup { padding: 20px; max-height: 60vh; overflow-y: auto; }
.popup-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; text-align: center; }
.history-list { display: flex; flex-direction: column; gap: 12px; }
.history-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border-dark); }
.history-date { font-size: 13px; color: var(--text-secondary); }
.history-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.status-high { color: var(--danger-color); }
.status-low { color: var(--info-color); }
.status-abnormal { color: var(--warning-color); }
.history-hospital { font-size: 12px; color: var(--text-tertiary); }
</style>