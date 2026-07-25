<template>
  <div class="admin-dashboard">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <van-loading size="32px" color="var(--primary-color)" vertical>加载中...</van-loading>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <van-icon name="warning-o" size="48" color="var(--danger-color)" />
      <p>{{ error }}</p>
      <van-button size="small" type="primary" @click="loadStats">重试</van-button>
    </div>

    <!-- 数据概览 -->
    <template v-else-if="stats">
      <!-- 统计卡片 -->
      <div class="stats-cards">
        <div class="stat-card" @click="navigateTo('/admin/users')">
          <div class="stat-icon" style="background: var(--primary-alpha-10)">
            <van-icon name="friends-o" size="24" style="color: var(--primary-color)" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.users.total }}</span>
            <span class="stat-label">用户总数</span>
          </div>
          <van-tag v-if="stats.users.today_new > 0" type="primary" size="small">+{{ stats.users.today_new }}</van-tag>
        </div>

        <div class="stat-card">
          <div class="stat-icon" style="background: var(--success-alpha-10)">
            <van-icon name="chat-o" size="24" style="color: var(--success-color)" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.consultations.total }}</span>
            <span class="stat-label">会诊总数</span>
          </div>
          <van-tag v-if="stats.consultations.ongoing > 0" type="success" size="small">{{ stats.consultations.ongoing }}进行中</van-tag>
        </div>

        <div class="stat-card" @click="navigateTo('/admin/indices')">
          <div class="stat-icon" style="background: var(--danger-alpha-10)">
            <van-icon name="search" size="24" style="color: var(--danger-color)" />
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.indices.total }}</span>
            <span class="stat-label">指标库</span>
          </div>
          <van-tag type="danger" size="small">{{ stats.indices.category_count }}分类</van-tag>
        </div>
      </div>

      <!-- 趋势折线图 -->
      <div class="chart-card">
        <div class="card-header">
          <van-icon name="chart-trending-o" size="18" />
          <span>近30天趋势</span>
        </div>
        <div ref="trendChartRef" class="chart-container"></div>
      </div>

      <!-- 饼图行 -->
      <div class="charts-row">
        <div class="chart-card pie-card">
          <div class="card-header">
            <van-icon name="friends-o" size="18" />
            <span>用户状态</span>
          </div>
          <div ref="userPieRef" class="chart-container pie-chart"></div>
        </div>
      </div>

      <!-- 系统概要 -->
      <div class="system-summary">
        <div class="card-header">
          <van-icon name="setting-o" size="18" />
          <span>系统概要</span>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-value">{{ stats.system.total_patients }}</span>
            <span class="summary-label">患者总数</span>
          </div>
          <div class="summary-item">
            <span class="summary-value">{{ stats.users.active }}</span>
            <span class="summary-label">活跃用户</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi } from '@/api/admin'
import { getThemeColors } from '@/styles/theme-colors'
import echarts from '@/utils/echarts'

const router = useRouter()
const loading = ref(true)
const error = ref(null)
const stats = ref(null)

const trendChartRef = ref(null)
const userPieRef = ref(null)

let trendChart = null
let userPieChart = null

function navigateTo(path) {
  router.push(path)
}

async function loadStats() {
  loading.value = true
  error.value = null
  try {
    const res = await adminApi.getAdminStats()
    stats.value = res
    loading.value = false
    await nextTick()
    renderCharts()
  } catch (e) {
    error.value = e.response?.data?.detail || '数据加载失败'
    loading.value = false
  }
}

function renderCharts() {
  if (!stats.value) return
  renderTrendChart()
  renderUserPie()
}

function renderTrendChart() {
  if (!trendChartRef.value) return
  const colors = getThemeColors()
  const trend = stats.value.daily_trend || []
  const dates = trend.map(t => t.date.slice(5))
  const newUsers = trend.map(t => t.new_users)
  const consultations = trend.map(t => t.consultations)

  trendChart = echarts.init(trendChartRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增用户', '会诊数'], bottom: 0, textStyle: { fontSize: 11 } },
    grid: { top: 10, right: 16, bottom: 36, left: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, interval: 6 } },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { fontSize: 10 } },
    series: [
      { name: '新增用户', type: 'line', data: newUsers, smooth: true, symbol: 'none', lineStyle: { width: 2 }, itemStyle: { color: colors.primary || '#1989fa' } },
      { name: '会诊数', type: 'line', data: consultations, smooth: true, symbol: 'none', lineStyle: { width: 2 }, itemStyle: { color: colors.success || '#07c160' } },
    ],
  })
}

function renderUserPie() {
  if (!userPieRef.value) return
  const u = stats.value.users
  userPieChart = echarts.init(userPieRef.value)
  userPieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['50%', '50%'],
      label: { show: true, fontSize: 11, formatter: '{b}\n{d}%' },
      data: [
        { value: u.active, name: '活跃', itemStyle: { color: '#07c160' } },
        { value: u.inactive, name: '禁用', itemStyle: { color: '#ee0a24' } },
      ],
    }],
  })
}

function handleResize() {
  trendChart?.resize()
  userPieChart?.resize()
}

onMounted(() => {
  loadStats()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  userPieChart?.dispose()
})
</script>

<style scoped>
.admin-dashboard {
  max-width: 1200px;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 12px;
  color: var(--text-secondary);
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-surface, #fff);
  border-radius: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.stat-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 图表卡片 */
.chart-card {
  background: var(--bg-surface, #fff);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.chart-container {
  width: 100%;
  height: 280px;
}

.pie-chart {
  height: 220px;
}

/* 饼图行 */
.charts-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

/* 系统概要 */
.system-summary {
  background: var(--bg-surface, #fff);
  border-radius: 12px;
  padding: 16px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  border-radius: 8px;
  background: var(--bg-primary, #f5f5f5);
}

.summary-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-label {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }
  .charts-row {
    grid-template-columns: 1fr;
  }
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
