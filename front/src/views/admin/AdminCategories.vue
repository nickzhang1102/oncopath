<template>
  <div class="admin-categories">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <van-search v-model="keyword" placeholder="搜索分类名称/键" @search="onSearch" @clear="onClearSearch" />
      <div class="action-buttons">
        <van-button type="primary" size="small" icon="plus" @click="openCreateDialog">新增分类</van-button>
      </div>
    </div>

    <!-- 分组展示 -->
    <div v-if="!loading" class="category-groups">
      <div v-for="group in filteredGroups" :key="group.key" class="group-section">
        <div class="group-header" @click="toggleGroup(group.key)">
          <div class="group-title">
            <van-icon :name="group.icon" size="20" />
            <span>{{ group.name }}</span>
            <van-tag type="primary" plain size="medium">{{ group.items.length }}</van-tag>
          </div>
          <van-icon :name="expandedGroups[group.key] ? 'arrow-down' : 'arrow'" size="16" />
        </div>

        <div v-show="expandedGroups[group.key]" class="group-items">
          <div v-for="cat in group.items" :key="cat.category_key" class="category-row" :class="{ inactive: !cat.is_active }">
            <div class="cat-color" :style="{ backgroundColor: cat.color || '#6B7280' }">{{ cat.icon || cat.category_name[0] }}</div>
            <div class="cat-info">
              <div class="cat-name">
                {{ cat.category_name }}
                <van-tag v-if="!cat.is_active" type="danger" size="mini">已禁用</van-tag>
              </div>
              <div class="cat-meta">
                <span class="cat-key">{{ cat.category_key }}</span>
                <span v-if="cat.report_type" class="cat-report-type">{{ cat.report_type }}</span>
                <span class="cat-count">{{ cat.index_count }} 个指标</span>
              </div>
            </div>
            <div class="cat-actions">
              <van-button size="mini" plain @click="openEditDialog(cat)">编辑</van-button>
              <van-button size="mini" type="danger" plain @click="onDeleteCategory(cat)">删除</van-button>
            </div>
          </div>
        </div>
      </div>

      <van-empty v-if="filteredGroups.length === 0" description="暂无分类数据" />
    </div>

    <div v-else class="loading-state">
      <van-loading size="24px">加载中...</van-loading>
    </div>

    <!-- 新增/编辑对话框 -->
    <van-dialog
      v-model:show="showEditDialog"
      :title="editingCategory ? '编辑分类' : '新增分类'"
      show-cancel-button
      :before-close="onSaveCategory"
    >
      <div style="padding: 16px;">
        <van-field
          v-model="form.category_key"
          label="分类键"
          placeholder="blood_routine"
          :disabled="!!editingCategory"
        />
        <van-field v-model="form.category_name" label="分类名称" placeholder="血常规" />
        <van-field v-model="form.group_key" is-link readonly label="分组" placeholder="选择分组" @click="showGroupPicker = true" />
        <van-field v-model="form.report_type" is-link readonly label="报告类型" placeholder="选择报告类型" @click="showReportTypePicker = true" />
        <van-field v-model="form.icon" label="图标" placeholder="🩸" />
        <van-field v-model="form.color" label="颜色" placeholder="#ff4d4f" />
        <van-field v-model="form.description" label="描述" placeholder="血常规检查" />
        <van-field v-model="form.sort" type="digit" label="排序" placeholder="0" />
        <van-field v-if="editingCategory" name="is_active" label="启用状态">
          <template #input>
            <van-switch v-model="form.is_active" size="20px" />
          </template>
        </van-field>
      </div>
    </van-dialog>

    <!-- 分组选择器 -->
    <van-popup
      v-model:show="showGroupPicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-picker
        :columns="groupPickerOptions"
        @confirm="onGroupConfirm"
        @cancel="showGroupPicker = false"
      />
    </van-popup>

    <!-- 报告类型选择器 -->
    <van-popup
      v-model:show="showReportTypePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-picker
        :columns="reportTypeOptions"
        @confirm="onReportTypeConfirm"
        @cancel="showReportTypePicker = false"
      />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { showConfirmDialog, showToast } from 'vant'
import { adminApi } from '@/api/admin'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop } = useResponsive()

// 分组元信息（与 ImageCategorySelector 一致）
const GROUP_META = {
  examination: { name: '影像学检查', icon: 'photo-o' },
  functional: { name: '功能检查', icon: 'chart-trending-o' },
  endoscopic: { name: '内镜检查', icon: 'aim' },
  pathology: { name: '病理检查', icon: 'records-o' },
  blood: { name: '血液检验', icon: 'point-gift-o' },
  urine: { name: '尿液检验', icon: 'flower-o' },
  body_fluid: { name: '体液检验', icon: 'balance-o' },
  microbiology: { name: '微生物检验', icon: 'cluster-o' },
  other: { name: '其他', icon: 'apps-o' },
}

const REPORT_TYPES = [
  { text: '不指定', value: '' },
  { text: '检验类 (lab)', value: 'lab' },
  { text: '检查类 (exam)', value: 'exam' },
  { text: '病理类 (pathology)', value: 'pathology' },
]

const keyword = ref('')
const loading = ref(false)
const categories = ref([])
const expandedGroups = reactive({})
const showEditDialog = ref(false)
const showGroupPicker = ref(false)
const showReportTypePicker = ref(false)
const editingCategory = ref(null)
const form = ref({
  category_key: '', category_name: '', group_key: '', report_type: '',
  sort: '0', icon: '', color: '', description: '', is_active: true,
})

// 分组选择器选项
const groupPickerOptions = computed(() => [
  { text: '不指定', value: '' },
  ...Object.entries(GROUP_META).map(([key, meta]) => ({ text: meta.name, value: key })),
])

const reportTypeOptions = REPORT_TYPES

// 按分组聚合分类
const groupedCategories = computed(() => {
  const groupMap = new Map()

  for (const cat of categories.value) {
    const gk = cat.group_key && GROUP_META[cat.group_key] ? cat.group_key : 'other'
    if (!groupMap.has(gk)) groupMap.set(gk, [])
    groupMap.get(gk).push(cat)
  }

  const groups = []
  for (const [key, items] of groupMap) {
    const meta = GROUP_META[key] || GROUP_META.other
    groups.push({
      key, name: meta.name, icon: meta.icon, items,
      minSort: Math.min(...items.map(i => i.sort ?? 999)),
    })
  }

  return groups.sort((a, b) => a.minSort - b.minSort)
})

// 搜索过滤
const filteredGroups = computed(() => {
  if (!keyword.value) return groupedCategories.value
  const kw = keyword.value.toLowerCase()
  return groupedCategories.value
    .map(g => ({
      ...g,
      items: g.items.filter(c =>
        c.category_name.toLowerCase().includes(kw) ||
        c.category_key.toLowerCase().includes(kw)
      ),
    }))
    .filter(g => g.items.length > 0)
})

// 加载分类数据
async function loadCategories() {
  loading.value = true
  try {
    const res = await adminApi.getIndexCategories()
    const data = res.data || res
    categories.value = data.items || []
    // 默认展开第一个分组
    if (groupedCategories.value.length > 0) {
      expandedGroups[groupedCategories.value[0].key] = true
    }
  } catch (e) {
    console.error('加载分类失败:', e)
  } finally {
    loading.value = false
  }
}

function toggleGroup(key) {
  expandedGroups[key] = !expandedGroups[key]
}

// 新增分类
function openCreateDialog() {
  editingCategory.value = null
  form.value = {
    category_key: '', category_name: '', group_key: '', report_type: '',
    sort: '0', icon: '', color: '', description: '', is_active: true,
  }
  showEditDialog.value = true
}

// 编辑分类
function openEditDialog(cat) {
  editingCategory.value = cat
  form.value = {
    category_key: cat.category_key,
    category_name: cat.category_name,
    group_key: cat.group_key || '',
    report_type: cat.report_type || '',
    sort: String(cat.sort ?? 0),
    icon: cat.icon || '',
    color: cat.color || '',
    description: cat.description || '',
    is_active: cat.is_active !== false,
  }
  showEditDialog.value = true
}

// 保存分类
function onSaveCategory(action) {
  if (action === 'cancel') return Promise.resolve(true)

  const { category_key, category_name, sort, icon, color, description, group_key, report_type, is_active } = form.value
  if (!category_key || !category_name) {
    showToast('请填写分类键和名称')
    return Promise.resolve(false)
  }

  const payload = { category_name, sort: parseInt(sort) || 0 }
  if (icon) payload.icon = icon
  if (color) payload.color = color
  if (description) payload.description = description
  if (group_key) payload.group_key = group_key
  if (report_type) payload.report_type = report_type

  const apiCall = editingCategory.value
    ? adminApi.updateIndexCategory(editingCategory.value.category_key, { ...payload, is_active })
    : adminApi.createIndexCategory({ category_key, ...payload })

  return apiCall.then(() => {
    showToast(editingCategory.value ? '保存成功' : '创建成功')
    loadCategories()
    return true
  }).catch(e => {
    console.error('保存分类失败:', e)
    return Promise.resolve(false)
  })
}

// 删除分类
async function onDeleteCategory(cat) {
  try {
    await showConfirmDialog({ title: '确认删除', message: `确定要删除分类 "${cat.category_name}" 吗？` })
    await adminApi.deleteIndexCategory(cat.category_key)
    showToast('已删除')
    loadCategories()
  } catch (e) {
    if (e !== 'cancel') console.error('删除分类失败:', e)
  }
}

// 分组选择确认
function onGroupConfirm({ selectedOptions }) {
  form.value.group_key = selectedOptions[0]?.value || ''
  showGroupPicker.value = false
}

// 报告类型选择确认
function onReportTypeConfirm({ selectedOptions }) {
  form.value.report_type = selectedOptions[0]?.value || ''
  showReportTypePicker.value = false
}

function onSearch() { /* 本地过滤，无需重新加载 */ }
function onClearSearch() { keyword.value = '' }

onMounted(() => { loadCategories() })
</script>

<style scoped>
.admin-categories {
  padding: 0;
}

.toolbar {
  background: var(--bg-surface, #fff);
  border-bottom: 1px solid var(--border-color, #ebedf0);
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

.category-groups {
  padding: 12px;
}

.group-section {
  background: var(--bg-surface, #fff);
  border-radius: 12px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color, #ebedf0);
}

.group-header:hover {
  background: var(--bg-primary, #f5f5f5);
}

.group-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #323233);
}

.group-items {
  padding: 4px 0;
}

.category-row {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  gap: 12px;
  border-bottom: 1px solid var(--border-color, #ebedf0);
}

.category-row:last-child {
  border-bottom: none;
}

.category-row.inactive {
  opacity: 0.5;
}

.cat-color {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
  font-weight: bold;
  flex-shrink: 0;
}

.cat-info {
  flex: 1;
  min-width: 0;
}

.cat-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #323233);
  display: flex;
  align-items: center;
  gap: 6px;
}

.cat-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-secondary, #969799);
}

.cat-key {
  font-family: monospace;
}

.cat-report-type {
  background: var(--primary-light, #e8f3fe);
  color: var(--primary-color, #1989fa);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.cat-count {
  color: var(--text-tertiary, #c8c9cc);
}

.cat-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 48px 0;
}
</style>
