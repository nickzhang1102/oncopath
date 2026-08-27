<!-- front/src/views/ConversationDisplay.vue -->
<template>
  <div class="conversation-display">
    <div v-if="loading" class="loading-state">
      <van-loading size="36" color="var(--primary-color)" vertical>加载中...</van-loading>
    </div>

    <div v-else-if="loadErrorTitle" class="error-container">
      <van-empty :description="loadErrorTitle" />
      <p v-if="loadErrorMessage" class="error-message">{{ loadErrorMessage }}</p>
      <div class="error-actions">
        <van-button plain @click="handleBack">返回列表</van-button>
        <van-button v-if="agentTeamsError.title" plain @click="showAgentTeamsError = true">查看处理方式</van-button>
        <van-button type="primary" @click="retryLoad">重试</van-button>
      </div>
    </div>

    <AgentTeamsEmbedFrame
      v-else-if="externalSession"
      :session="externalSession"
      @back="handleBack"
      @status-change="handleExternalStatusChange"
    />

    <AgentTeamsErrorDialog
      v-model:show="showAgentTeamsError"
      :error="agentTeamsError"
      @cta="handleAgentTeamsErrorCta"
    />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AgentTeamsEmbedFrame from '@/components/consultation/AgentTeamsEmbedFrame.vue'
import AgentTeamsErrorDialog from '@/components/consultation/AgentTeamsErrorDialog.vue'
import { consultationApi } from '@/api/consultation'
import { getAgentTeamsErrorUx, isAgentTeamsError } from '@/utils/agentteamsErrorUx'
import { mergeAgentTeamsStatus } from '@/utils/agentteamsStatus'

const router = useRouter()
const route = useRoute()

const props = defineProps({
  token: {
    type: String,
    default: ''
  }
})

const loading = ref(true)
const loadErrorTitle = ref('')
const loadErrorMessage = ref('')
const showAgentTeamsError = ref(false)
const agentTeamsError = ref({})
const externalSession = ref(null)
let statusUpdateChain = Promise.resolve()

function handleBack() {
  router.push('/home/consultation')
}

function handleExternalStatusChange(status) {
  if (!externalSession.value) return
  const nextStatus = mergeAgentTeamsStatus(externalSession.value.status, status)
  if (nextStatus === externalSession.value.status) return
  externalSession.value = { ...externalSession.value, status: nextStatus }
  const conversationId = externalSession.value.conversation_id
  const patientId = Number(route.query.patient_id)
  statusUpdateChain = statusUpdateChain
    .then(() => consultationApi.updateAgentTeamsExternalStatus(
      conversationId,
      patientId,
      nextStatus,
    ))
    .then(updatedSession => {
      if (externalSession.value?.conversation_id !== conversationId) return
      externalSession.value = {
        ...externalSession.value,
        ...updatedSession,
        status: mergeAgentTeamsStatus(
          externalSession.value.status,
          updatedSession?.status,
        ),
      }
    })
    .catch(() => {})
}

function getRouteToken() {
  return props.token || route.params.token || ''
}

function setPlainError(title, message = '') {
  loadErrorTitle.value = title
  loadErrorMessage.value = message
  agentTeamsError.value = {}
}

function setAgentTeamsError(error) {
  const ux = getAgentTeamsErrorUx(error)
  agentTeamsError.value = ux
  loadErrorTitle.value = ux.title
  loadErrorMessage.value = ux.message
}

function handleAgentTeamsErrorCta(url) {
  if (!url) return
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function loadExternalSession() {
  const token = String(getRouteToken())
  const patientId = String(route.query.patient_id || '')
  externalSession.value = null
  loadErrorTitle.value = ''
  loadErrorMessage.value = ''
  agentTeamsError.value = {}

  if (!token) {
    router.push('/home/consultation')
    return
  }

  if (!/^\d+$/.test(token)) {
    setPlainError('此会诊记录不可用或已下线')
    return
  }

  if (!/^\d+$/.test(patientId)) {
    setPlainError('此会诊记录缺少患者上下文，请从会诊历史重新进入')
    return
  }

  try {
    externalSession.value = await consultationApi.getAgentTeamsExternalSession(
      token,
      patientId,
    )
  } catch (error) {
    if (error?.response?.status === 404) {
      setPlainError('此会诊记录不可用或已下线')
      return
    }
    if (isAgentTeamsError(error)) {
      setAgentTeamsError(error)
      return
    }
    setPlainError('加载失败')
  }
}

async function retryLoad() {
  loading.value = true
  try {
    await loadExternalSession()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await retryLoad()
})
</script>

<style scoped>
.conversation-display {
  height: 100vh;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.loading-state,
.error-container {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-container {
  flex-direction: column;
  gap: var(--space-4);
}

.error-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: center;
}

.error-message {
  max-width: min(88vw, 520px);
  margin: calc(-1 * var(--space-2)) 0 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.7;
  text-align: center;
}

@media (max-width: 768px) {
  .conversation-display {
    height: calc(100vh - var(--tabbar-height) - env(safe-area-inset-bottom));
  }
}
</style>
