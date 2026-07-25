<template>
  <van-popup
    v-model:show="visible"
    :close-on-click-overlay="false"
    :position="isDesktop ? 'center' : 'bottom'"
    :round="!isDesktop"
    :class="isDesktop ? 'desktop-popup-lg' : ''"
    :style="!isDesktop ? { height: '85%' } : {}"
  >
    <div class="onboarding-guide">
      <!-- 步骤指示器 -->
      <div class="step-indicator">
        <div
          v-for="i in 3"
          :key="i"
          class="step-dot"
          :class="{ active: i === step, done: i < step }"
        />
      </div>

      <!-- 步骤1: 创建患者 -->
      <template v-if="step === 1">
        <div class="step-content">
          <div class="step-icon">
            <van-icon name="friends-o" size="48" color="var(--primary-color)" />
          </div>
          <h2 class="step-title">欢迎来到 OncoPath</h2>
          <p class="step-desc">
            OncoPath 帮助您管理检验报告、跟踪治疗时间线、获取 AI 专家会诊建议。
          </p>
          <p class="step-desc">首先，让我们创建一个患者档案。所有医疗数据都会关联到患者。</p>

          <van-form @submit="handleCreatePatient" class="step-form">
            <van-cell-group inset>
              <van-field
                v-model="patientName"
                label="姓名"
                placeholder="请输入患者姓名"
                required
                maxlength="50"
                :rules="[{ required: true, message: '请输入患者姓名' }]"
              />
              <van-field name="gender" label="性别">
                <template #input>
                  <van-radio-group v-model="gender" direction="horizontal">
                    <van-radio name="male">男</van-radio>
                    <van-radio name="female">女</van-radio>
                  </van-radio-group>
                </template>
              </van-field>
              <van-field
                v-model="birthDate"
                label="出生日期"
                placeholder="选择出生日期（选填）"
                readonly
                clickable
                @click="showDatePicker = true"
              />
              <van-field
                v-model="medicalHistory"
                label="病史"
                placeholder="如：肺腺癌 IIIA期（选填）"
                type="textarea"
                rows="2"
              />
            </van-cell-group>
            <div class="step-actions">
              <van-button round block type="primary" native-type="submit" :loading="creating">
                创建患者并继续
              </van-button>
            </div>
          </van-form>
        </div>
      </template>

      <!-- 步骤2: 上传报告 -->
      <template v-if="step === 2">
        <div class="step-content">
          <div class="step-icon">
            <van-icon name="photo-o" size="48" color="var(--primary-color)" />
          </div>
          <h2 class="step-title">上传检验报告</h2>
          <p class="step-desc">
            拍照或选择图片上传检验报告，系统将自动识别指标数据。您也可以跳过此步骤稍后再上传。
          </p>

          <div class="upload-preview" @click="goUpload">
            <van-icon name="photograph" size="36" color="var(--primary-color)" />
            <span>点击上传报告图片</span>
          </div>

          <div class="step-actions">
            <van-button round block type="primary" @click="nextStep">
              下一步
            </van-button>
            <van-button round block plain @click="nextStep" style="margin-top: 8px">
              稍后再说
            </van-button>
          </div>
        </div>
      </template>

      <!-- 步骤3: 功能介绍 -->
      <template v-if="step === 3">
        <div class="step-content">
          <div class="step-icon">
            <van-icon name="star-o" size="48" color="var(--primary-color)" />
          </div>
          <h2 class="step-title">开始使用</h2>
          <p class="step-desc">以下功能等您探索：</p>

          <div class="feature-list">
            <div class="feature-item" @click="goFeature('/home/medication')">
              <van-icon name="gem-o" size="24" color="var(--primary-color)" />
              <div>
                <div class="feature-name">用药管理</div>
                <div class="feature-desc">记录用药方案，服药打卡</div>
              </div>
            </div>
            <div class="feature-item" @click="goFeature('/home/timeline')">
              <van-icon name="clock-o" size="24" color="var(--success-color)" />
              <div>
                <div class="feature-name">治疗时间线</div>
                <div class="feature-desc">可视化治疗历程</div>
              </div>
            </div>
            <div class="feature-item" @click="goFeature('/home/consultation')">
              <van-icon name="friends-o" size="24" color="var(--warning-color)" />
              <div>
                <div class="feature-name">AI 专家会诊</div>
                <div class="feature-desc">多专家分析病情，给出建议</div>
              </div>
            </div>
            <div class="feature-item" @click="goFeature('/home/abnormal-indicators')">
              <van-icon name="warning-o" size="24" color="var(--danger-color)" />
              <div>
                <div class="feature-name">异常指标</div>
                <div class="feature-desc">追踪异常检验指标</div>
              </div>
            </div>
          </div>

          <div class="step-actions">
            <van-button round block type="primary" @click="complete">
              开始使用
            </van-button>
          </div>
        </div>
      </template>
    </div>

    <!-- 日期选择器 -->
    <van-popup v-model:show="showDatePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker
        title="选择出生日期"
        :min-date="minDate"
        :max-date="maxDate"
        @confirm="onDateConfirm"
        @cancel="showDatePicker = false"
      />
    </van-popup>
  </van-popup>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop } = useResponsive()
const router = useRouter()
const patientStore = usePatientStore()

const step = ref(1)
const creating = ref(false)
const showDatePicker = ref(false)
const completed = ref(!!localStorage.getItem('onboarding_completed'))

const patientName = ref('')
const gender = ref('male')
const birthDate = ref('')
const medicalHistory = ref('')

const minDate = new Date(1900, 0, 1)
const maxDate = new Date()

const visible = computed({
  get: () => !completed.value && patientStore.loaded && (patientStore.patientCount === 0 || step.value > 1),
  set: () => {},
})

watch(visible, (isVisible) => {
  document.body.classList.toggle('onboarding-active', isVisible)
}, { immediate: true })

onUnmounted(() => {
  document.body.classList.remove('onboarding-active')
})

function onDateConfirm({ selectedValues }) {
  birthDate.value = selectedValues.join('-')
  showDatePicker.value = false
}

async function handleCreatePatient() {
  if (!patientName.value.trim()) {
    showToast('请输入患者姓名')
    return
  }
  creating.value = true
  try {
    const patient = await patientStore.createPatient({
      patient_name: patientName.value.trim(),
      gender: gender.value,
      birth_date: birthDate.value || undefined,
      medical_history: medicalHistory.value || undefined,
    })
    showSuccessToast('患者创建成功')
    step.value = 2
  } catch (err) {
    showToast(err.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function nextStep() {
  step.value = 3
}

function goUpload() {
  markCompleted()
  router.push('/home/image-report')
}

function goFeature(path) {
  markCompleted()
  router.push(path)
}

function markCompleted() {
  completed.value = true
  localStorage.setItem('onboarding_completed', '1')
}

function complete() {
  markCompleted()
}
</script>

<style scoped>
.onboarding-guide {
  padding: 24px 20px;
  max-width: 480px;
  margin: 0 auto;
}

.step-indicator {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 24px;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--bg-secondary);
  transition: all 0.3s;
}

.step-dot.active {
  width: 24px;
  background: var(--primary-color);
}

.step-dot.done {
  background: var(--success-color);
}

.step-content {
  text-align: center;
}

.step-icon {
  margin-bottom: 16px;
}

.step-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px;
}

.step-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 16px;
}

.step-form {
  text-align: left;
  margin-top: 16px;
}

.step-actions {
  margin-top: 24px;
  padding: 0 16px;
}

.upload-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 140px;
  border: 2px dashed var(--border-color);
  border-radius: 12px;
  margin: 16px 0;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.upload-preview:active {
  border-color: var(--primary-color);
}

.feature-list {
  text-align: left;
  margin: 16px 0;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border-radius: 10px;
  margin-bottom: 8px;
  cursor: pointer;
}

.feature-item:active {
  background: var(--bg-elevated);
}

.feature-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.feature-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

:global(body.onboarding-active .drawer-trigger-btn),
:global(body.onboarding-active .tabbar-wrapper),
:global(body.onboarding-active .van-tabbar) {
  display: none !important;
}
</style>
