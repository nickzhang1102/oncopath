<template>
  <div class="ocr-indicator-list">
    <div class="section-header-row">
      <span class="section-title">
        指标匹配结果
        <span class="count-badge" v-if="indicators.length">({{ indicators.length }}项)</span>
      </span>
      <span class="edit-hint" v-if="canReview">点击值可编辑</span>
    </div>

    <div class="indicators-container">
      <div
        v-for="(indicator, index) in indicators"
        :key="index"
        class="indicator-row"
        :class="getRowClass(indicator)"
        @click="$emit('indicator-click', indicator)"
      >
        <div class="indicator-name">
          <span class="name-text">{{ indicator.normalized_name || indicator.raw_name }}</span>
          <span v-if="indicator.match_method === 'none'" class="unmatched-label">未匹配</span>
        </div>

        <div class="indicator-value-area">
          <template v-if="!isEditing(indicator)">
            <span v-if="isModified(indicator)" class="original-value">
              {{ indicator.value }}
            </span>
            <span
              class="value-text"
              :class="{ 'value-modified': isModified(indicator), 'value-clickable': canReview }"
              @click.stop="startEdit(indicator)"
            >
              {{ getDisplayValue(indicator) }}
            </span>
          </template>
          <template v-else>
            <input
              :ref="el => { if (el) inputRef = el }"
              class="value-input"
              :value="editValues[indicator.raw_name]"
              @input="onInput(indicator, $event)"
              @blur="stopEdit(indicator)"
              @keyup.enter="stopEdit(indicator)"
              @keyup.escape="clearEdit(indicator)"
            />
          </template>
        </div>

        <div class="indicator-unit" v-if="indicator.unit">
          {{ indicator.unit }}
        </div>

        <div class="indicator-status">
          <span v-if="isModified(indicator)" class="status-tag modified">已修改</span>
          <span v-else-if="indicator.status === 'normal'" class="status-tag normal">正常</span>
          <span v-else-if="indicator.status === 'high'" class="status-tag high">偏高</span>
          <span v-else-if="indicator.status === 'low'" class="status-tag low">偏低</span>
          <span v-else-if="indicator.status === 'abnormal'" class="status-tag abnormal">异常</span>
          <span v-else-if="indicator.match_method === 'none'" class="status-tag unmatched">未匹配</span>
          <span v-else class="status-tag default">{{ indicator.status || '' }}</span>
        </div>
      </div>
    </div>

    <div v-if="indicators.length === 0" class="empty-indicators">
      <van-empty description="暂无匹配指标" image="search" />
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  indicators: { type: Array, default: () => [] },
  reviewLogs: { type: Array, default: () => [] },
  canReview: { type: Boolean, default: false },
  editValues: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['indicator-click', 'toggle-edit', 'update-value'])

const editingField = ref(null)
const inputRef = ref(null)

const isModified = (indicator) => {
  const val = props.editValues[indicator.raw_name]
  return val !== undefined && val !== '' && val !== indicator.value
}

const isEditing = (indicator) => {
  return editingField.value === indicator.raw_name
}

const getDisplayValue = (indicator) => {
  if (isModified(indicator)) {
    return props.editValues[indicator.raw_name]
  }
  const log = props.reviewLogs.find(l => l.field_name === indicator.raw_name)
  if (log && log.corrected_value) {
    return log.corrected_value
  }
  return indicator.value || '-'
}

const getRowClass = (indicator) => {
  return {
    'row-modified': isModified(indicator),
    'row-unmatched': indicator.match_method === 'none',
    'row-abnormal': indicator.status === 'high' || indicator.status === 'low' || indicator.status === 'abnormal'
  }
}

const startEdit = (indicator) => {
  if (!props.canReview) return
  editingField.value = indicator.raw_name
  if (props.editValues[indicator.raw_name] === undefined || props.editValues[indicator.raw_name] === '') {
    emit('update-value', indicator.raw_name, indicator.value || '')
  }
  nextTick(() => {
    if (inputRef.value) inputRef.value.focus()
  })
}

const stopEdit = (indicator) => {
  editingField.value = null
}

const clearEdit = (indicator) => {
  emit('update-value', indicator.raw_name, '')
  editingField.value = null
}

const onInput = (indicator, event) => {
  const value = event.target.value.replace(/<[^>]*>/g, '')
  emit('update-value', indicator.raw_name, value)
}
</script>

<style scoped>
.ocr-indicator-list {
  background: var(--bg-surface-alpha);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(10px);
}

.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
}

.count-badge {
  color: var(--text-secondary);
  font-weight: 400;
  font-size: 12px;
}

.edit-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.indicators-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.indicator-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--bg-elevated);
  border-radius: 8px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
  cursor: pointer;
}

.indicator-row:hover {
  background: var(--primary-alpha-5);
}

.row-modified {
  border-color: var(--warning-color);
  background: rgba(255, 152, 0, 0.06);
}

.row-unmatched {
  opacity: 0.6;
}

.row-abnormal:not(.row-modified) {
  background: rgba(239, 83, 80, 0.06);
}

.indicator-name {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.name-text {
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.unmatched-label {
  font-size: 10px;
  color: var(--text-tertiary);
  background: var(--bg-primary);
  padding: 1px 4px;
  border-radius: 2px;
}

.indicator-value-area {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.original-value {
  font-size: 12px;
  color: var(--text-tertiary);
  text-decoration: line-through;
}

.value-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px dashed transparent;
  transition: all 0.15s ease;
}

.value-clickable {
  cursor: pointer;
  border-color: transparent;
}

.value-clickable:hover {
  border-color: var(--primary-color);
  background: var(--primary-alpha-5);
}

.value-modified {
  color: var(--warning-color);
  font-weight: 600;
}

.value-input {
  width: 80px;
  padding: 4px 8px;
  border: 1px solid var(--primary-color);
  border-radius: 4px;
  background: var(--bg-elevated);
  color: var(--primary-color);
  font-size: 14px;
  text-align: right;
  outline: none;
}

.value-input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-alpha-20);
}

.indicator-unit {
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.indicator-status {
  flex-shrink: 0;
}

.status-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.status-tag.normal { background: var(--status-normal-bg); color: var(--success-color); }
.status-tag.high { background: var(--status-danger-bg); color: var(--danger-color); }
.status-tag.low { background: var(--status-warning-bg); color: var(--warning-color); }
.status-tag.abnormal { background: var(--status-danger-bg); color: var(--danger-color); }
.status-tag.modified { background: rgba(255, 152, 0, 0.15); color: var(--warning-color); }
.status-tag.unmatched { background: var(--bg-primary); color: var(--text-tertiary); }
.status-tag.default { background: var(--bg-primary); color: var(--text-secondary); }

.empty-indicators {
  padding: 20px 0;
}
</style>
