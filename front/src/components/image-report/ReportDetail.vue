<template>
  <div class="report-detail">
    <van-nav-bar
      title="报告详情"
      left-arrow
      @click-left="$emit('close')"
    />

    <div class="detail-content" v-if="report">
      <!-- 图片/PDF 区域 -->
      <div class="image-section">
        <iframe
          v-if="isPdfReport"
          :src="pdfBlobUrl"
          class="pdf-iframe"
          frameborder="0"
        />
        <img v-else :src="getImageUrl(report)" alt="报告图片" class="report-image" />
      </div>

      <!-- 基本信息 -->
      <van-cell-group inset>
        <van-cell title="报告标题" :value="report.title" />
        <van-cell title="分类" :value="report.category" />
        <van-cell title="医院" :value="report.hospital || '-'" />
        <van-cell title="科室" :value="report.department || '-'" />
        <van-cell title="检查日期" :value="formatDate(report.capture_date)" />
        <van-cell title="上传时间" :value="formatDateTime(report.upload_date)" />
        <van-cell title="标签" :value="formatTags(report.tags)" />
        <van-cell title="描述" :value="report.description || '-'" />
        <van-cell title="备注" :value="report.notes || '-'" />
      </van-cell-group>

      <!-- OCR 状态 -->
      <div class="ocr-status-section" v-if="report.ocr_status">
        <div class="section-title">OCR状态</div>
        <van-tag :type="ocrStatusType" size="medium">{{ ocrStatusText }}</van-tag>
      </div>

      <!-- OCR 结果 -->
      <div class="ocr-section" v-if="report.ocr_text">
        <div class="section-title">OCR识别结果</div>
        <div class="ocr-content">
          <pre>{{ report.ocr_text }}</pre>
        </div>
      </div>

      <!-- 指标匹配结果（含审查修正） -->
      <div class="indicators-section" v-if="report.matching_details && report.matching_details.indicators">
        <div class="section-header">
          <div class="section-title">识别指标 ({{ report.matched_count }}/{{ report.total_count }} 匹配)</div>
          <van-button
            v-if="canReview"
            size="small"
            type="primary"
            plain
            @click="toggleEditMode"
          >
            {{ isEditMode ? '完成修正' : '修正指标' }}
          </van-button>
        </div>
        <div class="indicators-list">
          <div
            v-for="(indicator, index) in report.matching_details.indicators"
            :key="index"
            class="indicator-item"
          >
            <div class="indicator-name">{{ indicator.raw_name }}</div>
            <div class="indicator-value" v-if="!isEditMode">
              {{ getCorrectedValue(indicator) }} {{ indicator.unit || '' }}
            </div>
            <div class="indicator-edit" v-else>
              <van-field
                v-model="editValues[indicator.raw_name]"
                :placeholder="indicator.value || ''"
                size="small"
                input-align="right"
              />
            </div>
            <div class="indicator-status" :class="indicator.status">
              {{ getStatusText(indicator.status) }}
            </div>
          </div>
        </div>
        <!-- 提交修正按钮 -->
        <div class="review-actions" v-if="isEditMode">
          <van-button type="primary" block @click="submitReview" :loading="submitting">
            提交修正
          </van-button>
        </div>

        <!-- 确认无误按钮（非编辑模式且可审查时显示） -->
        <div class="review-actions" v-if="!isEditMode && canReview && needsReview">
          <van-button type="success" block @click="confirmAsReviewed" :loading="submitting">
            确认无误
          </van-button>
        </div>
      </div>

      <!-- 审查历史 -->
      <div class="review-history" v-if="reviewLogs.length > 0">
        <div class="section-title">审查记录</div>
        <div class="review-list">
          <div v-for="log in reviewLogs" :key="log.id" class="review-item">
            <div class="review-field">{{ log.field_name }}</div>
            <div class="review-change">
              <span class="old-value">{{ log.original_value || '-' }}</span>
              <span class="arrow">→</span>
              <span class="new-value">{{ log.corrected_value || '-' }}</span>
            </div>
            <div class="review-time">{{ formatDateTime(log.reviewed_at) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, toRef, onUnmounted } from 'vue'
import { useOCRReview } from '@/composables/useOCRReview'
import { getImageData } from '@/api/imageReport'

const props = defineProps({
  report: {
    type: Object,
    required: true
  }
})

defineEmits(['close'])

const reportRef = toRef(props, 'report')

const {
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
  getStatusText
} = useOCRReview(reportRef)

const fullImageData = ref('')

const getImageUrl = (report) => {
  if (fullImageData.value) return fullImageData.value
  if (report.image_data) {
    return report.image_data
  }
  return 'data:image/svg+xml,' + encodeURIComponent(`
    <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
      <rect width="200" height="200" fill="var(--border-light)" rx="12"/>
      <text x="100" y="100" font-size="40" text-anchor="middle" dominant-baseline="middle">📷</text>
    </svg>
  `)
}

// 异步加载完整图片（详情页不再内联 image_data）
watch(() => props.report?.report_id, async (id) => {
  fullImageData.value = ''
  if (!id) return
  if (props.report?.image_data) return
  try {
    const resp = await getImageData(id)
    if (resp?.data?.image_data) {
      fullImageData.value = resp.data.image_data
    }
  } catch (e) {
    console.warn('加载完整图片失败', e)
  }
}, { immediate: true })

const isPdfReport = computed(() => {
  if (props.report.image_type === 'pdf') return true
  const url = getImageUrl(props.report)
  return url.startsWith('data:application/pdf')
})

// PDF Blob URL，解决 iframe 无法渲染超长 data URI
const pdfBlobUrl = ref('')
let _currentBlobUrl = ''

function revokePdfBlob() {
  if (_currentBlobUrl) {
    URL.revokeObjectURL(_currentBlobUrl)
    _currentBlobUrl = ''
  }
}

function dataUriToBlob(dataUri) {
  const parts = dataUri.split(',')
  const mimeMatch = parts[0].match(/:(.*?);/)
  const mime = mimeMatch ? mimeMatch[1] : 'application/pdf'
  const b64 = atob(parts[1])
  const buf = new Uint8Array(b64.length)
  for (let i = 0; i < b64.length; i++) buf[i] = b64.charCodeAt(i)
  return new Blob([buf], { type: mime })
}

watch(() => props.report?.image_data, (newData) => {
  revokePdfBlob()
  if (isPdfReport.value && newData && newData.startsWith('data:')) {
    try {
      const blob = dataUriToBlob(newData)
      _currentBlobUrl = URL.createObjectURL(blob)
      pdfBlobUrl.value = _currentBlobUrl
    } catch {
      pdfBlobUrl.value = newData
    }
  } else {
    pdfBlobUrl.value = ''
  }
}, { immediate: true })

onUnmounted(() => {
  revokePdfBlob()
})

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

const formatTags = (tags) => {
  if (!tags || !Array.isArray(tags) || tags.length === 0) return '-'
  return tags.join(', ')
}

onMounted(() => {
  loadReviewLogs()
})

watch(() => props.report?.report_id, () => {
  loadReviewLogs()
})
</script>

<style scoped>
.report-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, var(--bg-primary) 0%, var(--border-color) 100%);
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.image-section {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

.report-image {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  border-radius: 8px;
}

.pdf-iframe {
  width: 100%;
  height: 400px;
  border: none;
  border-radius: 8px;
}

.ocr-status-section,
.ocr-section,
.indicators-section,
.review-history {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.section-header .section-title {
  margin-bottom: 0;
}

.ocr-content {
  background: var(--bg-elevated);
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.ocr-content pre {
  margin: 0;
  font-family: inherit;
}

.indicators-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.indicator-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-elevated);
  border-radius: 8px;
  gap: 8px;
}

.indicator-name {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.indicator-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
  white-space: nowrap;
}

.indicator-edit {
  width: 120px;
  flex-shrink: 0;
}

.indicator-edit :deep(.van-field) {
  padding: 4px 8px;
  background: var(--bg-elevated);
}

.indicator-status {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  flex-shrink: 0;
}

.indicator-status.normal { background: var(--status-normal-bg); color: var(--success-color); }
.indicator-status.high { background: var(--status-danger-bg); color: var(--danger-color); }
.indicator-status.low { background: var(--status-warning-bg); color: var(--warning-color); }
.indicator-status.abnormal { background: var(--status-danger-bg); color: var(--danger-color); }

.review-actions {
  margin-top: 12px;
}

.review-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-elevated);
  border-radius: 8px;
  gap: 8px;
  font-size: 13px;
}

.review-field {
  font-weight: 500;
  color: var(--text-primary);
  min-width: 60px;
}

.review-change {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
}

.old-value {
  color: var(--text-secondary);
  text-decoration: line-through;
}

.arrow {
  color: var(--text-hint);
}

.new-value {
  color: var(--primary-color);
  font-weight: 500;
}

.review-time {
  color: var(--text-hint);
  font-size: 12px;
  white-space: nowrap;
}
</style>