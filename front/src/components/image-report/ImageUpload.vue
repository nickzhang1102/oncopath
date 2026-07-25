<template>
  <div class="image-upload-container">
    <div class="upload-form">
      <van-cell-group inset>
        <!-- 选择病人 -->
        <van-field
          v-model="form.patientName"
          label="选择病人"
          placeholder="请选择病人"
          readonly
          required
          is-link
          @click="showPatientSelector = true"
        />

        <!-- 分类选择 -->
        <van-field
          v-model="form.categoryDisplay"
          label="检查分类"
          placeholder="请选择检查分类"
          readonly
          required
          is-link
          @click="showCategorySelector = true"
        >
          <template #input>
            <div v-if="form.categoryDisplay" class="selected-category-display">
              <span class="category-badge" :style="getCategoryStyle(form.category)">
                {{ form.categoryDisplay }}
              </span>
            </div>
            <div v-else class="placeholder-text">请选择检查分类</div>
          </template>
        </van-field>

        <!-- 医院选择 -->
        <van-field
          v-model="form.hospital"
          label="医院"
          placeholder="请输入医院名称"
          required
        />

        <!-- 检查日期 -->
        <van-field
          v-model="form.captureDate"
          label="检查日期"
          placeholder="请选择检查日期"
          readonly
          required
          is-link
          @click="showDatePicker = true"
        />

        <!-- 上传报告区域 -->
        <div class="image-upload-area">
          <div class="upload-label">上传报告 <span class="required">*</span></div>
          <div class="upload-zone" @click="selectImage">
            <div v-if="form.imageData" class="image-preview">
              <template v-if="form.imageType === 'pdf'">
                <div class="pdf-preview">
                  <van-icon name="description" class="pdf-icon" />
                  <div class="pdf-filename">{{ form.fileName || 'PDF文件' }}</div>
                </div>
              </template>
              <template v-else>
                <img :src="form.imageData" alt="预览图片" class="preview-img" />
              </template>
              <div class="image-actions">
                <van-button size="small" type="primary" @click.stop="selectImage">重新选择</van-button>
                <van-button size="small" type="danger" @click.stop="removeImage">删除</van-button>
              </div>
            </div>
            <div v-else class="upload-placeholder">
              <div class="upload-icon"><van-icon name="photograph" /></div>
              <div class="upload-text">点击选择文件</div>
              <div class="upload-hint">支持 JPG, PNG, PDF 格式，图片最大10MB，PDF最大20MB</div>
            </div>
          </div>
          <input
            ref="fileInput"
            type="file"
            accept="image/*,.pdf"
            @change="handleFileSelect"
            style="display: none"
          />
        </div>

        </van-cell-group>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <van-button type="default" @click="resetForm" class="action-btn">重置</van-button>
        <van-button type="primary" @click="submitForm" :loading="submitting" class="action-btn">
          {{ submitting ? '上传中...' : '上传报告' }}
        </van-button>
      </div>
    </div>

    <!-- 病人选择器 -->
    <van-popup
      v-model:show="showPatientSelector"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-picker
        :columns="patientColumns"
        @confirm="onPatientConfirm"
        @cancel="showPatientSelector = false"
      />
    </van-popup>

    <!-- 分类选择器 -->
    <van-popup
      v-model:show="showCategorySelector"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-md' : ''"
      :style="isDesktop ? 'width: 560px' : 'height: 80vh'"
    >
      <ImageCategorySelector
        @confirm="onCategoryConfirm"
        @cancel="showCategorySelector = false"
      />
    </van-popup>

    <!-- 日期选择器 -->
    <van-popup
      v-model:show="showDatePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="currentDate"
        title="选择检查日期"
        :min-date="minDate"
        :max-date="maxDate"
        @confirm="onDateConfirm"
        @cancel="showDatePicker = false"
      />
    </van-popup>

    <!-- 处理进度对话框 -->
    <van-dialog
      v-model:show="showLogDialog"
      title="处理进度"
      :show-cancel-button="false"
      :show-confirm-button="uploadCompleted"
      confirm-button-text="完成"
      @confirm="finishUpload"
      class="log-dialog"
    >
      <div class="log-container">
        <div
          v-for="(log, index) in processingLogs"
          :key="index"
          class="log-item"
          :class="log.status"
        >
          <van-icon :name="log.icon" class="log-icon" />
          <span class="log-message">{{ log.message }}</span>
          <span class="log-time">{{ log.timestamp }}</span>
        </div>
        <div v-if="processingLogs.length === 0" class="log-empty">
          正在连接服务器...
        </div>
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'
import { showToast, showConfirmDialog, showNotify } from 'vant'
import { uploadImageReport, uploadImageReportStream, checkDuplicate } from '@/api/imageReport'
import { getImageCategories } from '@/api/imageReport'
import ImageCategorySelector from './ImageCategorySelector.vue'

/**
 * 纯 JS SHA-256 实现（降级方案：HTTP 环境下 crypto.subtle 不可用）
 * 基于 FIPS 180-4 标准，仅用于去重预检哈希计算
 */
function _sha256PureJS(message) {
  const K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ]
  function rotr(x, n) { return ((x >>> n) | (x << (32 - n))) >>> 0 }
  function ch(x, y, z) { return ((x & y) ^ (~x & z)) >>> 0 }
  function maj(x, y, z) { return ((x & y) ^ (x & z) ^ (y & z)) >>> 0 }
  function sigma0(x) { return (rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)) >>> 0 }
  function sigma1(x) { return (rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)) >>> 0 }
  function gamma0(x) { return (rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3)) >>> 0 }
  function gamma1(x) { return (rotr(x, 17) ^ rotr(x, 19) ^ (x >>> 10)) >>> 0 }

  // 消息填充
  const bytes = []
  for (let i = 0; i < message.length; i++) bytes.push(message.charCodeAt(i))
  const bitLen = bytes.length * 8
  bytes.push(0x80)
  while ((bytes.length % 64) !== 56) bytes.push(0)
  for (let i = 56; i >= 0; i -= 8) bytes.push((bitLen >>> i) & 0xff)

  let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a
  let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19

  for (let offset = 0; offset < bytes.length; offset += 64) {
    const w = new Array(64)
    for (let t = 0; t < 16; t++) {
      w[t] = (bytes[offset + t * 4] << 24) | (bytes[offset + t * 4 + 1] << 16) |
             (bytes[offset + t * 4 + 2] << 8) | bytes[offset + t * 4 + 3]
      w[t] = w[t] >>> 0
    }
    for (let t = 16; t < 64; t++) {
      w[t] = (gamma1(w[t - 2]) + w[t - 7] + gamma0(w[t - 15]) + w[t - 16]) >>> 0
    }
    let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7
    for (let t = 0; t < 64; t++) {
      const T1 = (h + sigma1(e) + ch(e, f, g) + K[t] + w[t]) >>> 0
      const T2 = (sigma0(a) + maj(a, b, c)) >>> 0
      h = g; g = f; f = e; e = (d + T1) >>> 0
      d = c; c = b; b = a; a = (T1 + T2) >>> 0
    }
    h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0
    h4 = (h4 + e) >>> 0; h5 = (h5 + f) >>> 0; h6 = (h6 + g) >>> 0; h7 = (h7 + h) >>> 0
  }

  return [h0, h1, h2, h3, h4, h5, h6, h7]
    .map(h => h.toString(16).padStart(8, '0')).join('')
}

async function computeContentHash(base64Data) {
  // 优先使用 Web Crypto API（安全上下文: HTTPS 或 localhost）
  if (window.crypto?.subtle) {
    const binaryData = atob(base64Data)
    const uint8Array = new Uint8Array(binaryData.length)
    for (let i = 0; i < binaryData.length; i++) {
      uint8Array[i] = binaryData.charCodeAt(i)
    }
    const hashBuffer = await crypto.subtle.digest('SHA-256', uint8Array)
    return Array.from(new Uint8Array(hashBuffer))
      .map(b => b.toString(16).padStart(2, '0')).join('')
  }
  // 降级：纯 JS SHA-256（HTTP 非安全上下文）
  return _sha256PureJS(atob(base64Data))
}

const emit = defineEmits(['upload-completed'])
const patientStore = usePatientStore()
const { isDesktop } = useResponsive()

// 表单数据
const form = reactive({
  patientId: null,
  patientName: '',
  title: '',
  category: '',
  categoryDisplay: '',
  hospital: '',
  captureDate: '',
  imageData: null,
  imageType: '',
  fileName: '',
})

// 分类颜色缓存（从 API 加载）
const categoryColorMap = ref({})

async function loadCategoryColors() {
  try {
    const res = await getImageCategories()
    const data = res?.data !== undefined ? res.data : res
    const list = Array.isArray(data) ? data : (data?.items || [])
    const map = {}
    for (const cat of list) {
      if (cat.category_key && cat.color) {
        map[cat.category_key] = cat.color
      }
    }
    categoryColorMap.value = map
  } catch (e) {
    console.error('加载分类颜色失败:', e)
  }
}

// 状态变量
const submitting = ref(false)
const progressMessage = ref('')
const showPatientSelector = ref(false)
const showCategorySelector = ref(false)
const showDatePicker = ref(false)
const currentDate = ref([new Date().getFullYear(), new Date().getMonth() + 1, new Date().getDate()])
const fileInput = ref(null)
const cancelUpload = ref(null)

// 进度对话框状态
const showLogDialog = ref(false)
const processingLogs = ref([])
const uploadCompleted = ref(false)
const completedReportId = ref(null)

// 日期选择器限制
const minDate = new Date(1900, 0, 1)
const maxDate = new Date()

// 计算属性 - 直接使用 patientStore.patientList，避免冗余 API 请求
const patientColumns = computed(() => {
  return patientStore.patientList.map(p => ({
    text: `${p.patient_name} (${p.age ? p.age + '岁' : '未知年龄'})`,
    value: p.patient_id
  }))
})

// 初始化
onMounted(async () => {
  // 自动填充当前病人
  const currentPatient = patientStore.currentPatient
  if (currentPatient) {
    form.patientId = currentPatient.patient_id
    form.patientName = currentPatient.patient_name
  }
  await loadCategoryColors()
})

// 组件卸载时取消进行中的上传
onUnmounted(() => {
  if (cancelUpload.value) {
    cancelUpload.value()
    cancelUpload.value = null
  }
})

// 选择图片
const selectImage = () => {
  fileInput.value?.click()
}

// 处理文件选择
const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (!file) return

  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')

  // 验证文件类型
  if (!isPdf && !file.type.startsWith('image/')) {
    showToast('请选择图片或PDF文件')
    return
  }

  // 验证文件大小
  const maxSize = isPdf ? 20 * 1024 * 1024 : 10 * 1024 * 1024
  const sizeLabel = isPdf ? '20MB' : '10MB'
  if (file.size > maxSize) {
    showToast(`文件大小不能超过${sizeLabel}`)
    return
  }

  // 读取文件并转换为base64
  const reader = new FileReader()
  reader.onload = (e) => {
    form.imageData = e.target.result
    form.imageType = isPdf ? 'pdf' : file.type.split('/')[1]
    form.fileName = file.name
  }
  reader.readAsDataURL(file)
}

// 移除图片
const removeImage = async () => {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: '确定要删除这张图片吗？'
    })

    form.imageData = null
    form.imageType = ''
    form.fileName = ''
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  } catch {
    // 用户取消
  }
}

// 病人选择确认
const onPatientConfirm = ({ selectedOptions }) => {
  if (selectedOptions && selectedOptions.length > 0) {
    const selected = selectedOptions[0]
    form.patientId = selected.value
    form.patientName = selected.text
  }
  showPatientSelector.value = false
}

// 分类选择确认
const onCategoryConfirm = (category) => {
  if (category) {
    form.category = category.category_key
    form.categoryDisplay = category.category_name
    generateTitle()
  }
  showCategorySelector.value = false
}

// 日期选择确认
const onDateConfirm = (value) => {
  try {
    let year, month, day

    if (value && typeof value === 'object') {
      if (value.selectedValues && Array.isArray(value.selectedValues) && value.selectedValues.length >= 3) {
        year = value.selectedValues[0]
        month = String(value.selectedValues[1]).padStart(2, '0')
        day = String(value.selectedValues[2]).padStart(2, '0')
        currentDate.value = value.selectedValues
      } else if (Array.isArray(value) && value.length >= 3) {
        year = value[0]
        month = String(value[1]).padStart(2, '0')
        day = String(value[2]).padStart(2, '0')
        currentDate.value = value
      }
    }

    if (year && month && day) {
      form.captureDate = `${year}-${month}-${day}`
      generateTitle()
    }
    showDatePicker.value = false
  } catch (error) {
    console.error('日期选择错误:', error)
  }
}

// 自动生成标题
const generateTitle = () => {
  if (form.hospital && form.categoryDisplay && form.captureDate) {
    form.title = `${form.hospital}_${form.categoryDisplay}_${form.captureDate}`
  }
}

// 获取分类样式
const getCategoryStyle = (category) => {
  return {
    backgroundColor: categoryColorMap.value[category] || 'var(--text-secondary)',
    color: 'white'
  }
}

// 重置表单
const resetForm = () => {
  Object.assign(form, {
    patientId: null,
    patientName: '',
    title: '',
    category: '',
    categoryDisplay: '',
    hospital: '',
    captureDate: '',
    imageData: null,
    imageType: '',
    fileName: '',
  })

  // 重置文件输入
  if (fileInput.value) {
    fileInput.value.value = ''
  }

  // 恢复当前病人
  const currentPatient = patientStore.currentPatient
  if (currentPatient) {
    form.patientId = currentPatient.patient_id
    form.patientName = currentPatient.patient_name
  }
}

// 提交表单
const submitForm = async () => {
  // 验证必填字段
  if (!form.patientId) {
    showToast('请选择病人')
    return
  }
  if (!form.category) {
    showToast('请选择检查分类')
    return
  }
  if (!form.hospital) {
    showToast('请输入医院名称')
    return
  }
  if (!form.captureDate) {
    showToast('请选择检查日期')
    return
  }
  if (!form.imageData) {
    showToast('请上传报告')
    return
  }

  submitting.value = true
  progressMessage.value = '正在准备上传...'

  // 取消之前可能进行中的上传
  if (cancelUpload.value) {
    cancelUpload.value()
    cancelUpload.value = null
  }
  
  // 显示进度对话框
  showLogDialog.value = true
  processingLogs.value = []
  uploadCompleted.value = false
  
  addLog('正在准备上传数据...', 'pending')

  try {
    // 去重预检：计算文件内容 SHA-256 哈希
    const base64Data = form.imageData.split(',')[1] || form.imageData
    const contentHash = await computeContentHash(base64Data)

    try {
      const res = await checkDuplicate({
        patient_id: form.patientId,
        category: form.category,
        content_hash: contentHash,
      })
      const data = res?.data !== undefined ? res.data : res
      if (data?.is_duplicate) {
        submitting.value = false
        try {
          await showConfirmDialog({
            title: '报告已存在',
            message: `该报告已上传：${data.existing_report_title || '未知报告'}，是否继续上传？`,
            confirmButtonText: '继续上传',
            cancelButtonText: '取消',
          })
          // 用户确认继续
          submitting.value = true
        } catch {
          // 用户取消
          showLogDialog.value = false
          return
        }
      }
    } catch (e) {
      // 预检失败不阻塞上传，后端 SSE 流中还有双保险
      console.warn('去重预检失败:', e)
    }

    // 准备提交数据
    const submitData = {
      patient_id: form.patientId,
      title: form.title || `${form.hospital}_${form.categoryDisplay}_${form.captureDate}`,
      category: form.category,
      image_data: form.imageData,
      image_type: form.imageType,
      hospital: form.hospital,
      capture_date: form.captureDate,
    }

    // 使用 SSE 流式上传
    cancelUpload.value = uploadImageReportStream(submitData, {
      onProgress: (status, message) => {
        progressMessage.value = message
        // 根据状态映射日志类型
        let logStatus = 'info'
        if (status === 'ocr' || status === 'recognizing') {
          logStatus = 'pending'
        } else if (status === 'recognized' || status === 'parsed') {
          logStatus = 'success'
        } else if (status === 'parsing' || status === 'matching') {
          logStatus = 'info'
        } else if (status === 'saving') {
          logStatus = 'pending'
        }
        addLog(message, logStatus)
      },
      onError: (message, event) => {
        submitting.value = false
        progressMessage.value = ''
        addLog(message, 'error')
        uploadCompleted.value = true
        // SSE 重复拦截：后端返回 error_code=duplicate
        if (event?.error_code === 'duplicate') {
          showToast({ message: '该报告已上传', position: 'bottom' })
        }
      },
      onComplete: (data, message) => {
        submitting.value = false
        progressMessage.value = ''
        addLog(message, 'success')
        uploadCompleted.value = true
        completedReportId.value = data?.report_id || null
      }
    })
  } catch (error) {
    console.error('上传失败:', error)
    submitting.value = false
    progressMessage.value = ''
    const errorMsg = error.response?.data?.detail || '上传失败，请稍后重试'
    addLog(errorMsg, 'error')
  }
}

// 监听医院变化自动生成标题
watch(() => form.hospital, () => {
  generateTitle()
})

// 添加进度日志
const addLog = (message, status = 'info') => {
  const icons = {
    pending: 'clock-o',
    success: 'checked',
    error: 'warning-o',
    warning: 'warning-o',
    info: 'info-o'
  }

  processingLogs.value.push({
    message,
    status,
    icon: icons[status] || 'info-o',
    timestamp: new Date().toLocaleTimeString()
  })
}

// 完成上传
const finishUpload = () => {
  const reportId = completedReportId.value
  showLogDialog.value = false
  processingLogs.value = []
  uploadCompleted.value = false
  completedReportId.value = null
  resetForm()
  // 跳转到报告详情进行OCR确认
  if (reportId) {
    emit('upload-completed', reportId)
  }
}
</script>

<style scoped>
.image-upload-container {
  min-height: 100vh;
  padding: 10px;
  position: relative;
  z-index: 1;
}

.upload-form {
  background: var(--bg-surface-alpha);
  border-radius: 12px;
  padding: 15px;
  box-shadow: 0 8px 20px var(--primary-alpha-8);
  backdrop-filter: blur(10px);
}

.image-upload-area {
  padding: 16px;
  background: var(--bg-surface-alpha);
  backdrop-filter: blur(10px);
}

.upload-label {
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--text-primary);
  font-weight: 500;
}

.upload-label .required {
  color: var(--danger-color);
}

.upload-zone {
  border: 2px dashed var(--primary-color);
  border-radius: 12px;
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--primary-alpha-2);
}

.upload-zone:hover {
  border-color: var(--primary-dark);
  background: var(--primary-alpha-5);
}

.upload-placeholder {
  text-align: center;
  color: var(--primary-color);
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.image-preview {
  width: 100%;
  padding: 8px;
}

.preview-img {
  width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: 8px;
  margin-bottom: 8px;
}

.image-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.pdf-preview {
  text-align: center;
  padding: 16px 0;
}

.pdf-preview .pdf-icon {
  font-size: 64px;
  color: var(--danger-color);
}

.pdf-filename {
  margin-top: 8px;
  font-size: 14px;
  color: var(--text-primary);
  word-break: break-all;
}

.form-actions {
  display: flex;
  gap: 12px;
  padding: 16px;
  margin-top: 16px;
}

.action-btn {
  flex: 1;
  height: 44px;
  border-radius: 8px;
}

/* 分类显示样式 */
.selected-category-display {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-height: 24px;
  width: 100%;
}

.category-badge {
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  color: white;
  display: inline-block;
  margin-left: auto;
}

.placeholder-text {
  color: var(--text-tertiary);
  font-size: 14px;
}

/* 覆盖 vant 组件样式 */
:deep(.van-cell-group) {
  background: transparent;
}

:deep(.van-cell-group--inset) {
  margin: 0;
  border-radius: 0;
}

:deep(.van-field__label) {
  width: 90px;
  color: var(--text-primary);
}

:deep(.van-radio-group--horizontal) {
  justify-content: flex-start;
}

:deep(.van-radio) {
  margin-right: 16px;
}

:deep(.van-field__control) {
  text-align: right;
}

:deep(.van-button--primary) {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

:deep(.van-button--default) {
  color: var(--primary-color);
  border-color: var(--primary-color);
}

:deep(.van-switch--on) {
  background: var(--primary-color);
}

:deep(.van-radio__icon--checked .van-icon) {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

/* 日志对话框样式 */
.log-dialog {
  border-radius: 16px;
}

.log-container {
  max-height: 400px;
  overflow-y: auto;
  padding: 10px 0;
}

.log-item {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  margin: 4px 0;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.log-item.success {
  background: var(--status-normal-bg);
  color: var(--success-color);
}

.log-item.error {
  background: var(--status-danger-bg);
  color: var(--danger-color);
}

.log-item.warning {
  background: var(--status-warning-bg);
  color: var(--warning-color);
}

.log-item.pending {
  background: var(--status-info-bg);
  color: var(--info-color);
}

.log-item.info {
  background: var(--primary-alpha-10);
  color: var(--text-tertiary);
}

.log-icon {
  margin-right: 8px;
  font-size: 16px;
}

.log-message {
  flex: 1;
  font-size: 14px;
}

.log-time {
  font-size: 12px;
  opacity: 0.7;
  margin-left: 8px;
}

.log-empty {
  text-align: center;
  color: var(--text-tertiary);
  padding: 20px;
  font-size: 14px;
}
</style>
