<template>
  <div class="export-view">
    <BackButton title="数据导出" />

    <div class="export-content">
      <van-cell-group inset>
        <van-cell
          title="检验报告"
          label="导出所有检验报告为PDF"
          is-link
          @click="handleExport('timeline')"
          :loading="exporting === 'timeline'"
        >
          <template #icon><van-icon name="records" class="cell-icon" /></template>
        </van-cell>
        <van-cell
          title="完整病历摘要"
          label="导出患者信息、报告汇总、用药记录"
          is-link
          @click="handleExport('summary')"
          :loading="exporting === 'summary'"
        >
          <template #icon><van-icon name="description" class="cell-icon" /></template>
        </van-cell>
      </van-cell-group>

      <div class="export-hint">
        <van-icon name="info-o" />
        <span>导出的PDF文件将自动下载到您的设备</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { showToast } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { exportApi } from '@/api/export'
import { downloadBlob } from '@/utils/export'
import BackButton from '@/components/index-detail/BackButton.vue'

const patientStore = usePatientStore()
const exporting = ref('')

// blob 错误响应解析后端 detail（responseType: blob 时 e.response.data 也是 Blob）
async function resolveErrorMessage(e) {
  const detail = e?.response?.data
  if (detail instanceof Blob) {
    try {
      const parsed = JSON.parse(await detail.text())
      if (parsed?.detail) return parsed.detail
    } catch {
      // 非 JSON 响应，回退通用文案
    }
  }
  return '导出失败，请重试'
}

async function handleExport(type) {
  if (!patientStore.currentPatient) {
    showToast('请先选择患者')
    return
  }

  const patientId = patientStore.currentPatient.patient_id
  exporting.value = type

  try {
    let blob, filename
    if (type === 'timeline') {
      blob = await exportApi.exportTimeline(patientId)
      filename = `时间线_${patientId}.pdf`
    } else if (type === 'summary') {
      blob = await exportApi.exportSummary(patientId)
      filename = `病历摘要_${patientId}.pdf`
    }

    if (blob) {
      const ok = await downloadBlob(blob, filename)
      if (ok) showToast({ message: '导出成功', type: 'success' })
    }
  } catch (e) {
    console.error('导出失败:', e)
    showToast(await resolveErrorMessage(e))
  } finally {
    exporting.value = ''
  }
}
</script>

<style scoped>
.export-view {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: var(--safe-bottom);
}

.export-content {
  padding: 16px;
}

.cell-icon {
  font-size: 20px;
  margin-right: 8px;
  color: var(--primary-color);
}

.export-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 16px;
  font-size: 13px;
  color: var(--text-tertiary);
}

@media (min-width: 768px) {
  .export-view {
    max-width: 600px;
    margin: 0 auto;
  }
}
</style>