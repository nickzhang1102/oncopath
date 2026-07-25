<template>
  <div class="documents-section">
    <van-loading v-if="loading" class="loading-center" />

    <div v-else-if="documents.length === 0" class="empty-state">
      <van-empty
        image="search"
        description="暂无文档"
      >
        <van-button
          type="primary"
          size="small"
          @click="$emit('upload-click')"
        >
          上传第一个文档
        </van-button>
      </van-empty>
    </div>

    <div v-else class="document-list van-hairline--top">
      <van-cell-group>
        <van-cell
          v-for="doc in documents"
          :key="doc.doc_id"
          :title="doc.doc_name"
          :label="formatDocumentLabel(doc)"
          :value="formatFileSize(doc.file_size)"
          is-link
          title-style="min-width: 180px;"
          @click="handleDocumentClick(doc)"
          class="document-cell"
        >
          <template #icon>
            <div class="file-icon">
              <van-icon
                :name="getFileIcon(doc.file_type)"
                :color="getFileIconColor(doc.file_type)"
                size="20"
              />
            </div>
          </template>
          <template #right-icon>
            <van-popover
              :show="isActionActive(doc.doc_id)"
              @update:show="(val) => { if (!val) activeActionDocId = null }"
              theme="dark"
              placement="bottom-end"
              :actions="documentActions"
              @select="onDocumentActionSelect($event, doc)"
            >
              <template #reference>
                <van-icon
                  name="ellipsis"
                  @click.stop="toggleDocumentActions(doc)"
                  class="action-icon"
                />
              </template>
            </van-popover>
          </template>
        </van-cell>
      </van-cell-group>
    </div>

    <!-- 加载更多 -->
    <div v-if="!finished && documents.length > 0" class="load-more">
      <van-button
        block
        type="default"
        :loading="loading"
        @click="$emit('load-more')"
      >
        加载更多
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { showToast } from 'vant'

// Props
const props = defineProps({
  documents: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  finished: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits([
  'document-preview',
  'document-edit',
  'document-delete',
  'document-generate-summary',
  'upload-click',
  'load-more'
])

// 支持 AI 摘要的文件类型
const SUMMARY_SUPPORTED_TYPES = ['txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']

// 文档操作相关
const documentActions = [
  { text: '编辑', icon: 'edit', value: 'edit' },
  { text: '生成AI摘要', icon: 'notes-o', value: 'generate-summary' },
  { text: '删除', icon: 'delete-o', value: 'delete', color: 'var(--danger-color)' }
]

// 用响应式 Map 管理操作菜单状态，避免直接修改 props
const activeActionDocId = ref(null)

const isActionActive = (docId) => activeActionDocId.value === docId

const toggleDocumentActions = (doc) => {
  // 关闭其他文档的操作菜单，切换当前文档
  activeActionDocId.value = activeActionDocId.value === doc.doc_id ? null : doc.doc_id
}

const handleDocumentClick = (doc) => {
  // 检查必要字段
  if (!doc.doc_id) {
    showToast('文档ID缺失')
    return
  }

  emit('document-preview', doc)
}

const onDocumentActionSelect = (action, doc) => {
  activeActionDocId.value = null

  if (action.value === 'edit') {
    emit('document-edit', doc)
  } else if (action.value === 'delete') {
    emit('document-delete', doc)
  } else if (action.value === 'generate-summary') {
    if (!SUMMARY_SUPPORTED_TYPES.includes(doc.file_type?.toLowerCase())) {
      showToast('该文件类型不支持AI摘要')
      return
    }
    emit('document-generate-summary', doc)
  }
}

// 工具函数
const formatDocumentInfo = (doc) => {
  const parts = []
  if (doc.category_name) {
    parts.push(doc.category_name)
  }
  if (doc.created_at) {
    parts.push(new Date(doc.created_at).toLocaleDateString())
  }
  return parts.join(' • ')
}

const formatDocumentLabel = (doc) => {
  const info = formatDocumentInfo(doc)
  if (doc.summary_status === 'completed' && doc.summary) {
    const truncated = doc.summary.length > 80 ? doc.summary.slice(0, 80) + '...' : doc.summary
    return `${info}\n${truncated}`
  }
  if (doc.summary_status === 'pending') {
    return `${info}\n摘要生成中...`
  }
  return info
}

const formatFileSize = (bytes) => {
  if (!bytes) return ''
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

const getFileIcon = (fileType) => {
  const iconMap = {
    'pdf': 'description',
    'doc': 'description',
    'docx': 'description',
    'txt': 'notes-o',
    'md': 'notes-o',
    'jpg': 'photo-o',
    'jpeg': 'photo-o',
    'png': 'photo-o',
    'gif': 'photo-o',
    'mp4': 'video-o',
    'avi': 'video-o',
    'mp3': 'music-o',
    'wav': 'music-o'
  }
  return iconMap[fileType?.toLowerCase()] || 'description'
}

const getFileIconColor = (fileType) => {
  const colorMap = {
    'pdf': 'var(--file-icon-pdf)',
    'doc': 'var(--file-icon-doc)',
    'docx': 'var(--file-icon-doc)',
    'txt': 'var(--file-icon-txt)',
    'md': 'var(--file-icon-doc)',
    'jpg': 'var(--file-icon-image)',
    'jpeg': 'var(--file-icon-image)',
    'png': 'var(--file-icon-image)',
    'gif': 'var(--file-icon-image)',
    'mp4': 'var(--file-icon-video)',
    'avi': 'var(--file-icon-video)',
    'mp3': 'var(--file-icon-audio)',
    'wav': 'var(--file-icon-audio)'
  }
  return colorMap[fileType?.toLowerCase()] || 'var(--file-icon-default)'
}
</script>

<style scoped>
.documents-section {
  background: var(--bg-surface);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px var(--shadow-color);
  height: 100%;
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

.document-list {
  overflow-y: auto;
}

.document-cell .van-cell__title {
  flex: 2;
  font-weight: 500;
  color: var(--text-primary);
  min-width: 180px;
}

.document-cell .van-cell__label {
  color: var(--text-quaternary);
  font-size: 12px;
  margin-top: 4px;
  white-space: pre-line;
  line-height: 1.5;
}

.document-cell .van-cell__label .summary-text {
  color: var(--text-tertiary);
  font-size: 11px;
  margin-top: 2px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.document-cell .van-cell__value {
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

.load-more {
  margin-top: 16px;
  padding: 0 16px;
}
</style>
