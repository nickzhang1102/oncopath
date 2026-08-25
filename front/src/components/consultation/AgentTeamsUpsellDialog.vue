<template>
  <van-popup
    v-model:show="visible"
    round
    closeable
    class="agentteams-upsell-dialog"
    :style="popupStyle"
  >
    <div class="dialog-body">
      <header class="dialog-header">
        <div class="dialog-icon-wrap">
          <div class="dialog-icon">
            <van-icon name="cluster-o" size="26" />
          </div>
        </div>
        <div class="dialog-title-block">
          <span class="dialog-kicker">AgentTeams</span>
          <h2>{{ displayUpsell.title }}</h2>
        </div>
      </header>

      <p class="dialog-message">{{ displayUpsell.message }}</p>

      <div class="capability-row">
        <div class="capability-item">
          <van-icon name="records-o" />
          <span>资料聚合</span>
        </div>
        <div class="capability-item">
          <van-icon name="cluster-o" />
          <span>多 Agent 会诊</span>
        </div>
        <div class="capability-item">
          <van-icon name="desktop-o" />
          <span>嵌入展示</span>
        </div>
      </div>

      <div v-if="showDemoAsset" class="demo-frame">
        <img
          :src="displayUpsell.demo_asset_url"
          alt="AgentTeams consultation demo"
          @error="demoAssetFailed = true"
        />
      </div>

      <div class="dialog-actions">
        <van-button block plain @click="visible = false">稍后再说</van-button>
        <van-button
          v-if="hasCta"
          block
          type="primary"
          icon="guide-o"
          @click="$emit('cta', displayUpsell.cta_url)"
        >
          {{ displayUpsell.cta_label }}
        </van-button>
      </div>
    </div>
  </van-popup>
</template>

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

const demoAssetFailed = ref(false)

const visible = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value),
})

const displayUpsell = computed(() => ({
  title: props.upsell?.title || '需要部署 AgentTeams 项目',
  message: props.upsell?.message || '虚拟会诊由开源的 AgentTeams 项目提供分析引擎，部署并完成集成配置后即可使用。',
  demo_asset_url: props.upsell?.demo_asset_url || '',
  cta_label: props.upsell?.cta_label || '获取 AgentTeams（开源自部署）',
  cta_url: props.upsell?.cta_url || AGENTTEAMS_REPO_URL,
}))

const hasCta = computed(() => Boolean(displayUpsell.value.cta_url))
const showDemoAsset = computed(() => Boolean(displayUpsell.value.demo_asset_url) && !demoAssetFailed.value)
const popupStyle = computed(() => ({
  width: 'min(92vw, 520px)',
}))

watch(() => props.upsell?.demo_asset_url, () => {
  demoAssetFailed.value = false
})
</script>

<style scoped>
.agentteams-upsell-dialog {
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
  background: var(--primary-alpha-10);
}

.dialog-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  border-radius: 10px;
  color: var(--primary-color);
  background: var(--bg-surface);
  border: 1px solid var(--primary-alpha-20);
}

.dialog-title-block {
  min-width: 0;
  padding-top: 2px;
}

.dialog-kicker {
  display: inline-flex;
  margin-bottom: 4px;
  color: var(--primary-color);
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

.dialog-message {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.capability-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.capability-item {
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 8px;
  border-radius: 8px;
  color: var(--primary-color);
  background: var(--primary-alpha-5);
  border: 1px solid var(--primary-alpha-10);
  font-size: 12px;
  white-space: nowrap;
}

.demo-frame {
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-primary);
  aspect-ratio: 16 / 9;
}

.demo-frame img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.dialog-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding-top: 2px;
}

@media (max-width: 520px) {
  .dialog-body {
    padding: 20px 16px 16px;
  }

  .dialog-header h2 {
    font-size: 18px;
  }

  .capability-row {
    grid-template-columns: 1fr;
  }

  .capability-item {
    justify-content: flex-start;
  }

  .dialog-actions {
    grid-template-columns: 1fr;
  }
}
</style>
