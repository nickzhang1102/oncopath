<template>
  <div class="dashboard-card abnormal-summary">
    <div class="card-header">
      <van-icon name="warning-o" class="header-icon" />
      <span class="header-title">异常指标</span>
      <van-tag v-if="data.abnormal_indicator_count > 0" type="danger" size="small">
        {{ data.abnormal_indicator_count }}
      </van-tag>
    </div>
    <div v-if="data.abnormal_indicators?.length > 0" class="indicator-list">
      <div
        v-for="item in data.abnormal_indicators"
        :key="item.index_name"
        class="indicator-item"
        @click="$emit('go-abnormal')"
      >
        <span class="indicator-name">{{ item.index_name }}</span>
        <span class="indicator-value" :class="statusClass(item.index_status)">
          {{ item.index_value }}
          <span v-if="item.index_unit" class="indicator-unit">{{ item.index_unit }}</span>
        </span>
      </div>
    </div>
    <div v-else class="empty-hint">
      <van-icon name="checked" size="20" color="var(--success-color)" />
      <span>指标正常</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  data: { type: Object, required: true },
})

defineEmits(['go-abnormal'])

function statusClass(status) {
  return { high: 'status-high', low: 'status-low', abnormal: 'status-high' }[status] || ''
}
</script>

<style scoped>
.header-icon {
  color: var(--danger-color);
}

.header-title {
  color: var(--danger-color);
}

.indicator-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.indicator-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--primary-alpha-3);
  cursor: pointer;
  transition: background 0.2s;
}

.indicator-item:active {
  background: var(--primary-alpha-8);
}

.indicator-name {
  font-size: 13px;
  color: var(--text-primary);
}

.indicator-value {
  font-size: 13px;
  font-weight: 600;
}

.indicator-unit {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-left: 2px;
}

.status-high {
  color: var(--danger-color);
}

.status-low {
  color: var(--warning-color);
}

.empty-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px;
  color: var(--success-color);
  font-size: 13px;
}
</style>