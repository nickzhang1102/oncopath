<template>
  <div class="indicator-section">
    <!-- 标题 -->
    <div class="section-header">
      <h3 class="section-title">重要指标</h3>
      <div class="header-right">
        <div class="date-chips">
          <span
            v-for="opt in dateOptions"
            :key="opt.key"
            class="date-chip"
            :class="{ active: activeDateKey === opt.key }"
            @click="onDateChange(opt.key)"
          >{{ opt.label }}</span>
        </div>
        <div class="view-toggle">
          <span
            class="toggle-btn"
            :class="{ active: activeView === 'list' }"
            @click="activeView = 'list'"
          >
            <van-icon name="list-switch" />
            列表
          </span>
          <span
            class="toggle-btn"
            :class="{ active: activeView === 'chart' }"
            @click="activeView = 'chart'"
          >
            <van-icon name="chart-trending-o" />
            图表
          </span>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <van-loading v-if="loading" class="loading-center" />

    <!-- 空状态 -->
    <div v-else-if="!hasData" class="empty-state">
      <div class="empty-icon"><van-icon name="chart-trending-o" /></div>
      <div class="empty-text">暂无指标数据</div>
      <div class="empty-hint">上传检验报告后查看</div>
    </div>

    <!-- 列表视图 -->
    <div v-else-if="activeView === 'list'" class="list-view">
      <!-- 血常规 -->
      <div v-if="bloodTestData.length > 0" class="indicator-group">
        <div class="group-header">
          <span class="group-icon"><van-icon name="point-gift-o" /></span>
          <span class="group-title">血常规</span>
          <span class="group-date">{{ getLatestDate(bloodTestData) }}</span>
        </div>
        <div class="indicator-list">
          <div
            v-for="item in bloodTestData.slice(0, 6)"
            :key="item.detail_id || item.index_name"
            class="indicator-item"
            @click="goToIndicatorDetail(item)"
          >
            <span class="indicator-name">{{ item.index_name }}</span>
            <span class="indicator-value" :class="getStatusClass(item.index_status)">
              {{ item.index_value }}
              <span v-if="item.index_unit" class="indicator-unit">{{ item.index_unit }}</span>
            </span>
          </div>
        </div>
      </div>

      <!-- 肿瘤标志物 -->
      <div v-if="tumorMarkersData.length > 0" class="indicator-group">
        <div class="group-header">
          <span class="group-icon"><van-icon name="aim" /></span>
          <span class="group-title">肿瘤标志物</span>
          <span class="group-date">{{ getLatestDate(tumorMarkersData) }}</span>
        </div>
        <div class="indicator-list">
          <div
            v-for="item in tumorMarkersData.slice(0, 6)"
            :key="item.detail_id || item.index_name"
            class="indicator-item"
            @click="goToIndicatorDetail(item)"
          >
            <span class="indicator-name">{{ item.index_name }}</span>
            <span class="indicator-value" :class="getStatusClass(item.index_status)">
              {{ item.index_value }}
              <span v-if="item.index_unit" class="indicator-unit">{{ item.index_unit }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图表视图 -->
    <div v-else class="chart-view" :class="{ 'chart-view--desktop': isDesktop }">
      <!-- 血常规图表组 -->
      <div v-if="bloodChartData.length > 0" class="chart-group">
        <div class="group-header">
          <span class="group-icon"><van-icon name="point-gift-o" /></span>
          <span class="group-title">血常规</span>
          <span class="chart-count">{{ bloodChartData.length }}项</span>
        </div>
        <!-- 桌面端：网格直接排列 -->
        <div v-if="isDesktop" class="chart-grid">
          <div v-for="item in bloodChartData" :key="item.index_id" class="chart-card">
            <div class="chart-card-header">
              <h3>{{ item.index_name }} - 趋势分析</h3>
            </div>
            <div class="chart-card-content">
              <div :ref="el => setChartRef('blood', item.index_id, el)" class="chart-container"></div>
            </div>
          </div>
        </div>
        <!-- 移动端：swipe 轮播 -->
        <template v-else>
          <van-swipe
            ref="bloodSwipeRef"
            :autoplay="0"
            :show-indicators="false"
            class="chart-swipe"
            @change="(i) => onSwipeChange('blood', i)"
          >
            <van-swipe-item v-for="item in bloodChartData" :key="item.index_id">
              <div class="chart-card">
                <div class="chart-card-header">
                  <h3>{{ item.index_name }} - 趋势分析</h3>
                </div>
                <div class="chart-card-content">
                  <div :ref="el => setChartRef('blood', item.index_id, el)" class="chart-container"></div>
                </div>
              </div>
            </van-swipe-item>
          </van-swipe>
          <div v-if="bloodChartData.length > 1" class="swipe-indicators">
            <span
              v-for="(_, i) in bloodChartData"
              :key="i"
              class="indicator-dot"
              :class="{ active: bloodSwipeIndex === i }"
              @click="bloodSwipeRef?.swipeTo(i)"
            ></span>
          </div>
        </template>
      </div>

      <!-- 肿瘤标志物图表组 -->
      <div v-if="tumorChartData.length > 0" class="chart-group">
        <div class="group-header">
          <span class="group-icon"><van-icon name="aim" /></span>
          <span class="group-title">肿瘤标志物</span>
          <span class="chart-count">{{ tumorChartData.length }}项</span>
        </div>
        <!-- 桌面端：网格直接排列 -->
        <div v-if="isDesktop" class="chart-grid">
          <div v-for="item in tumorChartData" :key="item.index_id" class="chart-card">
            <div class="chart-card-header">
              <h3>{{ item.index_name }} - 趋势分析</h3>
            </div>
            <div class="chart-card-content">
              <div :ref="el => setChartRef('tumor', item.index_id, el)" class="chart-container"></div>
            </div>
          </div>
        </div>
        <!-- 移动端：swipe 轮播 -->
        <template v-else>
          <van-swipe
            ref="tumorSwipeRef"
            :autoplay="0"
            :show-indicators="false"
            class="chart-swipe"
            @change="(i) => onSwipeChange('tumor', i)"
          >
            <van-swipe-item v-for="item in tumorChartData" :key="item.index_id">
              <div class="chart-card">
                <div class="chart-card-header">
                  <h3>{{ item.index_name }} - 趋势分析</h3>
                </div>
                <div class="chart-card-content">
                  <div :ref="el => setChartRef('tumor', item.index_id, el)" class="chart-container"></div>
                </div>
              </div>
            </van-swipe-item>
          </van-swipe>
          <div v-if="tumorChartData.length > 1" class="swipe-indicators">
            <span
              v-for="(_, i) in tumorChartData"
              :key="i"
              class="indicator-dot"
              :class="{ active: tumorSwipeIndex === i }"
              @click="tumorSwipeRef?.swipeTo(i)"
            ></span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'
import { medicalApi } from '@/api/medical'
import { getThemeColors, hexToRgba } from '@/styles/theme-colors'
import echarts from '@/utils/echarts'
import dayjs from 'dayjs'

const router = useRouter()
const patientStore = usePatientStore()

// 状态
const loading = ref(false)
const activeView = ref('list')
const activeDateKey = ref('3m')

const dateOptions = [
  { key: '1m', label: '1月' },
  { key: '3m', label: '3月' },
  { key: '6m', label: '6月' },
  { key: '1y', label: '1年' },
  { key: 'all', label: '全部' },
]

function getDateRange(key) {
  const now = dayjs()
  switch (key) {
    case '1m': return { start: now.subtract(1, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '3m': return { start: now.subtract(3, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '6m': return { start: now.subtract(6, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '1y': return { start: now.subtract(1, 'year').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    default: return { start: null, end: null }
  }
}

function onDateChange(key) {
  activeDateKey.value = key
  loadData()
}

// 桌面端判断（768px 以上不使用 swipe，直接 grid 展示）
const { isDesktop } = useResponsive()

// 轮播状态
const bloodSwipeIndex = ref(0)
const tumorSwipeIndex = ref(0)
const bloodSwipeRef = ref(null)
const tumorSwipeRef = ref(null)

// 数据
const bloodTestData = ref([])
const tumorMarkersData = ref([])
const bloodChartData = ref([])
const tumorChartData = ref([])

// 图表 DOM 引用与实例
const chartRefMap = new Map()
const chartInstanceMap = new Map()
// 已初始化标记（避免重复初始化）
const chartInitializedSet = new Set()

// 计算属性
const hasData = computed(() => {
  return bloodTestData.value.length > 0 || tumorMarkersData.value.length > 0
})

// 方法
function getStatusClass(status) {
  return {
    'status-tag--normal': status === 'normal',
    'status-tag--high': status === 'high',
    'status-tag--low': status === 'low',
    'status-tag--abnormal': status === 'abnormal'
  }
}

function getLatestDate(dataArray) {
  if (!dataArray || dataArray.length === 0) return ''
  const latestItem = dataArray.reduce((latest, current) => {
    return new Date(current.medical_date) > new Date(latest.medical_date) ? current : latest
  })
  return dayjs(latestItem.medical_date).format('MM-DD')
}

function goToIndicatorDetail(item) {
  if (!item.index_id) {
    showToast('该指标未关联标准库，无法查看历史')
    return
  }
  router.push({
    path: '/home/indicator/history',
    query: {
      index_id: item.index_id,
      index_name: item.index_name
    }
  })
}

// 收集图表 DOM 元素
function setChartRef(group, indexId, el) {
  const key = `${group}_${indexId}`
  if (el) {
    chartRefMap.set(key, el)
  } else {
    chartRefMap.delete(key)
  }
}

// 格式化日期（与 ChartView 一致）
function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

// 初始化单个指标的图表（与 index-detail/ChartView 样式一致）
function initSingleChart(el, historyData, indicatorItem) {
  if (!el || !historyData || historyData.length === 0) return null
  // 容器宽度为0时跳过初始化（van-swipe 隐藏项）
  if (el.clientWidth === 0 || el.clientHeight === 0) return null

  const colors = getThemeColors()
  const chart = echarts.init(el)

  const sortedData = [...historyData].sort(
    (a, b) => new Date(a.medical_date) - new Date(b.medical_date)
  )
  const dates = sortedData.map(d => formatDate(d.medical_date))
  const unit = sortedData[0]?.index_unit || ''
  const values = sortedData.map(d => parseFloat(d.index_value) || 0)
  const mainColor = colors.primary

  const option = {
    title: {
      text: `${indicatorItem.index_name} 趋势图`,
      left: 'center',
      textStyle: {
        color: colors.primary,
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      enterable: true,
      position: function(pos, params, dom, rect, size) {
        const obj = { top: 10 }
        obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30
        return obj
      },
      // ECharts 不解析 CSS 变量，须用真实色值（对应 --bg-surface-alpha）
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: colors.borderLight || colors.borderColor,
      borderWidth: 1,
      textStyle: { color: colors.textPrimary, fontSize: 12 },
      formatter: function(params) {
        if (!params || params.length === 0) return ''
        const param = params[0]
        const d = sortedData[param.dataIndex]
        const statusText = d?.index_status && d.index_status !== 'normal'
          ? `<span style="color: ${d.index_status === 'high' ? colors.danger : colors.warning}; margin-left: 4px;">${d.index_status === 'high' ? '↑偏高' : '↓偏低'}</span>`
          : ''
        let result = `<div style="margin-bottom: 5px; font-weight: bold;">${param.axisValue}</div>`
        result += `<div style="margin: 2px 0;">
          <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${param.color};"></span>
          ${param.seriesName}: ${param.value} <span style="color:${colors.textSecondary}">${unit}</span>${statusText}
        </div>`
        // 备注信息
        if (d?.comment) {
          const comment = d.comment.length > 15 ? d.comment.substring(0, 15) + '...' : d.comment
          result += `<div style="margin-top: 5px; padding-top: 5px; border-top: 1px solid var(--border-dark); color: ${colors.textSecondary}; font-size: 12px;">备注: ${comment}</div>`
        }
        return result
      }
    },
    legend: {
      data: [indicatorItem.index_name],
      right: 10,
      top: 30,
      textStyle: {
        color: colors.textSecondary,
        fontSize: 12
      }
    },
    grid: {
      left: '8%',
      right: '3%',
      bottom: '18%',
      top: '18%',
      containLabel: true
    },
    dataZoom: [
      { type: 'slider', start: 0 },
      { start: 0 }
    ],
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: colors.textSecondary
      },
      axisLine: {
        lineStyle: { color: colors.borderLight || colors.borderColor }
      }
    },
    yAxis: {
      type: 'value',
      scale: false,
      min: function(value) {
        if (indicatorItem.referenceMin != null) {
          return Math.min(value.min, indicatorItem.referenceMin);
        }
        return value.min;
      },
      max: function(value) {
        if (indicatorItem.referenceMax != null) {
          return Math.max(value.max, indicatorItem.referenceMax);
        }
        return value.max;
      },
      axisLabel: {
        formatter: (value) => Number(value).toFixed(2),
        fontSize: 10,
        color: colors.textSecondary
      },
      splitLine: {
        lineStyle: { color: colors.borderLight || colors.borderColor }
      }
    },
    series: [{
      name: indicatorItem.index_name,
      type: 'line',
      data: values.map(v => parseFloat(v.toFixed(2))),
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: mainColor, width: 2 },
      itemStyle: { color: mainColor },
      // 参考范围区域（与 ChartView 的 markArea 一致）
      ...(indicatorItem.referenceMin != null && indicatorItem.referenceMax != null ? {
        markArea: {
          silent: true,
          itemStyle: {
            color: hexToRgba(colors.success, 0.1),
            borderColor: hexToRgba(colors.success, 0.3),
            borderWidth: 1,
            borderType: 'dashed'
          },
          label: {
            show: true,
            position: 'insideTopRight',
            formatter: '正常范围',
            color: colors.success,
            fontSize: 10
          },
          data: [[
            { yAxis: indicatorItem.referenceMin },
            { yAxis: indicatorItem.referenceMax }
          ]]
        }
      } : {})
    }]
  }

  chart.setOption(option)
  chart.on('click', () => goToIndicatorDetail(indicatorItem))
  return chart
}

// 初始化指定分组的当前可见图表
function initVisibleChart(group, index) {
  const chartData = group === 'blood' ? bloodChartData.value : tumorChartData.value
  if (index < 0 || index >= chartData.length) return

  const item = chartData[index]
  const key = `${group}_${item.index_id}`
  if (chartInitializedSet.has(key)) return

  const el = chartRefMap.get(key)
  if (!el || el.clientWidth === 0 || el.clientHeight === 0) return

  const chart = initSingleChart(el, item.data, item)
  if (chart) {
    chartInstanceMap.set(key, chart)
    chartInitializedSet.add(key)
  }
}

// 初始化所有当前可见的图表
function initAllCharts() {
  disposeAllCharts()
  if (isDesktop.value) {
    // 桌面端：初始化所有图表（grid 直接排列，全部可见）
    initAllVisibleCharts()
  } else {
    // 移动端：仅初始化当前 swipe 可见项
    initVisibleChart('blood', bloodSwipeIndex.value)
    initVisibleChart('tumor', tumorSwipeIndex.value)
  }
}

// 初始化所有图表（桌面端 grid 模式）
function initAllVisibleCharts() {
  bloodChartData.value.forEach((_, i) => initVisibleChart('blood', i))
  tumorChartData.value.forEach((_, i) => initVisibleChart('tumor', i))
}

// swipe 切换时延迟初始化新可见图表
async function onSwipeChange(group, index) {
  if (group === 'blood') {
    bloodSwipeIndex.value = index
  } else {
    tumorSwipeIndex.value = index
  }
  // 等待 swipe 动画完成、DOM 尺寸稳定后再初始化
  await nextTick()
  setTimeout(() => {
    initVisibleChart(group, index)
  }, 300)
}

// 销毁所有图表
function disposeAllCharts() {
  chartInstanceMap.forEach(chart => chart.dispose())
  chartInstanceMap.clear()
  chartInitializedSet.clear()
}

// 并行加载单个分组的图表历史数据
async function loadGroupChartData(testData) {
  const range = getDateRange(activeDateKey.value)
  const params = {}
  if (range.start) params.start_date = range.start
  if (range.end) params.end_date = range.end

  const results = await Promise.all(
    testData.map(async (item) => {
      if (!item.index_id) return null
      try {
        const result = await medicalApi.getIndexHistoryById(item.index_id, params)
        const historyData = result?.history || result
        const indexInfo = result?.index_info
        if (historyData && Array.isArray(historyData) && historyData.length > 0) {
          return {
            index_name: item.index_name,
            index_id: item.index_id,
            referenceMin: indexInfo?.reference_min ?? null,
            referenceMax: indexInfo?.reference_max ?? null,
            data: historyData.sort((a, b) => new Date(a.medical_date) - new Date(b.medical_date))
          }
        }
      } catch (err) {
        console.error(`加载指标 ${item.index_name} 历史数据失败:`, err)
      }
      return null
    })
  )
  return results.filter(Boolean)
}

async function loadData() {
  if (!patientStore.currentPatient) return

  const patientId = patientStore.currentPatient.patient_id
  loading.value = true

  try {
    const bloodResult = await medicalApi.getLatestIndicatorsByCategory(patientId, 'blood_routine', { limit: 6 })
    bloodTestData.value = bloodResult?.indicators || []

    const tumorResult = await medicalApi.getLatestIndicatorsByCategory(patientId, 'tumor_markers', { limit: 6 })
    tumorMarkersData.value = tumorResult?.indicators || []

    // 并行加载图表历史数据（含参考范围）
    const [bloodChart, tumorChart] = await Promise.all([
      loadGroupChartData(bloodTestData.value.slice(0, 6)),
      loadGroupChartData(tumorMarkersData.value.slice(0, 6))
    ])
    bloodChartData.value = bloodChart
    tumorChartData.value = tumorChart

    // 如果当前在图表视图，初始化图表
    if (activeView.value === 'chart') {
      await nextTick()
      setTimeout(() => {
        initAllCharts()
      }, 300)
    }
  } catch (error) {
    console.error('加载指标数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 监听视图切换
watch(activeView, async (newView) => {
  if (newView === 'chart') {
    await nextTick()
    // 延迟确保 DOM 渲染完成、容器有尺寸
    setTimeout(() => {
      initAllCharts()
    }, 300)
  } else {
    disposeAllCharts()
  }
})

// 监听桌面/移动端切换，重新初始化图表
watch(isDesktop, async () => {
  if (activeView.value === 'chart') {
    await nextTick()
    setTimeout(() => {
      initAllCharts()
    }, 300)
  }
})

// 窗口 resize 时刷新可见图表
function handleResize() {
  chartInstanceMap.forEach(chart => {
    if (!chart.isDisposed()) {
      chart.resize()
    }
  })
}

// 生命周期
onMounted(async () => {
  await loadData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  disposeAllCharts()
  window.removeEventListener('resize', handleResize)
})

// 监听患者变化
watch(() => patientStore.currentPatient?.patient_id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    await loadData()
  }
})
</script>

<style scoped>
.indicator-section {
  background: var(--bg-surface-alpha);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 16px var(--primary-alpha-10);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--primary-alpha-10);
  flex-wrap: wrap;
  gap: 8px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-chips {
  display: flex;
  gap: 4px;
}

.date-chip {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--primary-alpha-15);
  white-space: nowrap;
}

.date-chip.active {
  background: var(--primary-color);
  color: var(--color-white);
  border-color: var(--primary-color);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  margin: 0;
}

.view-toggle {
  display: flex;
  gap: 4px;
  background: var(--primary-alpha-8);
  padding: 4px;
  border-radius: 8px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.toggle-btn.active {
  background: var(--bg-surface);
  color: var(--primary-color);
  font-weight: 500;
  box-shadow: 0 2px 4px var(--shadow-color-md);
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.empty-text {
  font-size: 16px;
  color: var(--primary-color);
  font-weight: 500;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 列表视图 */
.list-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.indicator-group {
  background: var(--primary-alpha-3);
  border-radius: 12px;
  padding: 12px;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.group-icon {
  font-size: 16px;
}

.group-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
}

.group-date {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-surface);
  padding: 2px 6px;
  border-radius: 4px;
}

.indicator-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.indicator-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-surface);
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.indicator-item:hover {
  transform: translateX(4px);
  box-shadow: 0 2px 8px var(--primary-alpha-10);
}

.indicator-name {
  font-size: 13px;
  color: var(--text-primary);
}

.indicator-value {
  font-size: 14px;
  font-weight: 600;
}

.indicator-unit {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-left: 2px;
}

/* 图表视图 */
.chart-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-group {
  background: var(--primary-alpha-3);
  border-radius: 12px;
  padding: 12px;
}

.chart-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-surface);
  padding: 2px 6px;
  border-radius: 4px;
}

.chart-swipe {
  border-radius: 12px;
  overflow: hidden;
}

/* 图表卡片（与 index-detail/ChartView 一致） */
.chart-card {
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  overflow: hidden;
}

.chart-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--primary-alpha-10);
}

.chart-card-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
}

.chart-card-content {
  padding: 16px;
}

.chart-container {
  width: 100%;
  height: 320px;
  /* 覆盖全局 .chart-container 的 padding/shadow */
  padding: 0;
  background: transparent;
  box-shadow: none;
  border-radius: 0;
}

.swipe-indicators {
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 10px;
}

.indicator-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-alpha-30);
  cursor: pointer;
  transition: all 0.3s ease;
}

.indicator-dot.active {
  background: var(--primary-color);
  transform: scale(1.2);
}

.indicator-dot:hover {
  background: var(--text-tertiary);
}

/* 桌面端图表网格 */
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.chart-view--desktop .chart-group {
  grid-column: 1 / -1;
}

/* 响应式 */
@media (min-width: 768px) {
  .chart-card-content {
    padding: 12px;
  }

  .chart-container {
    height: 280px;
  }
}

@media (min-width: 1024px) {
  .chart-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .chart-card-header {
    padding: 15px;
  }

  .chart-card-header h3 {
    font-size: 16px;
  }

  .chart-card-content {
    padding: 15px;
  }

  .chart-container {
    height: 330px;
  }
}

@media (max-width: 480px) {
  .chart-card-header {
    padding: 15px;
  }

  .chart-card-content {
    padding: 10px;
  }

  .chart-container {
    height: 280px;
  }
}
</style>