<template>
  <Teleport to="body">
    <Transition name="guide-fade">
      <div v-if="visible" class="at-guide-mask" @click.self="handleSkip">
        <div class="at-guide-card">
          <!-- 步骤指示器 -->
          <div class="guide-steps">
            <span
              v-for="(step, i) in stepCount"
              :key="i"
              :class="['step-dot', { active: currentStep === i }]"
            />
            <button class="guide-skip" type="button" @click="handleSkip">跳过</button>
          </div>

          <!-- 步骤一：功能与部署说明 -->
          <div v-if="currentStep === 0" class="guide-step-body">
            <div class="hero-icon">
              <van-icon name="cluster-o" size="30" />
            </div>
            <h2 class="guide-title">虚拟会诊由 AgentTeams 提供</h2>
            <p class="guide-desc">
              虚拟会诊如同组织一场多学科会诊：OncoPath
              将患者的检验、检查、病理等记录整理成会诊材料，
              由开源项目 <strong>AgentTeams</strong> 的多名
              AI 专科专家并行分析。首次使用前需先部署
              AgentTeams 并完成集成配置。
            </p>
            <div class="feature-row">
              <div class="feature-chip"><van-icon name="records-o" />整理病历</div>
              <div class="feature-chip"><van-icon name="friends-o" />AI 专科专家</div>
              <div class="feature-chip"><van-icon name="notes-o" />会诊报告</div>
            </div>
          </div>

          <!-- 步骤二：部署后运行效果示意 -->
          <div v-else class="guide-step-body">
            <h2 class="guide-title">部署后的虚拟会诊流程</h2>
            <p class="guide-desc">发起会诊后，AI 专科专家团队基于会诊材料并行研判，汇总为综合会诊报告。</p>

            <!-- 有配置素材时展示图片，否则渲染内置 CSS 动画示意 -->
            <img
              v-if="demoAsset && !demoAssetFailed"
              :src="demoAsset"
              alt="AgentTeams consultation preview"
              class="demo-image"
              @error="demoAssetFailed = true"
            />
            <div v-else class="demo-stage" aria-hidden="true">
              <!-- 会诊材料（来自 OncoPath 病历） -->
              <div class="material-row">
                <span v-for="m in materials" :key="m.label" class="material-chip">
                  <van-icon :name="m.icon" />{{ m.label }}
                </span>
              </div>
              <div class="flow-lines">
                <span v-for="i in 3" :key="i" class="flow-line" :style="{ animationDelay: `${(i - 1) * 0.4}s` }" />
              </div>
              <!-- AI 专科专家并行分析 -->
              <div class="expert-row">
                <div
                  v-for="(expert, i) in experts"
                  :key="expert.label"
                  class="expert-node"
                  :style="{ animationDelay: `${i * 0.5}s` }"
                >
                  <div class="expert-avatar"><van-icon name="user-o" /></div>
                  <span class="expert-label">{{ expert.label }}</span>
                </div>
              </div>
              <div class="flow-lines">
                <span class="flow-line single" />
              </div>
              <!-- 综合会诊报告 -->
              <div class="report-card">
                <van-icon name="description" />
                <span>综合会诊报告</span>
              </div>
            </div>

            <van-button
              block
              type="primary"
              icon="guide-o"
              class="guide-cta"
              @click="$emit('cta', ctaUrl)"
            >前往 GitHub 获取 AgentTeams</van-button>
          </div>

          <!-- 底部操作 -->
          <div class="guide-actions">
            <van-button
              v-if="currentStep > 0"
              plain
              size="small"
              @click="currentStep--"
            >上一步</van-button>
            <span class="action-spacer" />
            <van-button
              type="primary"
              size="small"
              round
              @click="currentStep < stepCount - 1 ? currentStep++ : handleDone()"
            >{{ currentStep < stepCount - 1 ? '下一步' : '开始使用' }}</van-button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
// 引导已读标记的 localStorage key，供宿主页面判断是否需要弹出引导
export const GUIDE_SEEN_KEY = 'oncopath_agentteams_guide_seen'
</script>

<script setup>
import { computed, ref, watch } from 'vue'
import { AGENTTEAMS_REPO_URL } from '@/utils/agentteamsErrorUx'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  upsell: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['update:show', 'cta'])

const currentStep = ref(0)
const stepCount = 2
const demoAssetFailed = ref(false)

// 会诊材料与专科专家（示意，与真实虚拟会诊业务一致）
const materials = [
  { icon: 'label-o', label: '检验' },
  { icon: 'photo-o', label: '检查' },
  { icon: 'description', label: '病理' },
]

const experts = [
  { label: '肿瘤内科' },
  { label: '影像科' },
  { label: '病理科' },
]

const visible = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value),
})

const demoAsset = computed(() => props.upsell?.demo_asset_url || '')
const ctaUrl = computed(() => props.upsell?.cta_url || AGENTTEAMS_REPO_URL)

watch(() => props.show, (show) => {
  if (show) {
    currentStep.value = 0
    demoAssetFailed.value = false
  }
})

function markSeen() {
  try {
    localStorage.setItem(GUIDE_SEEN_KEY, '1')
  } catch {
    // localStorage 不可用时静默跳过：仅影响下次不再自动弹出
  }
}

function handleDone() {
  markSeen()
  visible.value = false
}

function handleSkip() {
  markSeen()
  visible.value = false
}
</script>

<style scoped>
.at-guide-mask {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.at-guide-card {
  width: min(92vw, 480px);
  max-height: 86vh;
  overflow-y: auto;
  padding: var(--space-5);
  border-radius: var(--radius-xl, 20px);
  background: var(--bg-surface);
  border: 1px solid var(--glass-border, transparent);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.25);
  animation: cardFloatIn 0.55s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes cardFloatIn {
  from {
    opacity: 0;
    transform: translateY(36px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* 遮罩淡入淡出 */
.guide-fade-enter-active,
.guide-fade-leave-active {
  transition: opacity 0.3s ease;
}

.guide-fade-enter-from,
.guide-fade-leave-to {
  opacity: 0;
}

/* 步骤指示器 */
.guide-steps {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: var(--space-4);
}

.step-dot {
  width: 20px;
  height: 4px;
  border-radius: 2px;
  background: var(--border-color);
  transition: background 0.3s ease, width 0.3s ease;
}

.step-dot.active {
  width: 32px;
  background: var(--primary-color);
}

.guide-skip {
  margin-left: auto;
  padding: 4px 8px;
  border: 0;
  background: transparent;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
  cursor: pointer;
}

.guide-step-body {
  animation: stepFadeIn 0.35s ease;
}

@keyframes stepFadeIn {
  from {
    opacity: 0;
    transform: translateX(12px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.hero-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin: 0 auto var(--space-3);
  border-radius: 18px;
  color: var(--primary-color);
  background: var(--primary-alpha-10);
  animation: heroGlow 2.4s ease-in-out infinite;
}

@keyframes heroGlow {
  0%,
  100% {
    box-shadow: 0 0 0 0 var(--primary-alpha-10);
  }
  50% {
    box-shadow: 0 0 24px 4px var(--primary-alpha-10);
  }
}

.guide-title {
  margin: 0 0 var(--space-2);
  text-align: center;
  font-size: var(--text-lg, 18px);
  font-weight: 700;
  color: var(--text-primary);
}

.guide-desc {
  margin: 0 0 var(--space-4);
  text-align: center;
  font-size: var(--text-sm);
  line-height: 1.7;
  color: var(--text-secondary);
}

.feature-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}

.feature-chip {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 9px 4px;
  border-radius: var(--radius-md, 8px);
  font-size: var(--text-xs);
  white-space: nowrap;
  color: var(--primary-color);
  background: var(--primary-alpha-5);
  border: 1px solid var(--primary-alpha-10);
}

/* ===== CSS 动画示意舞台 ===== */
.demo-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  margin-bottom: var(--space-3);
  border-radius: var(--radius-md, 12px);
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
}

.material-row {
  display: flex;
  gap: var(--space-2);
}

.material-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: var(--text-xs);
  color: var(--primary-color);
  background: var(--primary-alpha-5);
  border: 1px solid var(--primary-alpha-10);
  animation: materialFloat 2.4s ease-in-out infinite;
}

@keyframes materialFloat {
  0%,
  100% {
    transform: translateY(0);
    opacity: 0.75;
  }
  50% {
    transform: translateY(-3px);
    opacity: 1;
  }
}

.flow-line.single {
  width: 60px;
  height: 2px;
  background: linear-gradient(to right, var(--primary-color), var(--success-color));
  animation: lineGrowX 2.4s ease-in-out infinite;
}

@keyframes lineGrowX {
  0%,
  100% {
    transform: scaleX(0.2);
    opacity: 0.3;
  }
  45% {
    transform: scaleX(1);
    opacity: 1;
  }
}

.expert-row {
  display: flex;
  gap: var(--space-5);
}

.expert-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  animation: expertPulse 2.4s ease-in-out infinite;
}

@keyframes expertPulse {
  0%,
  100% {
    opacity: 0.45;
    transform: scale(0.96);
  }
  30% {
    opacity: 1;
    transform: scale(1.04);
  }
}

.expert-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-size: 16px;
  color: var(--color-white);
  background: var(--primary-color);
  box-shadow: 0 4px 12px var(--primary-alpha-20, rgba(0, 0, 0, 0.15));
}

.expert-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.flow-lines {
  display: flex;
  gap: var(--space-5);
}

.flow-line {
  width: 2px;
  height: 16px;
  border-radius: 1px;
  background: linear-gradient(to bottom, var(--primary-color), var(--success-color));
  transform-origin: top;
  animation: lineGrow 2.4s ease-in-out infinite;
}

@keyframes lineGrow {
  0%,
  100% {
    transform: scaleY(0.2);
    opacity: 0.3;
  }
  45% {
    transform: scaleY(1);
    opacity: 1;
  }
}

.report-card {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: var(--text-sm);
  color: var(--success-color);
  background: var(--status-normal-bg);
  border: 1px solid var(--success-color);
  animation: reportBounce 2.4s ease-in-out infinite;
}

@keyframes reportBounce {
  0%,
  100% {
    transform: translateY(0);
  }
  55% {
    transform: translateY(-3px);
  }
}

.demo-image {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  margin-bottom: var(--space-4);
  border-radius: var(--radius-md, 12px);
  border: 1px solid var(--border-color);
}

.guide-cta {
  --van-button-border-radius: 10px;
}

/* 底部操作区 */
.guide-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.action-spacer {
  flex: 1;
}

@media (max-width: 380px) {
  .expert-row,
  .flow-lines {
    gap: var(--space-3);
  }

  .feature-row {
    grid-template-columns: 1fr;
  }

  .feature-chip {
    justify-content: flex-start;
  }
}
</style>
