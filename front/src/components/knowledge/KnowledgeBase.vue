<template>
  <div class="swipe-content knowledge-container">

    <!-- 导航栏 -->
    <back-button title="护理指南知识库" />

    <!-- 搜索组件 -->
    <KnowledgeSearch
      v-model="searchKeyword"
      @search="onSearch"
      @clear="onSearchClear"
    />

    <!-- 桌面端操作栏 -->
    <div v-if="isDesktop" class="desktop-actions-bar">
      <van-button type="primary" size="small" icon="plus" @click="handleUploadClick">
        上传文档
      </van-button>
      <van-button type="default" size="small" icon="add-o" @click="handleCreateCategoryClick">
        新建分类
      </van-button>
    </div>

    <!-- 桌面端：左右分栏布局 -->
    <div v-if="isDesktop" class="knowledge-desktop-layout">
      <!-- 左侧分类树 -->
      <div class="knowledge-sidebar">
        <CategorySelector
          :category-tree="categoryTree"
          :selected-category-id="selectedCategoryId"
          :total-count="documents.length"
          @update:selected-category-id="selectedCategoryId = $event"
          @category-selected="onCategorySelected"
          @category-created="onCategoryCreated"
          ref="categorySelectorRef"
        />
      </div>
      <!-- 右侧文档列表 -->
    <div class="knowledge-main">
      <DocumentList
          :documents="documents"
          :loading="documentsLoading"
          :finished="documentsFinished"
          @document-preview="handlePreviewDocument"
          @document-edit="editDocument"
          @document-delete="confirmDeleteDocument"
          @document-generate-summary="handleGenerateSummary"
          @upload-click="handleUploadClick"
          @load-more="onLoadMore"
        />
      </div>
    </div>

    <!-- 移动端：单列布局 -->
    <template v-else>
      <!-- 分类选择组件 -->
      <CategorySelector
          :category-tree="categoryTree"
          :selected-category-id="selectedCategoryId"
          @update:selected-category-id="selectedCategoryId = $event"
          @category-selected="onCategorySelected"
          @category-created="onCategoryCreated"
          ref="categorySelectorRef"
        />

      <!-- 文档列表组件 -->
      <DocumentList
        :documents="documents"
        :loading="documentsLoading"
        :finished="documentsFinished"
        @document-preview="handlePreviewDocument"
        @document-edit="editDocument"
        @document-delete="confirmDeleteDocument"
        @document-generate-summary="handleGenerateSummary"
        @upload-click="handleUploadClick"
        @load-more="onLoadMore"
      />
    </template>

    <!-- 文档上传组件 -->
    <DocumentUpload
      v-model="showUploadDialog"
      :category-tree="categoryTree"
      :editing-document="editingDocument"
      @success="onDocumentUploaded"
      @cancel="handleUploadCancel"
    />

    <!-- 文档预览组件 -->
    <DocumentPreview
      v-if="!isImageFile(previewDocument) && !isPdfFile(previewDocument) && !isOfficeFile(previewDocument)"
      v-model="showPreviewDialog"
      :document="previewDocument"
      @close="handlePreviewClose"
    />

    <!-- 图片预览组件 -->
    <ImagePreview
      v-if="isImageFile(previewDocument)"
      v-model="showPreviewDialog"
      :document="previewDocument"
      @close="handlePreviewClose"
    />

    <!-- PDF预览组件 -->
    <PDFPreview
      v-if="isPdfFile(previewDocument)"
      v-model="showPreviewDialog"
      :document="previewDocument"
      @close="handlePreviewClose"
    />

    <!-- Office文档预览组件 -->
    <OfficePreview
      v-if="isOfficeFile(previewDocument)"
      v-model="showPreviewDialog"
      :document="previewDocument"
      @close="handlePreviewClose"
    />

  </div>

  <!-- 浮动操作按钮 - 参照老版本实现 -->
  <div v-if="!isDesktop" class="knowledge-fab">
    <van-floating-bubble
      v-model:show="showFloatingBubble"
      axis="xy"
      icon="plus"
      :gap="floatingBubbleGap"
      @click="showActionMenu = true"
    />
  </div>
  <van-action-sheet
    v-model:show="showActionMenu"
    :actions="floatingMenuActions"
    @select="onFloatingActionSelect"
    cancel-text="取消"
    close-on-click-action
  />
</template>

<script setup>
import { ref, computed, onMounted, onActivated, nextTick } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop, floatingBubbleGap } = useResponsive()

// 导入子组件
import KnowledgeSearch from './KnowledgeSearch.vue'
import CategorySelector from './CategorySelector.vue'
import DocumentList from './DocumentList.vue'
import DocumentUpload from './DocumentUpload.vue'
import DocumentPreview from './DocumentPreview.vue'
import ImagePreview from './ImagePreview.vue'
import PDFPreview from './PDFPreview.vue'
import OfficePreview from './OfficePreview.vue'
import BackButton from '@/components/index-detail/BackButton.vue'

// 导入状态管理
import { useKnowledgeStore } from '@/stores/knowledge'
import { storeToRefs } from 'pinia'

// 使用状态管理（关键：使用 storeToRefs 保持响应式）
const store = useKnowledgeStore()
const {
  categoryTree,
  documents,
  selectedCategoryId,
  searchKeyword,
  documentsLoading,
  documentsFinished,
} = storeToRefs(store)  // ✅ 响应式数据

const {
  onSearch,
  onSearchClear,
  onCategorySelected,
  onCategoryCreated,
  onDocumentUploaded,
  onLoadMore,
  confirmDeleteDocument,
  initialize
} = store  // ✅ 方法直接从 store 解构（不需要响应式）

// 本地状态
const showUploadDialog = ref(false)
const showPreviewDialog = ref(false)
const showActionMenu = ref(false)
const showFloatingBubble = ref(true)
const editingDocument = ref(null)
const previewDocument = ref(null)

// 组件引用
const categorySelectorRef = ref(null)

// 计算属性 - 检测是否有预览对话框打开
const isAnyPreviewVisible = computed(() => {
  return showPreviewDialog.value
})

// 浮动菜单
const floatingMenuActions = [
  { name: '上传文档', value: 'upload', icon: 'plus' },
  { name: '新建分类', value: 'create_category', icon: 'add-o' }
]

const onFloatingActionSelect = (action) => {
  if (action.value === 'upload') {
    handleUploadClick()
  } else if (action.value === 'create_category') {
    handleCreateCategoryClick()
  }
  showActionMenu.value = false
}

const handleUploadClick = () => {
  editingDocument.value = null
  showUploadDialog.value = true
}

const handleCreateCategoryClick = () => {
  if (categorySelectorRef.value) {
    categorySelectorRef.value.openCreateCategoryDialog()
  }
}

const editDocument = (doc) => {
  editingDocument.value = doc
  showUploadDialog.value = true
}

const handlePreviewDocument = (doc) => {
  // 检查文档对象
  if (!doc) {
    showToast('文档信息缺失')
    return
  }

  // 先设置文档对象，再显示对话框
  // 这样可以确保组件创建时props.document已经有值
  previewDocument.value = doc
  showPreviewDialog.value = true
}

const handleGenerateSummary = async (doc) => {
  try {
    await showConfirmDialog({
      title: '生成AI摘要',
      message: `将为"${doc.doc_name}"生成AI摘要，是否继续？`,
      confirmButtonText: '生成',
      cancelButtonText: '取消'
    })
  } catch {
    return // 用户取消
  }

  try {
    showToast({ type: 'loading', message: '提交中...', forbidClick: true, duration: 0 })
    const { generateSummary } = await import('@/api/knowledge')
    await generateSummary(doc.doc_id)
    showToast({ type: 'success', message: '摘要生成任务已提交' })
    // 刷新列表以更新状态
    store.loadDocuments(true)
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || '操作失败'
    showToast({ type: 'fail', message: msg })
  }
}

const handleUploadCancel = () => {
  showUploadDialog.value = false
  editingDocument.value = null
}

const handlePreviewClose = () => {
  showPreviewDialog.value = false
  previewDocument.value = null
}

// 判断是否为图片文件
const isImageFile = (document) => {
  if (!document) return false
  const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']
  const fileType = document.file_type?.toLowerCase() || ''
  return imageExtensions.includes(fileType)
}

// 判断是否为PDF文件
const isPdfFile = (document) => {
  if (!document) return false
  const fileType = document.file_type?.toLowerCase() || ''
  return fileType === 'pdf'
}

// 判断是否为Office文件
const isOfficeFile = (document) => {
  if (!document) return false
  const officeExtensions = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']
  const fileType = document.file_type?.toLowerCase() || ''
  return officeExtensions.includes(fileType)
}

// 生命周期
onMounted(() => {
  initialize()
})

// keep-alive 页面重新激活时刷新数据
onActivated(() => {
  initialize()
})

</script>

<style scoped>
/* 浮动按钮容器 - 层级高于底部 tab 栏 (9999) */
.knowledge-fab {
  position: relative;
  z-index: 10000;
}

.knowledge-fab :deep(.van-floating-bubble) {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  box-shadow: 0 4px 12px var(--primary-alpha-40);
}

.knowledge-container {
  padding: 16px;
  padding-bottom: calc(var(--safe-bottom) + 80px);
  min-height: 500px;
  background: var(--bg-primary);
}

/* 桌面端操作栏 */
.desktop-actions-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.section-header {
  text-align: center;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--shadow-color);
}

.section-title-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 6px;
}

.section-icon {
  font-size: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.section-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 工具栏 */
.toolbar-section {
  margin-bottom: 16px;
}

.current-category {
  margin-bottom: 12px;
}

.filter-bar {
  margin-bottom: 16px;
}

/* 文档列表 */
.documents-section {
  background: var(--bg-surface);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px var(--shadow-color);
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
}

.document-cell .van-cell__title {
  /* 增加文件名列宽度 */
  flex: 2;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 180px;
}

.document-cell .van-cell__label {
  /* 文档信息样式 */
  color: var(--text-quaternary);
  font-size: 12px;
  margin-top: 4px;
}

.document-cell .van-cell__value {
  /* 文件大小列 */
  flex: 0 0 auto;
  color: var(--text-quaternary);
  font-size: 12px;
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-right: 12px;
}

.action-icon {
  padding: 8px;
  color: var(--text-quaternary);
  cursor: pointer;
  transition: color 0.3s;
}

.action-icon:hover {
  color: var(--text-primary);
}

/* 加载更多 */
.load-more {
  margin-top: 16px;
  padding: 0 16px;
}

/* 对话框样式 */
.upload-form,
.category-form {
  padding: 16px;
}

.upload-form .van-field,
.category-form .van-field {
  margin-bottom: 12px;
}

.upload-form .van-uploader {
  margin-top: 12px;
}

/* 分类选择器样式 */
.category-tree-header {
  border-bottom: 1px solid var(--border-light);
}

.category-tree-content {
  height: calc(100% - 46px);
  overflow-y: auto;
}

.selected-category {
  background-color: var(--bg-primary);
  color: var(--primary-color);
}

.selected-category .van-cell__title {
  color: var(--primary-color);
  font-weight: 600;
}

/* 文档预览样式 */
.document-preview {
  max-height: 400px;
  overflow-y: auto;
}

.preview-info {
  padding: 16px;
  background: var(--bg-elevated);
  border-radius: 8px;
  margin-bottom: 16px;
}

.preview-info p {
  margin: 8px 0;
  font-size: 14px;
  color: var(--text-primary);
}

.preview-content {
  padding: 16px;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-text {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.preview-placeholder {
  text-align: center;
  color: var(--text-tertiary);
}

.preview-placeholder .van-icon {
  margin-bottom: 12px;
  color: var(--text-tertiary);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .knowledge-container {
    padding: 12px;
  }

  .upload-form,
  .category-form {
    padding: 12px;
  }

  .document-preview {
    max-height: 300px;
  }

  .preview-info {
    padding: 12px;
  }

  .preview-content {
    padding: 12px;
    min-height: 150px;
  }
}

/* 桌面端布局 */
@media (min-width: 768px) {
  .knowledge-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 32px;
    min-height: 100vh;
  }

  /* 桌面端搜索栏跟随主内容容器，避免侧边栏布局中产生视口级横向溢出 */
  :deep(.search-section) {
    width: 100%;
    margin: 0 0 16px;
    padding: 12px 16px;
    background: var(--bg-surface);
    border-radius: var(--radius-lg);
    border-bottom: 1px solid var(--border-light);
    box-sizing: border-box;
  }

  /* 桌面端左右分栏布局 */
  .knowledge-desktop-layout {
    display: flex;
    gap: var(--space-4);
    margin-top: var(--space-4);
  }

  .knowledge-sidebar {
    width: 240px;
    flex-shrink: 0;
  }

  .knowledge-main {
    flex: 1;
    min-width: 0;
  }

  .category-section {
    max-width: 600px;
  }

  .documents-section {
    max-width: 100%;
  }

  .stats-section {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }

  .stat-card {
    margin-bottom: 0;
  }

  .upload-form,
  .category-form {
    max-width: 600px;
  }

  .document-preview {
    max-height: 70vh;
    overflow-y: auto;
  }
}

@media (min-width: 1024px) {
  .knowledge-sidebar {
    width: 260px;
  }

  .stats-section {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
