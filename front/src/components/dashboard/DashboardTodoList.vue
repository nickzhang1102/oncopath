<template>
  <div class="dashboard-card todo-list">
    <div class="card-header">
      <van-icon name="todo-list-o" class="header-icon" />
      <span class="header-title">待办提醒</span>
      <van-tag v-if="todoCount > 0" type="warning" size="small">{{ todoCount }}</van-tag>
    </div>
    <div class="todo-items">
      <div v-if="data.pending_review_count > 0" class="todo-item" @click="$emit('go-pending-review')">
        <van-icon name="photo-o" size="16" color="var(--warning-color)" />
        <span class="todo-text">待确认OCR报告</span>
        <van-tag type="warning" size="small">{{ data.pending_review_count }}</van-tag>
      </div>
      <div v-if="data.pending_reminder_count > 0" class="todo-item" @click="$emit('go-reminders')">
        <van-icon name="clock-o" size="16" color="var(--primary-color)" />
        <span class="todo-text">待复查提醒</span>
        <van-tag type="primary" size="small">{{ data.pending_reminder_count }}</van-tag>
      </div>
      <div v-if="data.ongoing_consultation_count > 0" class="todo-item" @click="$emit('go-consultation')">
        <van-icon name="chat-o" size="16" color="var(--info-color)" />
        <span class="todo-text">进行中会诊</span>
        <van-tag type="primary" size="small">{{ data.ongoing_consultation_count }}</van-tag>
      </div>
      <div v-if="todoCount === 0" class="empty-hint">
        <van-icon name="checked" size="20" color="var(--success-color)" />
        <span>暂无待办</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
})

defineEmits(['go-pending-review', 'go-consultation', 'go-reminders'])

const todoCount = computed(() => {
  return (props.data.pending_review_count || 0)
    + (props.data.ongoing_consultation_count || 0)
    + (props.data.pending_reminder_count || 0)
})
</script>

<style scoped>
.header-icon {
  color: var(--warning-color);
}

.header-title {
  color: var(--warning-color);
}

.todo-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--primary-alpha-3);
  cursor: pointer;
  transition: background 0.2s;
}

.todo-item:active {
  background: var(--primary-alpha-8);
}

.todo-text {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
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