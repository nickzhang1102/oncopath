<template>
  <div class="ocr-image-viewer" :class="{ compact }">
    <!-- PDF 预览 -->
    <div v-if="isPdf" class="pdf-container">
      <iframe
        :src="pdfBlobUrl"
        class="pdf-iframe"
        frameborder="0"
      />
    </div>

    <!-- 图片预览 -->
    <div v-else class="image-container" ref="containerRef"
      @wheel.prevent="onWheel"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      @mouseleave="onMouseUp"
      @touchstart="onTouchStart"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
    >
      <img
        ref="imgRef"
        :src="src"
        alt="报告原图"
        class="report-image"
        :style="imageTransform"
        @load="onImageLoad"
      />
      <div
        v-if="highlightBbox && imageLoaded"
        class="highlight-overlay"
        :style="highlightStyle"
      ></div>
    </div>

    <div class="zoom-controls" v-if="!compact && !isPdf">
      <van-button size="mini" icon="add-o" @click="zoomIn" />
      <van-button size="mini" icon="minus" @click="zoomOut" />
      <van-button size="mini" icon="replay" @click="resetZoom" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'

const props = defineProps({
  src: { type: String, default: '' },
  highlightBbox: { type: Array, default: null },
  compact: { type: Boolean, default: false },
  imageType: { type: String, default: '' }
})

const isPdf = computed(() => {
  if (props.imageType === 'pdf') return true
  return props.src.startsWith('data:application/pdf')
})

// base64 data URI -> Blob URL，解决 iframe 无法渲染超长 data URI 的问题
const pdfBlobUrl = ref('')
let currentBlobUrl = ''

function revokeCurrentBlob() {
  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl)
    currentBlobUrl = ''
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

watch(() => props.src, (newSrc) => {
  revokeCurrentBlob()
  if (isPdf.value && newSrc && newSrc.startsWith('data:')) {
    try {
      const blob = dataUriToBlob(newSrc)
      currentBlobUrl = URL.createObjectURL(blob)
      pdfBlobUrl.value = currentBlobUrl
    } catch {
      pdfBlobUrl.value = newSrc
    }
  } else {
    pdfBlobUrl.value = newSrc
  }
}, { immediate: true })

onUnmounted(() => {
  revokeCurrentBlob()
})

const containerRef = ref(null)
const imgRef = ref(null)
const imageLoaded = ref(false)

const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })

const imageTransform = computed(() => ({
  transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
  transformOrigin: 'center center',
  transition: isDragging.value ? 'none' : 'transform 0.2s ease'
}))

const highlightStyle = computed(() => {
  if (!props.highlightBbox || props.highlightBbox.length < 4) return {}
  const bbox = props.highlightBbox
  const xs = bbox.map(p => p[0])
  const ys = bbox.map(p => p[1])
  const left = Math.min(...xs)
  const top = Math.min(...ys)
  const right = Math.max(...xs)
  const bottom = Math.max(...ys)
  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${right - left}%`,
    height: `${bottom - top}%`
  }
})

const onImageLoad = () => {
  imageLoaded.value = true
}

const zoomIn = () => {
  scale.value = Math.min(scale.value * 1.2, 5)
}

const zoomOut = () => {
  scale.value = Math.max(scale.value / 1.2, 0.5)
}

const resetZoom = () => {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
}

const onWheel = (e) => {
  if (e.deltaY < 0) zoomIn()
  else zoomOut()
}

const onMouseDown = (e) => {
  isDragging.value = true
  dragStart.value = { x: e.clientX - translateX.value, y: e.clientY - translateY.value }
}

const onMouseMove = (e) => {
  if (!isDragging.value) return
  translateX.value = e.clientX - dragStart.value.x
  translateY.value = e.clientY - dragStart.value.y
}

const onMouseUp = () => {
  isDragging.value = false
}

const onTouchStart = (e) => {
  if (e.touches.length === 1) {
    isDragging.value = true
    dragStart.value = {
      x: e.touches[0].clientX - translateX.value,
      y: e.touches[0].clientY - translateY.value
    }
  }
}

const onTouchMove = (e) => {
  if (!isDragging.value || e.touches.length !== 1) return
  e.preventDefault()
  translateX.value = e.touches[0].clientX - dragStart.value.x
  translateY.value = e.touches[0].clientY - dragStart.value.y
}

const onTouchEnd = () => {
  isDragging.value = false
}
</script>

<style scoped>
.ocr-image-viewer {
  background: var(--bg-surface-alpha);
  border-radius: 12px;
  padding: 12px;
  backdrop-filter: blur(10px);
}

.ocr-image-viewer.compact {
  padding: 8px;
}

.image-container {
  position: relative;
  background: var(--bg-elevated);
  border-radius: 8px;
  overflow: hidden;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
}

.image-container:active {
  cursor: grabbing;
}

/* PDF 预览 */
.pdf-container {
  background: var(--bg-elevated);
  border-radius: 8px;
  overflow: hidden;
  min-height: 300px;
}

.pdf-iframe {
  width: 100%;
  height: 500px;
  border: none;
  display: block;
}

.compact .pdf-container {
  min-height: 200px;
}

.compact .pdf-iframe {
  height: 250px;
}

.compact .image-container {
  min-height: 120px;
  max-height: 250px;
}

.report-image {
  max-width: 100%;
  max-height: 500px;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
}

.compact .report-image {
  max-height: 220px;
}

.highlight-overlay {
  position: absolute;
  border: 2px solid var(--warning-color);
  border-radius: 3px;
  background: rgba(255, 152, 0, 0.15);
  pointer-events: none;
  transition: all 0.3s ease;
}

.zoom-controls {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 8px;
}

.zoom-controls .van-button {
  min-width: 36px;
}
</style>