<template>
  <div class="ocr-review-view">
    <van-loading v-if="loading" size="24px" vertical class="page-loading">加载中...</van-loading>
    <div v-else-if="error" class="page-error">
      <van-empty :description="error" image="error">
        <van-button type="primary" @click="goBack">返回列表</van-button>
      </van-empty>
    </div>
    <OCRReviewLayout
      v-else-if="report"
      :report="report"
      :review-logs="reviewLogs"
      :can-review="canReview"
      :needs-review="needsReview"
      :edit-values="editValues"
      :submitting="submitting"
      @confirm="onConfirm"
      @back="goBack"
      @toggle-edit="toggleEditMode"
      @update-value="onUpdateValue"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast, showConfirmDialog } from 'vant'
import { getImageReportDetail } from '@/api/imageReport'
import { useOCRReview } from '@/composables/useOCRReview'
import OCRReviewLayout from '@/components/image-report/OCRReviewLayout.vue'

const route = useRoute()
const router = useRouter()

const report = ref(null)
const loading = ref(true)
const error = ref('')

const {
  submitting,
  canReview,
  needsReview,
  confirmAsReviewed,
  submitReview,
  editValues,
  reviewLogs,
  loadReviewLogs,
  updateEditValue,
  initEditValues,
  getModifiedCorrections
} = useOCRReview(report)

onMounted(async () => {
  const reportId = Number(route.params.id)
  if (!Number.isFinite(reportId) || reportId <= 0) {
    error.value = '无效的报告ID'
    loading.value = false
    return
  }
  try {
    report.value = await getImageReportDetail(reportId)
    await loadReviewLogs()
    initEditValues()
  } catch (e) {
    error.value = e.message || '加载报告失败'
  } finally {
    loading.value = false
  }
})

const onUpdateValue = (fieldName, value) => {
  updateEditValue(fieldName, value)
}

const onConfirm = async () => {
  // Use getModifiedCorrections to collect corrections from current edit state
  const modifiedCorrections = getModifiedCorrections()
  try {
    await showConfirmDialog({
      title: '确认审查',
      message: modifiedCorrections.length > 0
        ? `共修正 ${modifiedCorrections.length} 项指标，确认提交？`
        : '确认OCR识别结果无误？'
    })
  } catch {
    return
  }

  let success = false
  if (modifiedCorrections.length > 0) {
    success = await submitReview(modifiedCorrections)
  } else {
    success = await confirmAsReviewed()
  }

  if (success) {
    showSuccessToast('审查完成')
    goBack()
  }
}

const goBack = () => {
  router.push('/home/image-report?tab=list')
}
</script>

<style scoped>
.ocr-review-view {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-primary) 0%, var(--border-color) 100%);
  padding-bottom: var(--safe-bottom);
}

.page-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}

.page-error {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}
</style>
