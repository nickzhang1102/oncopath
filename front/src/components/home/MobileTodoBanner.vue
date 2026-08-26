<template>
  <div v-if="todoCount > 0" class="mobile-todo-banner">
    <div class="todo-header">
      <van-icon name="todo-list-o" size="14" color="var(--warning-color)" />
      <span class="todo-title">待办提醒</span>
      <van-tag type="warning" size="small">{{ todoCount }}</van-tag>
    </div>
    <div class="todo-tags">
      <div v-if="data.pending_review_count > 0" class="todo-tag" @click="$emit('go-pending-review')">
        <van-icon name="photo-o" size="13" />
        <span>OCR待确认</span>
        <van-tag type="warning" size="small">{{ data.pending_review_count }}</van-tag>
      </div>
      <div v-if="data.ongoing_consultation_count > 0" class="todo-tag" @click="$emit('go-consultation')">
        <van-icon name="chat-o" size="13" />
        <span>进行中会诊</span>
        <van-tag type="primary" size="small">{{ data.ongoing_consultation_count }}</van-tag>
      </div>
    </div>
  </div>
  <div v-else class="mobile-todo-banner mobile-todo-banner--empty">
    <van-icon name="checked" size="16" color="var(--success-color)" />
    <span class="empty-text">暂无待办</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
})

defineEmits(['go-pending-review', 'go-consultation'])

const todoCount = computed(() =>
  (props.data.pending_review_count || 0)
  + (props.data.ongoing_consultation_count || 0)
)
</script>

<style scoped>
.mobile-todo-banner {
  background: var(--bg-surface-alpha);
  padding: 12px 16px;
  border-radius: var(--radius-xl);
  box-shadow: 0 4px 16px var(--primary-alpha-10);
}

.mobile-todo-banner--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 16px;
}

.empty-text {
  font-size: 13px;
  color: var(--success-color);
}

.todo-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.todo-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--warning-color);
  flex: 1;
}

.todo-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.todo-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: var(--radius-md);
  background: var(--primary-alpha-3);
  font-size: 12px;
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.2s;
  min-height: 32px;
}

.todo-tag:active {
  background: var(--primary-alpha-8);
}
</style>