<template>
  <!-- 左箭头 -->
  <div class="swipe-arrow swipe-arrow-left" @click="$emit('prev')">
    <span class="arrow-icon">‹</span>
  </div>

  <!-- 右箭头 -->
  <div class="swipe-arrow swipe-arrow-right" @click="$emit('next')">
    <span class="arrow-icon">›</span>
  </div>
</template>

<script setup>
// 轮播导航箭头组件

// Emits
const emit = defineEmits(['prev', 'next'])
</script>

<style scoped>
/* 轮播箭头 */
.swipe-arrow {
  position: fixed;
  top: 50vh;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  background: var(--primary-alpha-40);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 1000;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px var(--shadow-color-lg);
  opacity: 0.6;
}

.swipe-arrow:hover {
  background: var(--primary-alpha-60);
  transform: translateY(-50%) scale(1.1);
  box-shadow: 0 6px 16px var(--shadow-color-xl);
  opacity: 1;
}

.swipe-arrow-left {
  left: 10px;
}

.swipe-arrow-right {
  right: 10px;
}

.swipe-arrow .arrow-icon {
  color: white;
  font-size: 20px;
  font-weight: bold;
  line-height: 1;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .swipe-arrow {
    width: 32px;
    height: 32px;
  }

  .swipe-arrow-left {
    left: 8px;
  }

  .swipe-arrow-right {
    right: 8px;
  }

  .swipe-arrow .arrow-icon {
    font-size: 18px;
  }
}

/* 超小屏幕适配 */
@media (max-width: 480px) {
  .swipe-arrow {
    width: 28px;
    height: 28px;
  }

  .swipe-arrow-left {
    left: 5px;
  }

  .swipe-arrow-right {
    right: 5px;
  }

  .swipe-arrow .arrow-icon {
    font-size: 16px;
  }
}
</style>
