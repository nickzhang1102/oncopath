<template>
  <div class="agentteams-embed-frame">
    <header class="embed-header">
      <div class="header-left">
        <button class="back-button" type="button" @click="$emit('back')" aria-label="返回">
          <van-icon name="arrow-left" />
        </button>
        <div class="title-block">
          <span class="title">虚拟会诊</span>
          <span class="subtitle">AgentTeams</span>
        </div>
      </div>
      <span :class="['status-badge', statusClass]">
        <span class="status-dot"></span>
        {{ statusText }}
      </span>
    </header>

    <main class="embed-body">
      <div v-if="!loaded && !loadFailed" class="embed-loading">
        <van-loading size="28" color="var(--primary-color)" vertical>加载中...</van-loading>
      </div>
      <div v-if="loadFailed" class="embed-error">
        <van-empty description="无法打开 AgentTeams 会诊页面">
          <van-button type="primary" size="small" @click="retryFrame">重试</van-button>
        </van-empty>
      </div>
      <iframe
        :key="frameKey"
        ref="embedFrame"
        v-show="!loadFailed"
        class="embed-iframe"
        :src="session.embed_url"
        title="AgentTeams consultation"
        allow="clipboard-read; clipboard-write"
        @load="handleLoad"
        @error="handleLoadError"
      />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const EMBED_STATUS_MESSAGE = 'oncopath:embed-status'
const EMBED_RENEW_MESSAGE = 'oncopath:embed-renew-required'
const EMBED_LOAD_TIMEOUT_MS = 15000
const EMBED_STATES = new Set([
  'created',
  'idle',
  'assessing',
  'monitoring',
  'questioning',
  'forming_team',
  'running',
  'web_search',
  'executing',
  'summarizing',
  'completed',
  'failed',
  'stopped'
])

const props = defineProps({
  session: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['back', 'status-change', 'renew-required'])

const loaded = ref(false)
const loadFailed = ref(false)
const embedFrame = ref(null)
const currentStatus = ref(props.session?.status || 'created')
const frameKey = ref(0)
let loadTimer = null

watch(
  () => props.session?.status,
  status => {
    if (status) currentStatus.value = status
  }
)

watch(
  () => props.session?.embed_url,
  () => resetFrameLoad(),
)

function clearLoadTimer() {
  if (!loadTimer) return
  clearTimeout(loadTimer)
  loadTimer = null
}

function startLoadTimer() {
  clearLoadTimer()
  loadTimer = setTimeout(() => {
    if (!loaded.value) loadFailed.value = true
  }, EMBED_LOAD_TIMEOUT_MS)
}

function resetFrameLoad() {
  loaded.value = false
  loadFailed.value = false
  startLoadTimer()
}

function handleLoad() {
  loaded.value = true
  loadFailed.value = false
  clearLoadTimer()
}

function handleLoadError() {
  loadFailed.value = true
  clearLoadTimer()
}

function retryFrame() {
  frameKey.value += 1
  resetFrameLoad()
}

function getEmbedOrigin() {
  try {
    return new URL(props.session.embed_url, window.location.href).origin
  } catch {
    return ''
  }
}

function handleEmbedStatus(event) {
  if (event.source !== embedFrame.value?.contentWindow) return
  if (event.origin !== getEmbedOrigin()) return
  if (event.data?.type === EMBED_RENEW_MESSAGE) {
    emit('renew-required')
    return
  }
  if (event.data?.type !== EMBED_STATUS_MESSAGE) return
  if (!EMBED_STATES.has(event.data.status)) return

  currentStatus.value = event.data.status
  emit('status-change', event.data.status)
}

onMounted(() => {
  window.addEventListener('message', handleEmbedStatus)
  startLoadTimer()
})
onUnmounted(() => {
  window.removeEventListener('message', handleEmbedStatus)
  clearLoadTimer()
})

const statusText = computed(() => {
  const map = {
    created: '已启动',
    idle: '已启动',
    running: '分析中',
    assessing: '评估中',
    forming_team: '组队中',
    web_search: '检索中',
    monitoring: '分析中',
    executing: '分析中',
    summarizing: '分析中',
    questioning: '待补充',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止',
    unknown: '未知'
  }
  return map[currentStatus.value] || '分析中'
})

const statusClass = computed(() => {
  if (currentStatus.value === 'failed' || currentStatus.value === 'stopped') return 'status-error'
  if (currentStatus.value === 'completed') return 'status-success'
  return 'status-active'
})
</script>

<style scoped>
.agentteams-embed-frame {
  height: 100vh;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.embed-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 10px 14px;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: var(--glass-border);
  box-shadow: var(--glass-shadow);
}

.header-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.back-button {
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-surface);
  font-size: 19px;
  color: var(--text-primary);
  cursor: pointer;
  flex-shrink: 0;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.back-button:active {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-sm);
}

.title-block {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.3;
}

.subtitle {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  line-height: 1.3;
}

.status-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 26px;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: var(--text-xs);
  font-weight: 500;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-active {
  background: var(--primary-alpha-10);
  color: var(--primary-color);
}

.status-success {
  background: var(--status-normal-bg);
  color: var(--success-color);
}

.status-error {
  background: var(--status-danger-bg);
  color: var(--danger-color);
}

.embed-body {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.embed-iframe {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: var(--bg-surface);
}

.embed-loading,
.embed-error {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
}

@media (max-width: 768px) {
  .agentteams-embed-frame {
    height: calc(100vh - var(--tabbar-height) - env(safe-area-inset-bottom));
  }

  .embed-header {
    padding: 8px 10px;
  }

  .back-button {
    width: 34px;
    height: 34px;
  }
}
</style>
