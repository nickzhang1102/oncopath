<template>
  <van-dialog
    v-model:show="visible"
    :title="isEditing ? '编辑文档' : '上传文档'"
    show-cancel-button
    :confirm-button-loading="loading"
    :cancel-button-disabled="loading"
    :before-close="handleBeforeClose"
  >
    <div class="upload-form" :class="{ 'upload-form--disabled': loading }">
      <van-field
        v-model="form.docName"
        label="文档名称"
        placeholder="请输入文档名称"
        required
        :disabled="loading"
      />

      <van-field
        v-model="form.description"
        label="文档描述"
        placeholder="请输入文档描述（可选）"
        type="textarea"
        rows="3"
        :disabled="loading"
      />

      <van-field
        v-model="selectedCategoryName"
        label="所属分类"
        placeholder="请选择分类（可选）"
        readonly
        is-link
        :disabled="loading"
        @click="!loading && (showCategorySelector = true)"
      />

      <!-- 上传文件区域 -->
      <div v-if="!isEditing" class="upload-area">
        <div class="upload-label">选择文件</div>
        <div class="upload-zone" :class="{ 'upload-zone--disabled': loading }" @click="!loading && selectFile()">
          <div v-if="selectedFile" class="file-preview">
            <template v-if="isImageFile">
              <img :src="filePreviewUrl" alt="预览" class="preview-img" />
            </template>
            <template v-else>
              <van-icon :name="fileIcon" class="file-type-icon" />
              <div class="file-name">{{ selectedFile.name }}</div>
              <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
            </template>
            <div class="file-actions">
              <van-button size="small" type="primary" :disabled="loading" @click.stop="selectFile">重新选择</van-button>
              <van-button size="small" type="danger" :disabled="loading" @click.stop="removeFile">删除</van-button>
            </div>
          </div>
          <div v-else class="upload-placeholder">
            <div class="upload-icon"><van-icon name="description" /></div>
            <div class="upload-text">点击选择文件</div>
            <div class="upload-hint">支持 PDF、Office、图片、文本，最大50MB</div>
          </div>
        </div>
        <input
          ref="fileInputRef"
          type="file"
          accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.jpg,.jpeg,.png,.gif,.bmp,.webp"
          @change="handleFileChange"
          style="display: none"
        />
      </div>

      <!-- 上传进度条 -->
      <div v-if="showProgress" class="upload-progress">
        <van-progress
          :percentage="uploadProgress"
          :show-pivot="true"
          pivot-text="上传中..."
          color="var(--primary-color)"
        />
        <p class="progress-text">正在上传文件，请稍候...</p>
      </div>
    </div>
  </van-dialog>

  <!-- 分类选择弹窗（放在 dialog 外部避免 z-index 冲突） -->
  <van-popup
    v-model:show="showCategorySelector"
    :position="isDesktop ? 'center' : 'bottom'"
    :round="!isDesktop"
    :z-index="2500"
    :style="isDesktop ? { width: '360px', maxHeight: '60vh', borderRadius: 'var(--radius-lg)', display: 'flex', flexDirection: 'column' } : { height: '50%' }"
  >
    <template v-if="isDesktop">
      <div class="category-popup-header">
        <span>选择分类</span>
        <van-icon name="cross" @click="showCategorySelector = false" />
      </div>
      <div class="category-popup-list">
        <div
          class="category-popup-item"
          :class="{ 'category-popup-item--active': form.categoryId === null }"
          @click="onCategoryListSelect(null, '未分类')"
        >
          <span>未分类</span>
          <van-icon v-if="form.categoryId === null" name="success" color="var(--primary-color)" />
        </div>
        <div
          v-for="cat in flatCategoryList"
          :key="cat.category_id"
          class="category-popup-item"
          :class="{ 'category-popup-item--active': form.categoryId === cat.category_id }"
          @click="onCategoryListSelect(cat.category_id, cat.display_name)"
        >
          <span>{{ cat.display_name }}</span>
          <van-icon v-if="form.categoryId === cat.category_id" name="success" color="var(--primary-color)" />
        </div>
      </div>
    </template>
    <van-picker
      v-else
      :columns="categoryOptions"
      @confirm="onCategorySelect"
      @cancel="showCategorySelector = false"
    />
  </van-popup>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { showToast } from 'vant'
import { uploadDocument, updateDocument } from '@/api/knowledge'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop } = useResponsive()

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  categoryTree: {
    type: Array,
    default: () => []
  },
  editingDocument: {
    type: Object,
    default: null
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'success', 'cancel'])

// 响应式数据
const visible = ref(props.modelValue)
const loading = ref(false)
const showCategorySelector = ref(false)
const selectedCategoryName = ref('')
const uploadProgress = ref(0)
const showProgress = ref(false)
const fileInputRef = ref(null)
const selectedFile = ref(null)
const filePreviewUrl = ref('')

const form = ref({
  docName: '',
  description: '',
  categoryId: null
})

// 计算属性
const isEditing = computed(() => !!props.editingDocument)

const flatCategoryList = computed(() => {
  const flatten = (categories, level = 0) => {
    let result = []
    categories.forEach(category => {
      result.push({
        ...category,
        level,
        display_name: '  '.repeat(level) + category.category_name
      })
      if (category.children && category.children.length > 0) {
        result = result.concat(flatten(category.children, level + 1))
      }
    })
    return result
  }
  return flatten(props.categoryTree)
})

const categoryOptions = computed(() => {
  return [
    { text: '未分类', value: null },
    ...flatCategoryList.value.map(cat => ({
      text: cat.display_name,
      value: cat.category_id
    }))
  ]
})

const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']

const isImageFile = computed(() => {
  if (!selectedFile.value) return false
  const ext = selectedFile.value.name.split('.').pop().toLowerCase()
  return IMAGE_EXTENSIONS.includes(ext)
})

const fileIcon = computed(() => {
  if (!selectedFile.value) return 'description'
  const ext = selectedFile.value.name.split('.').pop().toLowerCase()
  if (ext === 'pdf') return 'description'
  if (['doc', 'docx'].includes(ext)) return 'records'
  if (['xls', 'xlsx'].includes(ext)) return 'chart-trending-o'
  if (['ppt', 'pptx'].includes(ext)) return 'play-circle-o'
  return 'description'
})

const formatFileSize = (bytes) => {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

// 监听器
watch(() => props.modelValue, (newValue) => {
  visible.value = newValue
})

watch(visible, (newValue) => {
  emit('update:modelValue', newValue)
})

watch(() => props.editingDocument, (doc) => {
  if (doc) {
    // 编辑模式：填充表单数据
    form.value = {
      docName: doc.doc_name,
      description: doc.description || '',
      categoryId: doc.category_id
    }
    selectedCategoryName.value = doc.category_name || '未分类'
  } else {
    // 新建模式：重置表单
    resetForm()
  }
})

// 方法
const selectFile = () => {
  if (loading.value) return
  fileInputRef.value?.click()
}

const handleFileChange = (event) => {
  const file = event.target.files[0]
  if (!file) return

  // 验证文件大小（50MB）
  const maxSize = 50 * 1024 * 1024
  if (file.size > maxSize) {
    showToast(`文件大小不能超过50MB，当前：${formatFileSize(file.size)}`)
    return
  }

  // 验证文件类型
  const allowedExts = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
  const ext = file.name.split('.').pop().toLowerCase()
  if (!allowedExts.includes(ext)) {
    showToast('不支持的文件类型')
    return
  }

  selectedFile.value = file

  // 图片生成预览 URL
  if (filePreviewUrl.value) {
    URL.revokeObjectURL(filePreviewUrl.value)
    filePreviewUrl.value = ''
  }
  if (IMAGE_EXTENSIONS.includes(ext)) {
    filePreviewUrl.value = URL.createObjectURL(file)
  }

  // 自动填充文档名称
  if (!form.value.docName) {
    const nameWithoutExt = file.name.substring(0, file.name.lastIndexOf('.'))
    form.value.docName = nameWithoutExt
  }
}

const removeFile = () => {
  if (loading.value) return
  selectedFile.value = null
  if (filePreviewUrl.value) {
    URL.revokeObjectURL(filePreviewUrl.value)
    filePreviewUrl.value = ''
  }
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

const onCategorySelect = ({ selectedOptions }) => {
  if (selectedOptions && selectedOptions.length > 0) {
    const selectedOption = selectedOptions[0]
    form.value.categoryId = selectedOption.value
    selectedCategoryName.value = selectedOption.text
  }
  showCategorySelector.value = false
}

const onCategoryListSelect = (categoryId, categoryName) => {
  form.value.categoryId = categoryId
  selectedCategoryName.value = categoryName
  showCategorySelector.value = false
}

// beforeClose：Vant 通过 callInterceptor 调用，仅传 action 参数
// 返回 true/false 或 Promise<true/false> 控制弹窗是否关闭
const handleBeforeClose = (action) => {
  if (action === 'cancel') {
    // 加载中禁止取消（保持 UI 锁定）
    if (loading.value) return false
    resetForm()
    emit('cancel')
    return true
  }

  // action === 'confirm'
  if (loading.value) return false

  // 表单校验
  if (!form.value.docName.trim()) {
    showToast('请输入文档名称')
    return false
  }
  if (!isEditing.value && !selectedFile.value) {
    showToast('请选择要上传的文件')
    return false
  }

  // 返回 Promise：Vant 等待其 resolve，自动管理 confirm 按钮 loading
  return doSubmit()
}

const doSubmit = async () => {
  loading.value = true

  try {
    if (isEditing.value) {
      const updateData = {
        doc_name: form.value.docName,
        doc_description: form.value.description || ''
      }
      if (form.value.categoryId) {
        updateData.category_id = form.value.categoryId
      }

      await updateDocument(props.editingDocument.doc_id, updateData)
      showToast('文档更新成功')
      resetForm()
      emit('success')
      return true
    } else {
      const formData = new FormData()
      formData.append('doc_name', form.value.docName)
      if (form.value.categoryId) {
        formData.append('category_id', form.value.categoryId)
      }
      if (form.value.description) {
        formData.append('doc_description', form.value.description)
      }
      if (selectedFile.value) {
        formData.append('file', selectedFile.value)
      }

      showProgress.value = true
      uploadProgress.value = 0

      const onUploadProgress = (progressEvent) => {
        if (progressEvent.lengthComputable) {
          uploadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        }
      }

      const response = await uploadDocument(formData, onUploadProgress)
      if (response && response.doc_id) {
        uploadProgress.value = 100
        showToast('上传成功')
        resetForm()
        emit('success')
        return true
      } else {
        showToast(response?.message || '上传失败')
        return false
      }
    }
  } catch (error) {
    console.error('操作失败:', error)
    const msg = error?.response?.data?.detail || error?.message || '操作失败'
    showToast(msg)
    return false
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.value = {
    docName: '',
    description: '',
    categoryId: null
  }
  selectedCategoryName.value = ''
  uploadProgress.value = 0
  showProgress.value = false
  selectedFile.value = null
  if (filePreviewUrl.value) {
    URL.revokeObjectURL(filePreviewUrl.value)
    filePreviewUrl.value = ''
  }
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}
</script>

<style scoped>
.upload-form {
  padding: 16px;
}

.upload-form--disabled {
  pointer-events: none;
  opacity: 0.7;
}

.upload-form .van-field {
  margin-bottom: 12px;
}

.upload-area {
  padding: 12px 0;
}

.upload-label {
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--text-primary);
  font-weight: 500;
}

.upload-zone {
  border: 2px dashed var(--primary-color);
  border-radius: 12px;
  min-height: 120px;
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

.upload-zone--disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.upload-zone--disabled:hover {
  border-color: var(--primary-color);
  background: var(--primary-alpha-2);
}

.upload-placeholder {
  text-align: center;
  color: var(--primary-color);
  padding: 16px;
}

.upload-icon {
  font-size: 40px;
  margin-bottom: 6px;
}

.upload-text {
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.file-preview {
  width: 100%;
  padding: 12px;
  text-align: center;
}

.preview-img {
  width: 100%;
  max-height: 150px;
  object-fit: contain;
  border-radius: 8px;
  margin-bottom: 8px;
}

.file-type-icon {
  font-size: 48px;
  color: var(--primary-color);
  display: block;
  margin: 0 auto 6px;
}

.file-name {
  font-size: 14px;
  color: var(--text-primary);
  word-break: break-all;
  margin-bottom: 2px;
}

.file-size {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.file-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.upload-progress {
  margin-top: 16px;
  padding: 16px;
  background: var(--bg-elevated);
  border-radius: 8px;
}

.progress-text {
  margin-top: 8px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 14px;
}

.category-popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.category-popup-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.category-popup-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary);
  transition: background 0.2s;
}

.category-popup-item:hover {
  background: var(--primary-alpha-5);
}

.category-popup-item--active {
  color: var(--primary-color);
  font-weight: 500;
  background: var(--primary-alpha-8);
}
</style>
