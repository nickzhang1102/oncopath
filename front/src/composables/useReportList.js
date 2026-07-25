import { ref, computed, onMounted, watch } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { shareApi } from '@/api/share'
import dayjs from 'dayjs'

/**
 * 报告列表通用逻辑 composable
 * @param {Object} options
 * @param {Function} options.fetchFn - (patientId, {offset, limit}) => Promise<data[]>
 * @param {Function} options.deleteFn - (report) => Promise<void>
 * @param {string} options.shareContentType - 'exam_report' | 'pathology_report'
 * @param {Function} options.shareContentIdFn - (report) => number 获取分享用的 content_id
 * @param {string} options.deleteConfirmMsg - 删除确认消息
 * @param {string} options.dateField - 报告日期字段名 'medical_date' | 'report_date'
 */
export function useReportList(options) {
  const {
    fetchFn,
    deleteFn,
    shareContentType,
    shareContentIdFn,
    deleteConfirmMsg = '确定要删除该报告吗？删除后无法恢复。',
    dateField = 'medical_date',
  } = options

  const patientStore = usePatientStore()

  // 列表状态
  const loading = ref(false)
  const refreshing = ref(false)
  const loadingMore = ref(false)
  const finished = ref(false)
  const reports = ref([])
  const pageSize = 20
  const currentOffset = ref(0)

  // 图片预览状态
  const showImagePreview = ref(false)
  const previewImageUrl = ref('')
  const currentReport = ref(null)
  const imageLoading = ref(false)

  // 患者状态
  const hasPatient = computed(() => !!patientStore.currentPatient)

  // 最近日期
  const getLatestDate = computed(() => {
    if (reports.value.length === 0) return '-'
    const sorted = [...reports.value].sort((a, b) =>
      new Date(b[dateField]) - new Date(a[dateField])
    )
    return formatDate(sorted[0][dateField])
  })

  function formatDate(date) {
    if (!date) return ''
    return dayjs(date).format('YYYY-MM-DD')
  }

  async function fetchReports() {
    if (!patientStore.currentPatient) return

    loading.value = true
    currentOffset.value = 0
    try {
      const data = await fetchFn(patientStore.currentPatient.patient_id, {
        offset: 0,
        limit: pageSize,
      })
      reports.value = data || []
      currentOffset.value = reports.value.length
      finished.value = reports.value.length < pageSize
    } catch (error) {
      console.error('获取报告失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function onRefresh() {
    try {
      await fetchReports()
    } finally {
      refreshing.value = false
    }
  }

  async function onLoadMore() {
    if (!patientStore.currentPatient) return
    try {
      const data = await fetchFn(patientStore.currentPatient.patient_id, {
        offset: currentOffset.value,
        limit: pageSize,
      })
      const newReports = data || []
      reports.value.push(...newReports)
      currentOffset.value = reports.value.length
      finished.value = newReports.length < pageSize
    } catch (error) {
      console.error('加载更多失败:', error)
      finished.value = true
    } finally {
      loadingMore.value = false
    }
  }

  async function handleDelete(report) {
    try {
      await showConfirmDialog({
        title: '确认删除',
        message: deleteConfirmMsg,
      })
      await deleteFn(report)
      showToast('删除成功')
      await fetchReports()
    } catch (error) {
      if (error !== 'cancel') {
        showToast(error.response?.data?.detail || '删除失败')
      }
    }
  }

  async function handleShare(report) {
    try {
      const res = await shareApi.createShareToken({
        content_type: shareContentType,
        content_id: shareContentIdFn(report),
      })
      const url = `${window.location.origin}/share/report/${res.token}`
      await navigator.clipboard.writeText(url)
      showToast('分享链接已复制到剪贴板')
    } catch (error) {
      showToast(error.response?.data?.detail || '分享失败')
    }
  }

  function openImagePreview(report) {
    currentReport.value = report
    previewImageUrl.value = ''
    showImagePreview.value = true
  }

  // 患者切换自动重载
  watch(() => patientStore.currentPatient?.patient_id, async (newId, oldId) => {
    if (newId && newId !== oldId) {
      await fetchReports()
    }
  })

  onMounted(async () => {
    await fetchReports()
  })

  return {
    // 状态
    loading,
    refreshing,
    loadingMore,
    finished,
    reports,
    hasPatient,
    showImagePreview,
    previewImageUrl,
    currentReport,
    imageLoading,
    // 计算
    getLatestDate,
    // 方法
    formatDate,
    fetchReports,
    onRefresh,
    onLoadMore,
    handleDelete,
    handleShare,
    openImagePreview,
  }
}