<template>
  <!-- 全屏预览容器 -->
  <div v-if="visible" class="document-preview-overlay" @click="handleOverlayClick" @touchmove.prevent>
    <div class="document-preview-container" @click.stop>
      <!-- 圆形关闭按钮 -->
      <div class="close-button" @click="handleClose">
        <van-icon name="cross" size="20" color="var(--preview-text)" />
      </div>

      <!-- 文档摘要 -->
      <div v-if="document?.summary" class="preview-summary">
        <div class="summary-label">AI 摘要</div>
        <div class="summary-content">{{ document.summary }}</div>
      </div>
      <div v-else-if="document?.summary_status === 'pending'" class="preview-summary preview-summary--pending">
        <van-loading size="14" /> <span>摘要生成中...</span>
      </div>

      <!-- 预览内容区域 -->
      <div class="preview-content">
        <van-loading v-if="loading" size="24px">加载中...</van-loading>

        <!-- HTML内容预览 (非图片文件) -->
        <div v-else-if="previewContent && isHtmlContent && !isImageFile" class="preview-html" v-html="safePreviewContent"></div>

        <!-- 图片预览 (HTML内容通过iframe显示，sandbox限制脚本执行) -->
        <iframe
          v-else-if="isImageFile && previewContent"
          :srcdoc="safePreviewContent"
          class="preview-iframe"
          frameborder="0"
          sandbox="allow-same-origin"
        ></iframe>

        <!-- 文本内容预览 -->
        <div v-else-if="previewContent" class="preview-text">
          {{ previewContent }}
        </div>

        <!-- PDF 内嵌预览 -->
        <iframe
          v-else-if="isPdfFile && pdfUrl"
          :src="pdfUrl"
          class="pdf-iframe"
          frameborder="0"
        ></iframe>

        <!-- 图片加载失败时的降级显示 -->
        <img
          v-else-if="isImageFile && imageUrl && !previewContent"
          :src="imageUrl"
          class="image-preview"
          alt="图片预览"
          @error="handleImageError"
          @load="handleImageLoad"
        />

        <!-- 不支持的文件类型 -->
        <div v-else class="preview-placeholder">
          <van-icon name="description" size="48" />
          <p>正在加载预览...</p>
          <p v-if="document">文件类型：{{ document.file_type?.toUpperCase() }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { showToast } from 'vant'
import { sanitizeHtml } from '@/utils/sanitize'
import { useUserStore } from '@/stores/user'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  document: {
    type: Object,
    default: null
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'close'])

// 响应式数据
const visible = ref(props.modelValue)
const loading = ref(false)
const previewContent = ref('')
const isHtmlContent = ref(false)
const pdfUrl = ref('about:blank')
const imageUrl = ref('about:blank')

// 计算属性
const isPdfFile = computed(() => {
  return props.document?.file_type?.toLowerCase() === 'pdf'
})

const isImageFile = computed(() => {
  const imageTypes = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
  return imageTypes.includes(props.document?.file_type?.toLowerCase())
})

const safePreviewContent = computed(() => {
  if (!previewContent.value) return previewContent.value
  // 对包含 HTML 的内容统一消毒（包括图片文件的 iframe srcdoc）
  if (isHtmlContent.value || isImageFile.value) return sanitizeHtml(previewContent.value)
  return previewContent.value
})

// 监听器
watch(() => props.modelValue, (newValue) => {
  visible.value = newValue
})

watch(visible, (newValue) => {
  emit('update:modelValue', newValue)
  // 预览打开时锁定 body 滚动，关闭时恢复
  document.body.style.overflow = newValue ? 'hidden' : ''
})

// 组件卸载时确保恢复 body 滚动
onUnmounted(() => {
  document.body.style.overflow = ''
})

watch(() => props.document, (doc) => {
  if (doc && visible.value) {
    loadPreview()
  }
})

// 方法 - 统一使用 fetch + Blob URL 方案，绕过 iframe 无法发送 header 的限制
const loadPreview = async () => {
  if (!props.document) return

  // 清理之前的 Blob URL 防止内存泄漏
  if (pdfUrl.value && pdfUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(pdfUrl.value)
  }
  if (imageUrl.value && imageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(imageUrl.value)
  }

  try {
    loading.value = true
    previewContent.value = ''
    isHtmlContent.value = false
    pdfUrl.value = 'about:blank'
    imageUrl.value = 'about:blank'

    // 获取token
    const userStore = useUserStore()
    const token = userStore.token
    if (!token) {
      showToast('请先登录')
      return
    }

    // 通过 fetch + Authorization header 获取文件
    const apiUrl = `/api/v1/knowledge/documents/${props.document.doc_id}/preview`
    const response = await fetch(apiUrl, {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!response.ok) {
      throw new Error(`加载失败 (${response.status})`)
    }

    const contentType = response.headers.get('Content-Type') || ''

    // PDF文件：创建 Blob URL 用于 iframe
    if (isPdfFile.value) {
      const blob = await response.blob()
      pdfUrl.value = URL.createObjectURL(blob)
      loading.value = false
      return
    }

    // 图片文件：创建 Blob URL 用于 img 标签
    if (isImageFile.value) {
      const blob = await response.blob()
      imageUrl.value = URL.createObjectURL(blob)
      loading.value = false
      return
    }

    // HTML预览（图片/PDF/Office全屏查看器）
    if (contentType.includes('text/html')) {
      const htmlContent = await response.text()
      previewContent.value = htmlContent
      isHtmlContent.value = true
    } else if (contentType.includes('text')) {
      previewContent.value = await response.text()
      isHtmlContent.value = false
    } else if (contentType.includes('application/json')) {
      const result = await response.json()
      if (result.data && result.data.content) {
        previewContent.value = result.data.content
      } else if (result.data && result.data.error) {
        throw new Error(result.data.message || result.data.error || '文档转换失败')
      } else {
        throw new Error(result.message || '无法预览此文件')
      }
    } else {
      // 二进制文件：创建 Blob URL 作为降级下载链接
      const blob = await response.blob()
      const blobUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = props.document.doc_name || 'document'
      a.click()
      URL.revokeObjectURL(blobUrl)
      showToast('文件已开始下载')
    }

  } catch (error) {
    console.error('预览失败:', error)
    showToast('预览失败: ' + error.message)
    previewContent.value = ''
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  visible.value = false
  previewContent.value = ''
  isHtmlContent.value = false
  pdfUrl.value = 'about:blank'
  imageUrl.value = 'about:blank'
  emit('close')
}

const handleOverlayClick = () => {
  handleClose()
}

const handleImageError = () => {
  console.error('图片加载失败')
  showToast('图片加载失败')
  // 可以在这里添加更多错误处理逻辑
}

const handleImageLoad = () => {
  // 图片加载成功
}

// 当对话框打开时加载预览
watch([visible, () => props.document], ([isVisible, doc]) => {
  if (isVisible && doc) {
    // 延迟加载，确保组件完全初始化
    nextTick(() => {
      loadPreview()
    })
  }
})

// 组件挂载时检查是否需要立即加载
onMounted(() => {
  // 如果组件挂载时对话框已经是显示状态，立即加载文档
  if (visible.value && props.document) {
    nextTick(() => {
      loadPreview()
    })
  }
})

// 组件卸载时清理 Blob URL 防止内存泄漏
onUnmounted(() => {
  if (pdfUrl.value && pdfUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(pdfUrl.value)
  }
  if (imageUrl.value && imageUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(imageUrl.value)
  }
})
</script>

<style scoped>
/* 全屏遮罩层 */
.document-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: var(--preview-overlay-bg);
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* 预览容器 */
.document-preview-container {
  width: 100%;
  height: 100%;
  background: var(--preview-overlay-bg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* 圆形关闭按钮 */
.close-button {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  min-width: 44px;
  min-height: 44px;
  background: var(--preview-toolbar-bg);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 1000;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.close-button:hover {
  background: var(--preview-close-bg);
  transform: scale(1.1);
}

.close-button:active {
  transform: scale(0.95);
}

/* 文档摘要 */
.preview-summary {
  padding: 12px 16px;
  margin: 48px 16px 0;
  background: var(--bg-elevated);
  border-radius: 8px;
  border-left: 3px solid var(--primary-color);
  max-height: 120px;
  overflow-y: auto;
}

.preview-summary--pending {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-tertiary);
  font-size: 13px;
}

.summary-label {
  font-size: 11px;
  color: var(--primary-color);
  font-weight: 600;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.summary-content {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* 预览内容区域 */
.preview-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
  background: var(--preview-overlay-bg);
}

/* PDF iframe */
.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: var(--bg-surface);
}

/* 图片预览iframe - 等宽显示，支持垂直滚动 */
.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: var(--bg-surface);
}

/* 图片预览 - 降级显示时的样式 */
.image-preview {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  display: block;
  margin: auto;
}

/* HTML预览 */
.preview-html {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  background: var(--bg-surface);
  border-radius: 8px;
  margin: 10px;
}

/* 调整HTML预览中的字体大小 */
.preview-html :deep(body) {
  font-size: 14px !important;
}

.preview-html :deep(h1) {
  font-size: 18px !important;
}

.preview-html :deep(h2) {
  font-size: 16px !important;
}

.preview-html :deep(h3) {
  font-size: 15px !important;
}

.preview-html :deep(h4) {
  font-size: 14px !important;
}

.preview-html :deep(h5) {
  font-size: 13px !important;
}

.preview-html :deep(h6) {
  font-size: 12px !important;
}

.preview-html :deep(p) {
  font-size: 14px !important;
  line-height: 1.5 !important;
}

.preview-html :deep(td) {
  font-size: 13px !important;
  padding: 6px 8px !important;
}

.preview-html :deep(th) {
  font-size: 13px !important;
  padding: 6px 8px !important;
}

.preview-html :deep(li) {
  font-size: 14px !important;
}

.preview-html :deep(.container) {
  padding: 8px !important;
}

/* 文本预览 */
.preview-text {
  width: 100%;
  height: 100%;
  padding: 20px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  overflow-y: auto;
  text-align: left;
  background: var(--bg-surface);
  border-radius: 8px;
  margin: 10px;
}

/* 占位符 */
.preview-placeholder {
  text-align: center;
  color: var(--preview-text);
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  margin: 20px;
  padding: 40px 20px;
}

.preview-placeholder .van-icon {
  margin-bottom: 12px;
  color: var(--preview-text);
  opacity: 0.8;
}

.preview-placeholder p {
  margin: 8px 0;
  color: var(--preview-text);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .close-button {
    top: 15px;
    right: 15px;
    width: 36px;
    height: 36px;
  }

  .preview-text {
    padding: 16px;
    font-size: 13px;
    margin: 5px;
  }

  .preview-html {
    margin: 5px;
  }

  .preview-placeholder {
    margin: 10px;
    padding: 30px 15px;
  }
}
</style>
