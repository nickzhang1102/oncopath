<template>
  <van-dialog
    :show="visible"
    :show-confirm-button="false"
    :close-on-click-overlay="false"
    class="llm-config-prompt"
  >
    <div class="prompt-content">
      <div class="prompt-icon">
        <van-icon name="magic-stick-o" size="44" color="var(--primary-color)" />
      </div>
      <h2 class="prompt-title">配置 AI 模型</h2>
      <p class="prompt-desc">
        使用检验解读、报告识别等 AI 功能前，需要先配置对应的 LLM 模型服务。
        您可以在「AI 模型配置」中填入 OpenAI 兼容的 API 地址与密钥。
      </p>
      <div class="prompt-actions">
        <van-button round block type="primary" @click="goConfig">
          立即配置
        </van-button>
        <van-button round block plain style="margin-top: 8px" @click="dismiss">
          稍后再说
        </van-button>
      </div>
    </div>
  </van-dialog>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { llmConfigApi } from '@/api/llmConfig'
import { usePatientStore } from '@/stores/patient'

/**
 * LLM 未配置提醒弹窗：
 * 首次打开主页且会诊 LLM 未配置时弹出；「稍后再说」后本浏览器不再弹出，
 * 引导（OnboardingGuide）进行期间不弹，引导完成后自动衔接检查。
 */
const router = useRouter()
const patientStore = usePatientStore()
const visible = ref(false)

const DISMISS_KEY = 'llm_config_prompt_dismissed'
let checking = false

async function check() {
  if (checking || visible.value) return
  if (localStorage.getItem(DISMISS_KEY)) return
  // 新用户引导进行中则等待其完成（由 onboarding-completed 事件再次触发）
  if (document.body.classList.contains('onboarding-active')) return
  // 引导显隐依赖患者数据就绪；未就绪时延迟重试，
  // 避免弹窗与引导叠加，也避免直接放弃导致弹窗丢失
  if (!patientStore.loaded) {
    setTimeout(check, 800)
    return
  }

  checking = true
  try {
    const res = await llmConfigApi.getLLMConfigStatus()
    if (!res.configured) {
      visible.value = true
    }
  } catch {
    // 状态查询失败时静默，不打扰用户
  } finally {
    checking = false
  }
}

function goConfig() {
  visible.value = false
  router.push('/admin/llm-config')
}

function dismiss() {
  visible.value = false
  localStorage.setItem(DISMISS_KEY, '1')
}

function handleOnboardingCompleted() {
  // 首启引导刚完成，衔接检查 LLM 配置状态
  setTimeout(check, 400)
}

onMounted(() => {
  window.addEventListener('onboarding-completed', handleOnboardingCompleted)
  setTimeout(check, 600)
})

onUnmounted(() => {
  window.removeEventListener('onboarding-completed', handleOnboardingCompleted)
})
</script>

<style scoped>
.prompt-content {
  padding: 28px 20px 20px;
  text-align: center;
}

.prompt-icon {
  margin-bottom: 12px;
}

.prompt-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 10px;
}

.prompt-desc {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0 0 18px;
}

.prompt-actions {
  padding: 0 8px;
}
</style>
