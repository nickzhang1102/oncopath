<template>
  <div class="summary-section">
    <div class="summary-header">
      <span class="summary-title">{{ title }}</span>
      <van-button size="small" type="primary" plain @click="showGenerate = true">生成概要</van-button>
    </div>

    <!-- 概要列表 -->
    <van-loading v-if="loading" size="20" />
    <div v-else-if="summaries.length === 0" class="summary-empty">暂无概要</div>
    <div v-else class="summary-list">
      <div v-for="item in summaries" :key="item.summary_id" class="summary-card">
        <div class="summary-meta">
          <span class="summary-period">{{ item.period_start }} ~ {{ item.period_end }}</span>
          <van-tag :type="item.status === 'confirmed' ? 'success' : 'warning'" size="small">
            {{ item.status === 'confirmed' ? '已确认' : '草稿' }}
          </van-tag>
          <van-tag plain size="small">{{ item.source === 'rule_template' ? '规则' : 'LLM' }}</van-tag>
        </div>
        <div class="summary-text">{{ item.summary_text }}</div>
        <div class="summary-actions">
          <van-button size="mini" plain @click="editSummary(item)">编辑</van-button>
          <van-button v-if="item.status === 'draft'" size="mini" type="success" plain @click="confirmSummary(item)">确认</van-button>
          <van-button size="mini" type="danger" plain @click="onDeleteClick(item)">删除</van-button>
        </div>
      </div>
    </div>

    <!-- 生成弹窗 -->
    <van-dialog v-model:show="showGenerate" title="生成概要" show-cancel-button @confirm="onGenerate">
      <div class="generate-form">
        <van-field v-model="generateForm.period_start" label="起始日期" placeholder="点击选择" readonly clickable @click="openDatePicker('start')" />
        <van-field v-model="generateForm.period_end" label="结束日期" placeholder="点击选择" readonly clickable @click="openDatePicker('end')" />
        <van-field label="来源">
          <template #input>
            <van-radio-group v-model="generateForm.source" direction="horizontal">
              <van-radio name="rule_template">规则模板</van-radio>
              <van-radio name="llm_generated">LLM摘要</van-radio>
            </van-radio-group>
          </template>
        </van-field>
      </div>
    </van-dialog>

    <!-- 起始日期选择器 -->
    <van-popup v-model:show="showStartDatePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker v-model="selectedStartDate" title="选择起始日期" @confirm="onStartDateConfirm" @cancel="showStartDatePicker = false" />
    </van-popup>

    <!-- 结束日期选择器 -->
    <van-popup v-model:show="showEndDatePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker v-model="selectedEndDate" title="选择结束日期" @confirm="onEndDateConfirm" @cancel="showEndDatePicker = false" />
    </van-popup>

    <!-- 编辑弹窗 -->
    <van-dialog v-model:show="showEdit" title="编辑概要" show-cancel-button @confirm="onSaveEdit">
      <div class="edit-form">
        <van-field v-model="editForm.summary_text" type="textarea" rows="5" placeholder="概要内容" />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { showToast, showSuccessToast, showConfirmDialog } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'
import { listSummaries, generateSummary, updateSummary, deleteSummary } from '@/api/prompt'

const props = defineProps({
  title: { type: String, default: '概要摘要' },
  summaryType: { type: String, required: true },
})

const patientStore = usePatientStore()
const { isDesktop } = useResponsive()
const patientId = computed(() => patientStore.currentPatient?.patient_id)

const summaries = ref([])
const loading = ref(false)
const showGenerate = ref(false)
const showEdit = ref(false)

const generateForm = ref({
  period_start: '',
  period_end: '',
  source: props.summaryType === 'status' ? 'llm_generated' : 'rule_template',
})

const showStartDatePicker = ref(false)
const showEndDatePicker = ref(false)
const selectedStartDate = ref(['2026', '01', '01'])
const selectedEndDate = ref(['2026', '01', '01'])

const editForm = ref({ summary_id: null, summary_text: '' })

async function loadSummaries() {
  if (!patientId.value) return
  loading.value = true
  try {
    const res = await listSummaries(patientId.value, { summary_type: props.summaryType })
    summaries.value = res || []
  } catch (e) {
    console.error('加载概要失败', e)
  } finally {
    loading.value = false
  }
}

async function onGenerate() {
  if (!generateForm.value.period_start || !generateForm.value.period_end) {
    showToast('请选择时段')
    return
  }
  if (generateForm.value.source === 'rule_template' && props.summaryType === 'status') {
    showToast('状态记录仅支持 LLM 摘要')
    return
  }
  if (generateForm.value.source === 'llm_generated' && props.summaryType !== 'status') {
    showToast('LLM 摘要当前仅支持状态记录')
    return
  }
  try {
    await generateSummary({
      patient_id: patientId.value,
      summary_type: props.summaryType,
      period_start: generateForm.value.period_start,
      period_end: generateForm.value.period_end,
      source: generateForm.value.source,
    })
    showSuccessToast('生成成功')
    await loadSummaries()
  } catch (e) {
    showToast(e.response?.data?.detail || '生成失败')
  }
}

function openDatePicker(field) {
  const dateStr = field === 'start' ? generateForm.value.period_start : generateForm.value.period_end
  const now = new Date()
  const [y, m, d] = dateStr
    ? dateStr.split('-')
    : [String(now.getFullYear()), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')]
  if (field === 'start') {
    selectedStartDate.value = [y, m, d]
    showStartDatePicker.value = true
  } else {
    selectedEndDate.value = [y, m, d]
    showEndDatePicker.value = true
  }
}

function onStartDateConfirm({ selectedValues }) {
  generateForm.value.period_start = selectedValues.join('-')
  showStartDatePicker.value = false
}

function onEndDateConfirm({ selectedValues }) {
  generateForm.value.period_end = selectedValues.join('-')
  showEndDatePicker.value = false
}

function editSummary(item) {
  editForm.value = { summary_id: item.summary_id, summary_text: item.summary_text }
  showEdit.value = true
}

async function onSaveEdit() {
  try {
    await updateSummary(editForm.value.summary_id, { summary_text: editForm.value.summary_text })
    showSuccessToast('保存成功')
    await loadSummaries()
  } catch (e) {
    showToast('保存失败')
  }
}

async function confirmSummary(item) {
  try {
    await updateSummary(item.summary_id, { status: 'confirmed' })
    showSuccessToast('已确认')
    await loadSummaries()
  } catch (e) {
    showToast('确认失败')
  }
}

async function onDeleteClick(item) {
  try {
    await showConfirmDialog({ title: '确认删除', message: '删除后不可恢复，确定要删除吗？' })
  } catch {
    return
  }
  try {
    await deleteSummary(item.summary_id)
    showSuccessToast('已删除')
    await loadSummaries()
  } catch (e) {
    showToast('删除失败')
  }
}

onMounted(loadSummaries)
watch(patientId, loadSummaries)
</script>

<style scoped>
.summary-section {
  padding: 8px 0;
}
.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.summary-title {
  font-weight: 600;
  font-size: 14px;
}
.summary-empty {
  color: var(--text-tertiary);
  font-size: 13px;
  text-align: center;
  padding: 12px 0;
}
.summary-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.summary-card {
  background: var(--van-background-2);
  border-radius: 8px;
  padding: 10px 12px;
}
.summary-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}
.summary-period {
  color: var(--text-primary);
  font-weight: 500;
}
.summary-text {
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  color: var(--text-primary);
}
.summary-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}
.generate-form,
.edit-form {
  padding: 16px;
}
</style>