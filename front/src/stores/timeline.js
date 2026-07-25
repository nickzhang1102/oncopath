import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { timelineApi } from '@/api/timeline'
import {
  TIMELINE_SOURCE_COLORS,
  TIMELINE_SOURCE_ICONS,
  TIMELINE_SOURCE_LABELS,
  TIMELINE_CATEGORY_CONFIG,
} from '@/styles/constants'

/**
 * 时间线来源类型常量
 */
export const SOURCE_TYPES = {
  TIMELINE_EVENT: 'timeline_event',
  MEDICAL_CHECK: 'medical_check',
  MEDICAL_EXAM: 'medical_exam',
  PATHOLOGY_REPORT: 'pathology_report',
  MEDICATION: 'medication',
}

/**
 * 来源类型显示顺序
 */
export const SOURCE_ORDER = [
  SOURCE_TYPES.TIMELINE_EVENT,
  SOURCE_TYPES.MEDICAL_CHECK,
  SOURCE_TYPES.MEDICAL_EXAM,
  SOURCE_TYPES.PATHOLOGY_REPORT,
  SOURCE_TYPES.MEDICATION,
]

export const useTimelineStore = defineStore('timeline', () => {
  // State
  const timelineItems = ref([])
  const stats = ref(null)

  // 分页状态
  const currentOffset = ref(0)
  const pageSize = 50
  const hasMore = ref(true)

  // 加载计数器：解决并发请求竞态条件
  const _loadingCount = ref(0)
  const loading = computed(() => _loadingCount.value > 0)

  // 多选过滤：排除模型（空集=全选，集合中的值=被排除不显示）
  const disabledFilters = ref(new Set())

  const error = ref(null)

  // 日期范围筛选
  const dateRange = ref(null) // { start: 'YYYY-MM-DD', end: 'YYYY-MM-DD' } or null

  // Getters

  // 过滤后的列表
  const filteredItems = computed(() => {
    const disabled = disabledFilters.value
    if (disabled.size === 0) return timelineItems.value

    return timelineItems.value.filter(item => {
      // 检查 source_type 级别是否被排除
      if (disabled.has(item.source_type)) return false
      // 检查 category 级别是否被排除（仅 timeline_event）
      if (item.category && disabled.has(item.category)) return false
      return true
    })
  })

  // 统计各来源数量
  const sourceCounts = computed(() => {
    const counts = {}
    for (const item of timelineItems.value) {
      counts[item.source_type] = (counts[item.source_type] || 0) + 1
    }
    return counts
  })

  // 统计各 category 数量（仅 timeline_event）
  const categoryCounts = computed(() => {
    const counts = {}
    timelineItems.value
      .filter(item => item.source_type === SOURCE_TYPES.TIMELINE_EVENT)
      .forEach(item => {
        if (item.category) {
          counts[item.category] = (counts[item.category] || 0) + 1
        }
      })
    return counts
  })

  // 分组过滤标签数据（供 FilterChips 组件使用）
  const filterGroups = computed(() => {
    const disabled = disabledFilters.value
    const sCounts = sourceCounts.value
    const cCounts = categoryCounts.value
    const groups = []

    // 第一组：来源类型
    const sourceItems = SOURCE_ORDER
      .filter(key => (sCounts[key] ?? 0) > 0)
      .map(key => ({
        key,
        label: TIMELINE_SOURCE_LABELS[key],
        icon: TIMELINE_SOURCE_ICONS[key],
        color: TIMELINE_SOURCE_COLORS[key],
        count: sCounts[key],
        disabled: disabled.has(key),
        isSource: true,
      }))

    groups.push({ label: '来源类型', items: sourceItems })

    // 第二组：时间线事件子分类（仅当有时间线事件数据时）
    const categoryKeys = Object.keys(cCounts)
    if (categoryKeys.length > 0) {
      const categoryItems = categoryKeys
        .map(key => {
          const config = TIMELINE_CATEGORY_CONFIG[key]
          return {
            key,
            label: config?.label || key,
            icon: config?.icon || 'label-o',
            color: config?.color || getComputedStyle(document.documentElement).getPropertyValue('--text-tertiary').trim(),
            count: cCounts[key],
            disabled: disabled.has(key),
            isCategory: true,
          }
        })

      groups.push({ label: '事件分类', items: categoryItems })
    }

    return groups
  })

  // Actions

  async function fetchTimeline(patientId, params = {}) {
    _loadingCount.value++
    error.value = null
    try {
      const isLoadMore = params.loadMore === true
      const offset = isLoadMore ? currentOffset.value : 0

      const queryParams = {
        patient_id: patientId,
        offset,
        limit: params.limit || pageSize,
      }

      // 日期范围：优先用 params，否则用 store 中的 dateRange
      const startDate = params.start_date || dateRange.value?.start
      const endDate = params.end_date || dateRange.value?.end

      if (startDate) {
        queryParams.start_date = startDate
      }
      if (endDate) {
        queryParams.end_date = endDate
      }
      if (params.source_types) {
        queryParams.source_types = params.source_types
      }

      const data = await timelineApi.queryUnifiedTimeline(queryParams)
      const items = data || []

      if (isLoadMore) {
        timelineItems.value.push(...items)
      } else {
        timelineItems.value = items
      }
      currentOffset.value = offset + items.length
      hasMore.value = items.length >= (params.limit || pageSize)

      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      _loadingCount.value--
    }
  }

  async function fetchStats(patientId) {
    try {
      const data = await timelineApi.getUnifiedStats(patientId)
      stats.value = data
      return data
    } catch (err) {
      console.error('获取时间线统计失败:', err)
    }
  }

  // 切换某个过滤项的排除状态
  function toggleFilter(key) {
    const newSet = new Set(disabledFilters.value)
    if (newSet.has(key)) {
      newSet.delete(key)
    } else {
      newSet.add(key)
    }
    disabledFilters.value = newSet
  }

  // 全选（清空排除集合）
  function selectAll() {
    disabledFilters.value = new Set()
  }

  // 重置过滤
  function clearTimeline() {
    timelineItems.value = []
    stats.value = null
    disabledFilters.value = new Set()
    dateRange.value = null
    error.value = null
    currentOffset.value = 0
    hasMore.value = true
  }

  // 设置日期范围
  function setDateRange(start, end) {
    if (start && end) {
      dateRange.value = { start, end }
    } else {
      dateRange.value = null
    }
  }

  // 清除日期范围
  function clearDateRange() {
    dateRange.value = null
  }

  return {
    // State
    timelineItems,
    stats,
    loading,
    error,
    disabledFilters,
    dateRange,
    hasMore,
    // Getters
    filteredItems,
    sourceCounts,
    categoryCounts,
    filterGroups,
    // Actions
    fetchTimeline,
    fetchStats,
    toggleFilter,
    selectAll,
    clearTimeline,
    setDateRange,
    clearDateRange,
  }
})
