<template>
  <!-- PDF预览组件 - 全屏iframe版本 -->
  <div v-if="visible" class="pdf-preview-overlay">
    <!-- 圆形关闭按钮 -->
    <div class="close-button" @click="handleClose">
      <van-icon name="cross" size="20" color="var(--preview-text)" />
    </div>

    <!-- 全屏iframe -->
    <iframe
      v-if="previewUrl"
      :src="previewUrl"
      class="preview-iframe"
      frameborder="0"
      @load="handleIframeLoad"
      @error="handleIframeError"
    ></iframe>

    <!-- 加载提示 -->
    <div v-if="loading" class="loading-overlay">
      <van-loading size="24px" color="var(--preview-text)">加载中...</van-loading>
    </div>

    <!-- 加载失败提示 -->
    <div v-if="error" class="error-overlay">
      <van-icon name="description" size="48" color="var(--preview-text)" />
      <p>PDF加载失败</p>
      <p class="error-hint">请检查网络连接或稍后重试</p>
      <van-button size="small" type="primary" @click="retryLoad">重试</van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { showToast } from 'vant'
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
const loading = ref(false)
const error = ref(false)
const previewUrl = ref('')

// 计算属性
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 监听显示状态变化
watch(visible, (newValue) => {
  if (newValue) {
    document.body.style.overflow = 'hidden'
    // 延迟构建预览URL，确保组件完全初始化
    nextTick(() => {
      buildPreviewUrl()
    })
  } else {
    document.body.style.overflow = ''
    previewUrl.value = ''
    error.value = false
  }
})

// 监听文档对象变化
watch(() => props.document, (newDoc, oldDoc) => {
  if (visible.value && newDoc && newDoc !== oldDoc) {
    nextTick(() => {
      buildPreviewUrl()
    })
  }
})

// 组件挂载时检查是否需要立即加载
onMounted(() => {
  // 如果组件挂载时对话框已经是显示状态，立即构建URL
  if (visible.value && props.document) {
    nextTick(() => {
      buildPreviewUrl()
    })
  }
})

// 组件卸载前清理 body overflow 锁定（防止路由切换时页面无法滚动）
onBeforeUnmount(() => {
  document.body.style.overflow = ''
})

// 构建预览URL
const buildPreviewUrl = () => {
  if (!props.document) {
    showToast('文档信息缺失')
    error.value = true
    loading.value = false
    return
  }

  try {
    loading.value = true
    error.value = false

    const userStore = useUserStore()
    const token = userStore.token
    if (!token) {
      showToast('请先登录')
      error.value = true
      loading.value = false
      return
    }

    // 检查文档ID
    if (!props.document.doc_id) {
      showToast('文档ID缺失')
      error.value = true
      loading.value = false
      return
    }

    // 使用前端域名+端口，通过Vite代理访问后端，避免跨域问题
    const baseUrl = window.location.origin  // http://localhost:5173

    // 构建预览接口URL，使用/api/v1前缀让Vite代理处理
    const apiUrl = `${baseUrl}/api/v1/knowledge/documents/${props.document.doc_id}/preview`
    previewUrl.value = `${apiUrl}?token=${encodeURIComponent(token)}&t=${Date.now()}`

  } catch (err) {
    console.error('PDFPreview: 构建预览URL失败:', err)
    showToast(`PDF预览URL构建失败: ${err.message}`)
    error.value = true
  } finally {
    loading.value = false
  }
}

// 事件处理
const handleClose = () => {
  visible.value = false
  emit('close')
}

const handleIframeLoad = () => {
  loading.value = false
  error.value = false
}

const handleIframeError = () => {
  console.error('PDFPreview: iframe加载失败')
  loading.value = false
  error.value = true
  showToast('PDF预览加载失败')
}

const retryLoad = () => {
  buildPreviewUrl()
}
</script>

<style scoped>
/* 全屏遮罩层 */
.pdf-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: var(--preview-overlay-bg);
  z-index: var(--z-overlay) !important;
  overflow: hidden;
}

/* 全屏iframe */
.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
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
  background: var(--preview-close-bg);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10000;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.close-button:hover {
  background: var(--preview-close-bg-hover);
  transform: scale(1.1);
}

.close-button:active {
  transform: scale(0.95);
}

/* 加载遮罩层 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--preview-overlay-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

/* 错误遮罩层 */
.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--preview-overlay-bg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  color: var(--preview-text);
  text-align: center;
  padding: 20px;
}

.error-overlay .van-icon {
  margin-bottom: 16px;
  opacity: 0.8;
}

.error-overlay p {
  margin: 8px 0;
  font-size: 16px;
}

.error-overlay .error-hint {
  font-size: 14px;
  opacity: 0.7;
  margin-bottom: 20px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .close-button {
    top: 15px;
    right: 15px;
    width: 36px;
    height: 36px;
  }
}
</style>
