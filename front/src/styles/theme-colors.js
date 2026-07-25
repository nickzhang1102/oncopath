/**
 * 从 CSS 变量读取主题颜色，供 JS 逻辑使用（如 ECharts）
 * 注意：需在 DOM 渲染后调用
 */
export function getThemeColors() {
  const root = document.documentElement
  const s = (name) => getComputedStyle(root).getPropertyValue(name).trim()

  return {
    primary: s('--primary-color'),
    primaryLight: s('--primary-light'),
    primaryDark: s('--primary-dark'),
    success: s('--success-color'),
    warning: s('--warning-color'),
    danger: s('--danger-color'),
    info: s('--info-color'),
    textPrimary: s('--text-primary'),
    textSecondary: s('--text-secondary'),
    textTertiary: s('--text-tertiary'),
    bgPrimary: s('--bg-primary'),
    bgSurface: s('--bg-surface'),
    bgElevated: s('--bg-elevated'),
    borderColor: s('--border-color'),
    borderLight: s('--border-light'),
    borderDark: s('--border-dark'),
  }
}

/**
 * 将 hex 颜色转为 rgba 字符串
 * @param {string} hex - 如 '#0891B2' 或 '#DC2626'
 * @param {number} alpha - 透明度 0~1
 * @returns {string} 如 'var(--primary-alpha-20)'
 */
export function hexToRgba(hex, alpha = 1) {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}
