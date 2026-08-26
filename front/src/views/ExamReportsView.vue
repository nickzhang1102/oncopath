<template>
  <div class="exam-reports-view">
    <!-- 动态背景 -->
    <BackgroundAnimation />

    <!-- 返回按钮 -->
    <BackButton title="检查报告" />

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
          <div class="stat-value">{{ getTypeCount }}</div>
          <div class="stat-label">报告类型</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-value">{{ getLatestDate }}</div>
          <div class="stat-label">最近检查</div>
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

      <van-empty v-else-if="reports.length === 0" description="暂无检查报告">
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
            <ReportCard
              v-for="report in filteredReports"
              :key="report.exam_id"
              :type="report.exam_type"
              :title="report.title || EXAM_TYPE_LABELS[report.exam_type] || report.exam_type || '检查报告'"
              :date="report.medical_date"
              :hospital="report.hospital"
              :exam-info="report.exam_info"
              :exam-diag="report.exam_diag"
              :has-image="!!report.image_report_id"
              :interpretation="report.interpretation"
              @view-detail="viewDetail(report)"
              @share="handleShare(report)"
              @edit="editReport(report)"
              @delete="handleDelete(report)"
            />
          </TransitionGroup>
        </van-list>
      </van-pull-refresh>
    </div>

    <!-- 图片预览弹窗 -->
    <ImagePreviewModal
      v-model:show="showImagePreview"
      :title="currentReport?.title || EXAM_TYPE_LABELS[currentReport?.exam_type] || currentReport?.exam_type || '检查报告'"
      :image-url="previewImageUrl"
      :image-type="previewImageType"
      :loading="imageLoading"
    />

    <!-- 编辑弹窗 -->
    <van-dialog
      v-model:show="showEditDialog"
      title="编辑检查报告"
      show-cancel-button
      :before-close="onEditConfirm"
    >
      <div class="edit-form">
        <van-field v-model="editForm.title" label="报告标题" placeholder="如 胸部平扫+增强CT" />
        <van-field v-model="editForm.exam_type" label="检查类型" placeholder="如 CT、MRI、超声" />
        <van-field v-model="editForm.hospital" label="医院" placeholder="检查医院" />
        <van-field v-model="editForm.medical_date" label="检查日期" placeholder="点击选择" readonly clickable @click="showExamDatePicker = true" />
        <van-field v-model="editForm.exam_info" label="检查所见" type="textarea" rows="3" placeholder="检查所见" />
        <van-field v-model="editForm.exam_diag" label="诊断意见" type="textarea" rows="3" placeholder="诊断意见" />
        <van-field v-model="editForm.comment" label="备注" type="textarea" rows="2" placeholder="备注" />
      </div>
    </van-dialog>

    <!-- 日期选择器 -->
    <van-popup
      v-model:show="showExamDatePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="examDatePickerValue"
        title="选择检查日期"
        :min-date="new Date(2000, 0, 1)"
        :max-date="new Date()"
        @confirm="onExamDateConfirm"
        @cancel="showExamDatePicker = false"
      />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { medicalApi } from '@/api/medical'
import { getImageData } from '@/api/imageReport'
import { useReportList } from '@/composables/useReportList'
import { useResponsive } from '@/composables/useResponsive'
const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'
import FilterTabs from '@/components/report/FilterTabs.vue'
import ReportCard from '@/components/report/ReportCard.vue'
import ImagePreviewModal from '@/components/report/ImagePreviewModal.vue'
import dayjs from 'dayjs'
import { EXAM_TYPE_LABELS } from '@/styles/constants'

const router = useRouter()
const { isDesktop } = useResponsive()

// 使用通用报告列表 composable
const {
  loading, refreshing, loadingMore, finished, reports, hasPatient,
  showImagePreview, previewImageUrl, currentReport, imageLoading,
  getLatestDate, fetchReports, onRefresh, onLoadMore, handleDelete, handleShare,
  openImagePreview,
} = useReportList({
  fetchFn: (patientId, params) => medicalApi.getExamReports(patientId, params),
  deleteFn: (report) => medicalApi.deleteExamReport(report.exam_id),
  shareContentType: 'exam_report',
  shareContentIdFn: (report) => report.exam_id,
  deleteConfirmMsg: '确定要删除该检查报告吗？删除后无法恢复。',
  dateField: 'medical_date',
})

// 检查报告特有：筛选和统计
const filterType = ref('all')

const filterTabs = computed(() => {
  const baseTabs = [
    { text: '全部', value: 'all', icon: 'todo-list-o', count: reports.value.length }
  ]

  const typeCounts = {}
  reports.value.forEach(r => {
    if (r.exam_type) {
      const key = r.exam_type.toLowerCase()
      typeCounts[key] = (typeCounts[key] || 0) + 1
    }
  })

  const typeConfig = {
    'ct': { text: 'CT', icon: 'search' },
    'mri': { text: 'MRI', icon: 'microscope-o' },
    'ultrasound': { text: '超声', icon: 'wave' },
    'xray': { text: 'X光', icon: 'photo-o' },
    'ecg': { text: '心电图', icon: 'like-o' },
    'endoscopy': { text: '内镜', icon: 'aim' },
    'gastroscopy': { text: '胃镜', icon: 'gift-o' },
    'colonoscopy': { text: '肠镜', icon: 'scan' }
  }

  Object.keys(typeCounts).forEach(type => {
    const config = typeConfig[type] || { text: type.toUpperCase(), icon: 'description' }
    baseTabs.push({ text: config.text, value: type, icon: config.icon, count: typeCounts[type] })
  })

  return baseTabs
})

const getTypeCount = computed(() => {
  const types = new Set()
  reports.value.forEach(r => {
    if (r.exam_type) types.add(r.exam_type.toLowerCase())
  })
  return types.size
})

const filteredReports = computed(() => {
  if (filterType.value === 'all') return reports.value
  return reports.value.filter(r => r.exam_type?.toLowerCase() === filterType.value)
})

function onFilterChange() {}

function viewDetail(report) {
  router.push(`/home/exam-report/${report.exam_id}`)
}

// 检查报告特有：编辑
const showEditDialog = ref(false)
const showExamDatePicker = ref(false)
const examDatePickerValue = ref([])
const editForm = ref({
  title: '', exam_type: '', hospital: '', medical_date: '', exam_info: '', exam_diag: '', comment: ''
})

function editReport(report) {
  currentReport.value = report
  editForm.value = {
    title: report.title || '',
    exam_type: report.exam_type || '',
    hospital: report.hospital || '',
    medical_date: report.medical_date ? dayjs(report.medical_date).format('YYYY-MM-DD') : '',
    exam_info: report.exam_info || '',
    exam_diag: report.exam_diag || '',
    comment: report.comment || '',
  }
  showEditDialog.value = true
}

function onExamDateConfirm({ selectedValues }) {
  if (selectedValues?.length === 3) {
    editForm.value.medical_date = selectedValues.join('-')
  }
  showExamDatePicker.value = false
}

async function onEditConfirm(action) {
  if (action === 'confirm') {
    try {
      const data = { ...editForm.value }
      if (!data.medical_date) data.medical_date = null
      await medicalApi.updateExamReport(currentReport.value.exam_id, data)
      showToast('更新成功')
      await fetchReports()
    } catch (error) {
      showToast(error.response?.data?.detail || '更新失败')
      return false
    }
  }
  return true
}
</script>

<style scoped>
.exam-reports-view {
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

.edit-form {
  padding: 16px;
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
  .exam-reports-view {
    padding: 0 var(--space-6) var(--space-6);
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