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
          v-for="i in 4"
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

      <!-- 步骤2: 配置 AI 模型（已配置时自动跳过） -->
      <template v-if="step === 2">
        <div class="step-content">
          <div class="step-icon">
            <van-icon name="magic-stick-o" size="48" color="var(--primary-color)" />
          </div>
          <h2 class="step-title">配置 AI 模型</h2>
          <p class="step-desc">
            检验解读与报告识别依赖 AI 模型服务；AI 会诊由 AgentTeams 平台承接，无需在此配置。
            填入 OpenAI 兼容的 API 信息即可开始使用。
          </p>

          <van-form @submit="handleSaveLLMConfig" class="step-form">
            <van-cell-group inset>
              <van-field name="same-model" label="相同模型">
                <template #input>
                  <van-switch v-model="llmSameModel" size="20px" />
                  <span class="same-model-label">{{ llmSameModel ? '解读与 OCR 共用' : '分别配置' }}</span>
                </template>
              </van-field>

              <!-- 共用一组配置 -->
              <template v-if="llmSameModel">
                <van-field
                  v-model="sharedLlm.api_base"
                  label="API 地址"
                  placeholder="如 https://api.example.com/v1"
                  clearable
                />
                <van-field
                  v-model="sharedLlm.model_name"
                  label="模型名称"
                  placeholder="如 gpt-4o / glm-5"
                  clearable
                />
                <van-field
                  v-model="sharedLlm.api_key"
                  label="API Key"
                  type="password"
                  placeholder="留空则沿用已保存密钥"
                  clearable
                />
              </template>

              <!-- 解读 / OCR 分别配置 -->
              <template v-else>
                <div
                  v-for="g in [
                    { group: 'interpretation', label: '解读', fields: interpLlm },
                    { group: 'ocr', label: 'OCR', fields: ocrLlm },
                  ]"
                  :key="g.group"
                >
                  <div class="group-divider">{{ g.label }}</div>
                  <van-field
                    v-model="g.fields.api_base"
                    label="API 地址"
                    placeholder="如 https://api.example.com/v1"
                    clearable
                  />
                  <van-field
                    v-model="g.fields.model_name"
                    label="模型名称"
                    placeholder="如 gpt-4o / glm-5"
                    clearable
                  />
                  <van-field
                    v-model="g.fields.api_key"
                    label="API Key"
                    type="password"
                    placeholder="留空则沿用已保存密钥"
                    clearable
                  />
                </div>
              </template>
            </van-cell-group>

            <div class="step-actions">
              <van-button round block type="primary" native-type="submit" :loading="savingLlm">
                保存并继续
              </van-button>
              <van-button round block plain style="margin-top: 8px" @click="nextStep">
                稍后再说
              </van-button>
            </div>
          </van-form>
        </div>
      </template>

      <!-- 步骤3: 上传报告 -->
      <template v-if="step === 3">
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

      <!-- 步骤4: 锚点式功能导览入口 -->
      <template v-if="step === 4">
        <div class="step-content">
          <div class="step-icon">
            <van-icon name="guide-o" size="48" color="var(--primary-color)" />
          </div>
          <h2 class="step-title">快速了解</h2>
          <p class="step-desc">
            花 30 秒跟随导览了解主页各模块的用途，帮您快速上手。
          </p>

          <div class="step-actions">
            <van-button round block type="primary" @click="startTour">
              开始导览
            </van-button>
            <van-button round block plain style="margin-top: 8px" @click="markCompleted">
              跳过引导
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

  <!-- 锚点式功能导览 -->
  <GuideTour v-if="tourActive" :steps="tourSteps" @finish="onTourFinish" />
</template>

<script setup>
import { ref, reactive, computed, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { llmConfigApi } from '@/api/llmConfig'
import { useResponsive } from '@/composables/useResponsive'
import GuideTour from '@/components/home/GuideTour.vue'

const { isDesktop } = useResponsive()
const router = useRouter()
const patientStore = usePatientStore()

const step = ref(1)
const creating = ref(false)
const showDatePicker = ref(false)
const completed = ref(!!localStorage.getItem('onboarding_completed'))
const tourActive = ref(false)
const guideHidden = ref(false)

const patientName = ref('')
const gender = ref('male')
const birthDate = ref('')
const medicalHistory = ref('')

const minDate = new Date(1900, 0, 1)
const maxDate = new Date()

const visible = computed({
  get: () => !completed.value && !guideHidden.value && patientStore.loaded && (patientStore.patientCount === 0 || step.value > 1),
  set: () => {},
})

// LLM 已配置（解读+OCR 均可用）时跳过配置步骤，直接进入上传报告
async function advanceAfterCreate() {
  try {
    const res = await llmConfigApi.getLLMConfigStatus()
    step.value = res.configured ? 3 : 2
  } catch {
    // 状态查询失败时保守展示配置步骤，由用户自行选择
    step.value = 2
  }
}

// ===== 首启 AI 模型配置表单 =====
const llmSameModel = ref(true)
const sharedLlm = reactive({ api_base: '', model_name: '', api_key: '' })
const interpLlm = reactive({ api_base: '', model_name: '', api_key: '' })
const ocrLlm = reactive({ api_base: '', model_name: '', api_key: '' })
const savingLlm = ref(false)
let llmPrefetched = false

// 进入配置步骤时回填已生效的非敏感值；敏感掩码不回填，
// 非管理者（无权读取）静默降级为空白表单
async function prefetchLlmConfig() {
  if (llmPrefetched) return
  llmPrefetched = true
  try {
    const res = await llmConfigApi.getLLMConfigs()
    for (const item of res.items || []) {
      if (item.is_secret || !item.config_value) continue
      const target = item.config_group === 'interpretation' ? interpLlm
        : item.config_group === 'ocr' ? ocrLlm : null
      const field = item.config_key.replace(/^(interpretation|ocr)_/, '')
      if (target && field in target) target[field] = item.config_value
    }
    // 两组现有地址/模型一致时默认共用模式并带入共享表单
    const same = interpLlm.api_base === ocrLlm.api_base && interpLlm.model_name === ocrLlm.model_name
    llmSameModel.value = same
    if (same) {
      Object.assign(sharedLlm, { api_base: interpLlm.api_base, model_name: interpLlm.model_name })
    }
  } catch {
    // 保持空白表单，由用户自行填写
  }
}

/** 将一组表单字段映射为该组的 updates（空值/掩码密钥跳过） */
function buildGroupUpdates(group, fields) {
  const updates = []
  for (const field of ['api_base', 'model_name', 'api_key']) {
    const val = (fields[field] || '').trim()
    if (!val || (field === 'api_key' && val.startsWith('****'))) continue
    updates.push({ config_key: `${group}_${field}`, config_value: val })
  }
  return updates
}

async function handleSaveLLMConfig() {
  const targets = llmSameModel.value
    ? [['interpretation', sharedLlm], ['ocr', sharedLlm]]
    : [['interpretation', interpLlm], ['ocr', ocrLlm]]
  const groupUpdates = targets.map(([group, fields]) => [group, buildGroupUpdates(group, fields)])
  if (groupUpdates.every(([, updates]) => !updates.length)) {
    showToast('请至少填写 API 地址与模型名称')
    return
  }

  savingLlm.value = true
  try {
    for (const [group, updates] of groupUpdates) {
      if (updates.length) await llmConfigApi.updateLLMConfigGroup(group, updates)
    }
    showSuccessToast('AI 模型配置已保存')
    nextStep()
  } catch (e) {
    showToast(e.response?.data?.detail || '保存失败')
  } finally {
    savingLlm.value = false
  }
}

watch(step, (v) => {
  if (v === 2) prefetchLlmConfig()
})

// 锚点导览步骤（按端型区分；目标元素不存在时 GuideTour 自动跳过）
const tourSteps = computed(() => {
  if (isDesktop.value) {
    return [
      { selector: '.desktop-sidebar', title: '功能导航', desc: '所有功能模块的入口都在左侧导航中，包括报告、时间线、会诊等。' },
      { selector: '[data-tour="search"]', title: '全局搜索', desc: '一键搜索指标、药品和各类报告。' },
      { selector: '[data-tour="stats"]', title: '健康概览', desc: '汇总各类报告数量与异常指标，健康状态一目了然。' },
      { selector: '[data-tour="indicators"]', title: '指标关注', desc: '这里展示您收藏指标的最新结果与历史趋势。' },
    ]
  }
  return [
    { selector: '[data-tour="quick-actions"]', title: '快捷操作', desc: '上传报告图片、发起 AI 会诊等常用功能都在这里。' },
    { selector: '[data-tour="stats"]', title: '健康概览', desc: '汇总各类报告数量与异常指标，点击可查看详情。' },
    { selector: '[data-tour="indicators"]', title: '指标关注', desc: '这里展示您收藏指标的最新结果与历史趋势。' },
    { selector: '[data-tour="features"]', title: '全部功能', desc: '用药管理、知识库、随访提醒等更多功能入口。' },
    { selector: '.tabbar-wrapper', title: '底部导航', desc: '在主页、时间线、报告等主要页面之间快速切换。' },
  ]
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
    await advanceAfterCreate()
  } catch (err) {
    showToast(err.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

function nextStep() {
  step.value = step.value === 2 ? 3 : 4
}

function goUpload() {
  markCompleted()
  router.push('/home/image-report')
}

function startTour() {
  guideHidden.value = true
  tourActive.value = true
}

function onTourFinish() {
  tourActive.value = false
  markCompleted()
}

function markCompleted() {
  completed.value = true
  localStorage.setItem('onboarding_completed', '1')
  // 广播引导完成事件，供 LLM 配置提醒弹窗衔接
  window.dispatchEvent(new CustomEvent('onboarding-completed'))
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

.same-model-label {
  margin-left: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.group-divider {
  padding: 8px 16px 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
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

:global(body.onboarding-active .drawer-trigger-btn),
:global(body.onboarding-active .tabbar-wrapper),
:global(body.onboarding-active .van-tabbar) {
  display: none !important;
}
</style>
