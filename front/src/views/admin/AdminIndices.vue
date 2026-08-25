<template>
  <div class="admin-indices">
    <!-- 操作栏 -->
    <div class="toolbar">
      <van-search
        v-model="keyword"
        placeholder="搜索指标名/编码"
        @search="onSearch"
        @clear="onClearSearch"
      />
      <div class="action-buttons">
        <van-dropdown-menu class="category-filter">
          <van-dropdown-item v-model="categoryFilter" :options="categoryOptions" @change="onFilterChange" />
        </van-dropdown-menu>
        <van-dropdown-menu class="status-filter-menu">
          <van-dropdown-item v-model="statusFilter" :options="statusOptions" @change="onFilterChange" />
        </van-dropdown-menu>
        <van-button size="small" type="warning" @click="onImport">导入</van-button>
        <van-button size="small" type="success" @click="openCreateDialog">新增</van-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th>指标ID</th>
            <th class="sortable" @click="onSort('index_name')">
              指标名称 <span class="sort-indicator">{{ sortIcon('index_name') }}</span>
            </th>
            <th>编码</th>
            <th>英文名</th>
            <th>单位</th>
            <th>参考范围</th>
            <th>分类</th>
            <th>可生图</th>
            <th>可编辑</th>
            <th class="sortable" @click="onSort('sort')">
              排序 <span class="sort-indicator">{{ sortIcon('sort') }}</span>
            </th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="12" class="center-text"><van-loading size="24px" color="var(--primary-color)" /></td>
          </tr>
          <tr v-else-if="items.length === 0">
            <td colspan="12" class="center-text">暂无数据</td>
          </tr>
          <tr v-for="idx in items" :key="idx.index_id" v-else>
            <td class="secondary-text">{{ idx.index_id }}</td>
            <td class="name-cell">
              {{ idx.index_name }}
              <van-tag v-if="idx.is_system" type="warning" size="small" style="margin-left:4px">系统</van-tag>
            </td>
            <td><van-tag v-if="idx.index_code" type="primary" plain size="small">{{ idx.index_code }}</van-tag><span v-else>-</span></td>
            <td class="secondary-text">{{ idx.index_name_en || '-' }}</td>
            <td>{{ idx.index_unit || '-' }}</td>
            <td>
              <span v-if="idx.reference_min != null || idx.reference_max != null">
                {{ idx.reference_min ?? '-' }} ~ {{ idx.reference_max ?? '-' }}
              </span>
              <span v-else>-</span>
            </td>
            <td>{{ getCategoryName(idx.category) }}</td>
            <td><van-tag :type="idx.is_chart ? 'success' : 'default'" size="small">{{ idx.is_chart ? '是' : '否' }}</van-tag></td>
            <td><van-tag :type="idx.is_edit ? 'success' : 'default'" size="small">{{ idx.is_edit ? '是' : '否' }}</van-tag></td>
            <td>{{ idx.sort }}</td>
            <td>
              <van-tag :type="idx.is_active ? 'success' : 'danger'" size="small">
                {{ idx.is_active ? '启用' : '禁用' }}
              </van-tag>
            </td>
            <td class="action-cell">
              <van-button size="mini" plain @click="openEditDialog(idx)">编辑</van-button>
              <van-button
                size="mini"
                :type="idx.is_active ? 'warning' : 'success'"
                plain
                @click="onToggleStatus(idx)"
              >
                {{ idx.is_active ? '禁用' : '启用' }}
              </van-button>
              <van-button
                v-if="!idx.is_system"
                size="mini"
                type="danger"
                plain
                @click="onDelete(idx)"
              >
                删除
              </van-button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <van-button size="mini" :disabled="!hasPrev" @click="onPrevPage">上一页</van-button>
      <span class="page-info">{{ page }} / {{ totalPages || 1 }} (共 {{ total }} 条)</span>
      <van-button size="mini" :disabled="!hasNext" @click="onNextPage">下一页</van-button>
      <select class="page-size-select" :value="pageSize" @change="onPageSizeChange">
        <option v-for="s in pageSizeOptions" :key="s" :value="s">{{ s }}条/页</option>
      </select>
    </div>

    <!-- 新增/编辑对话框 -->
    <van-dialog
      v-model:show="showEditDialog"
      :title="editingIndex ? '编辑指标' : '新增指标'"
      show-cancel-button
      :before-close="onSaveIndex"
    >
      <div style="padding: 16px;">
        <van-field v-model="form.index_name" label="指标名称" placeholder="必填" />
        <van-field v-model="form.index_code" label="指标编码" placeholder="如 WBC" />
        <van-field v-model="form.index_name_en" label="英文名" placeholder="White Blood Cell" />
        <van-field v-model="form.index_unit" label="单位" placeholder="10^9/L" />
        <van-field
          v-model="form.category"
          is-link
          readonly
          label="分类"
          placeholder="选择分类"
          @click="showCategoryPicker = true"
        />
        <van-field v-model="form.sub_category" label="子分类" placeholder="红细胞系" />
        <van-field v-model="form.reference_min" type="number" label="参考下限" placeholder="4" />
        <van-field v-model="form.reference_max" type="number" label="参考上限" placeholder="10" />
        <van-field v-model="form.sort" type="digit" label="排序" placeholder="0" />
        <van-field v-model="form.description" label="描述" type="textarea" rows="2" placeholder="指标说明" />
        <van-field name="is_chart" label="可生图">
          <template #input>
            <van-switch v-model="form.is_chart" size="20px" />
          </template>
        </van-field>
        <van-field name="is_edit" label="可编辑">
          <template #input>
            <van-switch v-model="form.is_edit" size="20px" />
          </template>
        </van-field>
      </div>
    </van-dialog>

    <!-- 分类选择器 -->
    <van-popup
      v-model:show="showCategoryPicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-picker
        :columns="categoryPickerOptions"
        @confirm="onCategoryConfirm"
        @cancel="showCategoryPicker = false"
      />
    </van-popup>

    <!-- 批量导入对话框 -->
    <van-dialog
      v-model:show="showImportDialog"
      title="批量导入指标"
      show-cancel-button
      :before-close="onImportConfirm"
    >
      <div style="padding: 16px;">
        <p style="font-size: 13px; color: var(--text-quaternary); margin-bottom: 8px;">
          粘贴 JSON 数组，每项需含 index_name，最多 500 条
        </p>
        <van-field
          v-model="importJson"
          type="textarea"
          rows="6"
          placeholder='[{"index_name":"WBC","index_code":"WBC","category":"blood_routine"}]'
        />
      </div>
    </van-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showConfirmDialog, showToast } from 'vant'
import { adminApi } from '@/api/admin'
import { useSortableTable } from '@/composables/useSortableTable'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop } = useResponsive()

const keyword = ref('')
const categoryFilter = ref('')
const statusFilter = ref('')
const statusOptions = [
  { text: '全部状态', value: '' },
  { text: '启用', value: 'true' },
  { text: '禁用', value: 'false' },
]

// 分类数据
const categories = ref([])
const categoryOptions = ref([{ text: '全部分类', value: '' }])
const categoryPickerOptions = ref([])

// 编辑表单
const showEditDialog = ref(false)
const editingIndex = ref(null)
const form = ref({
  index_name: '', index_code: '', index_name_en: '',
  index_unit: '', category: '', sub_category: '',
  reference_min: '', reference_max: '', sort: '0',
  description: '', is_chart: true, is_edit: false,
})
const showCategoryPicker = ref(false)

// 批量导入
const showImportDialog = ref(false)
const importJson = ref('')

const {
  sortBy, sortOrder, page, pageSize, total, totalPages,
  items, loading, toggleSort, sortIcon,
  hasNext, hasPrev, goToPage, load, setPageSize,
} = useSortableTable(adminApi.getAdminIndices, {
  defaultSortBy: 'sort',
  defaultSortOrder: 'asc',
})

const pageSizeOptions = [10, 20, 50, 100]
function onPageSizeChange(e) {
  setPageSize(Number(e.target.value))
  loadData()
}

function getCategoryName(key) {
  const cat = categories.value.find(c => c.category_key === key)
  return cat ? cat.category_name : key || '-'
}

async function loadCategories() {
  try {
    const res = await adminApi.getIndexCategories()
    const data = res.data || res
    categories.value = data.items || []
    categoryOptions.value = [
      { text: '全部分类', value: '' },
      ...categories.value.map(c => ({ text: c.category_name, value: c.category_key })),
    ]
    categoryPickerOptions.value = categories.value.map(c => ({ text: c.category_name, value: c.category_key }))
  } catch (e) {
    console.error('加载分类失败:', e)
  }
}

function buildExtraParams() {
  const params = {}
  if (categoryFilter.value) params.category = categoryFilter.value
  if (statusFilter.value) params.is_active = statusFilter.value
  if (keyword.value) params.keyword = keyword.value
  return params
}

function loadData() { load(buildExtraParams()) }
function resetAndLoad() { page.value = 1; loadData() }
function onSearch() { resetAndLoad() }
function onClearSearch() { keyword.value = ''; resetAndLoad() }
function onFilterChange() { resetAndLoad() }

function onSort(field) { toggleSort(field); loadData() }
function onPrevPage() { if (hasPrev.value) { goToPage(page.value - 1); loadData() } }
function onNextPage() { if (hasNext.value) { goToPage(page.value + 1); loadData() } }

function onCategoryConfirm({ selectedOptions }) {
  form.value.category = selectedOptions[0]?.value || ''
  showCategoryPicker.value = false
}

function openCreateDialog() {
  editingIndex.value = null
  form.value = {
    index_name: '', index_code: '', index_name_en: '',
    index_unit: '', category: '', sub_category: '',
    reference_min: '', reference_max: '', sort: '0',
    description: '', is_chart: true, is_edit: false,
  }
  showEditDialog.value = true
}

function openEditDialog(idx) {
  editingIndex.value = idx
  form.value = {
    index_name: idx.index_name || '',
    index_code: idx.index_code || '',
    index_name_en: idx.index_name_en || '',
    index_unit: idx.index_unit || '',
    category: idx.category || '',
    sub_category: idx.sub_category || '',
    reference_min: idx.reference_min ?? '',
    reference_max: idx.reference_max ?? '',
    sort: String(idx.sort ?? 0),
    description: idx.description || '',
    is_chart: idx.is_chart !== false,
    is_edit: idx.is_edit !== false,
  }
  showEditDialog.value = true
}

function onSaveIndex(action) {
  if (action === 'cancel') return Promise.resolve(true)
  const { index_name, index_code, category, sub_category, index_unit,
          index_name_en, reference_min, reference_max, sort, description,
          is_chart, is_edit } = form.value

  if (!index_name) { showToast('请填写指标名称'); return Promise.resolve(false) }

  const payload = {
    index_name,
    index_code: index_code || null,
    index_name_en: index_name_en || null,
    index_unit: index_unit || null,
    category: category || null,
    sub_category: sub_category || null,
    reference_min: reference_min !== '' ? parseFloat(reference_min) : null,
    reference_max: reference_max !== '' ? parseFloat(reference_max) : null,
    sort: parseInt(sort) || 0,
    description: description || null,
    is_chart,
    is_edit,
  }

  const apiCall = editingIndex.value
    ? (() => {
        const updatePayload = {}
        for (const [k, v] of Object.entries(payload)) {
          const original = editingIndex.value[k]
          const originalVal = (k === 'is_chart' || k === 'is_edit') ? (original !== false) : (original ?? null)
          if (v !== originalVal) updatePayload[k] = v
        }
        return Object.keys(updatePayload).length > 0
          ? adminApi.updateIndex(editingIndex.value.index_id, updatePayload)
          : Promise.resolve(true)
      })()
    : adminApi.createIndex(payload)

  return apiCall.then(() => {
    showToast(editingIndex.value ? '保存成功' : '创建成功')
    resetAndLoad()
    return true
  }).catch(e => {
    console.error('保存指标失败:', e)
    return Promise.resolve(false)
  })
}

async function onToggleStatus(idx) {
  try {
    await adminApi.updateIndexStatus(idx.index_id, { is_active: !idx.is_active })
    showToast(idx.is_active ? '已禁用' : '已启用')
    resetAndLoad()
  } catch (e) {
    console.error('切换状态失败:', e)
  }
}

async function onDelete(idx) {
  try {
    await showConfirmDialog({ title: '确认删除', message: `确定要删除指标 "${idx.index_name}" 吗？` })
    await adminApi.deleteIndex(idx.index_id)
    showToast('已删除')
    resetAndLoad()
  } catch (e) {
    if (e !== 'cancel') console.error('删除指标失败:', e)
  }
}

function onImport() {
  importJson.value = ''
  showImportDialog.value = true
}

function onImportConfirm(action) {
  if (action === 'cancel') return Promise.resolve(true)
  if (!importJson.value.trim()) { showToast('请输入 JSON 数据'); return Promise.resolve(false) }
  let data
  try { data = JSON.parse(importJson.value) } catch { showToast('JSON 格式错误'); return Promise.resolve(false) }
  if (!Array.isArray(data)) { showToast('请输入 JSON 数组'); return Promise.resolve(false) }

  return adminApi.importIndices({ indices: data }).then(res => {
    const result = res.data || res
    showToast(`导入完成: 创建${result.created}条, 跳过${result.skipped}条`)
    resetAndLoad()
    return true
  }).catch(e => {
    console.error('导入失败:', e)
    return Promise.resolve(false)
  })
}

onMounted(() => { loadCategories(); loadData() })
</script>

<style scoped>
.admin-indices {
  padding: 0;
}

.toolbar {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}

.toolbar .van-search {
  padding: 8px 12px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px 8px;
}

.category-filter {
  flex: 1;
}

.status-filter-menu {
  flex: 1;
}

.table-wrapper {
  overflow-x: auto;
  background: var(--bg-surface);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.data-table th {
  background: var(--bg-primary);
  font-weight: 600;
  color: var(--text-primary);
  position: sticky;
  top: 0;
}

.data-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.data-table th.sortable:hover {
  color: var(--primary-color);
}

.sort-indicator {
  font-size: 12px;
  color: var(--primary-color);
}

.data-table tbody tr:hover {
  background: var(--bg-primary);
}

.center-text {
  text-align: center;
  color: var(--text-secondary);
  padding: 40px 0 !important;
}

.name-cell {
  font-weight: 500;
  color: var(--text-primary);
}

.secondary-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.action-cell {
  display: flex;
  gap: 4px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-color);
}

.page-info {
  font-size: 13px;
  color: var(--text-secondary);
}

.page-size-select {
  font-size: 12px;
  padding: 2px 4px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--bg-surface);
  color: var(--text-primary);
  outline: none;
  cursor: pointer;
}
</style>