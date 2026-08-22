<template>
  <div class="exam-detail">
    <BackgroundAnimation />
    <BackButton title="检查报告详情" />

    <div v-if="loading" class="loading-center">
      <van-loading />
    </div>

    <template v-else-if="record">
      <div class="detail-card">
        <div class="card-header">
          <div class="card-header-top">
            <h2 class="card-title">{{ record.title || examTypeLabel || '检查报告' }}</h2>
            <van-button
              class="export-btn"
              size="small"
              plain
              round
              icon="description-o"
              :loading="exporting"
              @click="handleExport"
            >
              导出
            </van-button>
            <van-button
              class="share-btn"
              size="small"
              plain
              round
              icon="share-o"
              @click="handleShare"
            >
              分享
            </van-button>
          </div>
          <div class="card-meta">
            <span v-if="record.medical_date">{{ formatDate(record.medical_date) }}</span>
            <span v-if="record.hospital">{{ record.hospital }}</span>
            <van-tag v-if="record.exam_type" type="primary">{{ examTypeLabel }}</van-tag>
          </div>
        </div>

        <!-- 报告原件 -->
        <div v-if="record.image_report_id" class="info-section">
          <div class="section-label">报告原件</div>
          <div class="original-report-btn" @click="handleViewOriginal">
            <van-icon name="eye-o" />
            <span>查看报告原件</span>
          </div>
        </div>

        <div v-if="record.exam_info" class="info-section">
          <div class="section-label">检查所见</div>
          <div class="section-content">{{ record.exam_info }}</div>
        </div>

        <div v-if="record.exam_diag" class="info-section">
          <div class="section-label">诊断意见</div>
          <div class="section-content">{{ record.exam_diag }}</div>
        </div>

        <div v-if="record.comment" class="info-section">
          <div class="section-label">备注</div>
          <div class="section-content">{{ record.comment }}</div>
        </div>
      </div>

      <!-- AI 解读区域 -->
      <div class="interpretation-section">
        <div class="section-header">
          <div class="section-title">AI 智能解读</div>
          <van-button
            v-if="!interpretation"
            type="primary"
            size="small"
            :loading="interpreting"
            @click="handleInterpret"
          >
            生成解读
          </van-button>
          <van-button
            v-else
            size="small"
            :loading="interpreting"
            @click="handleInterpret"
          >
            重新解读
          </van-button>
        </div>

        <van-notice-bar
          v-if="interpretation"
          left-icon="warning-o"
          text="AI解读仅供参考，不构成医疗诊断建议。如有疑问请咨询主治医生。"
          color="var(--warning-color)"
          background="var(--warning-alpha-10)"
          :scrollable="false"
          wrapable
        />

        <div v-if="interpretation" class="interpretation-content">
          <MarkdownRenderer :content="interpretation" />
          <div class="interpretation-time" v-if="record.interpretation_at">
            解读时间：{{ formatDate(record.interpretation_at) }}
          </div>
        </div>

        <div v-else-if="!interpreting" class="interpretation-hint">
          点击"生成解读"，AI 将为您分析检查报告中的关键发现及临床意义
        </div>
      </div>

      <!-- 图片预览弹窗 -->
      <ImagePreviewModal
        v-model:show="showImagePreview"
        :title="record?.title || '报告原件'"
        :image-url="previewImageUrl"
        :image-type="previewImageType"
        :loading="imageLoading"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { medicalApi } from '@/api/medical'
import { EXAM_TYPE_LABELS } from '@/styles/constants'
import { getImageData } from '@/api/imageReport'
import { shareApi } from '@/api/share'
import { exportApi } from '@/api/export'
const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import ImagePreviewModal from '@/components/report/ImagePreviewModal.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const interpreting = ref(false)
const exporting = ref(false)
const record = ref(null)

// 检查类型中文标签（与列表页/分享页口径一致：exam_type_name -> 映射表 -> 原始值）
const examTypeLabel = computed(() => {
  const r = record.value
  if (!r?.exam_type) return ''
  return r.exam_type_name || EXAM_TYPE_LABELS[r.exam_type] || r.exam_type
})
const interpretation = ref(null)
const showImagePreview = ref(false)
const previewImageUrl = ref('')
const previewImageType = ref('')
const imageLoading = ref(false)

async function handleInterpret() {
  const reportId = Number(route.params.id)
  if (!reportId) return

  if (interpretation.value) {
    try {
      await showConfirmDialog({
        title: '重新解读',
        message: '重新解读会覆盖当前解读结果，确定继续？',
      })
    } catch {
      return
    }
  }

  interpreting.value = true
  try {
    const res = await medicalApi.interpretExam(reportId)
    if (res?.data) {
      interpretation.value = res.data.interpretation
      if (record.value) {
        record.value.interpretation_at = res.data.interpretation_at
      }
      showToast('解读生成成功')
    }
  } catch (error) {
    const msg = error?.response?.data?.detail || '解读生成失败'
    showToast(msg)
  } finally {
    interpreting.value = false
  }
}

function formatDate(date) {
  if (!date) return ''
  const d = new Date(date)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function handleExport() {
  const reportId = Number(route.params.id)
  if (!reportId) return
  exporting.value = true
  try {
    // 响应拦截器已解包 response.data，这里拿到的直接就是 Blob
    const blob = await exportApi.exportExamReport(reportId)
    const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `检查报告_${reportId}.pdf`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
    showToast('导出成功')
  } catch (error) {
    showToast(error.response?.data?.detail || '导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleShare() {
  const reportId = Number(route.params.id)
  if (!reportId) return
  try {
    const res = await shareApi.createShareToken({
      content_type: 'exam_report',
      content_id: reportId,
    })
    const url = `${window.location.origin}/share/report/${res.token}`
    try {
      await navigator.clipboard.writeText(url)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = url
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    showToast('分享链接已复制到剪贴板')
  } catch (error) {
    showToast(error.response?.data?.detail || '分享失败')
  }
}

async function handleViewOriginal() {
  if (!record.value?.image_report_id) return
  showImagePreview.value = true
  imageLoading.value = true
  previewImageUrl.value = ''
  previewImageType.value = ''
  try {
    const res = await getImageData(record.value.image_report_id)
    if (res?.data?.image_data) {
      const imgData = res.data.image_data
      const imgType = res.data.image_type || 'jpeg'
      if (imgType === 'pdf') {
        previewImageUrl.value = imgData.startsWith('data:') ? imgData : `data:application/pdf;base64,${imgData}`
        previewImageType.value = 'pdf'
      } else {
        previewImageUrl.value = imgData.startsWith('data:') ? imgData : `data:image/${imgType};base64,${imgData}`
        previewImageType.value = ''
      }
    }
  } catch (e) {
    console.error('获取图片失败:', e)
    showImagePreview.value = false
  } finally {
    imageLoading.value = false
  }
}

onMounted(async () => {
  const reportId = Number(route.params.id)
  if (!reportId) {
    loading.value = false
    return
  }

  loading.value = true
  try {
    const data = await medicalApi.getExamReport(reportId)
    record.value = data

    // 加载已有解读
    if (data.interpretation) {
      interpretation.value = data.interpretation
    } else {
      try {
        const interpRes = await medicalApi.getExamInterpretation(reportId)
        if (interpRes?.data?.interpretation) {
          interpretation.value = interpRes.data.interpretation
        }
      } catch {
        // 无解读，忽略
      }
    }
  } catch (error) {
    console.error('获取报告详情失败:', error)
    showToast('获取报告详情失败')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.exam-detail {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.detail-card {
  background: var(--bg-surface);
  border-radius: 16px;
  margin: 16px;
  padding: 16px;
  box-shadow: 0 2px 12px var(--primary-alpha-8);
}

.card-header {
  margin-bottom: 16px;
}

.card-header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.share-btn {
  flex-shrink: 0;
  font-size: 12px;
}

.export-btn {
  flex-shrink: 0;
  font-size: 12px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  align-items: center;
}

.info-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--primary-alpha-10);
}

.section-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--primary-color);
  margin-bottom: 8px;
}

.section-content {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.original-report-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  color: var(--primary-color);
  font-size: 14px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.original-report-btn:active {
  opacity: 0.7;
}

.interpretation-section {
  background: var(--bg-surface);
  border-radius: 16px;
  margin: 16px;
  padding: 16px;
  box-shadow: 0 2px 12px var(--primary-alpha-8);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.interpretation-content {
  margin-top: 12px;
}

.interpretation-time {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 12px;
  text-align: right;
}

.interpretation-hint {
  font-size: 14px;
  color: var(--text-tertiary);
  text-align: center;
  padding: 24px;
}
</style>
