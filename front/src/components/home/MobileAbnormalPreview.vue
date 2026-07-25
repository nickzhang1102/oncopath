<template>
  <div class="mobile-abnormal-preview">
    <div class="preview-header">
      <van-icon name="warning-o" size="16" color="var(--danger-color)" />
      <span class="preview-title">异常指标</span>
      <van-tag v-if="data.abnormal_indicator_count > 0" type="danger" size="small">
        {{ data.abnormal_indicator_count }}
      </van-tag>
    </div>

    <!-- 有异常 -->
    <div v-if="data.abnormal_indicators?.length > 0" class="indicator-list">
      <div
        v-for="item in data.abnormal_indicators.slice(0, 3)"
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
      <div v-if="data.abnormal_indicator_count > 3" class="view-all" @click="$emit('go-abnormal')">
        查看全部 {{ data.abnormal_indicator_count }} 项异常
        <van-icon name="arrow" size="12" />
      </div>
    </div>

    <!-- 无异常 -->
    <div v-else class="normal-hint">
      <van-icon name="checked" size="18" color="var(--success-color)" />
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
.mobile-abnormal-preview {
  background: var(--bg-surface-alpha);
  padding: 12px 16px;
  border-radius: var(--radius-xl);
  box-shadow: 0 4px 16px var(--primary-alpha-10);
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.preview-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--danger-color);
  flex: 1;
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
  padding: 6px 10px;
  border-radius: var(--radius-md);
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

.view-all {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 0 2px;
  font-size: 12px;
  color: var(--primary-color);
  cursor: pointer;
}

.normal-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 0;
  color: var(--success-color);
  font-size: 13px;
}
</style>