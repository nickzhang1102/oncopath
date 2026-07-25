<template>
  <div class="mobile-stats-row">
    <div
      v-for="item in stats"
      :key="item.key"
      class="stat-item"
      @click="$emit('go', item.path)"
    >
      <span class="stat-value">{{ item.value }}</span>
      <span class="stat-label">{{ item.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { DASHBOARD_STATS_CONFIG } from '@/styles/dashboard-stats'

const props = defineProps({
  data: { type: Object, required: true },
})

defineEmits(['go'])

const stats = computed(() =>
  DASHBOARD_STATS_CONFIG.map(item => ({
    key: item.key,
    label: item.label,
    value: props.data[item.valueKey] ?? 0,
    path: item.path,
  }))
)
</script>

<style scoped>
.mobile-stats-row {
  display: flex;
  background: var(--bg-surface-alpha);
  padding: 10px 8px;
  border-radius: var(--radius-xl);
  box-shadow: 0 4px 16px var(--primary-alpha-10);
}

.stat-item {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 2px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s;
  min-height: 44px;
  justify-content: center;
}

.stat-item:active {
  background: var(--primary-alpha-8);
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--primary-color);
  line-height: 1.2;
}

.stat-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

@media (max-width: 340px) {
  .mobile-stats-row {
    flex-wrap: wrap;
    gap: 4px;
  }
  .stat-item {
    flex-basis: 30%;
  }
  .stat-value {
    font-size: 16px;
  }
}
</style>