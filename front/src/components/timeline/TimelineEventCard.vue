<template>
  <div class="timeline-card" @click="$emit('click', item)">
    <!-- 左侧颜色指示条 -->
    <div class="card-indicator" :style="{ backgroundColor: cardColor }"></div>

    <!-- 卡片主体 -->
    <div class="card-body">
      <!-- 头部区域 -->
      <div class="card-header">
        <div class="header-left">
          <div class="type-icon">
            <van-icon :name="cardIcon" size="20" />
          </div>
          <div class="header-info">
            <div class="card-title">{{ item.title }}</div>
            <div class="card-meta">
              <span class="meta-item">
                <van-icon name="calendar-o" size="12" />
                {{ formatDate(item.event_date) }}
              </span>
              <span v-if="categoryLabel" class="category-tag" :style="categoryStyle">
                {{ categoryLabel }}
              </span>
            </div>
          </div>
        </div>
        <van-icon name="arrow" class="card-arrow" />
      </div>

      <!-- 内容区域 -->
      <div v-if="item.description" class="card-content">
        <van-text-ellipsis
          :content="item.description"
          :rows="2"
          expand-text="展开"
          collapse-text="收起"
          @click.stop
        />
      </div>

      <!-- 底部查看链接 -->
      <div class="card-footer" @click.stop="$emit('click', item)">
        <van-icon name="eye-o" class="footer-icon" />
        <span class="footer-text">查看详情</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { TIMELINE_CATEGORY_CONFIG, TIMELINE_SOURCE_COLORS } from '@/styles/constants'

const props = defineProps({
  item: {
    type: Object,
    required: true
  }
})

defineEmits(['click'])

const cardColor = computed(() => {
  if (props.item.color) return props.item.color
  return TIMELINE_SOURCE_COLORS.timeline_event
})

const categoryConfig = computed(() => {
  return TIMELINE_CATEGORY_CONFIG[props.item.category] || null
})

const cardIcon = computed(() => {
  return categoryConfig.value?.icon || 'edit'
})

const categoryLabel = computed(() => {
  if (!props.item.category) return ''
  return categoryConfig.value?.label || props.item.extra?.category_label || props.item.category
})

const categoryStyle = computed(() => {
  const color = categoryConfig.value?.color || cardColor.value
  return {
    color,
    backgroundColor: `${color}15`,
    borderColor: `${color}30`
  }
})

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}
</script>

<style scoped>
.timeline-card {
  background: var(--bg-surface);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px var(--primary-alpha-8);
  transition: all 0.3s ease;
  display: flex;
}

.timeline-card:active {
  transform: scale(0.98);
}

.card-indicator {
  width: 4px;
  flex-shrink: 0;
}

.card-body {
  flex: 1;
  padding: 14px 16px;
  min-width: 0;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.type-icon {
  flex-shrink: 0;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-alpha-8);
  border-radius: 10px;
  color: var(--primary-color);
}

.header-info {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--text-secondary);
}

.category-tag {
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 10px;
  border: 1px solid;
  font-weight: 500;
}

.card-arrow {
  font-size: 14px;
  color: var(--text-tertiary);
  margin-top: 4px;
  flex-shrink: 0;
}

.card-content {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--primary-alpha-10);
}

.card-content :deep(.van-text-ellipsis) {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--primary-alpha-10);
}

.footer-icon {
  font-size: 13px;
  color: var(--text-tertiary);
}

.footer-text {
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>