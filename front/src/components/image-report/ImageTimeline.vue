<template>
  <div class="image-timeline-container">
    <!-- 过滤器 -->
    <div class="filter-section">
      <div class="filter-toggle">
        <van-button
          :type="showFilter ? 'primary' : 'default'"
          size="small"
          @click="toggleFilter"
          icon="filter-o"
        >
          {{ showFilter ? '隐藏筛选' : '显示筛选' }}
        </van-button>
      </div>

      <div class="filter-card" v-if="showFilter">
        <!-- 分类过滤 -->
        <div class="filter-row">
          <div class="filter-label">分类</div>
          <div class="filter-input">
            <van-field
              v-model="filters.categoryDisplay"
              readonly
              clickable
              placeholder="选择分类"
              @click="showCategoryPicker = true"
              right-icon="arrow-down"
            />
          </div>
        </div>

        <!-- 医院过滤 -->
        <div class="filter-row">
          <div class="filter-label">医院</div>
          <div class="filter-input">
            <van-field
              v-model="filters.hospital"
              placeholder="输入医院名称"
              clearable
            />
          </div>
        </div>

        <!-- 日期范围过滤 -->
        <div class="filter-row">
          <div class="filter-label">日期范围</div>
          <div class="filter-input date-range-inputs">
            <div class="date-input-wrapper">
              <van-field
                v-model="filters.startDate"
                readonly
                clickable
                placeholder="开始日期"
                @click="showStartDatePicker = true"
              />
            </div>
            <div class="date-separator">至</div>
            <div class="date-input-wrapper">
              <van-field
                v-model="filters.endDate"
                readonly
                clickable
                placeholder="结束日期"
                @click="showEndDatePicker = true"
              />
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="filter-actions">
          <van-button type="primary" size="small" @click="applyFilters" block>
            应用筛选
          </van-button>
          <van-button size="small" @click="resetFilters" block>
            重置
          </van-button>
        </div>

        <!-- OCR状态快捷筛选 -->
        <div class="ocr-status-filters">
          <div class="filter-label">OCR状态筛选</div>
          <div class="status-filter-tags">
            <van-tag
              :type="filters.ocrStatus === 'pending_review' ? 'warning' : 'default'"
              size="medium"
              @click="filters.ocrStatus = 'pending_review'; applyFilters()"
            >待确认</van-tag>
            <van-tag
              :type="filters.ocrStatus === 'completed' ? 'success' : 'default'"
              size="medium"
              @click="filters.ocrStatus = 'completed'; applyFilters()"
            >已完成</van-tag>
            <van-tag
              :type="filters.ocrStatus === 'failed' ? 'danger' : 'default'"
              size="medium"
              @click="filters.ocrStatus = 'failed'; applyFilters()"
            >失败</van-tag>
            <van-tag
              :type="filters.ocrStatus === 'reviewed' ? 'success' : 'default'"
              size="medium"
              @click="filters.ocrStatus = 'reviewed'; applyFilters()"
            >已审查</van-tag>
            <van-tag
              size="medium"
              @click="filters.ocrStatus = ''; applyFilters()"
            >全部</van-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 统计信息 -->
    <div class="stats-section" v-if="stats">
      <div class="stats-card">
        <div class="stats-item">
          <div class="stats-number">{{ stats.total_count || 0 }}</div>
          <div class="stats-label">总报告数</div>
        </div>
        <div class="stats-item" v-if="stats.category_stats && stats.category_stats.length > 0">
          <div class="stats-number">{{ stats.category_stats[0].count }}</div>
          <div class="stats-label">{{ stats.category_stats[0].category_name || stats.category_stats[0].category || '分类' }}</div>
        </div>
        <div class="stats-item" v-if="stats.hospital_stats && stats.hospital_stats.length > 0">
          <div class="stats-number">{{ stats.hospital_stats[0].count }}</div>
          <div class="stats-label">{{ stats.hospital_stats[0].hospital || '医院' }}</div>
        </div>
      </div>
    </div>

    <!-- 时间线内容 -->
    <div class="timeline-content">
      <van-loading v-if="loading" size="24px" vertical>加载中...</van-loading>

      <div v-else-if="reports.length === 0" class="empty-state">
        <van-empty description="暂无报告" />
      </div>

      <div v-else class="timeline-list">
        <div
          v-for="(group, index) in timelineData"
          :key="index"
          class="timeline-group"
        >
          <!-- 时间分组标题 -->
          <div class="timeline-header">
            <div class="timeline-date">{{ group.date }}</div>
            <div class="timeline-count">{{ group.items.length }} 个报告</div>
          </div>

          <!-- 报告卡片列表 -->
          <div class="report-cards">
            <div
              v-for="report in group.items"
              :key="report.report_id"
              class="report-card"
              @click="viewReportDetail(report)"
            >
              <!-- 卡片头部 -->
              <div class="card-header">
                <div class="card-title">
                  <span v-if="report.is_important" class="important-badge"><van-icon name="star" /></span>
                  {{ report.title }}
                </div>
                <van-tag
                  v-if="report.ocr_status && report.ocr_status !== 'reviewed'"
                  :type="ocrStatusTagType(report.ocr_status)"
                  size="small"
                  class="ocr-status-tag"
                >
                  {{ ocrStatusText(report.ocr_status) }}
                </van-tag>
              </div>

              <!-- 卡片内容 -->
              <div class="card-content">
                <!-- 缩略图 -->
                <div class="thumbnail-container">
                  <img
                    :src="getThumbnailUrl(report)"
                    :alt="report.title"
                    class="thumbnail"
                    @error="handleImageError"
                  />
                </div>

                <!-- 信息区域 -->
                <div class="info-area">
                  <div class="info-row">
                    <span class="info-label">分类:</span>
                    <span class="info-value category-tag" :style="getCategoryStyle(report.category)">
                      {{ report.category_name || report.category }}
                    </span>
                  </div>
                  <div class="info-row" v-if="report.hospital">
                    <span class="info-label">医院:</span>
                    <span class="info-value">{{ report.hospital }}</span>
                  </div>
                  <div class="info-row" v-if="report.department">
                    <span class="info-label">科室:</span>
                    <span class="info-value">{{ report.department }}</span>
                  </div>
                </div>
              </div>

              <!-- 卡片操作 -->
              <div class="card-actions">
                <van-button
                  size="small"
                  class="btn-view"
                  @click.stop="viewReportDetail(report)"
                >
                  查看详情
                </van-button>
                <van-button
                  size="small"
                  type="danger"
                  plain
                  @click.stop="deleteReport(report)"
                >
                  删除
                </van-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载更多 -->
      <div v-if="hasMore && !loading" class="load-more">
        <van-button block size="small" @click="loadMore" :loading="loadingMore">
          加载更多
        </van-button>
      </div>
    </div>

    <!-- 开始日期选择器 -->
    <van-popup v-model:show="showStartDatePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker
        v-model="startDateValue"
        title="选择开始日期"
        :min-date="minDate"
        :max-date="maxDate"
        @confirm="onStartDateConfirm"
        @cancel="showStartDatePicker = false"
      />
    </van-popup>

    <!-- 结束日期选择器 -->
    <van-popup v-model:show="showEndDatePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker
        v-model="endDateValue"
        title="选择结束日期"
        :min-date="minDate"
        :max-date="maxDate"
        @confirm="onEndDateConfirm"
        @cancel="showEndDatePicker = false"
      />
    </van-popup>

    <!-- 分类选择器 -->
    <van-popup v-model:show="showCategoryPicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-md' : ''" :style="isDesktop ? 'width: 560px' : 'height: 80vh'">
      <ImageCategorySelector
        @confirm="onCategoryConfirm"
        @cancel="showCategoryPicker = false"
      />
    </van-popup>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { getImageReports, getImageReportStats, deleteImageReport, getImageCategories } from '@/api/imageReport'
import { OCR_STATUS_TAG_TYPE, OCR_STATUS_TEXT } from '@/styles/constants'
import { useResponsive } from '@/composables/useResponsive'
import { useUserStore } from '@/stores/user'
import ImageCategorySelector from './ImageCategorySelector.vue'

const { isDesktop } = useResponsive()
const userStore = useUserStore()
const router = useRouter()

const props = defineProps({
  patientId: {
    type: Number,
    default: null
  },
  initialOcrStatus: {
    type: String,
    default: null
  }
})

// 状态变量
const loading = ref(false)
const loadingMore = ref(false)
const hasMore = ref(true)
const showStartDatePicker = ref(false)
const showEndDatePicker = ref(false)
const showCategoryPicker = ref(false)
const showFilter = ref(false)

const startDateValue = ref([new Date().getFullYear(), new Date().getMonth() + 1, new Date().getDate()])
const endDateValue = ref([new Date().getFullYear(), new Date().getMonth() + 1, new Date().getDate()])

// 数据
const reports = ref([])
const stats = ref(null)

// 过滤器
const filters = reactive({
  category: '',
  categoryDisplay: '',
  hospital: '',
  startDate: '',
  endDate: '',
  ocrStatus: '',
  page: 1,
  perPage: 20
})

// 日期选择器数据
const minDate = new Date(2020, 0, 1)
const maxDate = new Date()

// 时间线数据（按日期分组）
const timelineData = computed(() => {
  const grouped = {}

  reports.value.forEach(report => {
    const dateKey = report.capture_date ? new Date(report.capture_date).toLocaleDateString('zh-CN') : '未知日期'

    if (!grouped[dateKey]) {
      grouped[dateKey] = []
    }

    grouped[dateKey].push(report)
  })

  // 转换为数组并按日期排序
  return Object.keys(grouped)
    .sort((a, b) => new Date(b) - new Date(a))
    .map(date => ({
      date,
      items: grouped[date]
    }))
})

// 初始化
onMounted(async () => {
  if (props.initialOcrStatus) {
    filters.ocrStatus = props.initialOcrStatus
  }
  await Promise.all([loadData(), loadStats(), loadCategoryColors()])
})

// 监听病人ID变化
watch(() => props.patientId, async (newVal) => {
  filters.page = 1
  reports.value = []
  await loadData()
  await loadStats()
})

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const params = {
      page: filters.page,
      per_page: filters.perPage
    }

    if (props.patientId) {
      params.patient_id = props.patientId
    }
    if (filters.category) {
      params.category = filters.category
    }
    if (filters.hospital) {
      params.hospital = filters.hospital
    }
    if (filters.startDate) {
      params.start_date = filters.startDate
    }
    if (filters.endDate) {
      params.end_date = filters.endDate
    }
    if (filters.ocrStatus) {
      params.ocr_status = filters.ocrStatus
    }

    const res = await getImageReports(params)

    if (res) {
      const newReports = res.items || []

      if (filters.page === 1) {
        reports.value = newReports
      } else {
        reports.value = [...reports.value, ...newReports]
      }

      hasMore.value = reports.value.length < res.total
    }
  } catch (error) {
    console.error('加载数据失败:', error)
    showToast('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 加载统计信息
const loadStats = async () => {
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
  }
}

// 切换过滤框显示
const toggleFilter = () => {
  showFilter.value = !showFilter.value
}

// 应用筛选
const applyFilters = async () => {
  filters.page = 1
  reports.value = []
  await loadData()
  showToast('筛选完成')
}

// 重置筛选
const resetFilters = () => {
  filters.category = ''
  filters.categoryDisplay = ''
  filters.hospital = ''
  filters.startDate = ''
  filters.endDate = ''
  filters.ocrStatus = ''
  filters.page = 1
  reports.value = []
  loadData()
}

// 开始日期确认
const onStartDateConfirm = ({ selectedValues }) => {
  if (selectedValues && selectedValues.length === 3) {
    const year = selectedValues[0]
    const month = String(selectedValues[1]).padStart(2, '0')
    const day = String(selectedValues[2]).padStart(2, '0')
    filters.startDate = `${year}-${month}-${day}`
  }
  showStartDatePicker.value = false
}

// 结束日期确认
const onEndDateConfirm = ({ selectedValues }) => {
  if (selectedValues && selectedValues.length === 3) {
    const year = selectedValues[0]
    const month = String(selectedValues[1]).padStart(2, '0')
    const day = String(selectedValues[2]).padStart(2, '0')
    filters.endDate = `${year}-${month}-${day}`
  }
  showEndDatePicker.value = false
}

// 分类选择确认
const onCategoryConfirm = (category) => {
  if (category) {
    filters.category = category.category_key
    filters.categoryDisplay = category.category_name
  }
  showCategoryPicker.value = false
}

// 加载更多
const loadMore = () => {
  if (!hasMore.value || loadingMore.value) return

  loadingMore.value = true
  filters.page += 1

  loadData().finally(() => {
    loadingMore.value = false
  })
}

// 生成分类SVG占位符
const getCategoryPlaceholder = (category) => {
  const categoryIcons = {
    xray: '📷', ct: '🔍', mri: '🔬', ultrasound: '🌊',
    pathology: '🧪', endoscopy: '🎯', ecg: '❤️', other: '📁',
    pet_ct: '☢️', nuclear: '⚛️', eeg: '🧠', pulmonary: '🫁',
    blood_routine: '🩸', blood_biochemistry: '🧬', coagulation: '🩹',
    tumor_markers: '🎯', immune: '🛡️', infection: '🦠', hormone: '💊',
    genetics: '🧬', urine_routine: '🚰', urine_biochemistry: '🧪',
    stool: '💩', sputum: '😷'
  }

  const icon = categoryIcons[category] || '📷'

  return `data:image/svg+xml,${encodeURIComponent(`
    <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
      <rect width="200" height="200" fill="var(--border-light)" rx="12"/>
      <text x="100" y="100" font-size="80" text-anchor="middle" dominant-baseline="middle">
        ${icon}
      </text>
    </svg>
  `)}`
}

// 获取缩略图URL
const getThumbnailUrl = (report) => {
  if (report.thumbnail_url) {
    const token = userStore.token
    return `/api/v1${report.thumbnail_url}?token=${encodeURIComponent(token)}`
  }
  return getCategoryPlaceholder(report.category)
}

// 处理图片加载错误，回退到分类占位符
const handleImageError = (event) => {
  const img = event.target
  if (!img.dataset.fallback) {
    img.dataset.fallback = '1'
    const reportId = parseInt(img.src.match(/image_reports\/(\d+)\//)?.[1])
    const report = reports.value.find(r => r.report_id === reportId)
    img.src = getCategoryPlaceholder(report?.category || 'other')
  }
}

// 查看详情 - 导航到审查页面
const viewReportDetail = (report) => {
  router.push(`/home/image-report/${report.report_id}/review`)
}

// 删除报告
const deleteReport = async (report) => {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: '确定要删除这个报告吗？此操作不可恢复。'
    })

    const res = await deleteImageReport(report.report_id)
    if (res) {
      showToast('删除成功')
      reports.value = reports.value.filter(r => r.report_id !== report.report_id)
      await loadStats()
    }
  } catch (error) {
    if (error !== 'cancel') {
      showToast('删除失败')
    }
  }
}

// 分类颜色缓存（从 API 加载）
const categoryColorMap = ref({})

async function loadCategoryColors() {
  try {
    const res = await getImageCategories()
    const data = res?.data !== undefined ? res.data : res
    const list = Array.isArray(data) ? data : (data?.items || [])
    const map = {}
    for (const cat of list) {
      if (cat.category_key && cat.color) {
        map[cat.category_key] = cat.color
      }
    }
    categoryColorMap.value = map
  } catch (e) {
    console.error('加载分类颜色失败:', e)
  }
}

// 获取分类样式
const getCategoryStyle = (category) => {
  return {
    backgroundColor: categoryColorMap.value[category] || 'var(--text-secondary)',
    color: 'white'
  }
}

// OCR 状态标签类型映射
const ocrStatusTagType = (status) => {
  return OCR_STATUS_TAG_TYPE[status] || 'default'
}

// OCR 状态文字映射
const ocrStatusText = (status) => {
  return OCR_STATUS_TEXT[status] || status
}

const refreshData = async () => {
  filters.page = 1
  reports.value = []
  await loadData()
  await loadStats()
}

defineExpose({
  refreshData
})
</script>

<style scoped>
.image-timeline-container {
  min-height: 100vh;
  padding: 10px;
  position: relative;
  z-index: 1;
}

/* 过滤器样式 */
.filter-section {
  position: relative;
  z-index: 2;
  margin-bottom: 15px;
}

.filter-toggle {
  text-align: center;
  margin-bottom: 12px;
}

.filter-card {
  background: var(--bg-surface-alpha);
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 4px 12px var(--primary-alpha-8);
  backdrop-filter: blur(10px);
}

.filter-row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  gap: 12px;
}

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--primary-color);
  min-width: 60px;
  flex-shrink: 0;
}

.filter-input {
  flex: 1;
  min-width: 0;
}

.date-range-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-input-wrapper {
  flex: 1;
}

.date-separator {
  color: var(--text-secondary);
  font-size: 13px;
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.ocr-status-filters {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.ocr-status-filters .filter-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.status-filter-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-filter-tags .van-tag {
  cursor: pointer;
  padding: 4px 12px;
}

/* 统计信息样式 */
.stats-section {
  position: relative;
  z-index: 2;
  padding: 0 0 15px;
}

.stats-card {
  background: var(--bg-surface-alpha);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  justify-content: space-around;
  box-shadow: 0 8px 20px var(--primary-alpha-8);
  backdrop-filter: blur(10px);
}

.stats-item {
  text-align: center;
}

.stats-number {
  font-size: 20px;
  font-weight: bold;
  color: var(--primary-color);
  margin-bottom: 4px;
}

.stats-label {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 时间线内容 */
.timeline-content {
  position: relative;
  z-index: 2;
}

.timeline-group {
  margin-bottom: 15px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 2px solid var(--primary-alpha-20);
  margin-bottom: 10px;
}

.timeline-date {
  font-size: 16px;
  font-weight: bold;
  color: var(--primary-color);
}

.timeline-count {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--primary-alpha-10);
  padding: 4px 10px;
  border-radius: 12px;
}

/* 报告卡片样式 */
.report-card {
  background: var(--bg-surface-alpha);
  border-radius: 12px;
  padding: 15px;
  margin-bottom: 15px;
  box-shadow: 0 6px 15px var(--primary-alpha-8);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  flex: 1;
}

.ocr-status-tag {
  flex-shrink: 0;
  margin-left: 8px;
}

.important-badge {
  margin-right: 4px;
}

.card-content {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.thumbnail-container {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 12px;
  overflow: hidden;
  background: var(--border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.info-area {
  flex: 1;
  min-width: 0;
}

.info-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 6px;
  font-size: 14px;
}

.info-label {
  color: var(--text-secondary);
  margin-right: 8px;
  flex-shrink: 0;
  min-width: 50px;
}

.info-value {
  color: var(--text-primary);
  flex: 1;
}

.category-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

/* 卡片操作按钮 */
.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  border-color: var(--border-dark);
}

.card-actions .van-button {
  flex: 1;
  height: 32px;
}

.btn-view {
  color: var(--color-white) !important;
  background: var(--primary-color);
  border-color: var(--primary-color);
}

/* 加载更多 */
.load-more {
  padding: 16px;
  text-align: center;
}

/* 空状态 */
.empty-state {
  padding: 40px 0;
}

/* 覆盖 vant 样式 */
:deep(.van-button--primary) {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

:deep(.van-button--default) {
  color: var(--primary-color);
  border-color: var(--primary-color);
}
</style>