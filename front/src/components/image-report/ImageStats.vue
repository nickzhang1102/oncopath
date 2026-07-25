<template>
  <div class="image-stats-container">
    <van-loading v-if="loading" size="24px" vertical>加载中...</van-loading>

    <div v-else class="stats-content">
      <!-- 总览卡片 -->
      <div class="overview-card">
        <div class="overview-title">报告总览</div>
        <div class="overview-number">{{ stats.total_count || 0 }}</div>
        <div class="overview-label">总报告数</div>
      </div>

      <!-- 分类统计 -->
      <div class="stats-card" v-if="stats.category_stats && stats.category_stats.length > 0">
        <div class="card-title">分类统计</div>
        <div class="stats-list">
          <div
            v-for="item in stats.category_stats"
            :key="item.category"
            class="stats-item"
          >
            <div class="item-label">{{ item.category_name || item.category || '未分类' }}</div>
            <div class="item-value">{{ item.count }}</div>
            <div class="item-bar">
              <div
                class="bar-fill"
                :style="{ width: getBarWidth(item.count, stats.total_count) }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 医院统计 -->
      <div class="stats-card" v-if="stats.hospital_stats && stats.hospital_stats.length > 0">
        <div class="card-title">医院统计</div>
        <div class="stats-list">
          <div
            v-for="item in stats.hospital_stats"
            :key="item.hospital"
            class="stats-item"
          >
            <div class="item-label">{{ item.hospital || '未知医院' }}</div>
            <div class="item-value">{{ item.count }}</div>
            <div class="item-bar hospital-bar">
              <div
                class="bar-fill"
                :style="{ width: getBarWidth(item.count, stats.total_count) }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 最近报告 -->
      <div class="stats-card" v-if="stats.recent_reports && stats.recent_reports.length > 0">
        <div class="card-title">最近上传</div>
        <div class="recent-list">
          <div
            v-for="report in stats.recent_reports"
            :key="report.report_id"
            class="recent-item"
          >
            <div class="recent-title">{{ report.title }}</div>
            <div class="recent-date">{{ formatDate(report.upload_date) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { getImageReportStats } from '@/api/imageReport'

const props = defineProps({
  patientId: {
    type: Number,
    default: null
  }
})

const loading = ref(false)
const stats = ref({
  total_count: 0,
  category_stats: [],
  hospital_stats: [],
  recent_reports: []
})

onMounted(async () => {
  await loadStats()
})

watch(() => props.patientId, async () => {
  await loadStats()
})

const loadStats = async () => {
  loading.value = true
  try {
    const params = {}
    if (props.patientId) {
      params.patient_id = props.patientId
    }

    const res = await getImageReportStats(params)
    if (res) {
      stats.value = res
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  } finally {
    loading.value = false
  }
}

const getBarWidth = (count, total) => {
  if (!total || total === 0) return '0%'
  return Math.round((count / total) * 100) + '%'
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

const refreshData = async () => {
  await loadStats()
}

defineExpose({
  refreshData
})
</script>

<style scoped>
.image-stats-container {
  min-height: 100vh;
  padding: 10px;
  position: relative;
  z-index: 1;
}

.stats-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 总览卡片 */
.overview-card {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  color: white;
  box-shadow: 0 8px 20px var(--primary-alpha-30);
}

.overview-title {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.overview-number {
  font-size: 48px;
  font-weight: bold;
  margin-bottom: 4px;
}

.overview-label {
  font-size: 14px;
  opacity: 0.8;
}

/* 统计卡片 */
.stats-card {
  background: var(--bg-surface-alpha);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 12px var(--primary-alpha-8);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
}

.stats-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stats-item {
  display: grid;
  grid-template-columns: 100px 40px 1fr;
  align-items: center;
  gap: 12px;
}

.item-label {
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  text-align: right;
}

.item-bar {
  height: 8px;
  background: var(--border-light);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-light));
  border-radius: 4px;
  transition: width 0.3s ease;
}

.hospital-bar .bar-fill {
  background: linear-gradient(90deg, var(--success-color), var(--success-color));
}

/* 最近报告 */
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-elevated);
  border-radius: 8px;
}

.recent-title {
  font-size: 14px;
  color: var(--text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-date {
  font-size: 12px;
  color: var(--text-secondary);
  margin-left: 12px;
}
</style>