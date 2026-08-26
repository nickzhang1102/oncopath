<template>
  <div class="treatment-view">
    <!-- 动态背景 -->
    <BackgroundAnimation />

    <!-- 统一页面抬头 -->
    <BackButton title="治疗记录">
      <template #right>
        <van-button size="small" type="primary" icon="plus" @click="showAddForm = true">添加记录</van-button>
      </template>
    </BackButton>

    <!-- 筛选器 -->
    <div class="filter-section">
      <van-dropdown-menu z-index="2000">
        <van-dropdown-item v-model="filterType" :options="filterOptions" @change="loadTreatments" />
      </van-dropdown-menu>
    </div>

    <!-- 加载状态 -->
    <van-loading v-if="loading" class="loading-center" />

    <!-- 未选择患者时的空状态 -->
    <div v-else-if="!hasPatient" class="empty-patient">
      <van-empty description="请先选择患者" image="search">
        <van-button type="primary" class="bottom-button" @click="router.push('/home/patient-management')">
          选择患者
        </van-button>
      </van-empty>
    </div>

    <!-- 空状态 -->
    <div v-else-if="treatments.length === 0" class="empty-state">
      <div class="empty-icon"><van-icon name="gem-o" /></div>
      <div class="empty-text">暂无治疗记录</div>
      <div class="empty-hint">点击右下角按钮添加</div>
    </div>

    <!-- 治疗记录列表 -->
    <div v-else class="treatment-list">
      <!-- 按月份分组 -->
      <div v-for="(group, month) in groupedTreatments" :key="month" class="month-group">
        <div class="month-header">{{ formatMonth(month) }}</div>
        
        <div
          v-for="item in group"
          :key="item.event_id"
          class="treatment-item"
          @click="viewTreatment(item)"
        >
          <div class="item-icon"><van-icon :name="getTreatmentIcon(item.category)" /></div>
          <div class="item-content">
            <div class="item-header">
              <span class="item-title">{{ item.title }}</span>
              <span class="item-date">{{ formatDate(item.event_date) }}</span>
            </div>
            <div v-if="item.description" class="item-desc">{{ item.description }}</div>
            <div v-if="item.medical_details?.hospital" class="item-hospital">
              <van-icon name="location-o" />
              {{ item.medical_details.hospital }}
            </div>
            <div v-if="item.medical_details?.memo_items?.length" class="item-memo-count">
              <van-icon name="notes-o" />
              {{ item.medical_details.memo_items.length }} 条记录
            </div>
          </div>
          <van-icon name="arrow" class="item-arrow" />
        </div>
      </div>
    </div>

    <!-- 移动端浮动添加按钮 -->
    <van-floating-bubble
      v-if="!isDesktop"
      axis="xy"
      icon="plus"
      @click="showAddForm = true"
      :gap="floatingBubbleGap"
    />

    <!-- 治疗概要 -->
    <SummarySection title="治疗概要" summary-type="treatment" />

    <!-- 添加/编辑治疗记录弹窗 -->
    <van-popup
      v-model:show="showAddForm"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-lg' : ''"
      :style="!isDesktop ? { height: '90%' } : ''"
    >
      <div class="form-popup">
        <van-nav-bar
          :title="editingTreatment ? '编辑治疗记录' : '添加治疗记录'"
          :left-text="!isDesktop ? '取消' : ''"
          @click-left="closeForm"
        >
          <template v-if="!isDesktop" #right>
            <van-button type="primary" size="small" :loading="saving" @click="saveTreatment">
              保存
            </van-button>
          </template>
        </van-nav-bar>

        <div class="form-content">
          <van-form>
            <!-- 治疗类型 -->
            <van-cell-group inset>
              <van-field name="treatmentType" label="治疗类型" required>
                <template #input>
                  <div class="type-grid">
                    <div
                      v-for="type in treatmentTypes"
                      :key="type.value"
                      class="type-item"
                      :class="{ active: form.category === type.value }"
                      @click="form.category = type.value"
                    >
                      <span class="type-icon"><van-icon :name="type.icon" /></span>
                      <span class="type-name">{{ type.label }}</span>
                    </div>
                  </div>
                </template>
              </van-field>

              <van-field
                v-model="form.title"
                label="治疗名称"
                placeholder="如：第3周期化疗"
                required
              />

              <van-field
                v-model="form.event_date"
                label="治疗日期"
                placeholder="点击选择日期"
                readonly
                clickable
                required
                @click="showDatePicker = true"
              />

              <van-field
                v-model="form.hospital"
                label="治疗医院"
                placeholder="输入医院名称"
              />

              <van-field
                v-model="form.doctor"
                label="主治医生"
                placeholder="输入医生姓名"
              />

              <van-field
                v-model="form.cycle"
                label="治疗周期"
                placeholder="如：第3周期"
              />

              <van-field
                v-model="form.description"
                type="textarea"
                label="治疗描述"
                placeholder="输入治疗描述"
                rows="3"
              />
            </van-cell-group>

            <!-- 备忘录式详情 -->
            <div class="memo-section">
              <MemoInput
                v-model="form.memo_items"
                title="治疗详情（可选）"
              />
            </div>
          </van-form>
        </div>

        <!-- 桌面端底部按钮 -->
        <div v-if="isDesktop" class="form-footer">
          <van-button @click="closeForm">取消</van-button>
          <van-button type="primary" :loading="saving" @click="saveTreatment">保存</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 日期选择器 -->
    <van-popup v-model:show="showDatePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker
        v-model="selectedDate"
        title="选择日期"
        @confirm="onDateConfirm"
        @cancel="showDatePicker = false"
      />
    </van-popup>

    <!-- 详情弹窗 -->
    <van-popup
      v-model:show="showDetail"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-lg' : ''"
      :style="isDesktop ? { width: '560px', maxHeight: '85vh' } : { height: '70%' }"
    >
      <div class="detail-popup" v-if="currentTreatment">
        <!-- 移动端：NavBar -->
        <van-nav-bar v-if="!isDesktop" title="治疗详情" left-text="关闭" @click-left="showDetail = false">
          <template #right>
            <van-button type="primary" size="small" @click="editTreatment(currentTreatment)">
              编辑
            </van-button>
          </template>
        </van-nav-bar>
        <!-- 桌面端：Flex 头部 -->
        <div v-else class="detail-header-bar">
          <van-button size="small" @click="showDetail = false">关闭</van-button>
          <span class="detail-header-title">治疗详情</span>
          <van-button type="primary" size="small" @click="editTreatment(currentTreatment)">编辑</van-button>
        </div>

        <div class="detail-content">
          <div class="detail-header">
            <div class="detail-icon"><van-icon :name="getTreatmentIcon(currentTreatment.category)" /></div>
            <div class="detail-title">{{ currentTreatment.title }}</div>
            <div class="detail-date">{{ formatDate(currentTreatment.event_date) }}</div>
          </div>

          <van-cell-group inset>
            <van-cell v-if="currentTreatment.medical_details?.hospital" title="医院" :value="currentTreatment.medical_details.hospital" />
            <van-cell v-if="currentTreatment.medical_details?.doctor" title="医生" :value="currentTreatment.medical_details.doctor" />
            <van-cell v-if="currentTreatment.medical_details?.cycle" title="周期" :value="currentTreatment.medical_details.cycle" />
            <van-cell v-if="currentTreatment.description" title="描述" :value="currentTreatment.description" />
          </van-cell-group>

          <!-- 备忘录详情 -->
          <div v-if="currentTreatment.medical_details?.memo_items?.length" class="memo-detail">
            <div class="memo-title">治疗详情</div>
            <div class="memo-list">
              <div
                v-for="(item, index) in currentTreatment.medical_details.memo_items"
                :key="index"
                class="memo-item"
              >
                <span class="memo-time">{{ item.time }}</span>
                <span class="memo-event">{{ item.event }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onActivated, watch, defineAsyncComponent } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import { timelineApi } from '@/api/timeline'
import { showToast, showConfirmDialog } from 'vant'
import { useResponsive } from '@/composables/useResponsive'
import dayjs from 'dayjs'

const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'
import MemoInput from '@/components/common/MemoInput.vue'
import SummarySection from '@/components/common/SummarySection.vue'

const { isDesktop, floatingBubbleGap } = useResponsive()

const router = useRouter()
const route = useRoute()
const patientStore = usePatientStore()

// 状态
const loading = ref(false)
const saving = ref(false)
const showAddForm = ref(false)
const showDetail = ref(false)
const showDatePicker = ref(false)
const filterType = ref('all')
const selectedDate = ref(['2024', '01', '01'])
const editingTreatment = ref(null)
const currentTreatment = ref(null)

// 患者选择状态
const hasPatient = computed(() => !!patientStore.currentPatient)

// 治疗类型
const treatmentTypes = [
  { label: '化疗', value: 'chemotherapy', icon: 'gem-o' },
  { label: '放疗', value: 'radiation', icon: 'fire-o' },
  { label: '手术', value: 'surgery', icon: 'certificate' },
  { label: '靶向', value: 'targeted', icon: 'aim' },
  { label: '免疫', value: 'immunotherapy', icon: 'shield-o' },
  { label: 'ADC', value: 'adc', icon: 'aim' },
  { label: 'CAR-T', value: 'car_t', icon: 'shield-o' },
  { label: '其他', value: 'other', icon: 'medical' }
]

// 筛选选项
const filterOptions = [
  { text: '全部', value: 'all' },
  ...treatmentTypes.map(t => ({ text: t.label, value: t.value }))
]

// 表单数据
const form = ref({
  category: 'chemotherapy',
  title: '',
  event_date: '',
  hospital: '',
  doctor: '',
  cycle: '',
  description: '',
  memo_items: []
})

// 治疗记录列表
const treatments = ref([])

// 按月份分组
const groupedTreatments = computed(() => {
  const groups = {}
  const sortedTreatments = [...treatments.value].sort((a, b) => 
    new Date(b.event_date) - new Date(a.event_date)
  )
  
  sortedTreatments.forEach(item => {
    const month = item.event_date.substring(0, 7) // YYYY-MM
    if (!groups[month]) {
      groups[month] = []
    }
    groups[month].push(item)
  })
  
  return groups
})

// 方法
function getTreatmentIcon(category) {
  const type = treatmentTypes.find(t => t.value === category)
  return type ? type.icon : 'medical'
}

function formatDate(dateStr) {
  return dayjs(dateStr).format('MM月DD日')
}

function formatMonth(month) {
  const [year, mon] = month.split('-')
  return `${year}年${parseInt(mon)}月`
}

async function loadTreatments() {
  if (!patientStore.currentPatient) return

  loading.value = true
  try {
    const params = {
      patient_id: patientStore.currentPatient.patient_id,
      event_type: 'medical'
    }

    if (filterType.value !== 'all') {
      params.category = filterType.value
    }

    const data = await timelineApi.queryTimeline(params)

    // 直接使用本地数据，不污染全局 timelineStore
    treatments.value = (data || []).filter(item =>
      item.event_type === 'medical'
    )
  } finally {
    loading.value = false
  }
}

function viewTreatment(item) {
  currentTreatment.value = item
  showDetail.value = true
}

function editTreatment(item) {
  editingTreatment.value = item
  form.value = {
    category: item.category,
    title: item.title,
    event_date: item.event_date,
    hospital: item.medical_details?.hospital || '',
    doctor: item.medical_details?.doctor || '',
    cycle: item.medical_details?.cycle || '',
    description: item.description || '',
    memo_items: item.medical_details?.memo_items || []
  }
  
  // 设置日期选择器
  if (item.event_date) {
    const [year, month, day] = item.event_date.split('-')
    selectedDate.value = [year, month, day]
  }
  
  showDetail.value = false
  showAddForm.value = true
}

function closeForm() {
  showAddForm.value = false
  editingTreatment.value = null
  form.value = {
    category: 'chemotherapy',
    title: '',
    event_date: '',
    hospital: '',
    doctor: '',
    cycle: '',
    description: '',
    memo_items: []
  }
}

function onDateConfirm({ selectedValues }) {
  form.value.event_date = selectedValues.join('-')
  showDatePicker.value = false
}

async function saveTreatment() {
  if (!form.value.title || !form.value.event_date) {
    showToast('请填写必填项')
    return
  }

  saving.value = true
  try {
    const data = {
      patient_id: patientStore.currentPatient.patient_id,
      event_type: 'medical',
      category: form.value.category,
      title: form.value.title,
      event_date: form.value.event_date,
      description: form.value.description,
      medical_details: {
        hospital: form.value.hospital,
        doctor: form.value.doctor,
        cycle: form.value.cycle,
        memo_items: form.value.memo_items
      }
    }

    if (editingTreatment.value) {
      // 更新
      await timelineApi.updateTimelineItem(editingTreatment.value.event_id, data)
      showToast('更新成功')
    } else {
      // 新增
      await timelineApi.addTimelineItem(data)
      showToast('添加成功')
    }

    closeForm()
    await loadTreatments()
  } catch (error) {
    console.error('保存失败:', error)
    showToast('保存失败')
  } finally {
    saving.value = false
  }
}

// 从时间线跳入时，自动打开对应事件详情
function autoOpenDetail() {
  const targetEventId = route.query.event_id
  if (targetEventId) {
    const target = treatments.value.find(t => String(t.event_id) === String(targetEventId))
    if (target) {
      viewTreatment(target)
    }
  }
}

// 生命周期
onMounted(async () => {
  await loadTreatments()
  autoOpenDetail()
})

// keep-alive 页面重新激活时也检查
onActivated(() => {
  autoOpenDetail()
})

// 监听患者变化
watch(() => patientStore.currentPatient?.patient_id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    await loadTreatments()
  }
})
</script>

<style scoped>
.treatment-view {
  min-height: 100vh;
  background: var(--bg-primary);
  position: relative;
  padding-bottom: var(--safe-bottom);
}

.filter-section {
  background: var(--bg-surface);
  margin: 16px;
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  /* 不使用 overflow:hidden，避免裁剪下拉面板 */
}

.filter-section :deep(.van-dropdown-menu__bar) {
  border-radius: 12px;
}

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

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-icon .van-icon {
  font-size: 48px;
}

.empty-text {
  font-size: 18px;
  color: var(--primary-color);
  font-weight: 500;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 列表样式 */
.treatment-list {
  padding: 0 16px;
}

.month-group {
  margin-bottom: 16px;
}

.month-header {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
  padding: 8px 4px;
  margin-bottom: 8px;
  border-left: 3px solid var(--primary-color);
  padding-left: 8px;
}

.treatment-item {
  display: flex;
  align-items: flex-start;
  background: var(--bg-surface);
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 8px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  cursor: pointer;
  transition: all 0.2s;
}

.treatment-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--primary-alpha-12);
}

.item-icon {
  font-size: 24px;
  margin-right: 12px;
  flex-shrink: 0;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.item-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.item-date {
  font-size: 12px;
  color: var(--text-secondary);
}

.item-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  line-height: 1.4;
}

.item-hospital, .item-memo-count {
  font-size: 12px;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

.item-arrow {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

/* 表单弹窗 */
.form-popup {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-elevated);
}

.form-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.type-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.type-item:hover {
  background: var(--primary-alpha-8);
}

.type-item.active {
  background: var(--primary-alpha-15);
  border-color: var(--primary-color);
}

.type-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.type-name {
  font-size: 12px;
  color: var(--text-primary);
}

.memo-section {
  margin-top: 16px;
}

/* 桌面端表单底部按钮 */
.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-elevated);
}

/* 详情弹窗 */
.detail-popup {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-elevated);
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.detail-header {
  text-align: center;
  margin-bottom: 20px;
}

.detail-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.detail-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.detail-date {
  font-size: 14px;
  color: var(--text-secondary);
}

.memo-detail {
  margin-top: 16px;
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
}

.memo-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.memo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memo-item {
  display: flex;
  gap: 12px;
  padding: 8px;
  background: var(--primary-alpha-5);
  border-radius: 8px;
}

.memo-time {
  font-size: 13px;
  font-weight: 500;
  color: var(--primary-color);
  min-width: 50px;
}

.memo-event {
  font-size: 13px;
  color: var(--text-primary);
}

/* 浮动按钮样式覆盖 */
:deep(.van-floating-bubble) {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  box-shadow: 0 4px 12px var(--primary-alpha-40);
}

/* 桌面端侧边栏适配 + 居中限宽 */
@media (min-width: 768px) {
  .treatment-view {
    padding: var(--space-6);
    padding-bottom: var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
  }

  .detail-header-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color);
  }

  .detail-header-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
  }
}
</style>