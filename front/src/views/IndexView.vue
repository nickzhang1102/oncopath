<template>
  <div class="index-container">
    <!-- 动态背景 -->
    <BackgroundAnimation />

    <!-- 返回按钮 -->
    <BackButton title="指标查询" />

    <!-- 指标类型过滤区域 -->
    <div class="filter-section">
      <div class="filter-card">
        <van-tabs v-model:active="activeCategory" @change="onCategoryChange">
          <van-tab 
            v-for="cat in categories" 
            :key="cat.category_key" 
            :title="cat.category_name"
            :name="cat.category_key"
          />
        </van-tabs>
      </div>
    </div>

    <!-- 指标列表 -->
    <div class="list-section" ref="listSectionRef">
      <van-loading v-if="loading" class="loading-center" />

      <!-- 组合指标列表 -->
      <template v-else-if="activeCategory === 'index_groups'">
        <van-empty v-if="groupList.length === 0" description="暂无保存的组合" />
        <van-swipe-cell v-for="group in groupList" :key="group.id">
          <div class="index-item" @click="viewGroup(group)">
            <div class="item-container">
              <div class="index-content">
                <div class="index-name">{{ group.group_name }}</div>
                <div class="index-desc">
                  包含 {{ group.index_ids?.length || 0 }} 个指标
                </div>
              </div>
            </div>
            <div class="index-actions">
              <van-icon
                name="delete-o"
                class="delete-icon"
                @click.stop="confirmDeleteGroup(group)"
              />
              <van-icon name="arrow" class="arrow-icon" />
            </div>
          </div>
          <template #right>
            <van-button
              type="danger"
              square
              class="swipe-button"
              @click.stop="confirmDeleteGroup(group)"
            >
              删除
            </van-button>
          </template>
        </van-swipe-cell>
      </template>

      <!-- 常规指标列表 -->
      <template v-else>
        <van-empty v-if="indexList.length === 0" description="暂无指标数据" />

        <van-list
          v-else
          v-model:loading="loadingMore"
          :finished="finished"
          finished-text="没有更多数据了"
        >
        <!-- 对比模式控制按钮 -->
        <div class="compare-mode-controls">
          <van-button 
            class="compare-toggle-btn"
            :class="{ active: compareMode }"
            icon="cluster-o"
            size="small" 
            round
            @click="toggleCompareMode"
          >
            {{ compareMode ? '退出对比' : '指标对比' }}
          </van-button>
          
          <transition name="fade">
            <van-button 
              v-if="compareMode && selectedIndexes.length > 1" 
              class="start-compare-btn"
              icon="chart-trending-o"
              size="small" 
              type="primary"
              round
              @click="compareSelected"
            >
              开始对比({{ selectedIndexes.length }})
            </van-button>
          </transition>
        </div>

        <van-swipe-cell v-for="item in indexList" :key="item.index_id">
          <div
            class="index-item"
            :class="{ 'selected-item': compareMode && isIndexSelected(item) }"
            @click="compareMode ? toggleSelectIndex(item) : viewDetail(item)"
          >
            <div class="item-container">
              <div v-if="compareMode" class="checkbox-container">
                <van-checkbox
                  :checked="isIndexSelected(item)"
                  @click.stop="toggleSelectIndex(item)"
                  icon-size="20px"
                />
              </div>
              <div class="index-content">
                <div class="index-name">{{ item.index_name }}</div>
                <div class="index-desc">
                  {{ item.description || '暂无描述' }}
                  <span v-if="item.index_unit" class="unit">| 单位: {{ item.index_unit }}</span>
                </div>
                <div v-if="item.reference_min || item.reference_max" class="index-reference">
                  参考范围: {{ item.reference_min || '-' }} ~ {{ item.reference_max || '-' }} {{ item.index_unit }}
                </div>
              </div>
            </div>
            <div class="index-actions">
              <van-icon
                :name="item.is_favorited ? 'star' : 'star-o'"
                class="favorite-icon"
                :class="{ 'is-favorited': item.is_favorited }"
                @click.stop="handleFavorite(item)"
              />
              <van-icon name="arrow" class="arrow-icon" />
            </div>
          </div>
          <template #right>
            <van-button
              :type="item.is_favorited ? 'danger' : 'primary'"
              square
              class="swipe-button"
              @click.stop="handleFavorite(item)"
            >
              {{ item.is_favorited ? '取消收藏' : '收藏' }}
            </van-button>
          </template>
        </van-swipe-cell>
      </van-list>
      </template>

      <van-back-top :offset="100" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import { medicalApi } from '@/api/medical'
import { showToast, showConfirmDialog } from 'vant'
const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'

const router = useRouter()
const patientStore = usePatientStore()

// 响应式数据
const indexList = ref([])
const categories = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const finished = ref(false)
const activeCategory = ref('favorites')
const listSectionRef = ref(null)

// 对比模式
const compareMode = ref(false)
const selectedIndexes = ref([])

// 组合指标
const groupList = ref([])

// 获取分类列表
async function fetchCategories() {
  try {
    const result = await medicalApi.getIndexCategories()
    categories.value = result || []
    // 追加"组合指标"虚拟分类（放在最前面）
    categories.value.unshift({ category_key: 'index_groups', category_name: '组合指标' })
    // 默认选中第一个数据分类（跳过收藏和组合）
    if (result.length > 0) {
      const firstDataCategory = result.find(c => c.category_key !== 'favorites' && c.category_key !== 'index_groups')
      activeCategory.value = firstDataCategory?.category_key || result[0].category_key
    }
  } catch (error) {
    console.error('获取分类失败:', error)
    categories.value = [
      { category_key: 'index_groups', category_name: '组合指标' },
      { category_key: 'favorites', category_name: '我的收藏' },
      { category_key: 'blood_routine', category_name: '血常规' },
      { category_key: 'biochemistry', category_name: '生化' },
      { category_key: 'tumor_marker', category_name: '肿瘤标志物' },
      { category_key: 'coagulation', category_name: '凝血' },
      { category_key: 'urine_routine', category_name: '尿常规' },
    ]
  }
}

// 分类切换处理
function onCategoryChange(categoryKey) {
  activeCategory.value = categoryKey
  compareMode.value = false
  selectedIndexes.value = []
  if (categoryKey === 'index_groups') {
    fetchGroups()
  } else {
    fetchIndexData()
  }
}

// 获取指标数据
async function fetchIndexData() {
  loading.value = true
  try {
    const result = await medicalApi.getIndicesByCategory(activeCategory.value)
    indexList.value = result || []
    finished.value = true
  } catch (error) {
    console.error('获取指标列表失败:', error)
    showToast('获取指标列表失败')
    indexList.value = []
    finished.value = true
  } finally {
    loading.value = false
  }
}

// 获取组合列表
async function fetchGroups() {
  loading.value = true
  try {
    const patientId = patientStore.currentPatient?.patient_id
    if (!patientId) {
      groupList.value = []
      return
    }
    const result = await medicalApi.getIndexGroups(patientId)
    groupList.value = result || []
  } catch (error) {
    console.error('获取组合列表失败:', error)
    groupList.value = []
  } finally {
    loading.value = false
  }
}

// 查看指标详情
function viewDetail(item) {
  router.push({
    path: '/home/indicator/history',
    query: {
      index_id: item.index_id,
      index_name: item.index_name
    }
  })
}

// 查看组合对比
function viewGroup(group) {
  if (!group.index_ids || group.index_ids.length < 2) {
    showToast('组合数据异常')
    return
  }
  // 将 index_ids 转为 indexes 格式（只含 index_id 和 index_name）
  const indexes = group.index_ids.map(id => ({
    index_id: id,
    index_name: `指标${id}`,
    is_chart: 0,
    reference_max: '',
    reference_min: 0,
    is_edit: 0,
  }))
  router.push({
    path: '/home/indicator/history',
    query: {
      compare_mode: '1',
      indexes: JSON.stringify(indexes),
    }
  })
}

// 确认删除组合
function confirmDeleteGroup(group) {
  showConfirmDialog({
    title: '删除组合',
    message: `确定要删除「${group.group_name}」吗？`,
  }).then(() => {
    deleteGroup(group)
  }).catch(() => {})
}

// 删除组合
async function deleteGroup(group) {
  try {
    await medicalApi.deleteIndexGroup(group.id)
    showToast('已删除')
    fetchGroups()
  } catch (error) {
    showToast('删除失败')
  }
}

// 收藏/取消收藏
async function handleFavorite(item) {
  try {
    if (item.is_favorited) {
      await medicalApi.removeFavoriteIndex(item.index_id)
      showToast('已取消收藏')
    } else {
      await medicalApi.addFavoriteIndex(item.index_id)
      showToast('收藏成功')
    }
    // 刷新列表
    await fetchIndexData()
  } catch (error) {
    console.error('操作失败:', error)
    showToast('操作失败，请稍后重试')
  }
}

// 对比模式切换
function toggleCompareMode() {
  compareMode.value = !compareMode.value
  if (!compareMode.value) {
    selectedIndexes.value = []
  }
}

// 切换选择指标
function toggleSelectIndex(item) {
  const index = selectedIndexes.value.findIndex(i => i.index_id === item.index_id)
  if (index > -1) {
    selectedIndexes.value.splice(index, 1)
  } else {
    selectedIndexes.value.push(item)
  }
}

// 检查指标是否被选中
function isIndexSelected(item) {
  return selectedIndexes.value.some(i => i.index_id === item.index_id)
}

// 开始对比
function compareSelected() {
  if (selectedIndexes.value.length < 2) {
    showToast('请至少选择2个指标进行对比')
    return
  }

  router.push({
    path: '/home/indicator/history',
    query: {
      compare_mode: '1',
      indexes: JSON.stringify(selectedIndexes.value.map(item => ({
        index_id: item.index_id,
        index_name: item.index_name,
        is_chart: item.is_chart || 0,
        reference_max: item.reference_max || '',
        reference_min: item.reference_min || 0,
        is_edit: item.is_edit || 0
      })))
    }
  })
}

// 生命周期
onMounted(async () => {
  await fetchCategories()
  await fetchIndexData()
})

// 监听患者变化
watch(() => patientStore.currentPatient?.patient_id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    if (activeCategory.value === 'index_groups') {
      await fetchGroups()
    } else {
      await fetchIndexData()
    }
  }
})
</script>

<style scoped>
.index-container {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
}

.filter-section {
  margin: 16px;
  margin-top: 8px;
}

.filter-card {
  background: var(--bg-surface);
  border-radius: 12px;
  /* 不使用 overflow:hidden，避免裁剪 tabs 下拉内容 */
  box-shadow: 0 2px 8px var(--primary-alpha-8);
}

.list-section {
  padding: 0 16px;
  min-height: 400px;
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 60px;
}

/* 对比模式控制按钮样式 */
.compare-mode-controls {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 16px;
}

.compare-toggle-btn {
  background: var(--bg-surface);
  color: var(--primary-color);
  border: 1px solid var(--primary-alpha-30);
  transition: all 0.3s ease;
}

.compare-toggle-btn.active {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: var(--bg-surface);
  border: none;
}

.start-compare-btn {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border: none;
}

/* 淡入淡出动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 指标列表样式 */
.index-item {
  background: var(--bg-surface);
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.index-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--primary-alpha-12);
}

.index-item.selected-item {
  background: var(--primary-alpha-10);
  border-left: 3px solid var(--primary-color);
}

.item-container {
  display: flex;
  align-items: center;
  flex: 1;
}

.checkbox-container {
  display: flex;
  align-items: center;
  margin-right: 12px;
}

.index-content {
  flex: 1;
}

.index-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.index-desc {
  font-size: 13px;
  color: var(--primary-color);
  margin-top: 4px;
}

.index-desc .unit {
  color: var(--text-secondary);
}

.index-reference {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

.arrow-icon {
  color: var(--text-tertiary);
  font-size: 18px;
}

/* 收藏星标样式 */
.index-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.favorite-icon {
  font-size: 20px;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color 0.2s, transform 0.2s;
  padding: 4px;
}

.favorite-icon:hover {
  transform: scale(1.2);
}

.favorite-icon.is-favorited {
  color: var(--warning-color);
}

.delete-icon {
  font-size: 20px;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color 0.2s;
  padding: 4px;
}

.delete-icon:hover {
  color: var(--danger-color);
}

/* 滑动单元格样式 */
:deep(.van-swipe-cell) {
  margin-bottom: 12px;
  border-radius: 12px;
  overflow: hidden;
}

.swipe-button {
  height: 100%;
  width: 80px;
}

/* 桌面端侧边栏适配 + 居中限宽 */
@media (min-width: 768px) {
  .index-container {
    padding: 0 var(--space-6) var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
  }
  .filter-section {
    position: sticky;
    top: 0;
    z-index: 10;
  }
  .filter-card {
    max-width: none;
  }
  .filter-card :deep(.van-tabs__nav) {
    border-radius: 12px;
  }
  .list-section {
    padding: var(--space-4) 0;
  }
  /* 桌面端隐藏滑动收藏按钮，星标图标已可直接点击 */
  :deep(.van-swipe-cell__right) {
    display: none;
  }
}
</style>