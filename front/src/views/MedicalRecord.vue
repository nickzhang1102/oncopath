<template>
  <div class="medical-record">
    <BackButton title="报告详情" />

    <van-loading v-if="loading" class="loading-center" />

    <van-empty v-else-if="!record" description="报告不存在" />

    <template v-else>
      <!-- 报告基本信息 -->
      <div class="record-header">
        <div class="record-info">
          <h2 class="record-title">{{ record.hospital || '检验报告' }}</h2>
          <div class="record-meta">
            <span>{{ formatDate(record.medical_date) }}</span>
            <van-tag type="primary">检验报告</van-tag>
          </div>
          <div v-if="record.comment" class="record-comment">{{ record.comment }}</div>
        </div>
        <van-button
          class="export-btn"
          size="small"
          plain
          round
          icon="description"
          :loading="exporting"
          @click="handleExport"
        >
          导出 PDF
        </van-button>
        <van-button
          class="share-btn"
          size="small"
          plain
          round
          icon="share-o"
          @click="handleShare"
        >
          分享
        </van-button>
      </div>

      <!-- 指标列表 -->
      <div class="indicators-section">
        <div class="section-title">检验指标</div>
        <div class="indicator-list">
          <div
            v-for="indicator in details"
            :key="indicator.medical_detail_id"
            class="indicator-item"
            @click="viewIndicatorHistory(indicator)"
          >
            <div class="indicator-main">
              <div class="indicator-name">{{ indicator.index_name }}</div>
              <div class="indicator-value" :class="getStatusClass(indicator.index_status)">
                {{ indicator.index_value }}
                <span v-if="indicator.index_unit" class="indicator-unit">{{ indicator.index_unit }}</span>
                <span v-if="indicator.index_status === 'high'" class="status-arrow">↑</span>
                <span v-else-if="indicator.index_status === 'low'" class="status-arrow">↓</span>
              </div>
            </div>
            <div class="indicator-reference">
              参考范围: {{ indicator.reference_value || '无' }}
            </div>
          </div>
        </div>
      </div>
      
      <!-- AI 解读区域 -->
      <div class="interpretation-section">
        <div class="section-header">
          <div class="section-title">AI 智能解读</div>
          <van-button
            v-if="!interpretation"
            type="primary"
            size="small"
            :loading="interpreting"
            @click="handleInterpret"
          >
            生成解读
          </van-button>
          <van-button
            v-else
            size="small"
            :loading="interpreting"
            @click="handleInterpret"
          >
            重新解读
          </van-button>
        </div>

        <!-- 免责声明 -->
        <van-notice-bar
          v-if="interpretation"
          left-icon="warning-o"
          text="AI解读仅供参考，不构成医疗诊断建议。如有疑问请咨询主治医生。"
          color="var(--warning-color)"
          background="var(--warning-alpha-10)"
          :scrollable="false"
          wrapable
        />

        <!-- 解读内容 -->
        <div v-if="interpretation" class="interpretation-content">
          <MarkdownRenderer :content="interpretation" />
          <div class="interpretation-time">
            解读时间：{{ formatDate(record.interpretation_at) }}
          </div>
        </div>

        <!-- 无解读提示 -->
        <div v-else-if="!interpreting" class="interpretation-hint">
          点击"生成解读"，AI 将为您分析检验报告中的异常指标及临床意义
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showToast, showConfirmDialog } from 'vant'
import { medicalApi } from '@/api/medical'
import { exportApi } from '@/api/export'
import { downloadBlob } from '@/utils/export'
import { shareApi } from '@/api/share'
import BackButton from '@/components/index-detail/BackButton.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const interpreting = ref(false)
const exporting = ref(false)
const record = ref(null)
const details = ref([])
const interpretation = ref(null)

function formatDate(date) {
  if (!date) return ''
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

function getStatusClass(status) {
  return {
    'status-tag--normal': status === 'normal' || !status,
    'status-tag--high': status === 'high',
    'status-tag--low': status === 'low',
    'status-tag--abnormal': status === 'abnormal'
  }
}

function viewIndicatorHistory(indicator) {
  if (!indicator.index_id) {
    showToast('该指标未关联标准库，无法查看历史')
    return
  }
  router.push({
    path: '/home/indicator/history',
    query: {
      index_id: indicator.index_id,
      index_name: indicator.index_name
    }
  })
}

async function handleInterpret() {
  const reportId = route.params.id
  if (!reportId) return

  // 重新解读需确认
  if (interpretation.value) {
    try {
      await showConfirmDialog({
        title: '重新解读',
        message: '重新解读会覆盖当前解读结果，确定继续？',
      })
    } catch {
      return
    }
  }

  interpreting.value = true
  try {
    const res = await medicalApi.interpretMedicalCheck(reportId)
    if (res?.data) {
      interpretation.value = res.data.interpretation
      if (record.value) {
        record.value.interpretation_at = res.data.interpretation_at
      }
      showToast('解读生成成功')
    }
  } catch (error) {
    const msg = error?.response?.data?.detail || '解读生成失败'
    showToast(msg)
  } finally {
    interpreting.value = false
  }
}

async function handleExport() {
  const reportId = route.params.id
  if (!reportId) return

  exporting.value = true
  try {
    const blob = await exportApi.exportMedicalCheck(reportId)
    const ok = await downloadBlob(blob, `check_${reportId}.pdf`)
    if (ok) showToast('导出成功')
  } catch {
    showToast('导出失败')
  } finally {
    exporting.value = false
  }
}

async function handleShare() {
  const reportId = route.params.id
  if (!reportId) return
  try {
    const res = await shareApi.createShareToken({
      content_type: 'check_report',
      content_id: parseInt(reportId),
    })
    const url = `${window.location.origin}/share/report/${res.token}`
    try {
      await navigator.clipboard.writeText(url)
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = url
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    showToast('分享链接已复制到剪贴板')
  } catch (error) {
    showToast(error.response?.data?.detail || '分享失败')
  }
}

onMounted(async () => {
  const reportId = route.params.id
  if (!reportId) {
    loading.value = false
    return
  }

  loading.value = true
  try {
    const data = await medicalApi.getMedicalReport(reportId)
    record.value = data
    details.value = data.details || []

    // 加载已有解读
    if (data.interpretation) {
      interpretation.value = data.interpretation
    } else {
      try {
        const interpRes = await medicalApi.getInterpretation(reportId)
        if (interpRes?.data?.interpretation) {
          interpretation.value = interpRes.data.interpretation
        }
      } catch {
        // 无解读，忽略
      }
    }
  } catch (error) {
    console.error('获取报告详情失败:', error)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.medical-record {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.record-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  background: var(--bg-surface);
  padding: 16px;
  margin: 16px;
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
}

.export-btn {
  flex-shrink: 0;
  font-size: 12px;
}

.share-btn {
  flex-shrink: 0;
  font-size: 12px;
}

.record-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.record-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
  color: var(--text-secondary);
}

.record-comment {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  font-size: 13px;
  color: var(--text-secondary);
}

/* AI 解读区域 */
.interpretation-section {
  padding: 0 16px;
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.interpretation-content {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
  margin-top: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
}

.interpretation-time {
  text-align: right;
  font-size: 12px;
  color: var(--text-hint);
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border-light);
}

.interpretation-hint {
  text-align: center;
  padding: 24px;
  color: var(--text-hint);
  font-size: 14px;
}

/* 指标区域 */
.indicators-section {
  padding: 0 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.indicator-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.indicator-item {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  cursor: pointer;
  transition: all 0.2s;
}

.indicator-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--primary-alpha-12);
}

.indicator-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.indicator-name {
  font-size: 15px;
  color: var(--text-primary);
  font-weight: 500;
}

.indicator-value {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.indicator-unit {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
}

.status-arrow {
  font-size: 14px;
  margin-left: 2px;
}

.indicator-reference {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 8px;
}

/* 桌面端响应式布局 */
@media (min-width: 768px) {
  .medical-record {
    max-width: 960px;
    margin: 0 auto;
    padding: 0 32px 24px;
  }

  .record-header {
    padding: 20px 24px;
  }

  .indicator-list {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .indicator-item {
    padding: 14px 16px;
  }
}

@media (min-width: 1024px) {
  .indicator-list {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
