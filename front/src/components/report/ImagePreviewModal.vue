<template>
  <!-- 自定义全屏图片/PDF 预览 -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show" class="preview-overlay" @click="close">
        <!-- 下载按钮 -->
        <div v-if="imageUrl || pdfBlobUrl" class="preview-download" @click.stop>
          <van-icon name="down" class="download-icon" @click="saveFile" />
        </div>

        <!-- PDF 容器 -->
        <div v-if="isPdf" class="pdf-container" @click.stop>
          <iframe
            :src="pdfBlobUrl"
            class="pdf-iframe"
            frameborder="0"
          />
        </div>

        <!-- 图片容器 -->
        <div v-else class="image-container" @click.stop>
          <van-loading v-if="loading" class="image-loading" />
          <img
            v-else-if="imageUrl"
            :src="imageUrl"
            class="preview-image"
            @click="close"
          />
          <div v-else class="no-image">暂无图片</div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { showToast } from 'vant'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '报告预览'
  },
  imageUrl: {
    type: String,
    default: ''
  },
  imageType: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:show', 'close'])

const isPdf = ref(false)
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

watch(() => [props.imageUrl, props.imageType], ([url, type]) => {
  revokePdfBlob()
  const pdf = type === 'pdf' || url.startsWith('data:application/pdf')
  isPdf.value = pdf
  if (pdf && url) {
    if (url.startsWith('data:')) {
      try {
        const blob = dataUriToBlob(url)
        _currentBlobUrl = URL.createObjectURL(blob)
        pdfBlobUrl.value = _currentBlobUrl
      } catch {
        pdfBlobUrl.value = url
      }
    } else {
      pdfBlobUrl.value = url
    }
  } else {
    pdfBlobUrl.value = ''
  }
}, { immediate: true })

onUnmounted(() => {
  revokePdfBlob()
})

function close() {
  emit('update:show', false)
  emit('close')
}

function saveFile() {
  const url = isPdf.value ? pdfBlobUrl.value : props.imageUrl
  if (url) {
    const link = document.createElement('a')
    link.href = url
    link.download = isPdf.value ? `${props.title}.pdf` : `${props.title}.jpg`
    link.click()
    showToast(isPdf.value ? 'PDF已保存' : '图片已保存')
  }
}
</script>

<style scoped>
/* 遮罩层 */
.preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--preview-overlay-bg);
  z-index: 2000;
  display: flex;
  flex-direction: column;
}

/* 下载按钮 */
.preview-download {
  position: absolute;
  top: calc(16px + env(safe-area-inset-top));
  right: 16px;
  z-index: 2001;
}

.download-icon {
  font-size: 20px;
  color: var(--preview-text);
  cursor: pointer;
  padding: 10px;
  background: var(--preview-toolbar-bg);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* PDF 容器 */
.pdf-container {
  width: 100%;
  height: 100%;
  display: flex;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

/* 图片容器 - 可滚动 */
.image-container {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  -webkit-overflow-scrolling: touch;
}

.image-loading {
  margin-top: 50%;
}

/* 图片 - 宽度全屏 */
.preview-image {
  width: 100%;
  height: auto;
  display: block;
  object-fit: contain;
  cursor: pointer;
}

.no-image {
  color: var(--text-tertiary);
  font-size: 14px;
  margin-top: 50%;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>