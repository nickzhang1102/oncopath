import { ref, readonly, computed, onMounted, onUnmounted } from 'vue'

const BREAKPOINTS = {
  sm: 480,
  md: 768,
  lg: 1024,
}

const TABBAR_HEIGHT = 50

// 模块级立即初始化，避免首次渲染闪烁
const mediaSm = window.matchMedia(`(min-width: ${BREAKPOINTS.sm}px)`)
const mediaMd = window.matchMedia(`(min-width: ${BREAKPOINTS.md}px)`)
const mediaLg = window.matchMedia(`(min-width: ${BREAKPOINTS.lg}px)`)

// 单例状态，跨组件共享
const isSmallMobile = ref(!mediaSm.matches)
const isMobile = ref(!mediaMd.matches)
const isDesktop = ref(mediaMd.matches)
const isWide = ref(mediaLg.matches)

// safe-area-inset-bottom 单例
const safeAreaBottom = ref(0)

// 浮动按钮 gap 配置（tabbar + safe-area + 额外间距）
const floatingBubbleGap = computed(() => ({
  x: 24,
  y: TABBAR_HEIGHT + safeAreaBottom.value + 16
}))

let listenersCount = 0

function updateBreakpoints() {
  isSmallMobile.value = !mediaSm.matches
  isMobile.value = !mediaMd.matches
  isDesktop.value = mediaMd.matches
  isWide.value = mediaLg.matches
}

/**
 * 响应式断点 composable
 *
 * - isSmallMobile: < 480px（小屏手机）
 * - isMobile: < 768px（移动端）
 * - isDesktop: >= 768px（桌面端，含平板）
 * - isWide: >= 1024px（宽屏桌面）
 *
 * isDesktop 与 isWide 可同时为 true（如 1200px 视口）
 */
export function useResponsive() {
  onMounted(() => {
    if (listenersCount === 0) {
      mediaSm.addEventListener('change', updateBreakpoints)
      mediaMd.addEventListener('change', updateBreakpoints)
      mediaLg.addEventListener('change', updateBreakpoints)
      // 首次获取 safe-area-inset-bottom
      if (safeAreaBottom.value === 0) {
        const div = document.createElement('div')
        div.style.paddingBottom = 'env(safe-area-inset-bottom)'
        document.body.appendChild(div)
        safeAreaBottom.value = parseInt(getComputedStyle(div).paddingBottom) || 0
        document.body.removeChild(div)
      }
    }
    listenersCount++
  })

  onUnmounted(() => {
    listenersCount--
    if (listenersCount === 0) {
      mediaSm.removeEventListener('change', updateBreakpoints)
      mediaMd.removeEventListener('change', updateBreakpoints)
      mediaLg.removeEventListener('change', updateBreakpoints)
    }
  })

  return {
    isSmallMobile: readonly(isSmallMobile),
    isMobile: readonly(isMobile),
    isDesktop: readonly(isDesktop),
    isWide: readonly(isWide),
    floatingBubbleGap,
  }
}
