<template>
  <div class="share-report">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <van-loading size="36" color="var(--primary-color)" vertical>加载中...</van-loading>
    </div>

    <!-- 错误状态 -->
    <div v-if="loadError" class="error-container">
      <van-empty :description="loadError" image="error" />
      <van-button type="primary" @click="retryLoad">重试</van-button>
    </div>

    <!-- 主内容 -->
    <template v-if="!loading && !loadError && reportData">
      <!-- 顶部信息条 -->
      <header class="share-header">
        <div class="header-top">
          <van-icon name="shield-o" class="share-icon" />
          <div class="header-info">
            <span class="share-label">{{ contentTypeLabel }}</span>
            <span class="share-date">{{ reportData.medical_date || reportData.report_date }}</span>
          </div>
        </div>
      </header>

      <!-- 检验报告 -->
      <template v-if="reportData.content_type === 'check_report'">
        <div class="report-card">
          <div class="report-meta-row">
            <span v-if="reportData.report.hospital" class="meta-item">
              <van-icon name="location-o" />
              {{ reportData.report.hospital }}
            </span>
            <span class="meta-item">
              <van-icon name="calendar-o" />
              {{ reportData.report.medical_date }}
            </span>
          </div>

          <div v-if="reportData.report.details?.length" class="details-section">
            <div class="section-title">检验指标</div>
            <div class="detail-table">
              <div class="detail-header">
                <span class="col-name">指标</span>
                <span class="col-value">结果</span>
                <span class="col-ref">参考范围</span>
                <span class="col-status">状态</span>
              </div>
              <div
                v-for="(d, i) in reportData.report.details"
                :key="i"
                class="detail-row"
                :class="getStatusClass(d.index_status)"
              >
                <span class="col-name">{{ d.index_name }}</span>
                <span class="col-value">{{ d.index_value }} <small>{{ d.index_unit }}</small></span>
                <span class="col-ref">{{ d.reference_value || '-' }}</span>
                <span class="col-status">{{ statusLabel(d.index_status) }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 检查报告 -->
      <template v-if="reportData.content_type === 'exam_report'">
        <div class="report-card">
          <div class="report-meta-row">
            <span v-if="reportData.report.hospital" class="meta-item">
              <van-icon name="location-o" />
              {{ reportData.report.hospital }}
            </span>
            <span v-if="reportData.report.exam_type" class="meta-item">
              <van-icon name="scan" />
              {{ reportData.report.exam_type_name || EXAM_TYPE_LABELS[reportData.report.exam_type] || reportData.report.exam_type }}
            </span>
          </div>

          <div v-if="reportData.report.exam_info" class="info-section">
            <div class="section-title">检查所见</div>
            <div class="info-text">{{ reportData.report.exam_info }}</div>
          </div>

          <div v-if="reportData.report.exam_diag" class="info-section">
            <div class="section-title">诊断意见</div>
            <div class="info-text">{{ reportData.report.exam_diag }}</div>
          </div>
        </div>
      </template>

      <!-- 病理报告 -->
      <template v-if="reportData.content_type === 'pathology_report'">
        <div class="report-card">
          <div class="report-meta-row">
            <span v-if="reportData.report.hospital" class="meta-item">
              <van-icon name="location-o" />
              {{ reportData.report.hospital }}
            </span>
            <span class="meta-item">
              <van-icon name="calendar-o" />
              {{ reportData.report.report_date }}
            </span>
          </div>

          <div v-if="reportData.report.report_title" class="info-section">
            <div class="section-title">报告标题</div>
            <div class="info-text">{{ reportData.report.report_title }}</div>
          </div>

          <!-- 结构化字段 -->
          <div v-if="hasPathologyFields" class="info-section">
            <div class="section-title">病理信息</div>
            <div class="structured-fields">
              <div v-if="reportData.report.diagnosis" class="field-item full-width">
                <span class="field-label">诊断</span>
                <span class="field-value">{{ reportData.report.diagnosis }}</span>
              </div>
              <div v-if="reportData.report.cancer_type" class="field-item">
                <span class="field-label">癌种</span>
                <span class="field-value">{{ reportData.report.cancer_type }}</span>
              </div>
              <div v-if="reportData.report.stage" class="field-item">
                <span class="field-label">分期</span>
                <span class="field-value">{{ reportData.report.stage }}</span>
              </div>
              <div v-if="reportData.report.histology_type" class="field-item">
                <span class="field-label">组织学类型</span>
                <span class="field-value">{{ reportData.report.histology_type }}</span>
              </div>
              <div v-if="reportData.report.immunohistochemistry" class="field-item full-width">
                <span class="field-label">免疫组化</span>
                <span class="field-value">{{ reportData.report.immunohistochemistry }}</span>
              </div>
              <div v-if="reportData.report.gene_testing" class="field-item full-width">
                <span class="field-label">基因检测</span>
                <span class="field-value">{{ geneTestingDisplay }}</span>
              </div>
            </div>
          </div>

          <div v-if="reportData.report.comment" class="info-section">
            <div class="section-title">备注</div>
            <div class="info-text">{{ reportData.report.comment }}</div>
          </div>
        </div>
      </template>

      <!-- AI 解读区域 -->
      <template v-if="interpretation">
        <div class="interpretation-section">
          <div class="interpretation-header">
            <van-icon name="chat-o" class="interpretation-icon" />
            <span class="interpretation-label">AI 智能解读</span>
          </div>

          <van-notice-bar
            left-icon="warning-o"
            text="AI解读仅供参考，不构成医疗诊断建议。如有疑问请咨询主治医生。"
            color="var(--warning-color)"
            background="var(--warning-alpha-10)"
            :scrollable="false"
            wrapable
          />

          <div class="interpretation-content">
            <MarkdownRenderer :content="interpretation" />
            <div v-if="interpretationAt" class="interpretation-time">
              解读时间：{{ interpretationAt }}
            </div>
          </div>
        </div>
      </template>

      <!-- 底部免责声明 -->
      <div class="disclaimer">
        <van-icon name="warning-o" />
        本报告仅供查看参考，不作为诊疗依据。如有疑问请咨询主治医生。
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { shareApi } from '@/api/share'
import { EXAM_TYPE_LABELS } from '@/styles/constants'
import { useGeneTesting } from '@/composables/useGeneTesting'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const route = useRoute()

const loading = ref(false)
const loadError = ref(null)
const reportData = ref(null)

const contentTypeLabel = computed(() => {
  const labels = {
    check_report: '检验报告',
    exam_report: '检查报告',
    pathology_report: '病理报告',
  }
  return labels[reportData.value?.content_type] || '医疗报告'
})

const hasPathologyFields = computed(() => {
  const r = reportData.value?.report
  if (!r) return false
  return r.diagnosis || r.cancer_type || r.stage || r.histology_type || r.immunohistochemistry || r.gene_testing
})

const geneTestingRaw = computed(() => reportData.value?.report?.gene_testing || null)
const { display: geneTestingDisplay } = useGeneTesting(geneTestingRaw)

const interpretation = computed(() => reportData.value?.report?.interpretation || null)
const interpretationAt = computed(() => {
  const at = reportData.value?.report?.interpretation_at
  if (!at) return null
  const d = new Date(at)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
})

function getStatusClass(status) {
  return {
    'row-high': status === 'high',
    'row-low': status === 'low',
    'row-abnormal': status === 'abnormal',
  }
}

function statusLabel(status) {
  const labels = { high: '偏高↑', low: '偏低↓', normal: '正常', abnormal: '异常' }
  return labels[status] || '-'
}

async function fetchReport() {
  const token = route.params.token
  if (!token) {
    loadError.value = '无效的分享链接'
    return
  }

  loading.value = true
  loadError.value = null
  try {
    const data = await shareApi.getSharedReport(token)
    reportData.value = data
  } catch (error) {
    const detail = error?.response?.data?.detail
    if (detail) {
      loadError.value = detail
    } else {
      loadError.value = '加载报告失败'
    }
  } finally {
    loading.value = false
  }
}

function retryLoad() {
  fetchReport()
}

onMounted(() => {
  fetchReport()
})
</script>

<style scoped>
.share-report {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 16px;
  padding-bottom: var(--safe-bottom);
  box-sizing: border-box;
}

.loading-state,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16px;
}

/* 顶部信息条 */
.share-header {
  background: var(--bg-surface);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 12px var(--primary-alpha-8);
}

.header-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.share-icon {
  font-size: 28px;
  color: var(--primary-color);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.share-label {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
}

.share-date {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 报告卡片 */
.report-card {
  background: var(--bg-surface);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 2px 12px var(--primary-alpha-8);
}

.report-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--primary-alpha-10);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

/* 检验指标表格 */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 10px;
}

.details-section {
  margin-top: 4px;
}

.detail-table {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.detail-header {
  display: grid;
  grid-template-columns: 2fr 1.5fr 1.5fr 1fr;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 2px solid var(--primary-alpha-15);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.detail-row {
  display: grid;
  grid-template-columns: 2fr 1.5fr 1.5fr 1fr;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--primary-alpha-6);
  font-size: 13px;
  align-items: center;
}

.detail-row:last-child {
  border-bottom: none;
}

.col-name {
  color: var(--text-primary);
  font-weight: 500;
}

.col-value {
  color: var(--text-primary);
}

.col-value small {
  font-size: 11px;
  color: var(--text-tertiary);
}

.col-ref {
  color: var(--text-secondary);
  font-size: 12px;
}

.col-status {
  font-size: 12px;
  font-weight: 500;
}

.row-high .col-value,
.row-high .col-status {
  color: var(--danger-color, #ee0a24);
}

.row-low .col-value,
.row-low .col-status {
  color: var(--warning-color, #ed6a0c);
}

.row-abnormal .col-value,
.row-abnormal .col-status {
  color: var(--danger-color, #ee0a24);
}

/* 文本信息区 */
.info-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--primary-alpha-10);
}

.info-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-wrap;
}

/* 结构化字段 */
.structured-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-item.full-width {
  grid-column: 1 / -1;
}

.field-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.field-value {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.5;
  word-break: break-all;
}

/* AI 解读区域 */
.interpretation-section {
  background: var(--bg-surface);
  border-radius: 16px;
  padding: 16px;
  margin-top: 16px;
  box-shadow: 0 2px 12px var(--primary-alpha-8);
}

.interpretation-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.interpretation-icon {
  font-size: 20px;
  color: var(--primary-color);
}

.interpretation-label {
  font-size: 15px;
  font-weight: 600;
  color: var(--primary-color);
}

.interpretation-content {
  margin-top: 12px;
}

.interpretation-time {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 12px;
  text-align: right;
  padding-top: 8px;
  border-top: 1px solid var(--border-light);
}

/* 免责声明 */
.disclaimer {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 24px;
  padding: 12px;
  background: var(--warning-alpha-10, rgba(237, 106, 12, 0.1));
  border-radius: 12px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.disclaimer .van-icon {
  flex-shrink: 0;
  color: var(--warning-color, #ed6a0c);
  margin-top: 2px;
}

/* 桌面端 */
@media (min-width: 768px) {
  .share-report {
    max-width: 800px;
    margin: 0 auto;
    padding: var(--space-6);
  }
}
</style>