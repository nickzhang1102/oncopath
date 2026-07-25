/**
 * 仪表盘统计项共享配置
 * 桌面端 DashboardStatsGrid 和移动端 MobileStatsRow 共用
 */
export const DASHBOARD_STATS_CONFIG = [
  { key: 'check', label: '检验报告', valueKey: 'check_count', path: '/home/reports' },
  { key: 'exam', label: '检查报告', valueKey: 'exam_count', path: '/home/exam-reports' },
  { key: 'pathology', label: '病理报告', valueKey: 'pathology_count', path: '/home/pathology-reports' },
  { key: 'timeline', label: '时间线事件', valueKey: 'timeline_event_count', path: '/home/timeline' },
  { key: 'medication', label: '用药记录', valueKey: 'medication_total', path: '/home/medication' },
]