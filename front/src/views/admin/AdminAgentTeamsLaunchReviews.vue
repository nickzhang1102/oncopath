<template>
  <div class="launch-reviews">
    <section class="safety-notice">
      <van-icon name="shield-o" size="24" />
      <div>
        <h2>AgentTeams 会诊启动复核</h2>
        <p>
          这里仅查询 AgentTeams 已有启动记录，不会重新发送 launch POST。
          只有在外部系统确认 request ID 没有创建记录后，才能解除本地启动锁。
        </p>
      </div>
    </section>

    <div class="toolbar">
      <div>
        <strong>待人工复核</strong>
        <span class="count">{{ intents.length }} 条</span>
      </div>
      <van-button
        size="small"
        icon="replay"
        :loading="loading"
        :disabled="actionBusy"
        @click="loadIntents"
      >
        刷新
      </van-button>
    </div>

    <div v-if="loading && !intents.length" class="page-state">
      <van-loading size="28px" color="var(--primary-color)" vertical>加载中...</van-loading>
    </div>
    <div v-else-if="error && !intents.length" class="page-state error-state">
      <van-icon name="warning-o" size="42" />
      <p>{{ error }}</p>
      <van-button size="small" type="primary" @click="loadIntents">重试</van-button>
    </div>
    <div v-else-if="!intents.length" class="page-state">
      <van-icon name="passed" size="44" color="var(--success-color)" />
      <p>当前没有待人工复核的启动意图</p>
    </div>

    <div v-else class="review-grid">
      <section class="intent-list" aria-label="待人工复核启动意图">
        <button
          v-for="intent in intents"
          :key="intent.id"
          type="button"
          class="intent-card"
          :class="{ selected: selectedId === intent.id }"
          @click="selectIntent(intent.id)"
        >
          <span class="intent-heading">
            <span>患者 #{{ intent.patient_id }}</span>
            <van-tag type="warning" plain>人工复核</van-tag>
          </span>
          <code>{{ intent.request_id }}</code>
          <span class="intent-error">{{ intent.last_error_message || '启动结果无法自动确认' }}</span>
          <span class="intent-meta">
            尝试 {{ intent.attempt_count }} 次 · {{ formatDate(intent.updated_at) }}
          </span>
        </button>
      </section>

      <section class="detail-panel" aria-live="polite">
        <div v-if="detailLoading" class="detail-state">
          <van-loading size="26px">加载详情...</van-loading>
        </div>
        <template v-else-if="selectedIntent">
          <div class="detail-heading">
            <div>
              <h3>启动意图 #{{ selectedIntent.id }}</h3>
              <p>本页不展示或解密患者提示词。</p>
            </div>
            <van-tag :type="selectedIntent.launch_status === 'manual_review' ? 'warning' : 'default'">
              {{ statusLabel(selectedIntent.launch_status) }}
            </van-tag>
          </div>

          <dl class="detail-list">
            <div><dt>Request ID</dt><dd><code>{{ selectedIntent.request_id }}</code></dd></div>
            <div><dt>患者 / 账户</dt><dd>#{{ selectedIntent.patient_id }} / #{{ selectedIntent.account_id }}</dd></div>
            <div><dt>本地会诊</dt><dd>#{{ selectedIntent.conversation_id }}</dd></div>
            <div><dt>远端会诊</dt><dd>{{ selectedIntent.external_conversation_id || '尚未确认' }}</dd></div>
            <div><dt>错误代码</dt><dd>{{ selectedIntent.last_error_code || '-' }}</dd></div>
            <div><dt>错误说明</dt><dd>{{ selectedIntent.last_error_message || '-' }}</dd></div>
            <div><dt>Payload Hash</dt><dd><code>{{ selectedIntent.payload_hash }}</code></dd></div>
            <div>
              <dt>加密快照</dt>
              <dd>{{ selectedIntent.payload_retained ? '为只读对账暂时保留' : '已清理' }}</dd>
            </div>
            <div><dt>最后更新</dt><dd>{{ formatDate(selectedIntent.updated_at) }}</dd></div>
          </dl>

          <div class="action-note">
            <van-icon name="info-o" />
            <span>先执行“只读重新对账”。单次未查询到记录不能证明远端未创建。</span>
          </div>

          <div class="detail-actions">
            <van-button
              type="primary"
              icon="search"
              :loading="reconciling"
              :disabled="actionBusy || selectedIntent.launch_status !== 'manual_review'"
              @click="reconcileSelected"
            >
              只读重新对账
            </van-button>
            <van-button
              type="danger"
              plain
              icon="warning-o"
              :disabled="actionBusy || selectedIntent.launch_status !== 'manual_review'"
              @click="openResolveDialog"
            >
              确认未创建并解除锁
            </van-button>
          </div>

          <div class="audit-section">
            <h4>操作审计</h4>
            <div v-if="!selectedIntent.audits?.length" class="audit-empty">暂无人工操作记录</div>
            <ol v-else class="audit-list">
              <li v-for="audit in selectedIntent.audits" :key="audit.id">
                <div>
                  <strong>{{ auditActionLabel(audit.action) }}</strong>
                  <span>{{ audit.before_status }} → {{ audit.after_status }}</span>
                </div>
                <p v-if="audit.reason">{{ audit.reason }}</p>
                <small>管理员 #{{ audit.actor_account_id || '-' }} · {{ formatDate(audit.created_at) }}</small>
              </li>
            </ol>
          </div>
        </template>
      </section>
    </div>

    <van-dialog
      v-model:show="resolveDialogVisible"
      title="确认远端未创建"
      show-cancel-button
      confirm-button-text="确认并解除锁"
      confirm-button-color="var(--danger-color)"
      :before-close="beforeResolveClose"
    >
      <div class="resolve-dialog">
        <p>
          此操作会将本地启动意图标记为拒绝，并允许用户重新发起可能产生费用的新会诊。
          必须先在 AgentTeams 外部核验 request ID 没有创建记录。
        </p>
        <van-field
          v-model="resolveReason"
          type="textarea"
          rows="4"
          maxlength="1000"
          show-word-limit
          label="核验理由"
          placeholder="至少 10 个字符，写明核验位置与结果"
          :error-message="reasonError"
        />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { showSuccessToast, showToast } from 'vant'
import { adminApi } from '@/api/admin'

const intents = ref([])
const selectedId = ref(null)
const selectedIntent = ref(null)
const loading = ref(false)
const detailLoading = ref(false)
const reconciling = ref(false)
const resolving = ref(false)
const error = ref('')
const resolveDialogVisible = ref(false)
const resolveReason = ref('')
const reasonError = ref('')

const actionBusy = computed(() => reconciling.value || resolving.value)

function errorMessage(errorValue, fallback) {
  const detail = errorValue?.response?.data?.detail
  if (typeof detail === 'string') return detail
  return detail?.message || fallback
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function statusLabel(status) {
  const labels = {
    manual_review: '人工复核',
    accepted: '已确认创建',
    rejected: '已拒绝',
    confirming: '自动确认中',
  }
  return labels[status] || status
}

function auditActionLabel(action) {
  return action === 'confirmed_not_created' ? '确认远端未创建' : '只读重新对账'
}

async function loadIntents(options = {}) {
  loading.value = true
  error.value = ''
  try {
    intents.value = await adminApi.getAgentTeamsLaunchIntents({ status: 'manual_review' })
    if (!intents.value.length) {
      selectedId.value = null
      selectedIntent.value = null
      return
    }
    const keepId = options.preferredId || selectedId.value
    const next = intents.value.find(item => item.id === keepId) || intents.value[0]
    await selectIntent(next.id)
  } catch (errorValue) {
    error.value = errorMessage(errorValue, '加载人工复核列表失败')
  } finally {
    loading.value = false
  }
}

async function selectIntent(id) {
  selectedId.value = id
  detailLoading.value = true
  try {
    selectedIntent.value = await adminApi.getAgentTeamsLaunchIntent(id)
  } catch (errorValue) {
    showToast(errorMessage(errorValue, '加载启动意图详情失败'))
  } finally {
    detailLoading.value = false
  }
}

async function reconcileSelected() {
  if (!selectedIntent.value) return
  reconciling.value = true
  try {
    const result = await adminApi.reconcileAgentTeamsLaunchIntent(selectedIntent.value.id)
    selectedIntent.value = result
    showSuccessToast(result.launch_status === 'accepted' ? '已确认远端会诊' : '只读对账已完成')
    await loadIntents({ preferredId: result.id })
  } catch (errorValue) {
    showToast(errorMessage(errorValue, '只读对账失败'))
  } finally {
    reconciling.value = false
  }
}

function openResolveDialog() {
  resolveReason.value = ''
  reasonError.value = ''
  resolveDialogVisible.value = true
}

async function beforeResolveClose(action) {
  if (action !== 'confirm') return true
  const reason = resolveReason.value.trim()
  if (reason.length < 10) {
    reasonError.value = '请填写至少 10 个字符的外部核验理由'
    return false
  }
  resolving.value = true
  reasonError.value = ''
  try {
    const result = await adminApi.resolveAgentTeamsLaunchIntent(selectedIntent.value.id, {
      decision: 'confirmed_not_created',
      reason,
    })
    selectedIntent.value = result
    showSuccessToast('已解除启动锁')
    await loadIntents()
    return true
  } catch (errorValue) {
    reasonError.value = errorMessage(errorValue, '处置失败，请重新核验状态')
    return false
  } finally {
    resolving.value = false
  }
}

onMounted(loadIntents)
</script>

<style scoped>
.launch-reviews {
  max-width: 1180px;
}

.safety-notice {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 18px 20px;
  border: 1px solid var(--primary-alpha-20);
  border-radius: 12px;
  background: var(--primary-alpha-3);
  color: var(--primary-color);
}

.safety-notice h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 20px;
}

.safety-notice p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 18px 0 12px;
}

.count {
  margin-left: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.page-state,
.detail-state {
  display: flex;
  min-height: 260px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-radius: 12px;
  background: var(--bg-surface);
  color: var(--text-secondary);
}

.error-state {
  color: var(--danger-color);
}

.review-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.72fr) minmax(0, 1.28fr);
  gap: 16px;
  align-items: start;
}

.intent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.intent-card {
  width: 100%;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: var(--bg-surface);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
}

.intent-card:hover,
.intent-card:focus-visible,
.intent-card.selected {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-alpha-10);
  outline: none;
}

.intent-heading,
.intent-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.intent-heading {
  margin-bottom: 8px;
  font-weight: 600;
}

.intent-card code,
.detail-list code {
  display: block;
  overflow-wrap: anywhere;
  color: var(--text-secondary);
  font-size: 12px;
}

.intent-error {
  display: -webkit-box;
  margin: 10px 0;
  overflow: hidden;
  color: var(--danger-color);
  font-size: 12px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.intent-meta {
  color: var(--text-tertiary);
  font-size: 11px;
}

.detail-panel {
  min-height: 420px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-surface);
}

.detail-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-light);
}

.detail-heading h3,
.audit-section h4 {
  margin: 0;
  color: var(--text-primary);
}

.detail-heading p {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}

.detail-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
  padding: 10px 20px;
}

.detail-list > div {
  min-width: 0;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
}

.detail-list > div:nth-child(odd) {
  padding-right: 18px;
}

.detail-list dt {
  margin-bottom: 4px;
  color: var(--text-secondary);
  font-size: 11px;
}

.detail-list dd {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.5;
}

.action-note {
  display: flex;
  gap: 8px;
  margin: 14px 20px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--status-info-bg);
  color: var(--info-color);
  font-size: 12px;
  line-height: 1.5;
}

.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 0 20px 18px;
}

.audit-section {
  padding: 18px 20px;
  border-top: 1px solid var(--border-light);
}

.audit-empty {
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 12px;
}

.audit-list {
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}

.audit-list li {
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
}

.audit-list li > div {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
}

.audit-list p {
  margin: 6px 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.audit-list small {
  color: var(--text-tertiary);
}

.resolve-dialog {
  padding: 10px 16px 18px;
}

.resolve-dialog > p {
  margin: 0 0 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--status-danger-bg);
  color: var(--danger-color);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 900px) {
  .review-grid {
    grid-template-columns: 1fr;
  }

  .intent-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .safety-notice {
    padding: 14px;
  }

  .intent-list,
  .detail-list {
    grid-template-columns: 1fr;
  }

  .detail-list > div:nth-child(odd) {
    padding-right: 0;
  }

  .detail-actions {
    flex-direction: column;
  }

  .detail-actions :deep(.van-button) {
    width: 100%;
  }
}
</style>
