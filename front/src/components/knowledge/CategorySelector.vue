<template>
  <div class="category-section">
    <!-- 移动端：弹窗选择器 -->
    <template v-if="!isDesktop">
      <van-cell-group>
        <van-cell
          title="选择分类"
          :value="selectedCategoryDisplayName"
          is-link
          @click="showCategoryTreeSelect = true"
        >
          <template #icon>
            <van-icon name="folder-o" />
          </template>
        </van-cell>
      </van-cell-group>

      <!-- 分类树选择弹窗 -->
      <van-popup
        v-model:show="showCategoryTreeSelect"
        position="bottom"
        round
      >
        <div class="category-tree-header">
          <van-nav-bar title="选择分类" />
        </div>
        <div class="category-tree-content">
          <van-cell-group>
            <van-cell
              title="全部文档"
              :class="{ 'selected-category': !selectedCategoryId }"
              @click="selectCategoryItem(null, '全部文档')"
            />
            <van-cell
              v-for="category in flatCategoryList"
              :key="category.category_id"
              :title="category.display_name"
              :class="{ 'selected-category': selectedCategoryId === category.category_id }"
              @click="selectCategoryItem(category.category_id, category.category_name)"
            />
          </van-cell-group>
        </div>
      </van-popup>
    </template>

    <!-- 桌面端：直接展示分类树 -->
    <template v-else>
      <div class="desktop-category-tree">
        <div class="category-tree-title">
          <van-icon name="label-o" size="16" />
          <span>文档分类</span>
          <van-button
            size="mini"
            type="primary"
            plain
            icon="plus"
            class="add-category-btn"
            @click="openCreateCategoryDialog"
          />
        </div>
        <div class="category-tree-list">
          <div
            class="category-tree-item"
            :class="{ 'category-tree-item--active': !selectedCategoryId }"
            @click="selectCategoryItem(null, '全部文档')"
          >
            <van-icon name="apps-o" size="14" />
            <span class="category-tree-item__text">全部文档</span>
            <span class="category-tree-item__count">{{ totalCount }}</span>
          </div>
          <template v-for="category in flatCategoryList" :key="category.category_id">
            <div
              class="category-tree-item"
              :class="{ 'category-tree-item--active': selectedCategoryId === category.category_id }"
              :style="{ paddingLeft: 12 + category.level * 16 + 'px' }"
              @click="selectCategoryItem(category.category_id, category.category_name)"
            >
              <van-icon :name="category.level === 0 ? 'folder-o' : 'description'" size="14" />
              <span class="category-tree-item__text">{{ category.category_name }}</span>
              <span class="category-tree-item__count">{{ category.document_count || '' }}</span>
            </div>
          </template>
        </div>
      </div>
    </template>

    <!-- 创建分类对话框 -->
    <van-dialog
      v-model:show="showCreateCategoryDialog"
      title="新建分类"
      show-cancel-button
      @confirm="handleCreateCategory"
      @cancel="resetCategoryForm"
    >
      <div class="category-form">
        <van-field
          v-model="categoryForm.name"
          label="分类名称"
          placeholder="请输入分类名称"
          required
        />
        <van-field
          v-model="categoryForm.description"
          label="分类描述"
          placeholder="请输入分类描述（可选）"
          type="textarea"
          rows="3"
        />
        <van-field
          v-model="categoryForm.parentName"
          label="上级分类"
          placeholder="请选择上级分类（可选）"
          readonly
          is-link
          @click="showParentCategorySelector = true"
        />
      </div>
    </van-dialog>

    <!-- 上级分类选择器 -->
    <van-popup
      v-model:show="showParentCategorySelector"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :style="isDesktop ? { width: '360px', maxHeight: '60vh', borderRadius: 'var(--radius-lg)', display: 'flex', flexDirection: 'column' } : { height: '50%' }"
    >
      <template v-if="isDesktop">
        <div class="category-popup-header">
          <span>选择上级分类</span>
          <van-icon name="cross" @click="showParentCategorySelector = false" />
        </div>
        <div class="category-popup-list">
          <div
            class="category-popup-item"
            :class="{ 'category-popup-item--active': categoryForm.parentId === null }"
            @click="onParentListSelect(null, '无上级分类')"
          >
            <span>无上级分类</span>
            <van-icon v-if="categoryForm.parentId === null" name="success" color="var(--primary-color)" />
          </div>
          <div
            v-for="cat in flatCategoryList"
            :key="cat.category_id"
            class="category-popup-item"
            :class="{ 'category-popup-item--active': categoryForm.parentId === cat.category_id }"
            @click="onParentListSelect(cat.category_id, cat.display_name)"
          >
            <span>{{ cat.display_name }}</span>
            <van-icon v-if="categoryForm.parentId === cat.category_id" name="success" color="var(--primary-color)" />
          </div>
        </div>
      </template>
      <van-picker
        v-else
        :columns="parentCategoryOptions"
        @confirm="onParentCategorySelect"
        @cancel="showParentCategorySelector = false"
      />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { showToast } from 'vant'
import { createKnowledgeCategory } from '@/api/knowledge'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop } = useResponsive()

// Props
const props = defineProps({
  categoryTree: {
    type: Array,
    default: () => []
  },
  selectedCategoryId: {
    type: [String, Number],
    default: null
  },
  totalCount: {
    type: Number,
    default: 0
  }
})

// Emits
const emit = defineEmits(['update:selectedCategoryId', 'category-selected', 'category-created'])

// 响应式数据
const showCategoryTreeSelect = ref(false)
const showCreateCategoryDialog = ref(false)
const showParentCategorySelector = ref(false)
const categoryLoading = ref(false)

const categoryForm = ref({
  name: '',
  description: '',
  parentId: null,
  parentName: ''
})

// 计算属性
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

const selectedCategoryDisplayName = computed(() => {
  if (!props.selectedCategoryId) {
    return '全部文档'
  }
  const category = flatCategoryList.value.find(cat => cat.category_id === props.selectedCategoryId)
  return category ? category.category_name : '全部文档'
})

const parentCategoryOptions = computed(() => {
  return [
    { text: '无上级分类', value: null },
    ...flatCategoryList.value.map(cat => ({
      text: cat.display_name,
      value: cat.category_id
    }))
  ]
})

// 方法
const selectCategoryItem = (categoryId, categoryName) => {
  emit('update:selectedCategoryId', categoryId)
  emit('category-selected', { categoryId, categoryName })
  showCategoryTreeSelect.value = false
}

const onParentCategorySelect = ({ selectedOptions }) => {
  if (selectedOptions && selectedOptions.length > 0) {
    const selectedOption = selectedOptions[0]
    categoryForm.value.parentId = selectedOption.value
    categoryForm.value.parentName = selectedOption.text
  }
  showParentCategorySelector.value = false
}

const onParentListSelect = (parentId, parentName) => {
  categoryForm.value.parentId = parentId
  categoryForm.value.parentName = parentName
  showParentCategorySelector.value = false
}

const handleCreateCategory = async () => {
  if (!categoryForm.value.name.trim()) {
    showToast('请输入分类名称')
    return
  }

  try {
    categoryLoading.value = true
    const categoryData = {
      category_name: categoryForm.value.name,
      description: categoryForm.value.description || '',
      parent_id: categoryForm.value.parentId
    }

    const response = await createKnowledgeCategory(categoryData)
    if (response && response.category_id) {
      showToast('分类创建成功')
      showCreateCategoryDialog.value = false
      resetCategoryForm()
      emit('category-created')
    } else {
      showToast(response?.message || '创建失败')
    }
  } catch (error) {
    console.error('创建分类失败:', error)
    const msg = error?.response?.data?.detail || error?.message || '创建分类失败'
    showToast(msg)
  } finally {
    categoryLoading.value = false
  }
}

const resetCategoryForm = () => {
  categoryForm.value = {
    name: '',
    description: '',
    parentId: null,
    parentName: ''
  }
}

const openCreateCategoryDialog = () => {
  showCreateCategoryDialog.value = true
}

// 暴露方法给父组件
defineExpose({
  openCreateCategoryDialog
})
</script>

<style scoped>
.category-section {
  margin-bottom: 16px;
}

.category-tree-header {
  border-bottom: 1px solid var(--border-light);
}

.category-tree-content {
  height: calc(100% - 46px);
  overflow-y: auto;
  padding-bottom: calc(50px + env(safe-area-inset-bottom, 0px));
}

.selected-category {
  background-color: var(--bg-primary);
  color: var(--primary-color);
}

.selected-category .van-cell__title {
  color: var(--primary-color);
  font-weight: 600;
}

.category-form {
  padding: 16px;
}

.category-form .van-field {
  margin-bottom: 12px;
}

/* 桌面端分类树 */
.desktop-category-tree {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  overflow: hidden;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.category-tree-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.add-category-btn {
  margin-left: auto;
}

.category-tree-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.category-tree-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  color: var(--text-secondary);
}

.category-tree-item:hover {
  background: var(--primary-alpha-5);
  color: var(--text-primary);
}

.category-tree-item--active {
  background: var(--primary-alpha-8);
  color: var(--primary-color);
  font-weight: 500;
}

.category-tree-item--active:hover {
  background: var(--primary-alpha-10);
}

.category-tree-item__text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-tree-item__count {
  font-size: 12px;
  color: var(--text-tertiary);
  flex-shrink: 0;
  min-width: 20px;
  text-align: right;
}

.category-tree-item--active .category-tree-item__count {
  color: var(--primary-color);
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