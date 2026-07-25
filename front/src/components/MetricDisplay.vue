<template>
  <div class="metric-display" :class="`metric-display--${status}`" @click="handleClick">
    <div class="metric-display__header">
      <span class="metric-display__name">{{ name }}</span>
      <span v-if="unit" class="metric-display__unit">{{ unit }}</span>
    </div>

    <div class="metric-display__value">
      <span class="metric-display__number" :class="{ 'metric-display__number--large': large }">
        {{ formattedValue }}
      </span>
      <van-tag
        v-if="statusText"
        :type="tagType"
        size="medium"
        round
        class="metric-display__tag"
      >
        {{ statusText }}
      </van-tag>
    </div>

    <div v-if="reference" class="metric-display__reference">
      参考值: {{ reference }}
    </div>

    <div v-if="trend !== undefined" class="metric-display__trend">
      <van-icon
        :name="trend > 0 ? 'arrow-up' : trend < 0 ? 'arrow-down' : 'minus'"
        :color="trendColor"
      />
      <span :style="{ color: trendColor }">{{ Math.abs(trend) }}%</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  value: { type: [Number, String], required: true },
  unit: String,
  reference: String,
  status: {
    type: String,
    default: 'normal',
    validator: (v) => ['normal', 'success', 'warning', 'danger'].includes(v)
  },
  statusText: String,
  trend: Number, // 正数上升,负数下降
  large: Boolean,
  precision: { type: Number, default: 2 }
})

const emit = defineEmits(['click'])

const formattedValue = computed(() => {
  if (typeof props.value === 'number') {
    return props.value.toFixed(props.precision)
  }
  return props.value
})

const tagType = computed(() => {
  const map = { normal: 'primary', success: 'success', warning: 'warning', danger: 'danger' }
  return map[props.status]
})

const trendColor = computed(() => {
  if (props.trend > 0) return 'var(--success-color)'
  if (props.trend < 0) return 'var(--danger-color)'
  return 'var(--text-secondary)'
})

function handleClick(event) {
  emit('click', event)
}
</script>

<style scoped>
.metric-display {
  padding: var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border-left: 4px solid var(--primary-color);
}

.metric-display--success { border-left-color: var(--success-color); }
.metric-display--warning { border-left-color: var(--warning-color); }
.metric-display--danger { border-left-color: var(--danger-color); }

.metric-display__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.metric-display__name {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.metric-display__unit {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.metric-display__value {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.metric-display__number {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
}

.metric-display__number--large {
  font-size: var(--text-3xl);
}

.metric-display__reference {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.metric-display__trend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--space-2);
  font-size: var(--text-sm);
}
</style>
