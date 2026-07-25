/**
 * 统一导航配置源
 * 桌面端 Sidebar、移动端 Drawer、FeatureGrid 共用
 * 新增功能只需修改此文件，所有平台自动同步
 *
 * 导出结构：
 * - HOME_NAV_ITEMS: 首页核心功能（主页、时间线）
 * - MEDICAL_NAV_ITEMS: 医疗管理功能（检验/检查/病理报告、指标、用药等）
 * - AI_NAV_ITEMS: AI智能工具（会诊、提示词、搜索）
 * - MANAGEMENT_NAV_ITEMS: 生活管理（随访、知识库、病人管理）
 * - PROFILE_NAV_ITEMS: 个人中心（我的、数据导出）
 * - EXTERNAL_NAV_ITEMS: 外部链接（临床试验）
 * - NAV_GROUPS: 完整导航分组（用于 Sidebar/Drawer）
 * - MOBILE_TABBAR_ITEMS: 移动端底部导航（5项）
 * - MOBILE_FEATURE_GRID: 移动端主页功能网格配置
 * - OTHER_NAV_ITEMS: EXTERNAL_NAV_ITEMS 别名（向后兼容）
 */

// 首页核心功能
export const HOME_NAV_ITEMS = [
  { path: '/home/main', icon: 'home-o', label: '主页' },
  { path: '/home/timeline', icon: 'clock-o', label: '时间线' },
]

// 医疗管理功能项
export const MEDICAL_NAV_ITEMS = [
  { path: '/home/reports', icon: 'records', label: '检验报告' },
  { path: '/home/exam-reports', icon: 'scan', label: '检查报告' },
  { path: '/home/pathology-reports', icon: 'certificate', label: '病理报告' },
  { path: '/home/index', icon: 'chart-trending-o', label: '指标查询' },
  { path: '/home/abnormal-indicators', icon: 'warning-o', label: '异常指标' },
  { path: '/home/image-report', icon: 'photo-o', label: '上传报告' },
  { path: '/home/treatment', icon: 'comment-o', label: '治疗记录' },
  { path: '/home/medication', icon: 'gem-o', label: '用药记录' },
  { path: '/home/status', icon: 'smile-o', label: '状态记录' },
]

// AI/智能工具项
export const AI_NAV_ITEMS = [
  { path: '/home/consultation', icon: 'friends-o', label: '虚拟会诊' },
  { path: '/home/consultation/prompt-config', icon: 'edit', label: '提示词配置' },
  { path: '/home/search', icon: 'search', label: '全局搜索' },
]

// 管理功能项
export const MANAGEMENT_NAV_ITEMS = [
  { path: '/home/follow-up', icon: 'clock-o', label: '随访提醒' },
  { path: '/home/knowledge', icon: 'bookmark-o', label: '知识库' },
  { path: '/home/patient-management', icon: 'manager-o', label: '病人管理' },
]

// 个人中心功能项
export const PROFILE_NAV_ITEMS = [
  { path: '/home/profile', icon: 'user-o', label: '我的' },
  { path: '/home/profile/export', icon: 'down', label: '数据导出' },
]

// 其他功能项（外部链接）
export const EXTERNAL_NAV_ITEMS = [
  { path: 'https://www.chictr.org.cn/searchproj.html', icon: 'guide-o', label: '临床试验', external: true },
]

// 别名导出，保持向后兼容
export const OTHER_NAV_ITEMS = EXTERNAL_NAV_ITEMS

/**
 * 完整导航分组配置
 * 用于桌面端 Sidebar 和移动端 Drawer
 */
export const NAV_GROUPS = [
  { key: 'home', label: '首页', items: HOME_NAV_ITEMS },
  { key: 'medical', label: '医疗', items: MEDICAL_NAV_ITEMS },
  { key: 'ai', label: 'AI', items: AI_NAV_ITEMS },
  { key: 'management', label: '管理', items: MANAGEMENT_NAV_ITEMS },
  { key: 'profile', label: '个人', items: PROFILE_NAV_ITEMS },
  { key: 'external', label: '外部', items: EXTERNAL_NAV_ITEMS },
]

/**
 * 移动端 Tabbar 核心入口
 * 保留 5 个最常用功能
 */
export const MOBILE_TABBAR_ITEMS = [
  { path: '/home/main', icon: 'home-o', label: '主页' },
  { path: '/home/timeline', icon: 'clock-o', label: '时间线' },
  { path: '/home/image-report', icon: 'plus', label: '上传', isCenter: true },
  { path: '/home/consultation', icon: 'friends-o', label: '会诊' },
  { path: '/home/profile', icon: 'user-o', label: '我的' },
]

/**
 * 移动端主页 FeatureGrid 配置
 * 用于主页快捷入口展示
 */
export const MOBILE_FEATURE_GRID = {
  medical: {
    title: '医疗管理',
    items: MEDICAL_NAV_ITEMS.slice(0, 6), // 取前6项展示
  },
  ai: {
    title: 'AI 工具',
    items: AI_NAV_ITEMS.slice(0, 3),
  },
  management: {
    title: '生活管理',
    items: MANAGEMENT_NAV_ITEMS.slice(0, 3),
  },
}
