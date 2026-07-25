<template>
  <div class="filter-chips">
    <template v-for="group in groups" :key="group.label">
      <!-- 分组标签 -->
      <div class="group-header">
        <span class="group-label">{{ group.label }}</span>
        <span v-if="hasDisabledInGroup(group)" class="group-reset" @click="$emit('reset-group', group)">
          重置
        </span>
      </div>

      <!-- 标签列表 -->
      <div class="chip-list">
        <div
          v-for="item in group.items"
          :key="item.key"
          class="chip"
          :class="{ disabled: item.disabled }"
          :style="chipStyle(item)"
          @click="$emit('toggle', item.key)"
        >
          <van-icon :name="item.icon" size="14" />
          <span class="chip-text">{{ item.label }}</span>
          <span class="chip-count">{{ item.count }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { TIMELINE_SOURCE_COLORS, TIMELINE_CATEGORY_CONFIG } from '@/styles/constants'

const props = defineProps({
  groups: {
    type: Array,
    required: true,
    // [{ label: '来源类型', items: [{ key, label, icon, color, count, disabled, isSource, isCategory }] }]
  },
})

defineEmits(['toggle', 'reset-group'])

function hasDisabledInGroup(group) {
  return group.items.some(item => item.disabled)
}

/**
 * 将 hex 颜色转为 rgba
 * @param {string} hex - 如 '#DC2626'
 * @param {number} alpha - 0~1
 */
function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function chipStyle(item) {
  if (item.disabled) {
    return {}
  }
  const c = item.color || 'var(--primary-color)'
  return {
    color: c,
    background: hexToRgba(c, 0.1),
    borderColor: hexToRgba(c, 0.2),
    '--count-bg': hexToRgba(c, 0.18),
  }
}
</script>

<style scoped>
.filter-chips {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 1px 4px var(--primary-alpha-6);
}

/* 分组头 */
.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.group-header:not(:first-child) {
  margin-top: 12px;
}

.group-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.group-reset {
  font-size: 12px;
  color: var(--primary-color);
  cursor: pointer;
}

.group-reset:active {
  opacity: 0.7;
}

/* 标签列表 */
.chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 单个标签 */
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.chip:active {
  transform: scale(0.95);
}

/* 被排除（灰色、删除线） */
.chip.disabled {
  color: var(--text-tertiary);
  background: var(--bg-primary);
  border-color: transparent;
  opacity: 0.55;
}

.chip.disabled .chip-text {
  text-decoration: line-through;
}

.chip-icon {
  flex-shrink: 0;
}

.chip-text {
  line-height: 1;
}

.chip-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  border-radius: 7px;
  background: var(--count-bg, var(--primary-alpha-20));
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

.chip.disabled .chip-count {
    background: var(--shadow-color);
  color: var(--text-tertiary);
}

/* 响应式 */
@media (max-width: 360px) {
  .chip {
    padding: 5px 8px;
    font-size: 12px;
  }

  .chip-list {
    gap: 6px;
  }
}
</style>
