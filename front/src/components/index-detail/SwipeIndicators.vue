<template>
  <div class="custom-indicators">
    <div
      v-for="(_, index) in items"
      :key="index"
      class="indicator-dot"
      :class="{ active: currentIndex === index }"
      @click="$emit('change', index)"
    ></div>
  </div>
</template>

<script setup>
// 自定义轮播指示器组件

// Props
const props = defineProps({
  items: {
    type: Array,
    required: true
  },
  currentIndex: {
    type: Number,
    default: 0
  }
})

// Emits
const emit = defineEmits(['change'])
</script>

<style scoped>
/* 自定义指示器 */
.custom-indicators {
  display: flex;
  justify-content: center;
  padding: 10px;
  gap: 6px;
}

.indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.3s ease;
}

.indicator-dot.active {
  background: var(--primary-color);
  transform: scale(1.2);
}

.indicator-dot:hover {
  background: var(--text-secondary);
}
</style>
