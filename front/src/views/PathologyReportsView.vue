<template>
  <div class="pathology-reports-view">
    <!-- 动态背景 -->
    <BackgroundAnimation />

    <!-- 返回按钮 -->
    <BackButton title="病理报告" />

    <!-- 统计概览 -->
    <div v-if="!loading && reports.length > 0" class="stats-section">
      <div class="stats-card">
        <div class="stat-item">
          <div class="stat-value">{{ reports.length }}</div>
          <div class="stat-label">报告总数</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-value">{{ getImageCount }}</div>
          <div class="stat-label">图片数量</div>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <div class="stat-value">{{ getLatestDate }}</div>
          <div class="stat-label">最近报告</div>
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

      <van-empty v-else-if="reports.length === 0" description="暂无病理报告">
        <template #image>
          <div class="empty-icon"><van-icon name="certificate" /></div>
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
              v-for="report in reports"
              :key="report.report_id"
              type="pathology"
              :title="report.report_title || '病理报告'"
              :date="report.report_date"
              :hospital="report.hospital"
              :comment="report.comment"
              :has-image="report.has_image"
              :diagnosis="report.diagnosis"
              :cancer-type="report.cancer_type"
              :stage="report.stage"
              :histology-type="report.histology_type"
              :immunohistochemistry="formatIHC(report)"
              :gene-testing="report.gene_testing"
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
      :title="currentReport?.report_title || '病理报告'"
      :image-url="previewImageUrl"
      :image-type="previewImageType"
      :loading="imageLoading"
    />

    <!-- 编辑弹窗 -->
    <van-dialog
      v-model:show="showEditDialog"
      title="编辑病理报告"
      show-cancel-button
      :before-close="onEditConfirm"
    >
      <div class="edit-form">
        <van-field v-model="editForm.report_title" label="报告标题" placeholder="病理报告标题" />
        <van-field v-model="editForm.hospital" label="医院" placeholder="检查医院" />
        <van-field v-model="editForm.report_date" label="报告日期" placeholder="点击选择" readonly clickable @click="showPathDatePicker = true" />
        <van-field v-model="editForm.diagnosis" label="诊断" placeholder="病理诊断" />
        <van-field v-model="editForm.cancer_type" label="癌种" placeholder="癌种/肿瘤类型" />
        <van-field v-model="editForm.stage" label="分期" placeholder="临床分期" />
        <van-field v-model="editForm.histology_type" label="组织学类型" placeholder="组织学类型" />
        <van-field v-model="editForm.immunohistochemistry" label="免疫组化" type="textarea" rows="2" placeholder="免疫组化结果(文本)" />
        <div class="ihc-section">
          <div class="ihc-header">
            <span class="ihc-title">免疫组化标记物</span>
            <van-button size="mini" type="primary" plain @click="addIHCMarker">+ 添加</van-button>
          </div>
          <div v-for="(marker, idx) in editForm.ihc_markers" :key="idx" class="ihc-row">
            <van-field v-model="marker.marker_name" placeholder="标记物" class="ihc-field" />
            <van-field v-model="marker.result" placeholder="结果" class="ihc-field" />
            <van-field v-model="marker.intensity" placeholder="强度" class="ihc-field-short" />
            <van-field v-model="marker.percentage" placeholder="百分比" class="ihc-field-short" />
            <van-icon name="delete-o" class="ihc-remove" @click="editForm.ihc_markers.splice(idx, 1)" />
          </div>
        </div>
        <van-field v-if="!editForm.gene_test_items.length" v-model="editForm.gene_testing" label="基因检测" type="textarea" rows="2" placeholder="基因检测信息" />
        <div class="gene-section">
          <div class="gene-header">
            <span class="gene-title">基因检测项目</span>
            <van-button size="mini" type="primary" plain @click="addGeneTestItem">+ 添加</van-button>
          </div>
          <div v-for="(item, idx) in editForm.gene_test_items" :key="idx" class="gene-row">
            <van-field v-model="item.gene" placeholder="基因" class="gene-field" />
            <van-field v-model="item.result" placeholder="结果" class="gene-field" />
            <van-field v-model="item.mutation_type" placeholder="突变类型" class="gene-field-short" />
            <van-field v-model="item.frequency" placeholder="频率" class="gene-field-short" />
            <van-icon name="delete-o" class="gene-remove" @click="editForm.gene_test_items.splice(idx, 1)" />
          </div>
          <van-field v-if="editForm.gene_test_items.length" v-model="editForm.gene_test_method" label="检测方法" placeholder="如：NGS、PCR" />
          <van-field v-if="editForm.gene_test_items.length" v-model="editForm.gene_test_interpretation" label="结果解释" type="textarea" rows="2" placeholder="结果解释/临床意义" />
        </div>
        <van-field v-model="editForm.comment" label="备注" type="textarea" rows="3" placeholder="备注" />
      </div>
    </van-dialog>

    <!-- 日期选择器 -->
    <van-popup
      v-model:show="showPathDatePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="pathDatePickerValue"
        title="选择报告日期"
        :min-date="new Date(2000, 0, 1)"
        :max-date="new Date()"
        @confirm="onPathDateConfirm"
        @cancel="showPathDatePicker = false"
      />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { medicalApi } from '@/api/medical'
import { useReportList } from '@/composables/useReportList'
import { useResponsive } from '@/composables/useResponsive'
import { useGeneTesting } from '@/composables/useGeneTesting'
const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'
import ReportCard from '@/components/report/ReportCard.vue'
import ImagePreviewModal from '@/components/report/ImagePreviewModal.vue'
import dayjs from 'dayjs'

const router = useRouter()
const { isDesktop } = useResponsive()

// 使用通用报告列表 composable
const {
  loading, refreshing, loadingMore, finished, reports, hasPatient,
  showImagePreview, previewImageUrl, currentReport, imageLoading,
  getLatestDate, fetchReports, onRefresh, onLoadMore, handleDelete, handleShare,
  openImagePreview,
} = useReportList({
  fetchFn: (patientId, params) => medicalApi.getPathologyReports(patientId, params),
  deleteFn: (report) => medicalApi.deletePathologyReport(report.report_id),
  shareContentType: 'pathology_report',
  shareContentIdFn: (report) => report.report_id,
  deleteConfirmMsg: '确定要删除该病理报告吗？删除后无法恢复。',
  dateField: 'report_date',
})

// 病理报告特有：统计
const getImageCount = computed(() => {
  return reports.value.filter(r => r.has_image).length
})

function viewDetail(report) {
  router.push(`/home/pathology-report/${report.report_id}`)
}

// 病理报告特有：编辑
const showEditDialog = ref(false)
const showPathDatePicker = ref(false)
const pathDatePickerValue = ref([])
const editForm = ref({
  report_title: '', hospital: '', report_date: '', comment: '',
  diagnosis: '', cancer_type: '', stage: '', histology_type: '',
  immunohistochemistry: '', gene_testing: '',
  gene_test_items: [], gene_test_method: '', gene_test_interpretation: '',
  ihc_markers: []
})

function formatIHC(report) {
  if (report.ihc_markers?.length) {
    return report.ihc_markers.map(m => `${m.marker_name}(${m.result || '-'}${m.percentage ? ' ' + m.percentage : ''})`).join(', ')
  }
  return report.immunohistochemistry || ''
}

function addIHCMarker() {
  editForm.value.ihc_markers.push({ marker_name: '', result: '', intensity: '', percentage: '' })
}

function addGeneTestItem() {
  editForm.value.gene_test_items.push({ gene: '', result: '', mutation_type: '', frequency: '' })
}

function editReport(report) {
  currentReport.value = report
  const geneRaw = ref(report.gene_testing)
  const { items: geneItems, method: geneMethod, interpretation: geneInterp, isStructured } = useGeneTesting(geneRaw)
  const parsed = {
    items: geneItems.value,
    method: geneMethod.value,
    interpretation: geneInterp.value,
    text: isStructured.value ? '' : (report.gene_testing || ''),
  }
  editForm.value = {
    report_title: report.report_title || '',
    hospital: report.hospital || '',
    report_date: report.report_date ? dayjs(report.report_date).format('YYYY-MM-DD') : '',
    comment: report.comment || '',
    diagnosis: report.diagnosis || '',
    cancer_type: report.cancer_type || '',
    stage: report.stage || '',
    histology_type: report.histology_type || '',
    immunohistochemistry: report.immunohistochemistry || '',
    gene_testing: parsed.text,
    gene_test_items: parsed.items,
    gene_test_method: parsed.method,
    gene_test_interpretation: parsed.interpretation,
    ihc_markers: (report.ihc_markers || []).map(m => ({ ...m })),
  }
  showEditDialog.value = true
}

function onPathDateConfirm({ selectedValues }) {
  if (selectedValues?.length === 3) {
    editForm.value.report_date = selectedValues.join('-')
  }
  showPathDatePicker.value = false
}

async function onEditConfirm(action) {
  if (action === 'confirm') {
    try {
      const data = { ...editForm.value }
      if (!data.report_date) data.report_date = null
      // 过滤空标记物
      if (data.ihc_markers) {
        data.ihc_markers = data.ihc_markers.filter(m => m.marker_name.trim())
        if (data.ihc_markers.length === 0) delete data.ihc_markers
      }
      // 序列化基因检测结构化数据
      const validItems = (data.gene_test_items || []).filter(i => i.gene.trim())
      if (validItems.length > 0) {
        data.gene_testing = JSON.stringify({
          test_items: validItems,
          test_method: data.gene_test_method || null,
          interpretation: data.gene_test_interpretation || null,
        })
      } else if (data.gene_testing && data.gene_testing.trim()) {
        // 保留纯文本（向后兼容）
        // gene_testing 已有值，不覆盖
      } else {
        data.gene_testing = null
      }
      delete data.gene_test_items
      delete data.gene_test_method
      delete data.gene_test_interpretation
      await medicalApi.updatePathologyReport(currentReport.value.report_id, data)
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
.pathology-reports-view {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
  box-sizing: border-box;
  position: relative;
}

/* 统计概览 */
.stats-section {
  padding: 16px;
  margin-bottom: 0;
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
  padding: 16px;
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

.ihc-section {
  padding: 8px 16px;
}

.ihc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.ihc-title {
  font-size: 14px;
  color: var(--text-secondary);
}

.ihc-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
}

.ihc-field {
  flex: 1;
}

.ihc-field-short {
  width: 60px;
  flex-shrink: 0;
}

.ihc-remove {
  color: var(--van-danger-color, #ee0a24);
  font-size: 18px;
  flex-shrink: 0;
  cursor: pointer;
}

.gene-section {
  padding: 8px 16px;
}

.gene-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.gene-title {
  font-size: 14px;
  color: var(--van-text-color-2, #969799);
}

.gene-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
}

.gene-field {
  flex: 1;
}

.gene-field-short {
  width: 60px;
  flex-shrink: 0;
}

.gene-remove {
  color: var(--van-danger-color, #ee0a24);
  font-size: 18px;
  flex-shrink: 0;
  cursor: pointer;
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
  .stats-section,
  .report-list-section {
    padding-left: 12px;
    padding-right: 12px;
  }

  .stat-value {
    font-size: 18px;
  }
}

/* 桌面端侧边栏适配 + 居中限宽 */
@media (min-width: 768px) {
  .pathology-reports-view {
    padding: var(--space-6);
    padding-bottom: var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
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