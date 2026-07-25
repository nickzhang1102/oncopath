<template>
  <div class="ocr-review-layout">
    <van-nav-bar
      :title="'OCR审查 - ' + (report.title || '报告')"
      left-arrow
      @click-left="$emit('back')"
      fixed
      placeholder
      :safe-area-inset-top="true"
    >
      <template #right>
        <van-tag
          v-if="report.ocr_status"
          :type="ocrStatusTagType"
          size="medium"
        >
          {{ ocrStatusText }}
        </van-tag>
      </template>
    </van-nav-bar>

    <!-- Desktop dual-column layout -->
    <div v-if="isDesktop" class="layout-desktop">
      <div class="column column-image">
        <OCRImageViewer
          :src="imageUrl"
          :highlight-bbox="highlightBbox"
          :image-type="imageType"
        />
      </div>
      <div class="column column-data">
        <div class="section ocr-text-section">
          <div class="section-header" @click="toggleOcrText">
            <span class="section-title">OCR 识别原文</span>
            <van-icon :name="showOcrText ? 'arrow-up' : 'arrow-down'" />
          </div>
          <div v-show="showOcrText" class="ocr-text-content">
            <pre>{{ report.ocr_text || '无OCR文本' }}</pre>
          </div>
        </div>
        <!-- 检验指标列表 -->
        <OCRIndicatorList
          v-if="indicators.length > 0"
          :indicators="indicators"
          :review-logs="reviewLogs"
          :can-review="canReview"
          :edit-values="editValues"
          @indicator-click="onIndicatorClick"
          @toggle-edit="onToggleEdit"
          @update-value="onUpdateValue"
        />
        <!-- 非检验报告：LLM 提取信息 -->
        <div v-else-if="extractedFields.length > 0" class="section">
          <div class="section-title">{{ extractedInfoTitle }}</div>
          <div class="extracted-fields">
            <div v-for="field in extractedFields" :key="field.label" class="extracted-item">
              <div class="extracted-label">{{ field.label }}</div>
              <div class="extracted-value">{{ field.value }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Mobile collapsible layout -->
    <div v-else class="layout-mobile">
      <div class="section">
        <div class="section-header" @click="showImage = !showImage">
          <span class="section-title">原始报告</span>
          <van-icon :name="showImage ? 'arrow-up' : 'arrow-down'" />
        </div>
        <div v-show="showImage">
          <OCRImageViewer
            :src="imageUrl"
            :highlight-bbox="highlightBbox"
            :image-type="imageType"
            :compact="true"
          />
        </div>
      </div>
      <div class="section">
        <div class="section-header" @click="showOcrText = !showOcrText">
          <span class="section-title">OCR 识别原文</span>
          <van-icon :name="showOcrText ? 'arrow-up' : 'arrow-down'" />
        </div>
        <div v-show="showOcrText" class="ocr-text-content">
          <pre>{{ report.ocr_text || '无OCR文本' }}</pre>
        </div>
      </div>
      <!-- 检验指标列表 -->
      <OCRIndicatorList
        v-if="indicators.length > 0"
        :indicators="indicators"
        :review-logs="reviewLogs"
        :can-review="canReview"
        :is-edit-mode="isEditMode"
        :edit-values="editValues"
        @indicator-click="onIndicatorClick"
        @toggle-edit="onToggleEdit"
        @update-value="onUpdateValue"
      />
      <!-- 非检验报告：LLM 提取信息 -->
      <div v-else-if="extractedFields.length > 0" class="section">
        <div class="section-title">{{ extractedInfoTitle }}</div>
        <div class="extracted-fields">
          <div v-for="field in extractedFields" :key="field.label" class="extracted-item">
            <div class="extracted-label">{{ field.label }}</div>
            <div class="extracted-value">{{ field.value }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom action bar -->
    <div class="bottom-actions">
      <van-button @click="$emit('back')" class="action-btn">
        返回列表
      </van-button>
      <div class="action-spacer"></div>
      <van-button
        v-if="canReview && needsReview"
        type="primary"
        :loading="submitting"
        @click="onConfirmReview"
        class="action-btn action-confirm"
      >
        确认无误
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useResponsive } from '@/composables/useResponsive'
import { useUserStore } from '@/stores/user'
import { OCR_STATUS_TAG_TYPE, OCR_STATUS_TEXT } from '@/styles/constants'
import { useGeneTesting } from '@/composables/useGeneTesting'
import { getImageData } from '@/api/imageReport'
import OCRImageViewer from './OCRImageViewer.vue'
import OCRIndicatorList from './OCRIndicatorList.vue'

const EXAM_FIELD_MAP = {
  exam_findings: '检查所见',
  diagnosis: '诊断意见',
  key_findings: '关键发现',
  exam_type: '检查类型',
  exam_part: '检查部位',
}

const PATHOLOGY_FIELD_MAP = {
  pathology_diagnosis: '病理诊断',
  histology_type: '组织学类型',
  tumor_stage: '肿瘤分期',
  ihc_results: '免疫组化',
  gene_testing: '基因检测',
  key_findings: '关键发现',
  tumor_size: '肿瘤大小',
  differentiation: '分化程度',
  invasion_depth: '浸润深度',
  lymph_nodes: '淋巴结',
  margin_status: '切缘状态',
}

const props = defineProps({
  report: { type: Object, required: true },
  reviewLogs: { type: Array, default: () => [] },
  canReview: { type: Boolean, default: false },
  needsReview: { type: Boolean, default: true },
  editValues: { type: Object, default: () => ({}) },
  submitting: { type: Boolean, default: false }
})

const emit = defineEmits(['confirm', 'back', 'indicator-click', 'toggle-edit', 'update-value'])

const { isDesktop } = useResponsive()
const userStore = useUserStore()

const showOcrText = ref(true)
const showImage = ref(false)
const highlightBbox = ref(null)

const indicators = computed(() => {
  return props.report.matching_details?.indicators || []
})

const extractedInfoTitle = computed(() => {
  const type = props.report.report_type
  if (type === 'exam') return '检查信息'
  if (type === 'pathology') return '病理信息'
  return '提取信息'
})

const extractedFields = computed(() => {
  const info = props.report.extracted_info
  if (!info || typeof info !== 'object') return []

  const fieldMap = props.report.report_type === 'pathology' ? PATHOLOGY_FIELD_MAP : EXAM_FIELD_MAP
  const fields = []
  for (const [key, label] of Object.entries(fieldMap)) {
    if (info[key]) {
      let value = info[key]
      // 基因检测结构化展示：OCR 返回的是对象，转为 JSON 字符串后用 composable 解析
      if (key === 'gene_testing') {
        const rawStr = typeof value === 'object' ? JSON.stringify(value) : String(value)
        const rawRef = ref(rawStr)
        const { display } = useGeneTesting(rawRef)
        value = display.value || rawStr
      } else if (typeof value === 'object') {
        value = JSON.stringify(value)
      }
      fields.push({ label, value })
    }
  }
  return fields
})

const imageUrl = computed(() => {
  if (fullImageData.value) return fullImageData.value
  if (props.report.image_data) return props.report.image_data
  if (props.report.thumbnail_url) {
    const token = userStore.token
    return `/api/v1${props.report.thumbnail_url}?token=${encodeURIComponent(token)}`
  }
  return ''
})

const imageType = computed(() => {
  return props.report.image_type || ''
})

// 异步加载完整图片（详情页不再内联 image_data，需单独请求）
const fullImageData = ref('')
watch(() => props.report?.image_url, async (url) => {
  fullImageData.value = ''
  if (!url && !props.report?.report_id) return
  // 有 image_data 时无需额外请求
  if (props.report?.image_data) return
  try {
    const reportId = props.report.report_id
    const resp = await getImageData(reportId)
    if (resp?.data?.image_data) {
      fullImageData.value = resp.data.image_data
    }
  } catch (e) {
    console.warn('加载完整图片失败，将使用缩略图', e)
  }
}, { immediate: true })

const ocrStatusTagType = computed(() => {
  return OCR_STATUS_TAG_TYPE[props.report.ocr_status] || 'default'
})

const ocrStatusText = computed(() => {
  return OCR_STATUS_TEXT[props.report.ocr_status] || props.report.ocr_status
})

const toggleOcrText = () => {
  showOcrText.value = !showOcrText.value
}

const onIndicatorClick = (indicator) => {
  highlightBbox.value = indicator.bbox || null
}

const onToggleEdit = () => {
  emit('toggle-edit')
}

const onUpdateValue = (fieldName, value) => {
  emit('update-value', fieldName, value)
}

const onConfirmReview = () => {
  emit('confirm')
}
</script>

<style scoped>
.ocr-review-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding-bottom: calc(70px + var(--safe-bottom));
}

.layout-desktop {
  display: flex;
  gap: 16px;
  padding: 16px;
  flex: 1;
}

.column-image {
  flex: 1;
  min-width: 0;
}

.column-data {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.layout-mobile {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section {
  background: var(--bg-surface-alpha);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(10px);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
}

.ocr-text-content {
  margin-top: 8px;
  background: var(--bg-elevated);
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-secondary);
}

.ocr-text-content pre {
  margin: 0;
  font-family: inherit;
}

/* LLM 提取信息 */
.extracted-fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.extracted-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  background: var(--bg-elevated);
  border-radius: 8px;
}

.extracted-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.extracted-value {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.bottom-actions {
  position: fixed;
  bottom: var(--safe-bottom);
  left: 0;
  right: 0;
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-surface-alpha);
  backdrop-filter: blur(10px);
  box-shadow: 0 -4px 12px var(--primary-alpha-8);
  z-index: 100;
}

.action-btn {
  height: 44px;
  border-radius: 8px;
}

.action-spacer {
  flex: 1;
}

.action-confirm {
  min-width: 140px;
}

:deep(.van-nav-bar) {
  background: var(--bg-surface-alpha);
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  backdrop-filter: blur(10px);
}

:deep(.van-nav-bar__title) {
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
}

:deep(.van-icon-arrow-left) {
  color: var(--primary-color);
}

:deep(.van-button--primary) {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

:deep(.van-button--default) {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

@media (min-width: 768px) {
  .ocr-review-layout {
    max-width: 1200px;
    margin: 0 auto;
    --bottom-bar-height: 68px;
    padding-bottom: calc(var(--bottom-bar-height) + var(--space-4));
  }

  .bottom-actions {
    max-width: 1200px;
    left: 50%;
    transform: translateX(-50%);
  }
}
</style>