<template>
  <div class="timeline">
    <div
      v-for="(item, index) in items"
      :key="item.id || item.title + item.date"
      class="timeline-item"
      :class="{
        'timeline-item--last': index === items.length - 1,
        'timeline-item--clickable': clickable
      }"
      @click="handleClick(item)"
    >
      <div class="timeline-item__dot" :class="`timeline-item__dot--${item.type || 'default'}`">
        <van-icon v-if="item.icon" :name="item.icon" size="14" />
      </div>

      <div class="timeline-item__content">
        <div class="timeline-item__header">
          <span class="timeline-item__title">{{ item.title }}</span>
          <span class="timeline-item__date">{{ item.date }}</span>
        </div>
        <div v-if="item.description" class="timeline-item__description">
          {{ item.description }}
        </div>
        <div v-if="item.tags" class="timeline-item__tags">
          <van-tag
            v-for="tag in item.tags"
            :key="tag"
            size="small"
            round
            class="timeline-item__tag"
          >
            {{ tag }}
          </van-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits(['item-click'])

defineProps({
  items: {
    type: Array,
    required: true,
    // { title, date, description, icon, type: 'medical'|'life', tags: [] }
  },
  clickable: {
    type: Boolean,
    default: true
  }
})

function handleClick(item) {
  emit('item-click', item)
}
</script>

<style scoped>
.timeline {
  padding: var(--space-4);
}

.timeline-item {
  position: relative;
  padding-left: var(--space-8);
  padding-bottom: var(--space-6);
}

.timeline-item--last {
  padding-bottom: 0;
}

.timeline-item__dot {
  position: absolute;
  left: 0;
  top: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  border: 3px solid var(--bg-surface);
  box-shadow: 0 0 0 2px var(--primary-light);
  z-index: 1;
}

.timeline-item__dot--medical {
  background: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-light);
}

.timeline-item__dot--life {
  background: var(--success-color);
  box-shadow: 0 0 0 2px var(--primary-alpha-30);
}

.timeline-item__dot--milestone {
  background: var(--warning-color);
  box-shadow: 0 0 0 2px var(--status-warning-bg);
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 32px;
  width: 2px;
  height: calc(100% - 32px);
  background: var(--border-color);
}

.timeline-item--last::before {
  display: none;
}

.timeline-item__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-2);
}

.timeline-item__title {
  font-weight: 600;
  color: var(--text-primary);
}

.timeline-item__date {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.timeline-item__description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-2);
}

.timeline-item__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.timeline-item--clickable {
  cursor: pointer;
  transition: background 0.2s;
  border-radius: 8px;
  margin: -4px;
  padding: 4px;
}

.timeline-item--clickable:hover {
  background: var(--primary-alpha-5);
}

.timeline-item--clickable:active {
  background: var(--primary-alpha-10);
}
</style>
