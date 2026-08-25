<template>
  <van-popup
    v-model:show="visible"
    round
    closeable
    class="agentteams-error-dialog"
    :style="{ width: 'min(92vw, 480px)' }"
  >
    <div class="dialog-body">
      <header class="dialog-header">
        <div class="dialog-icon-wrap">
          <div class="dialog-icon">
            <van-icon name="warning-o" size="26" />
          </div>
        </div>
        <div class="dialog-title-block">
          <span class="dialog-kicker">处理提示</span>
          <h2>{{ error.title }}</h2>
        </div>
      </header>

      <div class="message-panel">
        <p class="dialog-message">{{ error.message }}</p>
      </div>

      <div :class="['dialog-actions', { single: !hasCta }]">
        <van-button block plain @click="visible = false">关闭</van-button>
        <van-button
          v-if="hasCta"
          block
          type="primary"
          icon="guide-o"
          @click="$emit('cta', error.cta_url)"
        >
          {{ error.cta_label }}
        </van-button>
      </div>
    </div>
  </van-popup>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  error: {
    type: Object,
    default: () => ({
      title: 'AgentTeams 会诊暂时不可用',
      message: '当前无法完成 AgentTeams 会诊操作，请稍后重试。',
      cta_label: '查看配置说明',
      cta_url: '',
    }),
  },
})

const emit = defineEmits(['update:show', 'cta'])

const visible = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value),
})

const hasCta = computed(() => Boolean(props.error?.cta_url))
</script>

<style scoped>
.agentteams-error-dialog {
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.dialog-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
  background: var(--bg-surface);
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding-right: 28px;
}

.dialog-icon-wrap {
  flex-shrink: 0;
  padding: 3px;
  border-radius: 12px;
  background: var(--status-warning-bg);
}

.dialog-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 10px;
  color: var(--warning-color);
  background: var(--bg-surface);
  border: 1px solid var(--warning-alpha-10);
}

.dialog-title-block {
  min-width: 0;
  padding-top: 2px;
}

.dialog-kicker {
  display: inline-flex;
  margin-bottom: 4px;
  color: var(--warning-color);
  font-size: 12px;
  font-weight: 600;
}

.dialog-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.35;
}

.message-panel {
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--status-warning-bg);
  border: 1px solid var(--warning-alpha-10);
}

.dialog-message {
  margin: 0;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.dialog-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding-top: 2px;
}

.dialog-actions.single {
  grid-template-columns: 1fr;
}

@media (max-width: 520px) {
  .dialog-body {
    padding: 20px 16px 16px;
  }

  .dialog-header h2 {
    font-size: 18px;
  }

  .dialog-actions {
    grid-template-columns: 1fr;
  }
}
</style>
