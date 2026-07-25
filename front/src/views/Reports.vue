<template>
  <div class="reports-view">
    <!-- 动态背景 -->
    <BackgroundAnimation />

    <!-- 返回按钮 -->
    <BackButton title="检验报告" />

    <!-- 筛选区域 -->
    <div class="filter-section">
      <FilterTabs v-model="filterType" :tabs="filterTabs" @change="onFilterChange" />
    </div>

    <!-- 统计概览 -->
    <div v-if="!loading && reports.length > 0" class="stats-section">
      <div class="stats-card">
        <div class="stat-item">
          <div class="stat-value">{{ reports.length }}</div>
          <div class="stat-label">报告总数</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-value">{{ getCategoryCount }}</div>
          <div class="stat-label">报告分类</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-value">{{ getLatestDate }}</div>
          <div class="stat-label">最近检验</div>
        </div>
      </div>
    </div>

    <!-- 未选择患者时的空状态 -->
    <div v-if="!hasPatient" class="empty-patient">
      <van-empty description="请先选择患者" image="search">
        <van-button type="primary" class="bottom-button" @click="router.push('/home/patient-management')">
          选择患者
        </van-button>
      </van-empty>
    </div>

    <!-- 报告列表 -->
    <div v-else class="report-list-section">
      <van-loading v-if="loading" class="loading-center" />

      <van-empty v-else-if="reports.length === 0" description="暂无检验报告">
        <template #image>
          <div class="empty-icon"><van-icon name="todo-list-o" /></div>
        </template>
        <van-button round type="primary" class="upload-btn" @click="router.push('/home/image-report')">
          <van-icon name="plus" />
          上传报告
        </van-button>
      </van-empty>

      <van-pull-refresh v-else v-model="refreshing" @refresh="onRefresh">
        <van-list
          v-model:loading="loadingMore"
          :finished="finished"
          finished-text="没有更多了"
          @load="onLoadMore"
        >
          <TransitionGroup name="list" tag="div" class="report-list">
            <div
              v-for="report in filteredReports"
              :key="report.medical_id"
              class="report-card-wrapper"
              @click="viewReport(report)"
            >
              <ReportCard
                type=""
                :color="report.category_color || ''"
                :title="report.category_name ? (report.details && report.details.length ? `${report.category_name}（${report.details.length}项）` : report.category_name) : '检验报告'"
                :date="report.medical_date"
                :hospital="report.hospital"
                :comment="report.comment"
                :has-image="false"
                :interpretation="report.interpretation"
                :show-actions="true"
                @view-detail="viewReport(report)"
                @share="handleShare(report)"
                @delete="handleDelete(report)"
              />
              <!-- 指标摘要 -->
              <div v-if="report.details && report.details.length > 0" class="report-indicators-bar">
                <span class="indicator-label">指标数: {{ report.details.length }}</span>
                <van-tag v-if="hasAbnormal(report.details)" type="danger" size="small">有异常</van-tag>
                <van-tag v-else type="success" size="small">正常</van-tag>
              </div>
            </div>
          </TransitionGroup>
        </van-list>
      </van-pull-refresh>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { medicalApi } from '@/api/medical'
import { useReportList } from '@/composables/useReportList'
const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'
import FilterTabs from '@/components/report/FilterTabs.vue'
import ReportCard from '@/components/report/ReportCard.vue'

const router = useRouter()

// 使用通用报告列表 composable
const {
  loading, refreshing, loadingMore, finished, reports, hasPatient,
  getLatestDate, fetchReports, onRefresh, onLoadMore, handleDelete, handleShare,
} = useReportList({
  fetchFn: (patientId, params) => medicalApi.getMedicalReportList(patientId, params),
  deleteFn: (report) => medicalApi.deleteMedicalCheck(report.medical_id),
  shareContentType: 'medical_check',
  shareContentIdFn: (report) => report.medical_id,
  deleteConfirmMsg: '确定要删除该检验报告吗？删除后无法恢复。',
  dateField: 'medical_date',
})

// 分类筛选
const filterType = ref('all')
const categoryList = ref([])

const filterTabs = computed(() => {
  const tabs = [
    { text: '全部', value: 'all', icon: 'apps-o', count: reports.value.length },
  ]

  const categoryCounts = {}
  reports.value.forEach(r => {
    if (r.category) {
      categoryCounts[r.category] = (categoryCounts[r.category] || 0) + 1
    }
  })

  categoryList.value.forEach(cat => {
    const count = categoryCounts[cat.category_key] || 0
    if (count > 0) {
      tabs.push({
        text: cat.category_name,
        value: cat.category_key,
        icon: cat.icon || 'description',
        count,
      })
    }
  })

  return tabs
})

const filteredReports = computed(() => {
  if (filterType.value === 'all') return reports.value
  return reports.value.filter(r => r.category === filterType.value)
})

const getCategoryCount = computed(() => {
  const types = new Set()
  reports.value.forEach(r => {
    if (r.category) types.add(r.category)
  })
  return types.size
})

function hasAbnormal(details) {
  return details.some(d => d.index_status && d.index_status !== 'normal')
}

function onFilterChange() {}

function viewReport(report) {
  router.push(`/home/report/${report.medical_id}`)
}

async function fetchCategories() {
  try {
    const data = await medicalApi.getIndexCategories()
    categoryList.value = data || []
  } catch (e) {
    console.error('获取分类失败:', e)
  }
}

onMounted(() => {
  fetchCategories()
})
</script>

<style scoped>
.reports-view {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
  box-sizing: border-box;
  position: relative;
}

/* 筛选区域 */
.filter-section {
  margin: 16px;
}

/* 统计概览 */
.stats-section {
  padding: 0 16px;
  margin-bottom: 16px;
}

.stats-card {
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: var(--bg-surface);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 2px 12px var(--primary-alpha-8);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary-color);
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--border-color);
}

/* 报告列表区域 */
.report-list-section {
  padding: 0 16px;
  min-height: 300px;
}

.report-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-card-wrapper {
  cursor: pointer;
}

/* 指标摘要条 */
.report-indicators-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-surface);
  border-radius: 0 0 16px 16px;
  margin-top: -12px;
  position: relative;
  z-index: 0;
}

.indicator-label {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 加载状态 */
.loading-center {
  display: flex;
  justify-content: center;
  padding: 60px;
}

/* 患者未选择空状态 */
.empty-patient {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.bottom-button {
  min-width: 160px;
  padding: 12px 24px;
}

/* 空状态 */
.empty-icon {
  font-size: 64px;
  opacity: 0.5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon .van-icon {
  font-size: 64px;
}

.upload-btn {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border: none;
  padding: 12px 24px;
}

/* 列表动画 */
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.list-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* 响应式调整 */
@media (max-width: 360px) {
  .filter-section,
  .stats-section,
  .report-list-section {
    padding-left: 12px;
    padding-right: 12px;
  }

  .stat-value {
    font-size: 18px;
  }
}

/* 桌面端居中限宽 */
@media (min-width: 768px) {
  .reports-view {
    padding: var(--space-6);
    padding-bottom: var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
  }

  .filter-section {
    margin: 0 0 var(--space-4) 0;
  }

  .report-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-4);
  }
}

@media (min-width: 1024px) {
  .report-list {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>