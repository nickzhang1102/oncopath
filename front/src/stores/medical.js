import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { medicalApi } from '@/api/medical'

export const useMedicalStore = defineStore('medical', () => {
  // State
  const currentRecord = ref(null)
  const reportList = ref([])
  const indicatorList = ref([])
  const abnormalIndicators = ref([])
  const error = ref(null)

  // 加载计数器：解决并发请求竞态条件
  const _loadingCount = ref(0)
  const loading = computed(() => _loadingCount.value > 0)

  // Getters
  const hasAbnormalIndicators = computed(() => abnormalIndicators.value.length > 0)

  const indicatorCount = computed(() => indicatorList.value.length)

  const abnormalCount = computed(() => abnormalIndicators.value.length)

  const reportCount = computed(() => reportList.value.length)

  // 按分类分组
  const indicatorsByCategory = computed(() => {
    const groups = {}
    indicatorList.value.forEach(indicator => {
      const category = indicator.indicator_category || '其他'
      if (!groups[category]) {
        groups[category] = []
      }
      groups[category].push(indicator)
    })
    return groups
  })

  // Actions
  async function fetchMedicalRecord(reportId) {
    _loadingCount.value++
    error.value = null
    try {
      const data = await medicalApi.getMedicalReport(reportId)
      currentRecord.value = data
      return data
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    } finally {
      _loadingCount.value--
    }
  }

  async function fetchReportList(patientId, params) {
    _loadingCount.value++
    error.value = null
    try {
      const data = await medicalApi.getMedicalReportList(patientId, params)
      reportList.value = data
      return data
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    } finally {
      _loadingCount.value--
    }
  }

  async function fetchIndicators(reportId) {
    _loadingCount.value++
    error.value = null
    try {
      const data = await medicalApi.getMedicalReport(reportId)
      // 从报告详情中提取指标列表
      const indicators = data.details || data || []
      indicatorList.value = indicators
      abnormalIndicators.value = indicators.filter(i => i.is_abnormal)
      return indicators
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    } finally {
      _loadingCount.value--
    }
  }

  async function fetchAbnormalIndicators(patientId, params = {}) {
    _loadingCount.value++
    error.value = null
    try {
      const data = await medicalApi.getAbnormalIndicators(patientId, params)
      abnormalIndicators.value = data
      return data
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    } finally {
      _loadingCount.value--
    }
  }

  async function getIndicatorHistory(indexId) {
    error.value = null
    try {
      return await medicalApi.getIndicatorHistory(indexId)
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    }
  }

  function clearMedicalData() {
    currentRecord.value = null
    reportList.value = []
    indicatorList.value = []
    abnormalIndicators.value = []
  }

  // ===== 新增方法：支持原版UI功能 =====

  // 获取最新检验数据（按类型）
  async function fetchLatestCheckData(patientId, medicalType, params = {}) {
    _loadingCount.value++
    error.value = null
    try {
      const data = await medicalApi.getLatestCheckData(patientId, medicalType, params)
      return data
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    } finally {
      _loadingCount.value--
    }
  }

  // 获取指标列表（按类型）
  async function fetchIndexes(patientId, medicalType) {
    _loadingCount.value++
    error.value = null
    try {
      const data = await medicalApi.getIndexes(patientId, medicalType)
      return data
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    } finally {
      _loadingCount.value--
    }
  }

  // 获取指标历史数据（按index_id）
  async function getIndexHistoryById(indexId, params = {}) {
    _loadingCount.value++
    error.value = null
    try {
      const data = await medicalApi.getIndexHistoryById(indexId, params)
      return data
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    } finally {
      _loadingCount.value--
    }
  }

  // 获取最新检查报告（CT等）
  async function fetchLatestExamReport(patientId, examType, params = {}) {
    _loadingCount.value++
    error.value = null
    try {
      const data = await medicalApi.getLatestExamReport(patientId, examType, params)
      return data
    } catch (e) {
      error.value = e.message || '加载失败'
      throw e
    } finally {
      _loadingCount.value--
    }
  }

  return {
    currentRecord,
    reportList,
    indicatorList,
    abnormalIndicators,
    error,
    loading,
    hasAbnormalIndicators,
    indicatorCount,
    abnormalCount,
    reportCount,
    indicatorsByCategory,
    fetchMedicalRecord,
    fetchReportList,
    fetchIndicators,
    fetchAbnormalIndicators,
    getIndicatorHistory,
    clearMedicalData,
    // 新增导出
    fetchLatestCheckData,
    fetchIndexes,
    getIndexHistoryById,
    fetchLatestExamReport,
  }
})
