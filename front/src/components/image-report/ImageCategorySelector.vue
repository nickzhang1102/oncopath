<template>
  <div class="category-selector">
    <!-- 标题栏 -->
    <div class="selector-header">
      <van-button size="small" @click="cancel" class="header-btn">取消</van-button>
      <span class="header-title">选择检查分类</span>
      <van-button size="small" type="primary" :disabled="!selectedCategory" @click="confirm" class="header-btn">确定</van-button>
    </div>

    <!-- 分类分组 -->
    <div
      class="category-groups"
      ref="categoryGroupsRef"
    >
      <div
        v-for="group in groupedCategories"
        :key="group.key"
        class="category-group"
      >
        <!-- 分组标题 -->
        <div class="group-header" @click="toggleGroup(group.key)">
          <div class="group-title">
            <span class="group-icon"><van-icon :name="group.icon" /></span>
            <span class="group-name">{{ group.name }}</span>
            <span class="group-count">{{ group.items.length }}</span>
          </div>
          <van-icon
            :name="expandedGroups[group.key] ? 'arrow-down' : 'arrow'"
            size="16"
            color="var(--text-tertiary)"
          />
        </div>

        <!-- 分组内容 -->
        <div
          v-show="expandedGroups[group.key]"
          class="group-items"
        >
          <div
            v-for="category in group.items"
            :key="category.category_key"
            class="category-item"
            :class="{ selected: selectedCategory === category.category_key }"
            @click="selectCategory(category)"
          >
            <div class="category-info">
              <div class="category-icon" :style="{ backgroundColor: category.color }">
                {{ category.icon }}
              </div>
              <div class="category-details">
                <div class="category-name">{{ category.category_name }}</div>
                <div class="category-desc">{{ category.description }}</div>
              </div>
            </div>
            <div class="category-check" v-if="selectedCategory === category.category_key">
              <van-icon name="success" color="white" size="14" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="groupedCategories.length === 0" class="empty-state">
      <van-empty description="暂无分类" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { getImageCategories } from '@/api/imageReport'

const emit = defineEmits(['confirm', 'cancel'])

// 状态变量
const selectedCategory = ref('')
const expandedGroups = ref({})
const allCategories = ref([])
const categoryGroupsRef = ref(null)

// 分组元信息常量（group_key → {name, icon}）
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

// 计算属性：按 group_key 动态聚合
const groupedCategories = computed(() => {
  const groupMap = new Map()

  for (const cat of allCategories.value) {
    const gk = cat.group_key && GROUP_META[cat.group_key] ? cat.group_key : 'other'
    if (!groupMap.has(gk)) {
      groupMap.set(gk, [])
    }
    groupMap.get(gk).push(cat)
  }

  const groups = []
  for (const [key, items] of groupMap) {
    const meta = GROUP_META[key] || GROUP_META.other
    groups.push({
      key,
      name: meta.name,
      icon: meta.icon,
      items,
      minSortOrder: Math.min(...items.map(item => item.sort_order ?? 999))
    })
  }

  return groups.sort((a, b) => a.minSortOrder - b.minSortOrder)
})

// 初始化
onMounted(async () => {
  await loadCategories()
  // 默认展开第一个分组
  if (groupedCategories.value.length > 0) {
    expandedGroups.value[groupedCategories.value[0].key] = true
  }
})

// 加载分类数据
const loadCategories = async () => {
  try {
    const res = await getImageCategories()
    
    // 处理不同的响应格式
    let data = res
    if (res && res.data !== undefined) {
      data = res.data
    }
    
    if (Array.isArray(data)) {
      allCategories.value = data
    } else if (data && data.status === 'success' && data.data) {
      allCategories.value = data.data
    } else if (data && Array.isArray(data.items)) {
      allCategories.value = data.items
    } else {
      console.error('分类数据加载失败，未知格式:', data)
      allCategories.value = []
    }
  } catch (error) {
    console.error('加载分类失败:', error)
    allCategories.value = []
  }
}

// 切换分组展开状态
const toggleGroup = (groupKey) => {
  expandedGroups.value[groupKey] = !expandedGroups.value[groupKey]
}

// 选择分类
const selectCategory = (category) => {
  selectedCategory.value = category.category_key
}

// 确认选择
const confirm = () => {
  if (selectedCategory.value) {
    const category = allCategories.value.find(
      cat => cat.category_key === selectedCategory.value
    )
    if (category) {
      emit('confirm', category)
    }
  }
}

// 取消
const cancel = () => {
  emit('cancel')
}
</script>

<style scoped>
.category-selector {
  min-height: 50vh;
  max-height: 85vh;
  background: var(--border-light);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

/* 标题栏 */
.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-light);
  flex-shrink: 0;
}

.header-btn {
  min-width: 60px;
  height: 32px;
  padding: 0 12px;
  font-size: 14px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  text-align: center;
}

/* 分类分组 */
.category-groups {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 12px 16px;
  -webkit-overflow-scrolling: touch;
}

.category-group {
  background: var(--bg-surface);
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px var(--shadow-color-sm);
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-light);
  transition: background 0.2s ease;
}

.group-header:active {
  background: var(--bg-secondary);
}

.group-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.group-icon {
  font-size: 18px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated);
  border-radius: 8px;
}

.group-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
}

.group-count {
  font-size: 12px;
  color: var(--text-tertiary);
  background: var(--border-light);
  padding: 2px 8px;
  border-radius: 12px;
  margin-left: 8px;
}

.group-items {
  padding: 8px;
}

.category-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  margin: 4px 0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.category-item:active {
  transform: scale(0.98);
}

.category-item.selected {
  background: var(--bg-primary);
  border-color: var(--primary-color);
  box-shadow: 0 2px 8px var(--primary-alpha-20);
}

.category-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.category-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: white;
  font-weight: bold;
  flex-shrink: 0;
}

.category-details {
  flex: 1;
  min-width: 0;
}

.category-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.category-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.category-check {
  width: 24px;
  height: 24px;
  background: var(--primary-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 12px;
}

/* 空状态 */
.empty-state {
  padding: 40px 0;
  text-align: center;
}

/* 覆盖 vant 组件样式 */
:deep(.van-empty__description) {
  color: var(--text-secondary);
}

/* 移动端优化 */
@media (max-width: 768px) {
  .category-selector {
    min-height: 60vh;
    max-height: 80vh;
  }

  .selector-header {
    padding: 12px;
  }

  .header-btn {
    min-width: 50px;
    height: 30px;
    padding: 0 10px;
    font-size: 13px;
  }

  .header-title {
    font-size: 15px;
  }

  .category-groups {
    padding: 0 8px 16px;
  }

  .category-group {
    margin-bottom: 8px;
  }

  .group-header {
    padding: 12px;
  }

  .group-name {
    font-size: 15px;
  }

  .category-item {
    padding: 10px;
  }

  .category-name {
    font-size: 14px;
  }

  .category-desc {
    font-size: 12px;
  }
}
</style>