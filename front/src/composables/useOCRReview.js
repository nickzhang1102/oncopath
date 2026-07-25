/**
 * OCR 审查逻辑 composable
 * 提取自 ReportDetail.vue，供 OCRReviewView 和 ReportDetail 复用
 */
import { ref, computed } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { submitOCRReview, getOCRReviews } from '@/api/imageReport'
import { OCR_STATUS_TAG_TYPE, OCR_STATUS_TEXT } from '@/styles/constants'

export function useOCRReview(reportRef) {
  const isEditMode = ref(false)
  const editValues = ref({})
  const submitting = ref(false)
  const reviewLogs = ref([])

  // 是否可审查
  const canReview = computed(() => {
    const report = reportRef.value
    if (!report) return false
    return report.ocr_status === 'pending_review' || report.ocr_status === 'completed' || report.ocr_status === 'failed'
  })

  // 是否需要审查（还未审查过）
  const needsReview = computed(() => {
    const report = reportRef.value
    if (!report) return false
    return report.ocr_status !== 'reviewed'
  })

  // OCR 状态标签类型
  const ocrStatusType = computed(() => {
    const report = reportRef.value
    if (!report) return 'default'
    return OCR_STATUS_TAG_TYPE[report.ocr_status] || 'default'
  })

  // OCR 状态文字
  const ocrStatusText = computed(() => {
    const report = reportRef.value
    if (!report) return ''
    return OCR_STATUS_TEXT[report.ocr_status] || report.ocr_status
  })

  // 获取修正后的值（优先显示审查修正值）
  const getCorrectedValue = (indicator) => {
    const log = reviewLogs.value.find(l => l.field_name === indicator.raw_name)
    if (log && log.corrected_value) {
      return log.corrected_value
    }
    return indicator.value
  }

  // 切换编辑模式
  const toggleEditMode = () => {
    if (isEditMode.value) {
      isEditMode.value = false
      editValues.value = {}
      return
    }
    // 初始化编辑值
    const values = {}
    const report = reportRef.value
    if (report?.matching_details?.indicators) {
      for (const indicator of report.matching_details.indicators) {
        const log = reviewLogs.value.find(l => l.field_name === indicator.raw_name)
        values[indicator.raw_name] = log?.corrected_value || ''
      }
    }
    editValues.value = values
    isEditMode.value = true
  }

  // 收集所有修改过的指标 corrections（统一逻辑，避免与 submitReview 不同步）
  const getModifiedCorrections = () => {
    const corrections = []
    const report = reportRef.value
    if (report?.matching_details?.indicators) {
      for (const indicator of report.matching_details.indicators) {
        const newValue = editValues.value[indicator.raw_name]
        // 显式空值检查，避免 falsy 值（如数字 0）被跳过
        if (newValue !== undefined && newValue !== null && newValue !== '' && newValue !== indicator.value) {
          corrections.push({
            field_name: indicator.raw_name,
            original_value: indicator.value,
            corrected_value: newValue
          })
        }
      }
    }
    return corrections
  }

  // 提交修正（可接受预收集的 corrections，避免二次收集导致不一致）
  const submitReview = async (preCollectedCorrections = null) => {
    const report = reportRef.value
    if (!report) return false

    const corrections = preCollectedCorrections || getModifiedCorrections()

    if (corrections.length === 0) {
      showToast('没有修改任何指标')
      isEditMode.value = false
      return false
    }

    submitting.value = true
    try {
      await submitOCRReview(report.report_id, {
        report_type: report.report_type || 'lab',
        corrections
      })
      showSuccessToast('修正已提交')
      isEditMode.value = false
      editValues.value = {}
      await loadReviewLogs()
      return true
    } catch (error) {
      showToast(error.message || '提交修正失败')
      return false
    } finally {
      submitting.value = false
    }
  }

  // 确认无误 - 不修改任何值，直接提交审查
  const confirmAsReviewed = async () => {
    const report = reportRef.value
    if (!report) return false

    submitting.value = true
    try {
      await submitOCRReview(report.report_id, {
        report_type: report.report_type || 'lab',
        corrections: []
      })
      showSuccessToast('已确认')
      await loadReviewLogs()
      return true
    } catch (error) {
      showToast(error.message || '确认失败')
      return false
    } finally {
      submitting.value = false
    }
  }

  // 加载审查记录
  const loadReviewLogs = async () => {
    const report = reportRef.value
    if (!report) return
    try {
      const res = await getOCRReviews(report.report_id)
      reviewLogs.value = res.items || []
    } catch {
      reviewLogs.value = []
    }
  }

  // 状态文字映射（指标正常/异常状态）
  const getStatusText = (status) => {
    const statusMap = {
      normal: '正常',
      high: '偏高',
      low: '偏低',
      abnormal: '异常'
    }
    return statusMap[status] || status
  }

  // 更新单个指标编辑值
  const updateEditValue = (fieldName, value) => {
    editValues.value[fieldName] = value
  }

  // 初始化所有指标的编辑值（空字符串，不等于原值即未修改）
  const initEditValues = () => {
    const values = {}
    const report = reportRef.value
    if (report?.matching_details?.indicators) {
      for (const indicator of report.matching_details.indicators) {
        values[indicator.raw_name] = ''
      }
    }
    editValues.value = values
  }

  return {
    isEditMode,
    editValues,
    submitting,
    reviewLogs,
    canReview,
    needsReview,
    ocrStatusType,
    ocrStatusText,
    getCorrectedValue,
    toggleEditMode,
    submitReview,
    confirmAsReviewed,
    loadReviewLogs,
    getStatusText,
    updateEditValue,
    initEditValues,
    getModifiedCorrections
  }
}
