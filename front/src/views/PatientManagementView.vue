<template>
  <div class="patient-management">
    <!-- 导航栏 -->
    <BackButton title="病人管理" />
    
    <!-- 当前病人提示 -->
    <div class="current-patient-tip" v-if="patientStore.currentPatient">
      <van-notice-bar
        :text="`当前病人：${patientStore.currentPatient.patient_name}`"
        mode="closeable"
        background="var(--primary-alpha-5)"
        color="var(--primary-color)"
        left-icon="info-o"
      />
    </div>
    
    <!-- 病人列表 -->
    <div class="patient-list">
      <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
        <van-list
          v-model:loading="loading"
          :finished="finished"
          finished-text="没有更多了"
          @load="onLoad"
        >
          <div v-if="patientStore.patientList.length === 0 && !loading" class="empty-state">
            <van-empty description="暂无病人信息" />
          </div>
          
          <van-card
            v-for="patient in patientStore.patientList"
            :key="patient.patient_id"
            :title="patient.patient_name"
            :desc="getPatientDesc(patient)"
            class="patient-card"
            :class="{ 'current-patient': isCurrentPatient(patient) }"
          >
            <template #thumb>
              <div class="patient-avatar">
                <van-icon
                  :name="patient.gender === 'male' ? 'manager' : patient.gender === 'female' ? 'friends' : 'contact'"
                  size="24"
                />
              </div>
            </template>
            <template #tags>
              <van-tag v-if="patient.is_primary" type="primary" size="small">主病人</van-tag>
              <van-tag v-if="isCurrentPatient(patient)" type="success" size="small">当前</van-tag>
            </template>
            
            <template #footer>
              <div class="card-actions">
                <van-button
                  v-if="!isCurrentPatient(patient)"
                  size="small"
                  type="primary"
                  @click="switchToPatient(patient)"
                  round
                >
                  切换
                </van-button>
                <van-button
                  v-if="!patient.is_primary"
                  size="small"
                  type="warning"
                  @click="setPrimary(patient)"
                  round
                >
                  设为主患者
                </van-button>
                <van-button
                  size="small"
                  @click="editPatient(patient)"
                  round
                >
                  编辑
                </van-button>
                <van-button
                  v-if="!patient.is_primary"
                  size="small"
                  type="danger"
                  @click="deletePatient(patient)"
                  round
                >
                  删除
                </van-button>
              </div>
            </template>
          </van-card>
        </van-list>
      </van-pull-refresh>
    </div>
    
    <!-- 浮动添加按钮 -->
    <van-floating-bubble
      axis="xy"
      icon="plus"
      :gap="bubbleGap"
      @click="addPatient"
      class="add-button"
    />
    
    <!-- 病人表单 -->
    <PatientForm
      v-model:show="showForm"
      :patient="editingPatient"
      @success="onPatientSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast, showConfirmDialog } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { patientApi } from '@/api/patient'
import { useResponsive } from '@/composables/useResponsive'
import BackButton from '@/components/index-detail/BackButton.vue'
import PatientForm from '@/components/PatientForm.vue'

const router = useRouter()
const patientStore = usePatientStore()
const { isDesktop } = useResponsive()

const BUBBLE_EDGE_GAP = 24
const MOBILE_TABBAR_CLEARANCE = 60
const bubbleGap = computed(() => ({
  x: BUBBLE_EDGE_GAP,
  y: BUBBLE_EDGE_GAP + (isDesktop.value ? 0 : MOBILE_TABBAR_CLEARANCE),
}))

const refreshing = ref(false)
const loading = ref(false)
const finished = ref(false)
const showForm = ref(false)
const editingPatient = ref(null)

// 获取病人描述
function getPatientDesc(patient) {
  const desc = []
  if (patient.age) desc.push(`${patient.age}岁`)
  if (patient.gender === 'male') desc.push('男')
  else if (patient.gender === 'female') desc.push('女')
  return desc.join(' · ') || '暂无详细信息'
}

// 判断是否为当前病人
function isCurrentPatient(patient) {
  return patientStore.currentPatient && patientStore.currentPatient.patient_id === patient.patient_id
}

// 加载病人列表
async function loadPatients() {
  try {
    await patientStore.fetchPatientList()
  } catch (error) {
    console.error('加载病人列表错误:', error)
    showToast('加载病人列表失败')
  } finally {
    finished.value = true
    loading.value = false
  }
}

// 下拉刷新
async function onRefresh() {
  refreshing.value = true
  await loadPatients()
  refreshing.value = false
}

// 加载更多（患者数量通常很少，一次加载完毕）
async function onLoad() {
  await loadPatients()
}

// 切换病人
async function switchToPatient(patient) {
  if (isCurrentPatient(patient)) {
    showToast('已经是当前病人了')
    return
  }

  try {
    await patientStore.switchPatient(patient.patient_id)
    showToast(`已切换到：${patient.patient_name}`)
  } catch (error) {
    console.error('切换病人错误:', error)
    showToast('切换失败')
  }
}

// 添加病人
function addPatient() {
  editingPatient.value = null
  showForm.value = true
}

// 编辑病人
function editPatient(patient) {
  editingPatient.value = patient
  showForm.value = true
}

// 设为主患者
async function setPrimary(patient) {
  try {
    await showConfirmDialog({
      title: '设为主患者',
      message: `确定将"${patient.patient_name}"设为主患者吗？`
    })
    await patientApi.setPrimaryPatient(patient.patient_id)
    showSuccessToast('已设为主患者')
    await loadPatients()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('设置主患者错误:', error)
      showToast('设置失败')
    }
  }
}

// 删除病人
async function deletePatient(patient) {
  if (patient.is_primary) {
    showToast('主病人不能删除')
    return
  }

  try {
    await showConfirmDialog({
      title: '确认删除',
      message: `确定要删除病人"${patient.patient_name}"吗？\n该操作不可恢复，关联的所有数据将被永久删除。`,
    })

    const result = await patientStore.deletePatient(patient.patient_id)

    // 展示删除统计
    const counts = result?.deleted_counts
    if (counts) {
      const parts = []
      if (counts.conversations) parts.push(`${counts.conversations}条会诊`)
      if (counts.medications) parts.push(`${counts.medications}条用药`)
      if (counts.checks) parts.push(`${counts.checks}条检验`)
      if (counts.exams) parts.push(`${counts.exams}条检查`)
      if (parts.length > 0) {
        showToast(`已删除：${patient.patient_name}（含${parts.join('、')}）`)
      } else {
        showToast(`已删除：${patient.patient_name}`)
      }
    } else {
      showToast(`已删除：${patient.patient_name}`)
    }
  } catch (error) {
    if (error !== 'cancel') {
      // 处理 409 拦截
      if (error?.response?.status === 409) {
        showToast(error.response.data?.detail || '该患者有进行中的会诊，无法删除')
      } else {
        console.error('删除病人错误:', error)
        showToast('删除失败')
      }
    }
  }
}

// 病人操作成功回调
async function onPatientSuccess(patient) {
  await loadPatients()

  // 如果是新增病人，询问是否切换
  if (!editingPatient.value && patient) {
    try {
      await showConfirmDialog({
        title: '添加成功',
        message: `病人添加成功，是否切换到该病人？`
      })
      await switchToPatient(patient)
    } catch (error) {
      // 用户取消切换
    }
  }
}

onMounted(() => {
  loadPatients()
})
</script>

<style scoped>
.patient-management {
  min-height: 100vh;
  background: var(--bg-primary);
}

.current-patient-tip {
  margin: 10px;
}

.patient-list {
  padding: 0 16px var(--safe-bottom);
}

.patient-card {
  margin-bottom: 12px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
}

.patient-card.current-patient {
  border: 2px solid var(--primary-color);
  box-shadow: 0 2px 12px var(--primary-alpha-30);
}

.patient-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--bg-surface);
}

.card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 8px;
}

.empty-state {
  padding: 60px 0;
}

.add-button {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: var(--bg-surface);
  box-shadow: 0 4px 12px var(--primary-alpha-40);
}

/* 桌面端侧边栏适配 */
@media (min-width: 768px) {
  .patient-management {
    padding: 0 var(--space-6) var(--space-6);
  }

  .patient-list {
    max-width: 900px;
    margin: 0 auto;
  }
}
</style>
