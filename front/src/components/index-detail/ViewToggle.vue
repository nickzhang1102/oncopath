<template>
  <div class="toggle-section">
    <div class="toggle-buttons">
      <button
        :class="['toggle-btn', { active: modelValue === 'table' }]"
        @click="$emit('update:modelValue', 'table')"
      >
        <van-icon name="list-switch" />
        表格数据
      </button>
      <button
        :class="['toggle-btn', { active: modelValue === 'chart' }]"
        @click="$emit('update:modelValue', 'chart')"
      >
        <van-icon name="chart-trending-o" />
        趋势图表
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true
  }
});

defineEmits(['update:modelValue']);
</script>

<style scoped>
.toggle-section {
  margin-bottom: 16px;
  position: relative;
  z-index: 2;
}

.toggle-buttons {
  display: flex;
  gap: 12px;
}

.toggle-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border: 1px solid var(--primary-alpha-30);
  background: var(--bg-surface);
  border-radius: 999px;
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
  cursor: pointer;
  transition: all 0.3s ease;
}

.toggle-btn.active {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: white;
  border: none;
}

.toggle-btn:hover:not(.active) {
  background: var(--bg-elevated);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .toggle-btn {
    font-size: 12px;
    padding: 10px 12px;
  }
}

@media (max-width: 480px) {
  .toggle-buttons {
    padding: 3px;
  }

  .toggle-btn {
    font-size: 12px;
    padding: 8px 10px;
    gap: 4px;
  }
}
</style>
