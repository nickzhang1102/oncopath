<template>
  <teleport to="body">
    <!-- 全屏拦截层：导览期间阻断底层元素点击，避免锚点错位 -->
    <div v-if="box" class="tour-blocker" />

    <!-- 高亮框（box-shadow 镂空遮罩） -->
    <div v-if="box" class="tour-highlight" :style="highlightStyle" />

    <!-- 步骤提示卡 -->
    <div v-if="box" class="tour-popover" :style="popoverStyle">
      <div class="tour-step-tag">{{ current + 1 }} / {{ steps.length }}</div>
      <h3 class="tour-title">{{ step.title }}</h3>
      <p class="tour-desc">{{ step.desc }}</p>
      <div class="tour-actions">
        <van-button size="small" plain @click="finish">跳过</van-button>
        <div class="tour-actions-right">
          <van-button v-if="current > 0" size="small" plain @click="prev">上一步</van-button>
          <van-button size="small" type="primary" @click="next">
            {{ current === steps.length - 1 ? '完成' : '下一步' }}
          </van-button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

/**
 * 锚点式新手导览：按 steps 顺序高亮页面元素并逐个讲解。
 * steps: [{ selector, title, desc }]，目标元素不存在时自动跳过该步。
 */
const props = defineProps({
  steps: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['finish'])

const POPover_GAP = 12
const HIGHLIGHT_PAD = 6

const current = ref(0)
const box = ref(null)
const below = ref(true)

const step = computed(() => props.steps[current.value])

const highlightStyle = computed(() => ({
  top: `${box.value.top}px`,
  left: `${box.value.left}px`,
  width: `${box.value.width}px`,
  height: `${box.value.height}px`,
}))

const popoverStyle = computed(() => {
  const vw = window.innerWidth
  const width = Math.min(320, vw - 32)
  const left = Math.max(16, Math.min(box.value.left, vw - width - 16))
  return {
    width: `${width}px`,
    left: `${left}px`,
    top: below.value ? `${box.value.top + box.value.height + POPover_GAP}px` : `${box.value.top - POPover_GAP}px`,
    transform: below.value ? 'none' : 'translateY(-100%)',
  }
})

function locate() {
  if (!step.value) {
    finish()
    return
  }
  const el = document.querySelector(step.value.selector)
  if (!el) {
    // 目标元素不存在（如桌面端访问移动端布局），自动跳过该步
    next()
    return
  }
  el.scrollIntoView({ block: 'center', behavior: 'auto' })
  const rect = el.getBoundingClientRect()
  box.value = {
    top: rect.top - HIGHLIGHT_PAD,
    left: rect.left - HIGHLIGHT_PAD,
    width: rect.width + HIGHLIGHT_PAD * 2,
    height: rect.height + HIGHLIGHT_PAD * 2,
  }
  below.value = rect.bottom + 200 < window.innerHeight || rect.top < 200
}

function next() {
  if (current.value >= props.steps.length - 1) {
    finish()
    return
  }
  current.value += 1
  locate()
}

function prev() {
  if (current.value <= 0) return
  current.value -= 1
  locate()
}

function finish() {
  emit('finish')
}

function handleResize() {
  if (box.value) locate()
}

onMounted(async () => {
  document.body.style.overflow = 'hidden'
  window.addEventListener('resize', handleResize)
  // 等待引导弹窗关闭动画结束后再定位首个目标
  await new Promise(resolve => setTimeout(resolve, 350))
  await nextTick()
  locate()
})

onUnmounted(() => {
  document.body.style.overflow = ''
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.tour-blocker {
  position: fixed;
  inset: 0;
  z-index: 3009;
  background: transparent;
}

.tour-highlight {
  position: fixed;
  z-index: 3010;
  border-radius: 14px;
  border: 2px dashed var(--primary-color);
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.65);
  pointer-events: none;
  transition: all 0.25s ease;
}

.tour-popover {
  position: fixed;
  z-index: 3011;
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
}

.tour-step-tag {
  display: inline-block;
  font-size: 11px;
  color: var(--primary-color);
  background: var(--primary-alpha-8, rgba(114, 50, 160, 0.08));
  border-radius: 10px;
  padding: 2px 8px;
  margin-bottom: 8px;
}

.tour-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 6px;
}

.tour-desc {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text-secondary);
  margin: 0 0 14px;
}

.tour-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.tour-actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
