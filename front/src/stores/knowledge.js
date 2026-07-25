import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { showToast, showConfirmDialog } from 'vant'
import {
  getKnowledgeCategories,
  getDocumentList
} from '@/api/knowledge'
import { useUserStore } from '@/stores/user'
import request from '@/api/request'

export const useKnowledgeStore = defineStore('knowledge', () => {
  // State
  const categoryTree = ref([])
  const documents = ref([])
  const selectedCategoryId = ref(null)
  const searchKeyword = ref('')
  const sortBy = ref('created_at_desc')
  const fileTypeFilter = ref('all')
  const documentsLoading = ref(false)
  const documentsFinished = ref(false)
  const currentPage = ref(1)
  const error = ref(null)

  // 防并发锁
  let _loadingLock = false
  let _initializing = false

  // Computed
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
    return flatten(categoryTree.value)
  })

  const selectedCategoryDisplayName = computed(() => {
    if (!selectedCategoryId.value) return '全部文档'
    const category = flatCategoryList.value.find(cat => cat.category_id === selectedCategoryId.value)
    return category ? category.category_name : '全部文档'
  })

  // Actions
  const loadCategories = async () => {
    try {
      error.value = null
      const response = await getKnowledgeCategories()
      categoryTree.value = response
    } catch (e) {
      error.value = e.message || '加载目录失败'
      showToast('加载目录失败')
    }
  }

  const loadDocuments = async (reset = false) => {
    // 防并发锁
    if (_loadingLock) return
    _loadingLock = true
    try {
      if (reset) {
        currentPage.value = 1
        documents.value = []
      }

      documentsLoading.value = true
      error.value = null
      const params = {
        category_id: selectedCategoryId.value,
        search: searchKeyword.value,
        sort_by: sortBy.value.split('_')[0],
        sort_order: sortBy.value.split('_')[1] || 'desc',
        page: currentPage.value,
        per_page: 20
      }

      if (fileTypeFilter.value !== 'all') {
        params.file_type = fileTypeFilter.value
      }

      const response = await getDocumentList(params)
      const result = response
      const newDocuments = result.documents || []

      if (reset) {
        documents.value = newDocuments
      } else {
        documents.value = [...documents.value, ...newDocuments]
      }

      const pagination = result.pagination || {}
      documentsFinished.value = !pagination.has_next

      if (pagination.has_next) {
        currentPage.value += 1
      }
    } catch (e) {
      error.value = e.message || '加载文档失败'
      showToast('加载文档失败')
    } finally {
      documentsLoading.value = false
      _loadingLock = false
    }
  }

  const deleteDocument = async (doc) => {
    try {
      error.value = null
      const userStore = useUserStore()
      if (!userStore.token) {
        showToast('请先登录')
        return
      }

      showToast({ type: 'loading', message: '删除中...', forbidClick: true, duration: 0 })

      const response = await request.delete(`/knowledge/documents/${doc.doc_id}`)

      showToast({ type: 'success', message: '删除成功' })

      const index = documents.value.findIndex(d => d.doc_id === doc.doc_id)
      if (index > -1) {
        documents.value.splice(index, 1)
      }

      loadCategories()
      loadDocuments(true)
    } catch (e) {
      error.value = e.message || '删除失败'
      showToast({ type: 'fail', message: e.message || '删除失败' })
    }
  }

  const confirmDeleteDocument = (doc) => {
    showConfirmDialog({
      title: '确认删除',
      message: `确定要删除文档"${doc.doc_name}"吗?此操作不可恢复。`,
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      confirmButtonColor: getComputedStyle(document.documentElement).getPropertyValue('--danger-color').trim()
    }).then(() => {
      deleteDocument(doc)
    }).catch(() => {})
  }

  const onSearch = (keyword) => { searchKeyword.value = keyword; loadDocuments(true) }
  const onSearchClear = () => { searchKeyword.value = ''; loadDocuments(true) }
  const onCategorySelected = ({ categoryId }) => {
    selectedCategoryId.value = categoryId
  }
  const onCategoryCreated = () => { loadCategories() }
  const onDocumentUploaded = () => { loadCategories(); loadDocuments(true) }
  const onLoadMore = () => { if (!documentsLoading.value && !documentsFinished.value) loadDocuments(false) }

  const initialize = async () => {
    // 防止重复初始化
    if (_initializing) return
    _initializing = true

    try {
      await loadCategories()
      // 每次初始化都加载文档（确保数据更新）
      await loadDocuments(true)
    } finally {
      _initializing = false
    }
  }

  // 监听分类变化自动加载文档
  watch(selectedCategoryId, () => {
    loadDocuments(true)
  })

  return {
    categoryTree, documents, selectedCategoryId, searchKeyword,
    sortBy, fileTypeFilter, documentsLoading, documentsFinished,
    currentPage, error,
    flatCategoryList, selectedCategoryDisplayName,
    loadCategories, loadDocuments, deleteDocument, confirmDeleteDocument,
    onSearch, onSearchClear, onCategorySelected, onCategoryCreated,
    onDocumentUploaded, onLoadMore, initialize
  }
})
