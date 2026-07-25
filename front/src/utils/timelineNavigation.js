/**
 * 时间线事件导航工具函数
 * 根据 source_type 和 category 确定跳转目标
 */

/**
 * 治疗/用药类 category
 */
const TREATMENT_CATEGORIES = new Set([
  'chemotherapy',
  'radiation',
  'surgery',
  'targeted',
  'immunotherapy',
  'adc',
  'car_t',
  'other'
])

/**
 * 生活/状态类 category
 */
const STATUS_CATEGORIES = new Set([
  'pain',
  'mood',
  'diet',
  'sleep',
  'stool',
  'life'
])

/**
 * timeline_event 类型事件的导航逻辑
 * @param {Object} item - 时间线事件对象
 * @returns {{ path: string, query?: Object } | null} 路由对象
 */
function getTimelineEventTarget(item) {
  const { category, related_report_id, event_id } = item

  // 每日状态记录 -> 状态记录页
  if (category === 'daily_status') {
    return {
      path: '/home/status',
      query: event_id ? { event_id: String(event_id) } : undefined
    }
  }

  // 治疗/用药类 -> 治疗记录页
  if (TREATMENT_CATEGORIES.has(category)) {
    return {
      path: '/home/treatment',
      query: event_id ? { event_id: String(event_id) } : undefined
    }
  }

  // 诊断/医疗类 -> 有报告ID跳详情，否则跳检验报告列表
  if (category === 'diagnosis' || category === 'medical') {
    if (related_report_id) {
      return { path: `/home/report/${related_report_id}` }
    }
    return { path: '/home/reports' }
  }

  // 生活/状态类 -> 状态记录页
  if (STATUS_CATEGORIES.has(category)) {
    return {
      path: '/home/status',
      query: event_id ? { event_id: String(event_id) } : undefined
    }
  }

  // 默认：无法识别的分类不跳转
  return null
}

/**
 * 根据时间线项数据获取导航目标
 * @param {Object} item - 统一时间线项对象 (含 source_type 字段)
 * @returns {{ path: string, query?: Object } | null} 路由对象，无匹配则返回 null
 */
export function getNavigationTarget(item) {
  switch (item.source_type) {
    case 'medical_check':
      return { path: `/home/report/${item.source_id}` }
    case 'medical_exam':
      return { path: '/home/exam-reports' }
    case 'pathology_report':
      return { path: '/home/pathology-reports' }
    case 'timeline_event':
      return getTimelineEventTarget(item)
    default:
      return null
  }
}