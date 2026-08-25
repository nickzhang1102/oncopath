<template>
  <div class="index-detail-container">
    <!-- 背景动画 -->
    <BackgroundAnimation />

    <!-- 返回按钮 -->
    <BackButton :title="compareMode ? '指标对比' : '指标明细'" />

    <!-- 日期范围过滤 -->
    <div class="date-filter-section">
      <div class="date-chips">
        <span
          v-for="opt in dateOptions"
          :key="opt.key"
          class="date-chip"
          :class="{ active: activeDateKey === opt.key }"
          @click="onDateChange(opt.key)"
        >{{ opt.label }}</span>
      </div>
      <!-- 自定义日期触发 -->
      <div v-if="activeDateKey === 'custom'" class="custom-date-trigger">
        <span class="date-field" @click="showStartPicker = true">
          {{ customStart || '开始日期' }}
        </span>
        <span class="date-separator">至</span>
        <span class="date-field" @click="showEndPicker = true">
          {{ customEnd || '结束日期' }}
        </span>
        <span v-if="customStart && customEnd" class="apply-btn" @click="applyCustomDate">应用</span>
      </div>
    </div>

    <!-- 自定义日期弹出选择器 -->
    <van-popup
      v-model:show="showStartPicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="customStartDate"
        title="开始日期"
        :min-date="new Date(2000, 0, 1)"
        :max-date="new Date()"
        @confirm="onStartPickerConfirm"
        @cancel="showStartPicker = false"
      />
    </van-popup>
    <van-popup
      v-model:show="showEndPicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
      <van-date-picker
        v-model="customEndDate"
        title="结束日期"
        :min-date="new Date(2000, 0, 1)"
        :max-date="new Date()"
        @confirm="onEndPickerConfirm"
        @cancel="showEndPicker = false"
      />
    </van-popup>

    <!-- 视图切换按钮 -->
    <ViewToggle
      v-if="showChart && !compareMode"
      v-model="currentView"
    />

    <!-- 对比模式视图切换 -->
    <ViewToggle
      v-if="compareMode"
      v-model="compareView"
    />

    <!-- 表格视图（单指标） -->
    <DataTable
      v-if="currentView === 'table' && !compareMode"
      :index-name="indexName"
      :table-data="tableData"
      :loading="loading"
      :is-editable="isEditable"
      @add="openAddDialog"
      @edit="editItem"
      @delete="confirmDelete"
    />

    <!-- 图表视图（单指标） -->
    <ChartView
      v-if="showChart && currentView === 'chart' && !compareMode"
      :index-name="indexName"
      :chart-data="chartData"
      :loading="loading"
      :reference-max="referenceMax"
      :reference-min="referenceMin"
    />

    <!-- 对比表格 -->
    <CompareTable
      v-if="compareMode && compareView === 'table'"
      :indexes="compareIndexes"
      :aligned-data="compareAlignedData"
      :loading="loading"
    />

    <!-- 对比图表 -->
    <CompareChartView
      v-if="compareMode && compareView === 'chart'"
      :indexes="compareIndexes"
      :aligned-data="compareAlignedData"
      :loading="loading"
    />

    <!-- 对比模式保存组合按钮 -->
    <div v-if="compareMode" class="save-group-bar">
      <van-button
        icon="star-o"
        size="small"
        round
        type="primary"
        plain
        @click="showSaveGroupDialog = true"
      >
        保存组合
      </van-button>
    </div>

    <!-- 添加浮动气泡 -->
    <van-floating-bubble
      v-if="!compareMode && isEditable"
      axis="xy"
      icon="plus"
      magnetic="x"
      @click="openAddDialog"
      :gap="isDesktop ? 24 : floatingBubbleGap"
    />

    <!-- 添加/编辑数据表单 -->
    <DataForm
      v-model="showAddDialog"
      :form-data="formData"
      :is-editing="isEditing"
      :reference-max="referenceMax"
      :reference-min="referenceMin"
      :comment-only="!isEditable && isEditing"
      @save="saveData"
    />

    <!-- 删除确认对话框 -->
    <van-dialog
      v-model:show="showDeleteConfirm"
      title="确认删除"
      message="确定要删除这条数据吗？此操作不可恢复。"
      show-cancel-button
      @confirm="deleteData"
    />

    <!-- 保存组合弹窗 -->
    <van-dialog
      v-model:show="showSaveGroupDialog"
      title="保存指标组合"
      show-cancel-button
      :before-close="onSaveGroupClose"
    >
      <div class="save-group-form">
        <van-field
          v-model="groupNameInput"
          label="组合名称"
          placeholder="如：血常规三项"
          maxlength="50"
          show-word-limit
          :rules="[{ required: true, message: '请输入组合名称' }]"
        />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, computed, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast, showFailToast, showNotify } from 'vant'
import { medicalApi } from '@/api/medical'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'
import dayjs from 'dayjs'
// 导入拆分的组件
import BackButton from '@/components/index-detail/BackButton.vue'
const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import ViewToggle from '@/components/index-detail/ViewToggle.vue'
import DataTable from '@/components/index-detail/DataTable.vue'
import ChartView from '@/components/index-detail/ChartView.vue'
import DataForm from '@/components/index-detail/DataForm.vue'
import CompareTable from '@/components/index-detail/CompareTable.vue'
import CompareChartView from '@/components/index-detail/CompareChartView.vue'

const route = useRoute()
const router = useRouter()
const patientStore = usePatientStore()
const { isDesktop, floatingBubbleGap } = useResponsive()

// 日期过滤
const activeDateKey = ref('6m')
const customStart = ref(null)
const customEnd = ref(null)
const customStartDate = ref([])
const customEndDate = ref([])
const showStartPicker = ref(false)
const showEndPicker = ref(false)

const dateOptions = [
  { key: 'all', label: '全部' },
  { key: '1m', label: '1月' },
  { key: '3m', label: '3月' },
  { key: '6m', label: '6月' },
  { key: '1y', label: '1年' },
  { key: 'custom', label: '自定义' },
]

function getDateRange(key) {
  const now = dayjs()
  switch (key) {
    case '1m': return { start: now.subtract(1, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '3m': return { start: now.subtract(3, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '6m': return { start: now.subtract(6, 'month').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case '1y': return { start: now.subtract(1, 'year').format('YYYY-MM-DD'), end: now.format('YYYY-MM-DD') }
    case 'custom': return { start: customStart.value, end: customEnd.value }
    default: return { start: null, end: null }
  }
}

function onDateChange(key) {
  activeDateKey.value = key
  if (key !== 'custom') {
    if (compareMode.value) {
      fetchCompareData()
    } else {
      fetchIndexDetail()
    }
  }
}

function onStartPickerConfirm({ selectedValues }) {
  if (selectedValues?.length === 3) {
    customStart.value = selectedValues.join('-')
  }
  showStartPicker.value = false
}

function onEndPickerConfirm({ selectedValues }) {
  if (selectedValues?.length === 3) {
    customEnd.value = selectedValues.join('-')
  }
  showEndPicker.value = false
}

function applyCustomDate() {
  if (customStart.value && customEnd.value) {
    if (compareMode.value) {
      fetchCompareData()
    } else {
      fetchIndexDetail()
    }
  }
}

// 响应式数据
const loading = ref(false)
const currentView = ref('table')
const tableData = ref([])
const indexName = ref('')
const indexId = ref('')
const showChart = ref(true)
const referenceMax = ref(null)
const referenceMin = ref(null)
const indexUnit = ref('')
const showAddDialog = ref(false)
const showDeleteConfirm = ref(false)
const isEditing = ref(false)
const currentEditIndex = ref(-1)
const isEditable = ref(true)
const formData = ref({
  medical_date: '',
  index_value: '',
  index_unit: '',
  reference_value: '',
  index_status: 'normal',
  comment: ''
})

// 对比模式相关状态
const compareMode = ref(false)
const indexesList = ref([])
const multiIndexData = ref({})

// 新对比模式状态
const compareView = ref('table')
const compareIndexes = ref([])
const compareAlignedData = ref([])
const showSaveGroupDialog = ref(false)
const groupNameInput = ref('')

// 转换数据格式给 ChartView 使用
const chartData = computed(() => {
  return tableData.value.map(item => ({
    date: item.medical_date,
    value: parseFloat(item.index_value) || 0,
    comment: item.comment || ''
  }))
})

// 获取路由参数
onMounted(() => {
  // 检查是否是对比模式
  compareMode.value = route.query.compare_mode === '1'

  // 从路由获取基本参数，is_edit/is_chart 将从后端 API 获取
  indexId.value = route.query.index_id
  indexName.value = route.query.index_name || ''

  if (compareMode.value) {
    try {
      indexesList.value = JSON.parse(route.query.indexes || '[]')
      if (indexesList.value.length > 0) {
        indexId.value = indexesList.value[0].index_id
        indexName.value = indexesList.value[0].index_name || ''
      }
    } catch (e) {
      console.error('解析指标数据失败:', e)
      showFailToast('解析指标数据失败')
    }
  }

  if (compareMode.value) {
    fetchCompareData()
  } else {
    fetchIndexDetail()
  }
})

// 获取指标详情数据
const fetchIndexDetail = async () => {
  if (!indexId.value) {
    showFailToast('缺少指标ID参数')
    return
  }

  try {
    loading.value = true
    const range = getDateRange(activeDateKey.value)
    const params = {}
    if (range.start) params.start_date = range.start
    if (range.end) params.end_date = range.end
    const result = await medicalApi.getIndexHistoryById(indexId.value, params)

    // 从 index_info 设置元信息（is_edit, is_chart, 参考范围等）
    if (result?.index_info) {
      const info = result.index_info
      indexName.value = indexName.value || info.index_name || '未知指标'
      isEditable.value = info.is_edit !== false
      showChart.value = info.is_chart !== false
      referenceMax.value = info.reference_max
      referenceMin.value = info.reference_min
      indexUnit.value = info.index_unit || ''
    }

    // 处理历史数据
    const data = result?.history || result
    if (data && Array.isArray(data)) {
      tableData.value = data.sort((a, b) => new Date(b.medical_date) - new Date(a.medical_date))
    } else {
      tableData.value = []
    }
  } catch (error) {
    console.error('获取指标详情失败:', error)
    showFailToast('网络错误，请稍后重试')
    tableData.value = []
  } finally {
    loading.value = false
  }
}

// 获取多个指标数据（新对比接口）
const fetchCompareData = async () => {
  if (indexesList.value.length === 0) {
    showFailToast('缺少指标参数')
    return
  }

  try {
    loading.value = true
    const range = getDateRange(activeDateKey.value)
    const payload = {
      index_ids: indexesList.value.map(i => i.index_id),
    }
    if (patientStore.currentPatient?.patient_id) {
      payload.patient_id = patientStore.currentPatient.patient_id
    }
    if (range.start) payload.start_date = range.start
    if (range.end) payload.end_date = range.end

    const result = await medicalApi.compareIndices(payload)
    compareIndexes.value = result.indexes || []
    compareAlignedData.value = result.aligned_data || []
  } catch (error) {
    console.error('获取对比数据失败:', error)
    showFailToast('网络错误，请稍后重试')
    compareIndexes.value = []
    compareAlignedData.value = []
  } finally {
    loading.value = false
  }
}

// 保存指标组合
const onSaveGroupClose = (action) => {
  if (action !== 'confirm') {
    groupNameInput.value = ''
    return true
  }

  const name = groupNameInput.value?.trim()
  if (!name) {
    showFailToast('请输入组合名称')
    return false
  }

  return medicalApi.createIndexGroup({
    patient_id: patientStore.currentPatient?.patient_id,
    group_name: name,
    index_ids: indexesList.value.map(i => i.index_id),
  }).then(() => {
    showSuccessToast('组合保存成功')
    groupNameInput.value = ''
    return true
  }).catch((error) => {
    if (error?.response?.status === 409) {
      showFailToast('组合名称已存在')
    } else {
      showFailToast('保存失败')
    }
    return false
  })
}

// 监听视图切换
watch(currentView, (newView) => {
  if (newView === 'chart' && tableData.value.length > 0) {
    nextTick(() => {})
  }
})

// 对比模式默认显示表格
watch(compareMode, (newVal) => {
  if (newVal) {
    compareView.value = 'table'
  }
})

// 打开添加对话框
const openAddDialog = () => {
  isEditing.value = false
  currentEditIndex.value = -1
  formData.value = {
    medical_date: '',
    index_value: '',
    index_unit: indexUnit.value,
    reference_value: referenceMin.value && referenceMax.value 
      ? `${referenceMin.value}-${referenceMax.value}` 
      : '',
    index_status: 'normal',
    comment: ''
  }
  showAddDialog.value = true
}

// 编辑项目
const editItem = (item, index) => {
  isEditing.value = true
  currentEditIndex.value = index
  formData.value = {
    medical_id: item.medical_id,
    medical_date: item.medical_date,
    index_value: item.index_value,
    index_unit: item.index_unit || '',
    reference_value: item.reference_value || '',
    index_status: item.index_status || 'normal',
    comment: item.comment || ''
  }
  showAddDialog.value = true
}

// 确认删除
const confirmDelete = (item, index) => {
  currentEditIndex.value = index
  showDeleteConfirm.value = true
}

// 删除数据
const deleteData = async () => {
  if (currentEditIndex.value >= 0 && currentEditIndex.value < tableData.value.length) {
    try {
      const item = tableData.value[currentEditIndex.value]
      if (!item.medical_detail_id && !item.medical_id) {
        showNotify({ type: 'danger', message: '缺少记录ID，无法删除' })
        return
      }
      
      await medicalApi.deleteMedicalCheckDetail(item.medical_detail_id || item.medical_id)
      
      tableData.value.splice(currentEditIndex.value, 1)
      showSuccessToast('删除成功')
    } catch (error) {
      console.error('删除数据失败:', error)
      showNotify({ type: 'danger', message: '删除失败，请稍后重试' })
    }
  }
}

// 保存数据
const saveData = async (data) => {
  try {
    if (isEditing.value && currentEditIndex.value >= 0) {
      if (!isEditable.value) {
        if (data.medical_id) {
          await medicalApi.updateMedicalCheckComment(data.medical_id, { comment: data.comment })
          tableData.value[currentEditIndex.value].comment = data.comment
          showSuccessToast('备注更新成功')
        } else {
          showNotify({ type: 'danger', message: '缺少医疗检查ID，无法更新备注' })
          return
        }
      } else {
        tableData.value[currentEditIndex.value] = {
          ...tableData.value[currentEditIndex.value],
          ...data
        }
        showSuccessToast('更新成功')
      }
    } else if (isEditable.value) {
      try {
        const patient = patientStore.currentPatient
        const apiData = {
          index_id: indexId.value || undefined,
          index_name: indexName.value,
          index_unit: indexUnit.value,
          hospital: '居家测量',
          patient_id: patient?.patient_id,
          ...data
        }
        
        const response = await medicalApi.addMedicalCheckDetail(apiData)
        
        if (response && response.status === 'success') {
          tableData.value.push({
            ...data,
            medical_id: response.data?.medical_id,
            medical_detail_id: response.data?.medical_detail_id
          })
          showSuccessToast('添加成功')
        } else {
          showNotify({ type: 'danger', message: response?.message || '添加失败' })
          return
        }
      } catch (error) {
        console.error('添加数据失败:', error)
        showNotify({ type: 'danger', message: '添加失败，请稍后重试' })
        return
      }
    }

    showAddDialog.value = false
    resetForm()
    tableData.value.sort((a, b) => new Date(b.medical_date) - new Date(a.medical_date))
  } catch (error) {
    console.error('保存数据失败:', error)
    showNotify({ type: 'danger', message: '保存失败，请稍后重试' })
  }
}

// 重置表单
const resetForm = () => {
  formData.value = {
    medical_date: '',
    index_value: '',
    index_unit: '',
    reference_value: '',
    index_status: 'normal',
    comment: ''
  }
  isEditing.value = false
  currentEditIndex.value = -1
}
</script>

<style scoped>
.index-detail-container {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 20px;
  padding-bottom: calc(var(--safe-bottom) + 20px);
  position: relative;
  /* 不使用 overflow-x:hidden，避免裁剪下拉面板内容 */
}

/* 日期过滤 */
.date-filter-section {
  margin-bottom: 12px;
}

.date-chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 0;
}

.date-chip {
  flex-shrink: 0;
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--primary-alpha-15);
}

.date-chip.active {
  background: var(--primary-color);
  color: var(--color-white);
  border-color: var(--primary-color);
}

.custom-date-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.date-field {
  padding: 4px 10px;
  border-radius: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--primary-alpha-15);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.date-field:hover {
  border-color: var(--primary-alpha-30);
}

.date-separator {
  color: var(--text-tertiary);
  font-size: 13px;
}

.apply-btn {
  padding: 4px 12px;
  border-radius: 12px;
  background: var(--primary-color);
  color: var(--color-white);
  font-size: 12px;
  cursor: pointer;
}

@media (max-width: 768px) {
  .index-detail-container {
    padding: 10px;
    padding-bottom: calc(var(--safe-bottom) + 10px);
  }
}

@media (max-width: 480px) {
  .index-detail-container {
    padding: 8px;
    padding-bottom: calc(var(--safe-bottom) + 8px);
  }
}

@media (min-width: 768px) {
  .index-detail-container {
    padding: var(--space-6);
    padding-bottom: var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
  }
}

.save-group-bar {
  display: flex;
  justify-content: center;
  margin: 16px 0;
}

.save-group-form {
  padding: 16px;
}
</style>
