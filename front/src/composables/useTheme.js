import { ref, onMounted, onUnmounted, readonly } from 'vue'

const THEME_KEY = 'oncopath-theme'

// 单例状态，跨组件共享
const currentTheme = ref(localStorage.getItem(THEME_KEY) || 'system')
const resolvedTheme = ref('light')

let systemListener = null
let listenersCount = 0

function resolveTheme(theme) {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
}

function applyTheme(theme) {
  const resolved = resolveTheme(theme)
  document.documentElement.setAttribute('data-theme', resolved)
  resolvedTheme.value = resolved
}

function setTheme(theme) {
  currentTheme.value = theme
  localStorage.setItem(THEME_KEY, theme)
  applyTheme(theme)
}

function cycleTheme() {
  const next = { light: 'dark', dark: 'system', system: 'light' }
  setTheme(next[currentTheme.value])
}

function handleSystemChange() {
  if (currentTheme.value === 'system') {
    applyTheme('system')
  }
}

// 立即初始化，避免首次渲染闪烁
applyTheme(currentTheme.value)

/**
 * 主题管理 composable
 *
 * - currentTheme: 用户选择的主题 ('light' | 'dark' | 'system')
 * - resolvedTheme: 实际解析后的主题 ('light' | 'dark')
 * - setTheme: 设置主题
 * - cycleTheme: 循环切换 light -> dark -> system -> light
 */
export function useTheme() {
  onMounted(() => {
    if (listenersCount === 0) {
      systemListener = window.matchMedia('(prefers-color-scheme: dark)')
      systemListener.addEventListener('change', handleSystemChange)
    }
    listenersCount++
  })

  onUnmounted(() => {
    listenersCount--
    if (listenersCount === 0 && systemListener) {
      systemListener.removeEventListener('change', handleSystemChange)
      systemListener = null
    }
  })

  return {
    currentTheme: readonly(currentTheme),
    resolvedTheme: readonly(resolvedTheme),
    setTheme,
    cycleTheme,
  }
}
