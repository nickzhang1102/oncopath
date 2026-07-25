<template>
  <div class="pathology-detail">
    <BackgroundAnimation />
    <BackButton title="病理报告详情" />

    <div v-if="loading" class="loading-center">
      <van-loading />
    </div>

    <template v-else-if="record">
      <div class="detail-card">
        <div class="card-header">
          <div class="card-header-top">
            <h2 class="card-title">{{ record.report_title || '病理报告' }}</h2>
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
            <span v-if="record.report_date">{{ formatDate(record.report_date) }}</span>
            <span v-if="record.hospital">{{ record.hospital }}</span>
          </div>
        </div>

        <!-- 报告原件 -->
        <div v-if="record.has_image" class="info-section">
          <div class="section-label">报告原件</div>
          <div class="original-report-btn" @click="handleViewOriginal">
            <van-icon name="eye-o" />
            <span>查看报告原件</span>
          </div>
        </div>

        <div v-if="record.diagnosis" class="info-section">
          <div class="section-label">病理诊断</div>
          <div class="section-content">{{ record.diagnosis }}</div>
        </div>

        <div v-if="record.cancer_type || record.stage || record.histology_type" class="info-section">
          <div class="section-label">诊断详情</div>
          <div class="tag-group">
            <span v-if="record.cancer_type" class="info-tag">癌种：{{ record.cancer_type }}</span>
            <span v-if="record.stage" class="info-tag">分期：{{ record.stage }}</span>
            <span v-if="record.histology_type" class="info-tag">组织学：{{ record.histology_type }}</span>
          </div>
        </div>

        <div v-if="ihcText" class="info-section">
          <div class="section-label">免疫组化</div>
          <div class="section-content">{{ ihcText }}</div>
        </div>

        <div v-if="record.gene_testing" class="info-section">
          <div class="section-label">基因检测</div>
          <div class="section-content">{{ record.gene_testing }}</div>
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
          点击"生成解读"，AI 将为您分析病理报告中的诊断结论及临床意义
        </div>
      </div>

      <!-- 图片预览弹窗 -->
      <ImagePreviewModal
        v-model:show="showImagePreview"
        :title="record?.report_title || '报告原件'"
        :image-url="previewImageUrl"
        :image-type="previewImageType"
        :loading="imageLoading"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { medicalApi } from '@/api/medical'
import { shareApi } from '@/api/share'
import { exportApi } from '@/api/export'
const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import ImagePreviewModal from '@/components/report/ImagePreviewModal.vue'

const route = useRoute()

const loading = ref(false)
const interpreting = ref(false)
const exporting = ref(false)
const record = ref(null)
const interpretation = ref(null)
const showImagePreview = ref(false)
const previewImageUrl = ref('')
const previewImageType = ref('')
const imageLoading = ref(false)

const ihcText = computed(() => {
  if (!record.value) return ''
  const r = record.value
  if (r.ihc_markers?.length) {
    return r.ihc_markers.map(m => 
      `${m.marker_name}：${m.result || ''}${m.intensity ? ' (' + m.intensity + ')' : ''}${m.percentage ? ' 阳性' + m.percentage : ''}`
    ).join('\n')
  }
  return r.immunohistochemistry || ''
})

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
    const res = await medicalApi.interpretPathology(reportId)
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
    const res = await exportApi.exportPathologyReport(reportId)
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `病理报告_${reportId}.pdf`
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
      content_type: 'pathology_report',
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
  if (!record.value?.has_image) return
  const reportId = Number(route.params.id)
  showImagePreview.value = true
  imageLoading.value = true
  previewImageUrl.value = ''
  previewImageType.value = ''
  try {
    const data = await medicalApi.getPathologyImage(reportId)
    if (data?.image_data) {
      if (data.image_data.startsWith('data:')) {
        previewImageUrl.value = data.image_data
        previewImageType.value = data.image_data.startsWith('data:application/pdf') ? 'pdf' : ''
      } else {
        const imgType = data.image_type || 'jpeg'
        const mimeType = imgType === 'pdf' ? 'application/pdf' : `image/${imgType}`
        previewImageUrl.value = `data:${mimeType};base64,${data.image_data}`
        previewImageType.value = imgType === 'pdf' ? 'pdf' : ''
      }
    }
  } catch (e) {
    console.error('获取病理图片失败:', e)
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
    const data = await medicalApi.getPathologyReport(reportId)
    record.value = data

    // 加载已有解读
    if (data.interpretation) {
      interpretation.value = data.interpretation
    } else {
      try {
        const interpRes = await medicalApi.getPathologyInterpretation(reportId)
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
.pathology-detail {
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

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.info-tag {
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 2px 10px;
  border-radius: 4px;
  line-height: 1.6;
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

.image-preview {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80px;
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
  padding: 16px;
}
</style>
