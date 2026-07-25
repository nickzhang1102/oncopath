<template>
  <div class="agentteams-config">
    <div v-if="loading" class="loading-state">
      <van-loading size="32px" color="var(--primary-color)" vertical>加载中...</van-loading>
    </div>

    <div v-else-if="error" class="error-state">
      <van-icon name="warning-o" size="48" color="var(--danger-color)" />
      <p>{{ error }}</p>
      <van-button size="small" type="primary" icon="replay" @click="loadConfig">重试</van-button>
    </div>

    <form v-else class="config-form" @submit.prevent="handleSave">
      <section class="overview-panel">
        <div class="overview-main">
          <div class="overview-icon">
            <van-icon name="cluster-o" size="24" />
          </div>
          <div class="overview-copy">
            <h2>AgentTeams 集成</h2>
            <p>连接外部多 Agent 会诊服务，OncoPath 负责资料整理、启动代理和嵌入展示。</p>
          </div>
        </div>

        <div class="overview-actions">
          <div class="status-stack">
            <van-tag :type="statusMeta.type" size="medium" plain>{{ statusMeta.label }}</van-tag>
            <span v-if="config.has_integration_secret" class="secret-mask">{{ config.integration_secret }}</span>
          </div>
          <van-button type="primary" icon="passed" native-type="submit" :loading="saving">
            保存配置
          </van-button>
        </div>
      </section>

      <div class="config-grid">
        <section class="config-card main-card">
          <div class="card-heading">
            <div>
              <h3>基础配置</h3>
              <p>保存后普通用户端会按启用状态开放会诊入口。</p>
            </div>
            <van-switch v-model="form.enabled" size="24px" />
          </div>

          <van-cell-group class="field-group" :border="false">
            <van-field
              v-model="form.base_url"
              label="访问地址"
              placeholder="/agentteams 或 https://agentteams.example.com"
              clearable
            >
              <template #left-icon>
                <van-icon name="link-o" />
              </template>
            </van-field>
            <van-field
              v-model="form.integration_secret"
              label="集成密钥"
              type="password"
              :placeholder="config.has_integration_secret ? '留空则不修改' : '首次保存必填'"
              clearable
            >
              <template #left-icon>
                <van-icon name="shield-o" />
              </template>
            </van-field>
          </van-cell-group>
        </section>

        <section class="config-card deploy-card">
          <div class="card-heading compact">
            <div>
              <h3>部署状态</h3>
              <p>{{ updatedText }}</p>
            </div>
          </div>

          <div class="deploy-list">
            <div class="deploy-item">
              <span class="deploy-label">前端入口</span>
              <span class="deploy-value">{{ form.base_url || '未填写' }}</span>
            </div>
            <div class="deploy-item">
              <span class="deploy-label">密钥状态</span>
              <span class="deploy-value">{{ config.has_integration_secret ? '已保存' : '未保存' }}</span>
            </div>
            <div class="deploy-item">
              <span class="deploy-label">入口状态</span>
              <span class="deploy-value">{{ form.enabled ? '已启用' : '已停用' }}</span>
            </div>
          </div>

          <div class="deploy-note">
            <van-icon name="info-o" />
            <span>docker-compose 默认支持 `/agentteams` 同站反代；外部域名部署可填写完整 HTTPS 地址。</span>
          </div>
        </section>
      </div>
    </form>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted } from 'vue'
import { showSuccessToast, showToast } from 'vant'
import { adminApi } from '@/api/admin'

const loading = ref(true)
const saving = ref(false)
const error = ref('')

const config = reactive({
  configured: false,
  enabled: false,
  base_url: '',
  integration_secret: '',
  has_integration_secret: false,
  updated_at: null,
})

const form = reactive({
  enabled: false,
  base_url: '',
  integration_secret: '',
})

const statusMeta = computed(() => {
  if (!config.configured) return { label: '未配置', type: 'warning' }
  if (!form.enabled) return { label: '已配置 / 停用', type: 'default' }
  return { label: '已配置 / 启用', type: 'success' }
})

const updatedText = computed(() => {
  if (!config.updated_at) return '尚未保存配置'
  return `最后更新：${new Date(config.updated_at).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })}`
})

function applyConfig(data) {
  Object.assign(config, {
    configured: Boolean(data.configured),
    enabled: Boolean(data.enabled),
    base_url: data.base_url || '',
    integration_secret: data.integration_secret || '',
    has_integration_secret: Boolean(data.has_integration_secret),
    updated_at: data.updated_at || null,
  })

  form.enabled = config.enabled
  form.base_url = config.base_url
  form.integration_secret = ''
}

async function loadConfig() {
  loading.value = true
  error.value = ''
  try {
    const data = await adminApi.getAgentTeamsConfig()
    applyConfig(data)
  } catch (e) {
    error.value = e.response?.data?.detail || '加载 AgentTeams 配置失败'
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const data = await adminApi.updateAgentTeamsConfig({
      enabled: form.enabled,
      base_url: form.base_url,
      integration_secret: form.integration_secret,
    })
    applyConfig(data)
    showSuccessToast('保存成功')
  } catch (e) {
    showToast(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.agentteams-config {
  max-width: 1040px;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 12px;
  color: var(--text-secondary);
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.overview-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-color, #ebedf0);
  border-radius: 12px;
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
}

.overview-main {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 14px;
}

.overview-icon {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--primary-color);
  background: var(--primary-alpha-10);
  border: 1px solid var(--primary-alpha-20);
}

.overview-copy {
  min-width: 0;
}

.overview-copy h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.3;
}

.overview-copy p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.overview-actions,
.status-stack {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.secret-mask {
  color: var(--text-tertiary, #999);
  font-family: monospace;
  font-size: 13px;
  white-space: nowrap;
}

.config-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.75fr);
  gap: 18px;
  align-items: start;
}

.config-card {
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-color, #ebedf0);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.card-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--primary-alpha-10);
  background: var(--primary-alpha-3);
}

.card-heading.compact {
  align-items: flex-start;
}

.card-heading h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
}

.card-heading p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.field-group {
  padding: 6px 0;
}

.field-group :deep(.van-cell) {
  padding: 14px 18px;
  background: transparent;
}

.field-group :deep(.van-field__left-icon) {
  color: var(--primary-color);
}

.field-group :deep(.van-field__label) {
  width: 92px;
  color: var(--text-secondary);
}

.deploy-list {
  display: flex;
  flex-direction: column;
}

.deploy-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 18px;
  border-bottom: 1px solid var(--border-light);
}

.deploy-label {
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.deploy-value {
  min-width: 0;
  color: var(--text-primary);
  font-family: monospace;
  font-size: 13px;
  text-align: right;
  word-break: break-all;
}

.deploy-note {
  display: flex;
  gap: 8px;
  margin: 14px 18px 18px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--status-info-bg);
  color: var(--info-color);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .overview-panel,
  .overview-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .overview-actions .van-button {
    width: 100%;
  }

  .status-stack {
    justify-content: space-between;
  }

  .config-grid {
    grid-template-columns: 1fr;
  }

  .field-group :deep(.van-field__label) {
    width: 78px;
  }
}
</style>
