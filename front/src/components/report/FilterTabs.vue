<template>
  <div class="filter-tabs">
    <div class="tabs-scroll" ref="scrollRef">
      <div class="tabs-container" ref="containerRef">
        <div
          v-for="tab in tabs"
          :key="tab.value"
          class="tab-item"
          :class="{ active: modelValue === tab.value }"
          @click="selectTab(tab.value)"
        >
          <van-icon v-if="tab.icon" :name="tab.icon" class="tab-icon" />
          <span class="tab-text">{{ tab.text }}</span>
          <span v-if="tab.count !== undefined && tab.count > 0" class="tab-count">{{ tab.count }}</span>
        </div>
      </div>
      <!-- 滑块指示器 -->
      <div class="tabs-indicator" :style="indicatorStyle" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'

const props = defineProps({
  tabs: {
    type: Array,
    required: true,
    // [{ text: '全部', value: 'all', icon: 'apps-o', count: 10 }]
  },
  modelValue: {
    type: [String, Number],
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const scrollRef = ref(null)
const containerRef = ref(null)
const itemRects = ref([])

function selectTab(value) {
  if (props.modelValue !== value) {
    emit('update:modelValue', value)
    emit('change', value)
  }
}

// 计算指示器位置
const indicatorStyle = computed(() => {
  const idx = props.tabs.findIndex(t => t.value === props.modelValue)
  if (idx < 0 || !itemRects.value[idx]) return { left: '0px', width: '0px' }

  const rect = itemRects.value[idx]
  // 指示器宽度为文字区域的 60%，居中
  const indicatorWidth = Math.min(rect.width * 0.5, 28)
  const left = rect.left + (rect.width - indicatorWidth) / 2

  return {
    left: `${left}px`,
    width: `${indicatorWidth}px`,
  }
})

// 测量各 tab 位置
async function measureItems() {
  await nextTick()
  if (!containerRef.value) return
  const containerRect = containerRef.value.getBoundingClientRect()
  const children = containerRef.value.children
  const rects = []
  for (let i = 0; i < children.length; i++) {
    const childRect = children[i].getBoundingClientRect()
    rects.push({
      left: childRect.left - containerRect.left,
      width: childRect.width,
    })
  }
  itemRects.value = rects
}

onMounted(measureItems)
watch(() => props.modelValue, () => nextTick(measureItems))
watch(() => props.tabs, () => nextTick(measureItems), { deep: true })
</script>

<style scoped>
.filter-tabs {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 4px 0;
  box-shadow: 0 1px 4px var(--primary-alpha-6);
}

.tabs-scroll {
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  position: relative;
}

.tabs-scroll::-webkit-scrollbar {
  display: none;
}

.tabs-container {
  display: flex;
  min-width: min-content;
  position: relative;
}

.tab-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px 14px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: color 0.25s ease;
  color: var(--text-secondary);
  position: relative;
}

.tab-item:active {
  opacity: 0.7;
}

.tab-item.active {
  color: var(--primary-color);
  font-weight: 600;
}

.tab-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.tab-text {
  font-size: 14px;
  line-height: 1;
}

.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 8px;
  background: var(--primary-alpha-12);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  line-height: 1;
}

.tab-item.active .tab-count {
  background: var(--primary-alpha-20);
  color: var(--primary-color);
}

/* 滑块指示器 */
.tabs-indicator {
  position: absolute;
  bottom: 2px;
  height: 3px;
  border-radius: 1.5px;
  background: var(--primary-color);
  transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 响应式调整 */
@media (max-width: 360px) {
  .tab-item {
    padding: 8px 10px;
  }

  .tab-text {
    font-size: 13px;
  }
}

/* 桌面端适配 */
@media (min-width: 768px) {
  .tabs-container {
    justify-content: center;
  }

  .tab-item {
    padding: 12px 20px;
  }

  .tab-text {
    font-size: 15px;
  }

  .tab-icon {
    font-size: 18px;
  }
}
</style>