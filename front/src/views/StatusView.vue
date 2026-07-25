<template>
  <div class="status-view">
    <!-- 动态背景 -->
    <BackgroundAnimation />

    <!-- 移动端返回按钮 -->
    <BackButton v-if="!isDesktop" title="状态记录" />

    <!-- 桌面端页面头部 -->
    <header v-if="isDesktop" class="desktop-header">
      <div class="header-content">
        <h1 class="page-title">状态记录</h1>
        <div class="header-actions">
          <van-button type="primary" icon="plus" @click="showAddForm = true">添加记录</van-button>
        </div>
      </div>
    </header>

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
    <div v-else-if="statusRecords.length === 0" class="empty-state">
      <div class="empty-icon"><van-icon name="todo-list-o" /></div>
      <div class="empty-text">暂无状态记录</div>
      <div class="empty-hint">点击右下角按钮添加每日状态</div>
    </div>

    <!-- 状态记录列表 -->
    <div v-else class="status-list">
      <!-- 按月份分组 -->
      <div v-for="(group, month) in groupedStatusRecords" :key="month" class="month-group">
        <div class="month-header">{{ formatMonth(month) }}</div>
        
        <div
          v-for="item in group"
          :key="item.event_id"
          class="status-card"
          @click="viewStatus(item)"
        >
          <div class="card-header">
            <span class="card-date">{{ formatDate(item.event_date) }}</span>
            <span class="card-summary">{{ getStatusSummary(item) }}</span>
          </div>
          
          <!-- 状态评分概览 - 始终显示所有状态 -->
          <div class="status-overview">
            <div 
              v-for="(type, key) in statusTypes" 
              :key="key"
              class="status-badge"
              :class="`status-badge--${key}`"
            >
              <span class="badge-icon"><van-icon :name="type.icon" /></span>
              <span v-if="key === 'stool'" class="badge-value">
                {{ getStoolLabel(item.life_details?.stool?.status) }}
              </span>
              <span v-else class="badge-value">
                {{ item.life_details?.[key]?.score ?? type.defaultScore }}/{{ item.life_details?.[key]?.max_score || 10 }}
              </span>
            </div>
          </div>

          <!-- 备注 -->
          <div v-if="item.life_details?.general_memo" class="card-memo">
            {{ item.life_details.general_memo }}
          </div>
        </div>
      </div>
    </div>

    <!-- 移动端浮动添加按钮 -->
    <van-floating-bubble
      v-if="!isDesktop"
      axis="xy"
      icon="plus"
      @click="openAddForm"
      :gap="floatingBubbleGap"
    />

    <!-- 状态概要 -->
    <SummarySection title="状态概要" summary-type="status" />

    <!-- 添加/编辑状态记录弹窗 -->
    <van-popup
      v-model:show="showAddForm"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-lg' : ''"
      :style="!isDesktop ? { height: '95%' } : ''"
    >
      <div class="form-popup">
        <van-nav-bar
          :title="editingStatus ? '编辑状态记录' : '添加状态记录'"
          :left-text="!isDesktop ? '取消' : ''"
          @click-left="closeForm"
        >
          <template v-if="!isDesktop" #right>
            <van-button type="primary" size="small" :loading="saving" @click="saveStatus">
              保存
            </van-button>
          </template>
        </van-nav-bar>

        <div class="form-content">
          <!-- 日期选择 -->
          <van-cell-group inset>
            <van-field
              v-model="form.event_date"
              label="记录日期"
              placeholder="点击选择日期"
              readonly
              clickable
              required
              @click="showDatePicker = true"
            />
          </van-cell-group>

          <!-- 各状态评分 -->
          <div class="status-scores">
            <div class="section-title">状态评分</div>
            
            <van-cell-group inset>
              <!-- 疼痛 -->
              <div class="score-item">
                <div class="score-header">
                  <span class="score-icon"><van-icon name="warning-o" /></span>
                  <span class="score-label">疼痛</span>
                  <span class="score-value">{{ form.scores.pain.score }}/{{ form.scores.pain.max_score }}</span>
                </div>
                <van-slider
                  v-model="form.scores.pain.score"
                  :max="form.scores.pain.max_score"
                  :step="1"
                  active-color="var(--danger-color)"
                />
                <div class="score-hint">0分无痛，10分最痛</div>
              </div>

              <!-- 心情 -->
              <div class="score-item">
                <div class="score-header">
                  <span class="score-icon"><van-icon name="smile-o" /></span>
                  <span class="score-label">心情</span>
                  <span class="score-value">{{ form.scores.mood.score }}/{{ form.scores.mood.max_score }}</span>
                </div>
                <van-slider
                  v-model="form.scores.mood.score"
                  :max="form.scores.mood.max_score"
                  :step="1"
                  active-color="var(--success-color)"
                />
                <div class="score-hint">1分很差，10分很好</div>
              </div>

              <!-- 睡眠 -->
              <div class="score-item">
                <div class="score-header">
                  <span class="score-icon"><van-icon name="closed-eye" /></span>
                  <span class="score-label">睡眠</span>
                  <span class="score-value">{{ form.scores.sleep.score }}/{{ form.scores.sleep.max_score }}</span>
                </div>
                <van-slider
                  v-model="form.scores.sleep.score"
                  :max="form.scores.sleep.max_score"
                  :step="1"
                  active-color="var(--info-color)"
                />
                <div class="score-hint">1分很差，10分很好</div>
              </div>

              <!-- 饮食 -->
              <div class="score-item">
                <div class="score-header">
                  <span class="score-icon"><van-icon name="gift-o" /></span>
                  <span class="score-label">饮食</span>
                  <span class="score-value">{{ form.scores.diet.score }}/{{ form.scores.diet.max_score }}</span>
                </div>
                <van-slider
                  v-model="form.scores.diet.score"
                  :max="form.scores.diet.max_score"
                  :step="1"
                  active-color="var(--warning-color)"
                />
                <div class="score-hint">1分很差，10分很好</div>
              </div>

              <!-- 大便 -->
              <div class="score-item stool-item">
                <div class="score-header stool-header-inline">
                  <div class="stool-left">
                    <span class="score-icon"><van-icon name="records" /></span>
                    <span class="score-label">大便</span>
                  </div>
                  <van-radio-group v-model="form.scores.stool.status" direction="horizontal" class="stool-radio-inline">
                    <van-radio name="normal">正常</van-radio>
                    <van-radio name="loose">稀便</van-radio>
                    <van-radio name="constipation">便秘</van-radio>
                  </van-radio-group>
                </div>
                <!-- <van-field
                  v-model="form.scores.stool.memo"
                  placeholder="补充说明（可选）"
                  class="stool-memo"
                /> -->
              </div>
            </van-cell-group>
          </div>

          <!-- 整体备注 -->
          <van-cell-group inset class="memo-section">
            <van-field
              v-model="form.general_memo"
              type="textarea"
              label="整体备注"
              placeholder="记录今天的整体感受..."
              rows="3"
              autosize
            />
          </van-cell-group>

          <!-- 备忘录式详情 -->
          <div class="memo-section">
            <MemoInput
              v-model="form.memo_items"
              title="详细记录（可选）"
            />
          </div>
        </div>

        <!-- 桌面端底部按钮 -->
        <div v-if="isDesktop" class="form-footer">
          <van-button @click="closeForm">取消</van-button>
          <van-button type="primary" :loading="saving" @click="saveStatus">保存</van-button>
        </div>
      </div>
    </van-popup>

    <!-- 日期选择器 -->
    <van-popup
      v-model:show="showDatePicker"
      :position="isDesktop ? 'center' : 'bottom'"
      :round="!isDesktop"
      :class="isDesktop ? 'desktop-popup-sm' : ''"
    >
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
      :style="!isDesktop ? { height: '80%' } : ''"
    >
      <div class="detail-popup" v-if="currentStatus">
        <!-- 移动端：NavBar -->
        <van-nav-bar v-if="!isDesktop" title="状态详情" left-text="关闭" @click-left="showDetail = false">
          <template #right>
            <van-button type="primary" size="small" @click="editStatus(currentStatus)">
              编辑
            </van-button>
          </template>
        </van-nav-bar>
        <!-- 桌面端：Flex 头部 -->
        <div v-else class="detail-header-bar">
          <van-button size="small" @click="showDetail = false">关闭</van-button>
          <span class="detail-header-title">状态详情</span>
          <van-button type="primary" size="small" @click="editStatus(currentStatus)">编辑</van-button>
        </div>

        <div class="detail-content">
          <div class="detail-header">
            <div class="detail-date">{{ formatFullDate(currentStatus.event_date) }}</div>
            <div class="detail-summary">
              <span v-for="(type, key) in statusTypes" :key="key" class="summary-item">
                <template v-if="key === 'stool'">
                  大便{{ getStoolLabel(currentStatus.life_details?.stool?.status) }}
                </template>
                <template v-else>
                  {{ type.label }}{{ currentStatus.life_details?.[key]?.score ?? type.defaultScore }}
                </template>
              </span>
            </div>
          </div>

          <!-- 状态评分详情 - 始终显示所有状态 -->
          <div class="detail-scores">
            <div 
              v-for="(type, key) in statusTypes" 
              :key="key" 
              class="detail-score-item"
            >
              <div class="detail-score-header">
                <span class="detail-score-icon"><van-icon :name="type.icon" /></span>
                <span class="detail-score-label">{{ type.label }}</span>
              </div>
              <div v-if="key === 'stool'" class="detail-score-value">
                {{ getStoolLabel(currentStatus.life_details?.stool?.status) }}
                <span v-if="currentStatus.life_details?.stool?.memo" class="stool-memo-detail">
                  （{{ currentStatus.life_details.stool.memo }}）
                </span>
              </div>
              <div v-else class="detail-score-bar">
                <van-progress 
                  :percentage="((currentStatus.life_details?.[key]?.score ?? type.defaultScore) / (currentStatus.life_details?.[key]?.max_score || 10)) * 100"
                  :color="type.color"
                  :show-pivot="false"
                />
                <span class="detail-score-text">
                  {{ currentStatus.life_details?.[key]?.score ?? type.defaultScore }}/{{ currentStatus.life_details?.[key]?.max_score || 10 }}
                </span>
              </div>
            </div>
          </div>

          <!-- 整体备注 -->
          <van-cell-group v-if="currentStatus.life_details?.general_memo" inset>
            <van-cell title="整体备注" :value="currentStatus.life_details.general_memo" />
          </van-cell-group>

          <!-- 备忘录详情 -->
          <div v-if="currentStatus.life_details?.memo_items?.length" class="memo-detail">
            <div class="memo-title">详细记录</div>
            <div class="memo-list">
              <div
                v-for="(item, index) in currentStatus.life_details.memo_items"
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
import { useResponsive } from '@/composables/useResponsive'
import { timelineApi } from '@/api/timeline'
import { showToast } from 'vant'
import dayjs from 'dayjs'

const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))
import BackButton from '@/components/index-detail/BackButton.vue'
import MemoInput from '@/components/common/MemoInput.vue'
import SummarySection from '@/components/common/SummarySection.vue'

const router = useRouter()
const route = useRoute()
const patientStore = usePatientStore()
const { isDesktop, floatingBubbleGap } = useResponsive()

// 状态类型定义 - 包含默认值
const statusTypes = {
  pain: { label: '疼痛', icon: 'warning-o', color: 'var(--danger-color)', defaultScore: 0 },
  mood: { label: '心情', icon: 'smile-o', color: 'var(--success-color)', defaultScore: 5 },
  sleep: { label: '睡眠', icon: 'closed-eye', color: 'var(--info-color)', defaultScore: 5 },
  diet: { label: '饮食', icon: 'gift-o', color: 'var(--warning-color)', defaultScore: 5 },
  stool: { label: '大便', icon: 'records', color: 'var(--primary-color)', defaultStatus: 'normal' }
}

// 状态
const loading = ref(false)
const saving = ref(false)
const showAddForm = ref(false)
const showDetail = ref(false)
const showDatePicker = ref(false)
const selectedDate = ref(['2024', '01', '01'])
const editingStatus = ref(null)
const currentStatus = ref(null)

// 患者选择状态
const hasPatient = computed(() => !!patientStore.currentPatient)

// 表单数据 - 包含所有状态类型
const defaultScores = () => ({
  mood: { score: 5, max_score: 10 },
  pain: { score: 0, max_score: 10 },
  sleep: { score: 5, max_score: 10 },
  diet: { score: 5, max_score: 10 },
  stool: { status: 'normal', memo: '' }
})

const form = ref({
  event_date: '',
  scores: defaultScores(),
  general_memo: '',
  memo_items: []
})

// 状态记录列表
const statusRecords = ref([])

// 按月份分组
const groupedStatusRecords = computed(() => {
  const groups = {}
  const sortedRecords = [...statusRecords.value].sort((a, b) => 
    new Date(b.event_date) - new Date(a.event_date)
  )
  
  sortedRecords.forEach(item => {
    const month = item.event_date.substring(0, 7) // YYYY-MM
    if (!groups[month]) {
      groups[month] = []
    }
    groups[month].push(item)
  })
  
  return groups
})

// 方法
function getStoolLabel(status) {
  const labels = {
    normal: '正常',
    loose: '稀便',
    constipation: '便秘'
  }
  return labels[status] || '正常'
}

function formatDate(dateStr) {
  return dayjs(dateStr).format('MM月DD日')
}

function formatFullDate(dateStr) {
  return dayjs(dateStr).format('YYYY年MM月DD日')
}

function formatMonth(month) {
  const [year, mon] = month.split('-')
  return `${year}年${parseInt(mon)}月`
}

function getStatusSummary(item) {
  if (!item.life_details) return ''
  const parts = []
  const ld = item.life_details
  parts.push(`疼痛${ld.pain?.score ?? 0}`)
  parts.push(`心情${ld.mood?.score ?? 5}`)
  parts.push(`睡眠${ld.sleep?.score ?? 5}`)
  parts.push(`饮食${ld.diet?.score ?? 5}`)
  const stoolLabels = { normal: '正常', loose: '稀便', constipation: '便秘' }
  parts.push(`大便${stoolLabels[ld.stool?.status] || '正常'}`)
  return parts.join('/')
}

function openAddForm() {
  // 设置默认日期为今天
  const today = dayjs().format('YYYY-MM-DD')
  form.value.event_date = today
  const [year, month, day] = today.split('-')
  selectedDate.value = [year, month, day]
  
  // 重置表单
  form.value.scores = defaultScores()
  form.value.general_memo = ''
  form.value.memo_items = []
  editingStatus.value = null
  
  showAddForm.value = true
}

async function loadStatusRecords() {
  if (!patientStore.currentPatient) return

  loading.value = true
  try {
    const params = {
      patient_id: patientStore.currentPatient.patient_id,
      event_type: 'life',
      category: 'daily_status'
    }

    const data = await timelineApi.queryTimeline(params)

    // 直接使用本地数据，不污染全局 timelineStore
    statusRecords.value = (data || []).filter(item =>
      item.event_type === 'life' && item.category === 'daily_status'
    )
  } finally {
    loading.value = false
  }
}

function viewStatus(item) {
  currentStatus.value = item
  showDetail.value = true
}

function editStatus(item) {
  editingStatus.value = item
  
  // 填充表单
  form.value.event_date = item.event_date
  form.value.general_memo = item.life_details?.general_memo || ''
  form.value.memo_items = item.life_details?.memo_items || []
  
  // 填充分数
  const scores = defaultScores()
  if (item.life_details) {
    ['mood', 'pain', 'sleep', 'diet'].forEach(key => {
      if (item.life_details[key]) {
        scores[key] = { ...scores[key], ...item.life_details[key] }
      }
    })
    if (item.life_details.stool) {
      scores.stool = { ...scores.stool, ...item.life_details.stool }
    }
  }
  form.value.scores = scores
  
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
  editingStatus.value = null
  form.value = {
    event_date: '',
    scores: defaultScores(),
    general_memo: '',
    memo_items: []
  }
}

function onDateConfirm({ selectedValues }) {
  form.value.event_date = selectedValues.join('-')
  showDatePicker.value = false
}

async function saveStatus() {
  if (!form.value.event_date) {
    showToast('请选择日期')
    return
  }

  saving.value = true
  try {
    // 构建标题
    const dateStr = dayjs(form.value.event_date).format('MM月DD日')
    const scoreParts = []
    if (form.value.scores.pain.score > 0) scoreParts.push(`疼痛${form.value.scores.pain.score}`)
    if (form.value.scores.mood.score > 0) scoreParts.push(`心情${form.value.scores.mood.score}`)
    if (form.value.scores.sleep.score > 0) scoreParts.push(`睡眠${form.value.scores.sleep.score}`)
    if (form.value.scores.diet.score > 0) scoreParts.push(`饮食${form.value.scores.diet.score}`)
    
    const title = scoreParts.length > 0 
      ? `${dateStr} · ${scoreParts.join(' / ')}`
      : `${dateStr}状态记录`

    const data = {
      patient_id: patientStore.currentPatient.patient_id,
      event_type: 'life',
      category: 'daily_status',  // 新的分类
      title: title,
      event_date: form.value.event_date,
      description: form.value.general_memo,
      life_details: {
        // 始终保存所有状态，使用默认值
        mood: form.value.scores.mood,
        pain: form.value.scores.pain,
        sleep: form.value.scores.sleep,
        diet: form.value.scores.diet,
        stool: form.value.scores.stool,
        general_memo: form.value.general_memo,
        memo_items: form.value.memo_items
      }
    }

    if (editingStatus.value) {
      // 更新
      await timelineApi.updateTimelineItem(editingStatus.value.event_id, data)
      showToast('更新成功')
    } else {
      // 新增
      await timelineApi.addTimelineItem(data)
      showToast('添加成功')
    }

    closeForm()
    await loadStatusRecords()
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
    const target = statusRecords.value.find(t => String(t.event_id) === String(targetEventId))
    if (target) {
      viewStatus(target)
    }
  }
}

// 生命周期
onMounted(async () => {
  await loadStatusRecords()
  autoOpenDetail()
})

// keep-alive 页面重新激活时也检查
onActivated(() => {
  autoOpenDetail()
})

// 监听患者变化
watch(() => patientStore.currentPatient?.patient_id, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    await loadStatusRecords()
  }
})
</script>

<style scoped>
.status-view {
  min-height: 100vh;
  background: var(--bg-primary);
  position: relative;
  padding-bottom: var(--safe-bottom);
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
.status-list {
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

.status-card {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  cursor: pointer;
  transition: all 0.2s;
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--primary-alpha-12);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-date {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
}

.card-summary {
  font-size: 13px;
  color: var(--text-secondary);
}

.card-title {
  font-size: 13px;
  color: var(--text-secondary);
}

.status-overview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 13px;
}

.badge-icon {
  font-size: 14px;
}

.badge-value {
  font-weight: 500;
}

.status-badge--mood {
  background: var(--status-normal-bg);
  color: var(--success-color);
}

.status-badge--pain {
  background: var(--status-danger-bg);
  color: var(--danger-color);
}

.status-badge--sleep {
  background: var(--status-info-bg);
  color: var(--info-color);
}

.status-badge--diet {
  background: var(--status-warning-bg);
  color: var(--warning-color);
}

.status-badge--stool {
  background: var(--primary-alpha-10);
  color: var(--primary-dark);
}

.card-memo {
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  padding-top: 12px;
  border-top: 1px solid var(--border-dark);
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

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 16px 0 8px 0;
  padding-left: 4px;
}

.status-scores {
  margin-top: 8px;
}

.score-item {
  padding: 16px;
  background: var(--bg-surface);
  border-radius: 8px;
  margin-bottom: 8px;
}

.score-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.score-icon {
  font-size: 20px;
  margin-right: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.score-icon .van-icon {
  font-size: 20px;
}

.score-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}

.score-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
}

.score-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 8px;
}

.stool-item {
  padding-bottom: 8px;
}

.stool-header-inline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 0;
}

.stool-left {
  display: flex;
  align-items: center;
}

.stool-radio-inline {
  flex-wrap: wrap;
}

.stool-radio-inline :deep(.van-radio) {
  margin-right: 8px;
}

.stool-memo {
  margin-top: 12px;
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
  padding: 20px;
  background: var(--bg-surface);
  border-radius: 12px;
}

.detail-date {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.detail-summary {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.summary-item {
  margin: 0 2px;
}

.summary-item:not(:last-child)::after {
  content: '/';
  margin-left: 4px;
  color: var(--text-tertiary);
}

.detail-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.detail-scores {
  background: var(--bg-surface);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.detail-score-item {
  padding: 12px 0;
  border-top: 1px solid var(--border-dark);
}

.detail-score-item:last-child {
  border-bottom: none;
}

.detail-score-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.detail-score-icon {
  font-size: 18px;
  margin-right: 8px;
}

.detail-score-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.detail-score-value {
  font-size: 14px;
  color: var(--primary-color);
  font-weight: 500;
}

.stool-memo-detail {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: normal;
}

.detail-score-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-score-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
  min-width: 50px;
  text-align: right;
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
  background: linear-gradient(135deg, var(--success-color) 0%, var(--success-color) 100%);
  box-shadow: 0 4px 12px var(--success-alpha-40);
}

/* 滑块样式 */
:deep(.van-slider) {
  margin: 8px 0;
}

.desktop-header {
  margin-bottom: var(--space-4);
}

.desktop-header .header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.desktop-header .page-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.desktop-header .header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* 桌面端侧边栏适配 + 居中限宽 */
@media (min-width: 768px) {
  .status-view {
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
