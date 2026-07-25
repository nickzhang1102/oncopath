<template>
  <div class="medication-view">
    <BackgroundAnimation />
    <BackButton v-if="!isDesktop" title="用药记录" />

    <!-- Tab 切换 -->
    <div class="tab-section">
      <van-tabs v-model:active="activeTab" animated sticky>
        <van-tab title="用药记录" name="list" />
        <van-tab title="今日服药" name="today" />
        <van-tab title="依从性" name="adherence" />
      </van-tabs>
    </div>

    <!-- ===== 用药记录 ===== -->
    <template v-if="activeTab === 'list'">
      <header v-if="isDesktop" class="desktop-header">
        <div class="header-content">
          <h1 class="page-title">用药记录</h1>
          <div class="header-actions">
            <van-dropdown-menu>
              <van-dropdown-item v-model="filterStatus" :options="statusOptions" @change="loadMedications" />
            </van-dropdown-menu>
            <van-button type="primary" icon="plus" @click="openAddForm">添加用药</van-button>
          </div>
        </div>
      </header>

      <div v-if="!isDesktop" class="filter-section">
        <van-dropdown-menu z-index="2000">
          <van-dropdown-item v-model="filterStatus" :options="statusOptions" @change="loadMedications" />
        </van-dropdown-menu>
      </div>

      <van-loading v-if="loading" class="loading-center" />

      <div v-else-if="!hasPatient" class="empty-patient">
        <van-empty description="请先选择患者" image="search">
          <van-button type="primary" class="bottom-button" @click="router.push('/home/patient-management')">选择患者</van-button>
        </van-empty>
      </div>

      <div v-else-if="medications.length === 0" class="empty-state">
        <div class="empty-icon"><van-icon name="gem-o" /></div>
        <div class="empty-text">暂无用药记录</div>
        <div class="empty-hint">点击右下角按钮添加</div>
      </div>

      <div v-else class="medication-list">
        <div v-for="(group, month) in groupedMedications" :key="month" class="month-group">
          <div class="month-header">{{ formatMonth(month) }}</div>
          <div v-for="med in group" :key="med.id" class="medication-item" @click="viewMedication(med)">
            <div class="item-icon"><van-icon :name="med.is_ongoing ? 'gem-o' : 'passed'" /></div>
            <div class="item-content">
              <div class="item-header">
                <span class="item-title">{{ med.medication_name }}</span>
                <div class="item-tags">
                  <span v-if="med.category" class="category-tag">{{ categoryLabelFor(med.category) }}</span>
                  <van-tag :type="statusTagType(med.status)" size="small">{{ statusLabel(med.status) }}</van-tag>
                </div>
              </div>
              <div v-if="med.dosage || med.frequency" class="item-dosage">{{ [med.dosage, med.frequency].filter(Boolean).join(' · ') }}</div>
              <div class="item-date">
                {{ formatDate(med.start_date) }}
                <template v-if="med.end_date"> ~ {{ formatDate(med.end_date) }}</template>
                <template v-else> ~ 至今</template>
              </div>
              <div v-if="med.route" class="item-route"><van-icon name="guide-o" /> {{ med.route }}</div>
            </div>
            <van-icon name="arrow" class="item-arrow" />
          </div>
        </div>
      </div>

      <van-floating-bubble v-if="!isDesktop" axis="xy" icon="plus" @click="openAddForm" :gap="floatingBubbleGap" />

      <!-- 用药概要 -->
      <SummarySection title="用药概要" summary-type="medication_record" />
    </template>

    <!-- ===== 今日服药 ===== -->
    <template v-if="activeTab === 'today'">
      <div v-if="!hasPatient" class="empty-patient">
        <van-empty description="请先选择患者" image="search" />
      </div>

      <van-loading v-else-if="todayLoading" class="loading-center" />

      <div v-else-if="todayTasks.length === 0" class="empty-state">
        <div class="empty-icon"><van-icon name="gem-o" /></div>
        <div class="empty-text">今日无需服药</div>
        <div class="empty-hint">请先添加用药记录</div>
      </div>

      <div v-else class="today-tasks">
        <div class="today-summary">
          <span>共 {{ todayTasks.length }} 种药物</span>
          <span class="summary-done">已打卡 {{ todayTakenCount }}</span>
        </div>

        <div v-for="task in todayTasks" :key="task.medication_id" class="task-item">
          <div class="task-content">
            <div class="task-name">{{ task.medication_name }}</div>
            <div v-if="task.dosage || task.frequency" class="task-dosage">
              {{ [task.dosage, task.frequency].filter(Boolean).join(' · ') }}
            </div>
          </div>
          <div class="task-actions">
            <template v-if="task.slots.length <= 1">
              <!-- 每日一次：兼容旧逻辑 -->
              <van-button v-if="task.slots[0]?.logged && task.slots[0]?.status === 'taken'" size="small" type="success" plain icon="success" disabled>
                已服药
              </van-button>
              <van-button v-else-if="task.slots[0]?.logged && task.slots[0]?.status === 'skipped'" size="small" type="warning" plain icon="cross" @click="handleLog(task, 'taken', task.slots[0]?.time_slot)">
                跳过(改已服)
              </van-button>
              <div v-else class="task-btns">
                <van-button size="small" type="primary" @click="handleLog(task, 'taken', task.slots[0]?.time_slot)">已服药</van-button>
                <van-button size="small" plain @click="handleLog(task, 'skipped', task.slots[0]?.time_slot)">跳过</van-button>
              </div>
            </template>
            <template v-else>
              <!-- 每日多次：按 time_slot 展开 -->
              <div class="slot-btns">
                <van-button
                  v-for="slot in task.slots"
                  :key="slot.time_slot"
                  size="small"
                  :type="slot.status === 'taken' ? 'success' : slot.status === 'skipped' ? 'warning' : 'primary'"
                  :plain="slot.logged"
                  :disabled="slot.status === 'taken'"
                  @click="slot.status !== 'taken' && handleLog(task, slot.logged ? 'taken' : 'taken', slot.time_slot)"
                >
                  {{ slotLabel(slot) }}
                </van-button>
              </div>
            </template>
          </div>
        </div>
      </div>
    </template>

    <!-- ===== 依从性 ===== -->
    <template v-if="activeTab === 'adherence'">
      <div v-if="!hasPatient" class="empty-patient">
        <van-empty description="请先选择患者" image="search" />
      </div>

      <van-loading v-else-if="adherenceLoading" class="loading-center" />

      <div v-else-if="adherenceStats.length === 0" class="empty-state">
        <div class="empty-icon"><van-icon name="chart-trending-o" /></div>
        <div class="empty-text">暂无依从性数据</div>
        <div class="empty-hint">添加用药记录后开始统计</div>
      </div>

      <div v-else class="adherence-view">
        <div class="adherence-period">
          <van-dropdown-menu>
            <van-dropdown-item v-model="adherenceDays" :options="adherencePeriodOptions" @change="loadAdherence" />
          </van-dropdown-menu>
        </div>

        <div v-for="stat in adherenceStats" :key="stat.medication_id" class="adherence-card">
          <div class="adherence-header">
            <span class="adherence-name">{{ stat.medication_name }}</span>
            <span :class="['adherence-rate', stat.adherence_rate >= 80 ? 'rate-good' : stat.adherence_rate >= 50 ? 'rate-warn' : 'rate-bad']">
              {{ stat.adherence_rate }}%
            </span>
          </div>
          <van-progress :percentage="stat.adherence_rate" :color="stat.adherence_rate >= 80 ? '#4caf50' : stat.adherence_rate >= 50 ? '#ff9800' : '#f44336'" stroke-width="8" :show-pivot="false" />
          <div class="adherence-detail">
            <span>应服 {{ stat.total_slots }} 次</span>
            <span class="detail-taken">实服 {{ stat.taken_slots }}</span>
            <span class="detail-skipped">跳过 {{ stat.skipped_slots }}</span>
            <span class="detail-missed">漏服 {{ stat.missed_slots }}</span>
            <span class="detail-unrecorded">未打卡 {{ stat.unrecorded_slots }}</span>
          </div>
          <!-- 记录率 -->
          <div class="recording-section">
            <div class="recording-label">
              <span>记录率</span>
              <span :class="['recording-value', stat.recording_rate < 50 ? 'rate-bad' : '']">{{ stat.recording_rate }}%</span>
            </div>
            <van-progress :percentage="stat.recording_rate" :color="stat.recording_rate >= 80 ? '#4caf50' : stat.recording_rate >= 50 ? '#ff9800' : '#f44336'" stroke-width="4" :show-pivot="false" />
            <div v-if="stat.recording_rate < 50" class="recording-warning">记录不足，数据参考性低</div>
          </div>
        </div>
      </div>
    </template>

    <!-- 添加/编辑弹窗 -->
    <van-popup v-model:show="showForm" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-lg' : ''" :style="!isDesktop ? { height: '90%' } : ''">
      <div class="form-popup">
        <van-nav-bar :title="editingId ? '编辑用药记录' : '添加用药记录'" :left-text="!isDesktop ? '取消' : ''" @click-left="closeForm">
          <template v-if="!isDesktop" #right><van-button type="primary" size="small" :loading="saving" @click="saveMedication">保存</van-button></template>
        </van-nav-bar>
        <div class="form-content">
          <van-form>
            <van-cell-group inset>
              <van-field v-model="form.medication_name" label="药品名称" placeholder="如：阿莫西林" required />
              <van-field v-model="form.generic_name" label="通用名" placeholder="如：阿莫西林胶囊" />
              <van-field v-model="categoryLabel" label="分类" placeholder="选择药品分类" readonly clickable @click="showCategoryPicker = true" />
              <van-field v-model="form.dosage" label="剂量" placeholder="如：5mg" />
              <van-field v-model="form.frequency" label="用药频率" placeholder="如：每日2次" />
              <van-field v-model="form.route" label="给药途径" placeholder="如：口服/静脉" readonly clickable @click="showRoutePicker = true" />
              <van-field v-model="form.duration" label="用药时长" placeholder="如：14天" />
              <van-field v-model="form.start_date" label="开始日期" placeholder="点击选择" readonly clickable required @click="openDatePicker('start')" />
              <van-field v-model="form.end_date" label="结束日期" placeholder="持续用药可不填" readonly clickable @click="openDatePicker('end')" />
              <van-field v-model="form.prescriber" label="开药医生" placeholder="医生姓名" />
              <van-field v-model="form.hospital" label="开药医院" placeholder="医院名称" />
              <van-field v-model="form.notes" type="textarea" label="备注" placeholder="备注信息" rows="2" />
              <van-field v-model="form.side_effects" type="textarea" label="副作用" placeholder="副作用记录" rows="2" />
            </van-cell-group>
          </van-form>
        </div>

        <!-- 桌面端底部按钮 -->
        <div v-if="isDesktop" class="form-footer">
          <van-button @click="closeForm">取消</van-button>
          <van-button type="primary" :loading="saving" @click="saveMedication">保存</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 日期选择器 -->
    <van-popup v-model:show="showDatePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker v-model="selectedDate" title="选择日期" @confirm="onDateConfirm" @cancel="showDatePicker = false" />
    </van-popup>

    <!-- 给药途径选择器 -->
    <van-popup v-model:show="showRoutePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-picker :columns="routeOptions" @confirm="onRouteConfirm" @cancel="showRoutePicker = false" />
    </van-popup>

    <!-- 分类选择器 -->
    <van-popup v-model:show="showCategoryPicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-picker :columns="categoryOptions" @confirm="onCategoryConfirm" @cancel="showCategoryPicker = false" />
    </van-popup>

    <!-- 详情弹窗 -->
    <van-popup v-model:show="showDetail" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-lg' : ''" :style="!isDesktop ? { height: '70%' } : ''">
      <div class="detail-popup" v-if="currentMed">
        <van-nav-bar title="用药详情" left-text="关闭" @click-left="showDetail = false">
          <template #right><van-button type="primary" size="small" @click="editMedication(currentMed)">编辑</van-button></template>
        </van-nav-bar>
        <div class="detail-content">
          <div class="detail-header">
            <div class="detail-name">{{ currentMed.medication_name }}</div>
            <van-tag :type="statusTagType(currentMed.status)" size="medium">{{ statusLabel(currentMed.status) }}</van-tag>
          </div>
          <van-cell-group inset>
            <van-cell v-if="currentMed.generic_name" title="通用名" :value="currentMed.generic_name" />
            <van-cell v-if="currentMed.category" title="分类" :value="categoryLabelFor(currentMed.category)" />
            <van-cell v-if="currentMed.dosage" title="剂量" :value="currentMed.dosage" />
            <van-cell v-if="currentMed.frequency" title="频率" :value="currentMed.frequency" />
            <van-cell v-if="currentMed.route" title="给药途径" :value="currentMed.route" />
            <van-cell v-if="currentMed.duration" title="用药时长" :value="currentMed.duration" />
            <van-cell title="开始日期" :value="formatDate(currentMed.start_date)" />
            <van-cell v-if="currentMed.end_date" title="结束日期" :value="formatDate(currentMed.end_date)" />
            <van-cell v-if="currentMed.prescriber" title="开药医生" :value="currentMed.prescriber" />
            <van-cell v-if="currentMed.hospital" title="开药医院" :value="currentMed.hospital" />
            <van-cell v-if="currentMed.notes" title="备注" :value="currentMed.notes" />
            <van-cell v-if="currentMed.side_effects" title="副作用" :value="currentMed.side_effects" />
          </van-cell-group>
          <div v-if="currentMed.status === 'active'" class="detail-actions">
            <van-button type="warning" size="small" block @click="handleDiscontinue">停药</van-button>
          </div>
        </div>
      </div>
    </van-popup>

    <!-- 停药确认 -->
    <van-dialog v-model:show="showDiscontinueDialog" title="确认停药" show-cancel-button @confirm="confirmDiscontinue">
      <div style="padding: 16px;"><van-field v-model="discontinueReason" label="停药原因" placeholder="选填" /></div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import { medicationApi, medicationLogApi } from '@/api/medication'
import { showToast, showConfirmDialog } from 'vant'
import { useResponsive } from '@/composables/useResponsive'
import dayjs from 'dayjs'

const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'
import SummarySection from '@/components/common/SummarySection.vue'

const { isDesktop, floatingBubbleGap } = useResponsive()
const router = useRouter()
const patientStore = usePatientStore()

// Tab
const activeTab = ref('list')

// 状态
const loading = ref(false)
const saving = ref(false)
const showForm = ref(false)
const showDetail = ref(false)
const showDatePicker = ref(false)
const showRoutePicker = ref(false)
const showCategoryPicker = ref(false)
const showDiscontinueDialog = ref(false)
const editingId = ref(null)
const currentMed = ref(null)
const filterStatus = ref('all')
const discontinueReason = ref('')
const dateField = ref('start')
const selectedDate = ref(['2024', '01', '01'])

const hasPatient = computed(() => !!patientStore.currentPatient)

// ===== 今日服药 =====
const todayLoading = ref(false)
const todayTasks = ref([])

async function loadTodayTasks() {
  if (!patientStore.currentPatient) return
  todayLoading.value = true
  try {
    todayTasks.value = await medicationLogApi.getTodayTasks(patientStore.currentPatient.patient_id)
  } catch (e) {
    console.error('加载今日任务失败:', e)
  } finally {
    todayLoading.value = false
  }
}

const SLOT_LABELS = { morning: '早', afternoon: '午', evening: '晚', bedtime: '睡前' }

const todayTakenCount = computed(() =>
  todayTasks.value.reduce((sum, t) => sum + t.slots.filter(s => s.logged && s.status === 'taken').length, 0)
)

function slotLabel(slot) {
  const label = SLOT_LABELS[slot.time_slot] || slot.time_slot || '服药'
  if (slot.status === 'taken') return `${label}✓`
  if (slot.status === 'skipped') return `${label}跳`
  return label
}

async function handleLog(task, status, timeSlot) {
  try {
    const payload = {
      medication_id: task.medication_id,
      scheduled_date: dayjs().format('YYYY-MM-DD'),
      status
    }
    if (timeSlot) payload.time_slot = timeSlot
    await medicationLogApi.createLog(payload)
    showToast(status === 'taken' ? '已记录服药' : '已标记跳过')
    await loadTodayTasks()
  } catch (e) {
    console.error('打卡失败:', e)
    showToast('操作失败')
  }
}

// ===== 依从性 =====
const adherenceLoading = ref(false)
const adherenceStats = ref([])
const adherenceDays = ref(30)
const adherencePeriodOptions = [
  { text: '7天', value: 7 },
  { text: '30天', value: 30 },
  { text: '90天', value: 90 },
  { text: '180天', value: 180 },
  { text: '365天', value: 365 },
]

async function loadAdherence() {
  if (!patientStore.currentPatient) return
  adherenceLoading.value = true
  try {
    adherenceStats.value = await medicationLogApi.getAdherenceStats(patientStore.currentPatient.patient_id, adherenceDays.value)
  } catch (e) {
    console.error('加载依从性失败:', e)
  } finally {
    adherenceLoading.value = false
  }
}

// ===== 用药记录 =====
const statusOptions = [
  { text: '全部', value: 'all' },
  { text: '用药中', value: 'active' },
  { text: '已停药', value: 'discontinued' },
  { text: '已完成', value: 'completed' }
]

const routeOptions = ['口服', '静脉注射', '静脉滴注', '肌肉注射', '皮下注射', '外用', '吸入', '舌下含服', '直肠给药', '其他']
const categoryOptions = ['化疗', '靶向', '免疫', '支持', '止痛', '其他']
const categoryMap = { chemotherapy: '化疗', targeted: '靶向', immunotherapy: '免疫', supportive: '支持', analgesic: '止痛', other: '其他' }

function categoryLabelFor(val) { return categoryMap[val] || val || '' }
const categoryLabel = computed({ get: () => categoryLabelFor(form.value.category), set: () => {} })

const form = ref(getEmptyForm())
function getEmptyForm() {
  return { medication_name: '', generic_name: '', category: '', dosage: '', frequency: '', route: '', duration: '', start_date: '', end_date: '', prescriber: '', hospital: '', notes: '', side_effects: '' }
}

const medications = ref([])
const groupedMedications = computed(() => {
  const groups = {}
  const sorted = [...medications.value].sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
  sorted.forEach(med => {
    const month = med.start_date.substring(0, 7)
    if (!groups[month]) groups[month] = []
    groups[month].push(med)
  })
  return groups
})

function statusLabel(s) { return { active: '用药中', discontinued: '已停药', completed: '已完成' }[s] || s }
function statusTagType(s) { return { active: 'primary', discontinued: 'warning', completed: 'success' }[s] || 'default' }
function formatDate(d) { return dayjs(d).format('YYYY-MM-DD') }
function formatMonth(m) { const [year, mon] = m.split('-'); return `${year}年${parseInt(mon)}月` }

async function loadMedications() {
  if (!patientStore.currentPatient) return
  loading.value = true
  try {
    const params = { patient_id: patientStore.currentPatient.patient_id }
    if (filterStatus.value !== 'all') params.status = filterStatus.value
    const data = await medicationApi.listMedications(params)
    medications.value = data.items || []
  } catch (e) {
    console.error('加载用药记录失败:', e)
  } finally {
    loading.value = false
  }
}

function viewMedication(med) { currentMed.value = med; showDetail.value = true }

function editMedication(med) {
  editingId.value = med.id
  form.value = { medication_name: med.medication_name || '', generic_name: med.generic_name || '', category: med.category || '', dosage: med.dosage || '', frequency: med.frequency || '', route: med.route || '', duration: med.duration || '', start_date: med.start_date || '', end_date: med.end_date || '', prescriber: med.prescriber || '', hospital: med.hospital || '', notes: med.notes || '', side_effects: med.side_effects || '' }
  showDetail.value = false
  showForm.value = true
}

function openAddForm() { editingId.value = null; form.value = getEmptyForm(); showForm.value = true }
function closeForm() { showForm.value = false; editingId.value = null; form.value = getEmptyForm() }

function openDatePicker(field) {
  dateField.value = field
  const dateStr = form.value[`${field}_date`] || form.value.start_date || dayjs().format('YYYY-MM-DD')
  const [y, m, d] = dateStr.split('-')
  selectedDate.value = [y || '2024', m || '01', d || '01']
  showDatePicker.value = true
}
function onDateConfirm({ selectedValues }) { form.value[`${dateField.value}_date`] = selectedValues.join('-'); showDatePicker.value = false }
function onRouteConfirm({ selectedOptions }) { form.value.route = selectedOptions[0]?.text || selectedOptions[0]; showRoutePicker.value = false }
function onCategoryConfirm({ selectedOptions }) {
  const text = selectedOptions[0]?.text || selectedOptions[0]
  form.value.category = Object.entries(categoryMap).find(([, v]) => v === text)?.[0] || text
  showCategoryPicker.value = false
}

async function saveMedication() {
  if (!form.value.medication_name || !form.value.start_date) { showToast('请填写药品名称和开始日期'); return }
  saving.value = true
  try {
    const data = { patient_id: patientStore.currentPatient.patient_id, ...form.value, is_ongoing: !form.value.end_date }
    if (editingId.value) { await medicationApi.updateMedication(editingId.value, data); showToast('更新成功') }
    else { await medicationApi.createMedication(data); showToast('添加成功') }
    closeForm()
    await loadMedications()
  } catch (e) { console.error('保存失败:', e); showToast('保存失败') }
  finally { saving.value = false }
}

function handleDiscontinue() { discontinueReason.value = ''; showDiscontinueDialog.value = true }
async function confirmDiscontinue() {
  if (!currentMed.value) return
  try {
    await medicationApi.discontinueMedication(currentMed.value.id, { reason: discontinueReason.value || undefined })
    showToast('已停药'); showDetail.value = false; await loadMedications()
  } catch (e) { console.error('停药操作失败:', e); showToast('操作失败') }
}

// Tab 切换时加载数据
watch(activeTab, (tab) => {
  if (tab === 'today') loadTodayTasks()
  else if (tab === 'adherence') loadAdherence()
})

onMounted(() => loadMedications())
watch(() => patientStore.currentPatient?.patient_id, (newId, oldId) => {
  if (newId && newId !== oldId) {
    loadMedications()
    if (activeTab.value === 'today') loadTodayTasks()
    if (activeTab.value === 'adherence') loadAdherence()
  }
})
</script>

<style scoped>
.medication-view { min-height: 100vh; background: var(--bg-primary); position: relative; padding-bottom: var(--safe-bottom); }
.tab-section { background: var(--bg-surface); margin: 0 16px; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px var(--primary-alpha-8); margin-top: 8px; }
.tab-section :deep(.van-tabs__wrap) { height: 44px; }
.filter-section { background: var(--bg-surface); margin: 16px; border-radius: 12px; box-shadow: 0 2px 8px var(--primary-alpha-8); }
.filter-section :deep(.van-dropdown-menu__bar) { border-radius: 12px; }
.loading-center { display: flex; justify-content: center; padding: 60px; }
.empty-patient { display: flex; align-items: center; justify-content: center; min-height: 60vh; }
.bottom-button { min-width: 160px; padding: 12px 24px; }
.empty-state { text-align: center; padding: 60px 20px; }
.empty-icon { font-size: 48px; margin-bottom: 16px; display: flex; align-items: center; justify-content: center; }
.empty-icon .van-icon { font-size: 48px; }
.empty-text { font-size: 18px; color: var(--primary-color); font-weight: 500; margin-bottom: 8px; }
.empty-hint { font-size: 14px; color: var(--text-secondary); }

/* 用药记录列表 */
.medication-list { padding: 0 16px; }
.month-group { margin-bottom: 16px; }
.month-header { font-size: 14px; font-weight: 600; color: var(--primary-color); padding: 8px 4px; margin-bottom: 8px; border-left: 3px solid var(--primary-color); padding-left: 8px; }
.medication-item { display: flex; align-items: flex-start; background: var(--bg-surface); padding: 16px; border-radius: 12px; margin-bottom: 8px; box-shadow: 0 2px 8px var(--primary-alpha-8); cursor: pointer; transition: all 0.2s; }
.medication-item:hover { transform: translateY(-2px); box-shadow: 0 4px 12px var(--primary-alpha-12); }
.item-icon { font-size: 24px; margin-right: 12px; flex-shrink: 0; }
.item-content { flex: 1; min-width: 0; }
.item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.item-tags { display: flex; gap: 4px; align-items: center; }
.category-tag {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 0 6px;
  border-radius: 4px;
  line-height: 1.8;
  margin-right: 2px;
}
.item-title { font-size: 15px; font-weight: 500; color: var(--text-primary); }
.item-dosage { font-size: 13px; color: var(--text-secondary); margin-bottom: 2px; }
.item-date { font-size: 12px; color: var(--text-secondary); }
.item-route { font-size: 12px; color: var(--primary-color); display: flex; align-items: center; gap: 4px; margin-top: 4px; }
.item-arrow { color: var(--text-tertiary); flex-shrink: 0; }

/* 今日服药 */
.today-tasks { padding: 16px; }
.today-summary { display: flex; justify-content: space-between; padding: 8px 4px; font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; }
.summary-done { color: var(--primary-color); font-weight: 500; }
.task-item { display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface); padding: 16px; border-radius: 12px; margin-bottom: 8px; box-shadow: 0 2px 8px var(--primary-alpha-8); }
.task-content { flex: 1; min-width: 0; }
.task-name { font-size: 15px; font-weight: 500; color: var(--text-primary); }
.task-dosage { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }
.task-actions { margin-left: 12px; flex-shrink: 0; }
.task-btns { display: flex; gap: 8px; }
.slot-btns { display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }

/* 依从性 */
.adherence-view { padding: 16px; }
.adherence-period { margin-bottom: 16px; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px var(--primary-alpha-8); }
.adherence-card { background: var(--bg-surface); padding: 16px; border-radius: 12px; margin-bottom: 12px; box-shadow: 0 2px 8px var(--primary-alpha-8); }
.adherence-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.adherence-name { font-size: 15px; font-weight: 500; color: var(--text-primary); }
.adherence-rate { font-size: 20px; font-weight: 700; }
.rate-good { color: #4caf50; }
.rate-warn { color: #ff9800; }
.rate-bad { color: #f44336; }
.adherence-detail { display: flex; gap: 12px; margin-top: 8px; font-size: 12px; color: var(--text-secondary); flex-wrap: wrap; }
.detail-taken { color: #4caf50; }
.detail-skipped { color: #ff9800; }
.detail-missed { color: #f44336; }
.detail-unrecorded { color: #9e9e9e; }
.recording-section { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-color); }
.recording-label { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }
.recording-value { font-weight: 500; }
.recording-warning { font-size: 11px; color: #f44336; margin-top: 4px; }

/* 表单弹窗 */
.form-popup { height: 100%; display: flex; flex-direction: column; background: var(--bg-elevated); }
.form-content { flex: 1; overflow-y: auto; padding: 16px; }

/* 桌面端表单底部按钮 */
.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-elevated);
}
.detail-popup { height: 100%; display: flex; flex-direction: column; background: var(--bg-elevated); }
.detail-content { flex: 1; overflow-y: auto; padding: 16px; }
.detail-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; padding: 0 4px; }
.detail-name { font-size: 20px; font-weight: 600; color: var(--text-primary); }
.detail-actions { margin-top: 16px; padding: 0 16px; }
:deep(.van-floating-bubble) { background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%); box-shadow: 0 4px 12px var(--primary-alpha-40); }
.desktop-header { margin-bottom: var(--space-4); }
.desktop-header .header-content { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) var(--space-4); background: var(--bg-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }
.desktop-header .page-title { font-size: var(--text-xl); font-weight: 600; color: var(--text-primary); margin: 0; }
.desktop-header .header-actions { display: flex; align-items: center; gap: var(--space-3); }

@media (min-width: 768px) {
  .medication-view { padding: var(--space-6); padding-bottom: var(--space-6); max-width: 1000px; margin: 0 auto; }
}
</style>