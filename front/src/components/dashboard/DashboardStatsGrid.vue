<template>
  <div class="dashboard-card stats-grid">
    <div class="card-header">
      <van-icon name="bar-chart-o" class="header-icon" />
      <span class="header-title">数据统计</span>
    </div>
    <div class="stats-row" v-for="(row, ri) in rows" :key="ri">
      <div
        v-for="item in row"
        :key="item.key"
        class="stat-item"
        @click="$emit('go', item.path)"
      >
        <span class="stat-value">{{ data[item.valueKey] }}</span>
        <span class="stat-label">{{ item.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { DASHBOARD_STATS_CONFIG } from '@/styles/dashboard-stats'

defineProps({
  data: { type: Object, required: true },
})

defineEmits(['go'])

const rows = computed(() => {
  const result = []
  for (let i = 0; i < DASHBOARD_STATS_CONFIG.length; i += 3) {
    result.push(DASHBOARD_STATS_CONFIG.slice(i, i + 3))
  }
  return result
})
</script>

<style scoped>
.stats-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.stats-row:last-child {
  margin-bottom: 0;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 4px;
  border-radius: 8px;
  background: var(--primary-alpha-3);
  cursor: pointer;
  transition: background 0.2s;
}

.stat-item:active {
  background: var(--primary-alpha-8);
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}
</style>