import { ref, computed } from 'vue'

/**
 * 可排序分页表格 composable
 * @param {Function} fetchFn - (params) => Promise<{ items, total, page, page_size, total_pages }>
 * @param {Object} options - { defaultSortBy, defaultSortOrder, pageSize }
 */
export function useSortableTable(fetchFn, options = {}) {
  const sortBy = ref(options.defaultSortBy || 'created_at')
  const sortOrder = ref(options.defaultSortOrder || 'desc')
  const page = ref(1)
  const pageSize = ref(options.pageSize || 20)
  const total = ref(0)
  const totalPages = ref(0)
  const items = ref([])
  const loading = ref(false)
  const lastExtraParams = ref({})

  async function load(extraParams = {}) {
    if (Object.keys(extraParams).length > 0) {
      lastExtraParams.value = { ...extraParams }
    }
    loading.value = true
    try {
      const params = {
        page: page.value,
        page_size: pageSize.value,
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
        ...lastExtraParams.value,
      }
      const res = await fetchFn(params)
      const data = res.data || res
      items.value = data.items || []
      total.value = data.total || 0
      totalPages.value = data.total_pages || 0
    } catch (e) {
      console.error('加载失败:', e)
      items.value = []
    } finally {
      loading.value = false
    }
  }

  function toggleSort(field) {
    if (sortBy.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortBy.value = field
      sortOrder.value = 'asc'
    }
    page.value = 1
    load(lastExtraParams.value)
  }

  function sortIcon(field) {
    if (sortBy.value !== field) return ''
    return sortOrder.value === 'asc' ? '↑' : '↓'
  }

  const hasNext = computed(() => page.value < totalPages.value)
  const hasPrev = computed(() => page.value > 1)

  function goToPage(p) {
    if (p < 1 || p > totalPages.value) return
    page.value = p
    load(lastExtraParams.value)
  }

  function setPageSize(size) {
    pageSize.value = size
    page.value = 1
    load(lastExtraParams.value)
  }

  return {
    sortBy, sortOrder, page, pageSize, total, totalPages,
    items, loading,
    load, toggleSort, sortIcon,
    hasNext, hasPrev, goToPage, setPageSize,
  }
}