<!-- front/src/views/ShareConsultation.vue -->
<template>
  <div class="share-consultation">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <van-loading size="36" color="var(--primary-color)" vertical>加载中...</van-loading>
    </div>

    <!-- 错误状态 -->
    <div v-if="loadError" class="error-container">
      <van-empty :description="loadError" image="error" />
      <van-button type="primary" @click="retryLoad">重试</van-button>
    </div>

    <!-- 密码验证 -->
    <div v-if="requiresPassword" class="password-container">
      <div class="password-card">
        <van-icon name="lock" class="lock-icon" />
        <h3 class="password-title">该分享链接需要密码访问</h3>
        <van-field
          v-model="sharePassword"
          type="password"
          placeholder="请输入访问密码"
          maxlength="32"
          @keyup.enter="verifyPassword"
        />
        <van-button type="primary" block :loading="verifying" @click="verifyPassword">
          验证
        </van-button>
      </div>
    </div>

    <!-- 主内容 -->
    <template v-if="!loading && !loadError && !requiresPassword">
      <!-- 顶部信息条 -->
      <header class="share-header">
        <div class="header-top">
          <div class="header-left">
            <van-icon name="shield-o" class="share-icon" />
            <div class="header-info">
              <span class="share-label">会诊分享</span>
              <span class="share-title">{{ conversationTitle }}</span>
            </div>
          </div>
          <div class="header-right">
            <div class="status-badge" :class="statusClass">
              <span class="status-dot"></span>
              <span class="status-text">{{ statusText }}</span>
            </div>
          </div>
        </div>
      </header>

      <!-- Tab 切换 -->
      <div class="tab-bar">
        <button
          :class="['tab', { active: activeTab === 'leader' }]"
          @click="activeTab = 'leader'"
        >Leader 消息</button>
        <button
          :class="['tab', { active: activeTab === 'agents' }]"
          @click="activeTab = 'agents'"
        >专家报告</button>
        <button
          :class="['tab', { active: activeTab === 'final' }]"
          @click="activeTab = 'final'"
        >最终报告</button>
      </div>

      <!-- 内容区域 -->
      <div class="share-content" ref="contentRef">
        <!-- Leader 消息 -->
        <div v-show="activeTab === 'leader'" class="leader-view">
          <template v-if="leaderMessages.length > 0">
            <div class="message-list">
              <div
                v-for="(msg, idx) in reversedLeaderMessages"
                :key="idx"
                class="message-item"
                :class="getMessageClass(msg.type)"
              >
                <div class="message-header">
                  <span class="message-type">{{ getMessageLabel(msg.type) }}</span>
                  <span v-if="msg.time" class="message-time">{{ msg.time }}</span>
                </div>
                <div class="message-body">
                  <MarkdownRenderer v-if="shouldRenderMarkdown(msg.type)" :content="msg.content" />
                  <div v-else class="message-plain">{{ msg.content }}</div>
                </div>
              </div>
            </div>
          </template>
          <van-empty v-else description="暂无 Leader 消息" image="search" />
        </div>

        <!-- 专家报告 -->
        <div v-show="activeTab === 'agents'" class="agents-view">
          <template v-if="agentResults.length > 0">
            <van-collapse v-model="activeAgentNames" accordion>
              <van-collapse-item
                v-for="agent in agentResults"
                :key="agent.agent_id"
                :name="agent.agent_id"
              >
                <template #title>
                  <div class="agent-header">
                    <div class="agent-avatar" :style="{ background: getAgentColor(agent.agent_id) }">
                      {{ agent.agent_name?.[0] || '?' }}
                    </div>
                    <span class="agent-name">{{ agent.agent_name }}</span>
                    <van-tag v-if="isAgentCompleted(agent)" type="success" size="medium" round>已完成</van-tag>
                    <van-tag v-else-if="agent.status === 'failed'" type="danger" size="medium" round>失败</van-tag>
                    <van-tag v-else type="primary" size="medium" round>{{ agent.status }}</van-tag>
                  </div>
                </template>
                <div class="agent-content">
                  <MarkdownRenderer v-if="agent.content" :content="agent.content" />
                  <div v-else class="agent-error">{{ agent.error || '暂无分析内容' }}</div>
                </div>
              </van-collapse-item>
            </van-collapse>
          </template>
          <van-empty v-else description="暂无专家报告" image="search" />
        </div>

        <!-- 最终报告 -->
        <div v-show="activeTab === 'final'" class="final-report-view">
          <div v-if="finalReport" class="report-card">
            <div class="report-header">
              <van-icon name="records" class="report-icon" />
              <span class="report-title">最终报告</span>
            </div>
            <div class="report-content">
              <MarkdownRenderer :content="finalReport" />
            </div>
          </div>
          <van-empty v-else description="暂无最终报告" image="search" />
        </div>
      </div>

      <!-- 底部信息 -->
      <footer class="share-footer">
        <span class="footer-text">本页面为会诊分享链接，仅供参考</span>
      </footer>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// 最新消息在顶部
const reversedLeaderMessages = computed(() => [...leaderMessages.value].reverse())
import { useRoute } from 'vue-router'
import { useConversationsStore } from '@/stores/conversations'
import { showToast } from 'vant'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

const route = useRoute()
const conversationsStore = useConversationsStore()

// 状态
const loading = ref(true)
const loadError = ref(null)
const requiresPassword = ref(false)
const verifying = ref(false)
const sharePassword = ref('')
const activeTab = ref('agents')
const activeAgentNames = ref([])
const contentRef = ref(null)

// 数据
const sessionData = ref(null)
const conversationTitle = ref('')
const leaderState = ref('idle')
const leaderMessages = ref([])
const agentResults = ref([])
const finalReport = ref('')

// 计算属性
const statusClass = computed(() => {
  const state = leaderState.value
  if (state === 'completed') return 'status-success'
  if (state === 'failed' || state === 'stopped') return 'status-error'
  return 'status-active'
})

const statusText = computed(() => {
  const stateMap = {
    'idle': '空闲',
    'assessing': '评估中',
    'questioning': '提问中',
    'forming_team': '组建团队',
    'web_search': '搜索中',
    'monitoring': '执行中',
    'summarizing': '汇总中',
    'completed': '已完成',
    'stopped': '已停止',
    'failed': '失败'
  }
  return stateMap[leaderState.value] || '未知'
})

// 专家状态判断（兼容历史分享数据）
function isAgentCompleted(agent) {
  return agent.status === 'success' || agent.status === 'completed' || (agent.content && !agent.error)
}

// 专家头像颜色
function getAgentColor(agentId) {
  const colors = [
    'var(--primary-color)', 'var(--success-color)', 'var(--warning-color)', 'var(--danger-color)', 'var(--color-purple)',
    'var(--info-color)', 'var(--color-pink)', 'var(--color-lime)', 'var(--color-orange)', 'var(--color-indigo)'
  ]
  let hash = 0
  for (let i = 0; i < agentId.length; i++) {
    hash = agentId.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

// Leader 消息相关
function getMessageLabel(type) {
  const map = {
    'assessment': '评估',
    'assessment_result': '评估结果',
    'question': '追问',
    'answer': '用户回答',
    'team_config': '团队配置',
    'team_ready': '团队就绪',
    'team_forming': '组建团队',
    'team_start': '团队启动',
    'team_complete': '团队完成',
    'leader_thinking': '思考过程',
    'leader_summarizing': '汇总中',
    'execution_status': '执行状态',
    'agent_status': '专家状态',
    'agent_error': '专家错误',
    'web_search_result': '搜索结果',
    'discussion_round': '讨论',
    'error': '错误',
    'api_retry': '重试',
  }
  return map[type] || type
}

function getMessageClass(type) {
  const highlightTypes = ['assessment_result', 'question', 'team_ready', 'team_complete', 'discussion_round', 'web_search_result', 'error']
  return highlightTypes.includes(type) ? 'message-highlight' : ''
}

function shouldRenderMarkdown(type) {
  const markdownTypes = ['assessment_result', 'team_config', 'team_ready', 'discussion_round', 'leader_thinking', 'leader_summarizing']
  return markdownTypes.includes(type)
}

// 将后端 messages 转换为前端可渲染格式（复用 leader.js 的历史消息解析逻辑）
function parseMessages(messages) {
  if (!messages?.length) return []

  return messages.map(msg => {
    let contentText = ''
    const msgType = msg.message_type || msg.type

    if (typeof msg.content === 'string') {
      contentText = msg.content
    } else if (typeof msg.content === 'object' && msg.content !== null) {
      switch (msgType) {
        case 'assessment':
        case 'assessment_result':
          contentText = `## 评估结果\n\n**评分**: ${(msg.content.score || 0)}/100\n\n${msg.content.details?.analysis || ''}`
          break
        case 'question':
        case 'leader_question':
          if (msg.content.questions && Array.isArray(msg.content.questions)) {
            const questionTexts = msg.content.questions.map(q =>
              typeof q === 'object' && q !== null ? (q.text || q.field || JSON.stringify(q)) : String(q)
            )
            contentText = questionTexts.map((q, i) => `${i + 1}. ${q}`).join('\n\n')
          }
          break
        case 'answer':
          if (msg.content.text) {
            contentText = msg.content.text
          } else if (msg.content.answers && Array.isArray(msg.content.answers)) {
            contentText = '## 用户回答\n\n' + msg.content.answers.map((a, i) => `${i + 1}. ${a}`).join('\n\n')
          }
          break
        case 'team_config':
        case 'team_ready':
          const tc = msg.content
          const tcAgents = tc.agent_details || tc.agents || []
          contentText = `## 团队配置完成\n\n**团队成员** (${tcAgents.length} 位专家):\n` +
            tcAgents.map((agent, i) => `${i + 1}. **${agent.agent_name || agent.name}**${agent.reason || agent.description ? ` - ${agent.reason || agent.description}` : ''}`).join('\n')
          break
        case 'leader_thinking':
          contentText = msg.content.text || msg.content.content || ''
          break
        case 'leader_summarizing':
          contentText = msg.content.text || msg.content.content || msg.content.message || ''
          break
        case 'team_forming':
          contentText = msg.content.content || msg.content.text || '正在组建专家团队...'
          break
        case 'team_start':
          contentText = `团队已启动，共 ${msg.content.total_agents || 0} 个 Agent 开始执行...`
          break
        case 'team_complete':
          contentText = `团队执行完成：成功 ${msg.content.successful || 0}/${msg.content.total_agents || 0}，失败 ${msg.content.failed || 0}/${msg.content.total_agents || 0}`
          break
        case 'agent_status':
          contentText = `${msg.content.agent_name || msg.content.agent_id || '专家'}：${msg.content.status === 'completed' ? '分析完成' : msg.content.status === 'running' ? '正在分析' : msg.content.status}`
          break
        case 'agent_error':
          contentText = `${msg.content.agent_name || msg.content.agent_id || '专家'}执行失败：${msg.content.error || '未知错误'}`
          break
        case 'discussion_round':
          contentText = `第 ${msg.content.round || 1} 轮讨论：达成 ${(msg.content.consensus_points || []).length} 项共识，${(msg.content.divergence_points || []).length} 项分歧${msg.content.consensus_reached ? '（已达成共识）' : ''}`
          break
        case 'web_search_result':
          contentText = msg.content.summary || ''
          break
        case 'error':
          contentText = `错误：${msg.content.message || '未知错误'}`
          break
        case 'api_retry':
          contentText = `${msg.content.message || 'API调用失败'}，正在重试 (${msg.content.attempt || '?'}/${msg.content.max_attempts || '?'})...`
          break
        case 'execution_status':
          const stateLabels = {
            assessing: '正在评估需求...',
            questioning: '需要补充信息',
            forming_team: '正在组建专家团队...',
            web_search: '正在搜索相关医学信息...',
            monitoring: '专家团队分析中...',
            discussing: '专家团队讨论中...',
            summarizing: '正在生成综合报告...',
            completed: '会诊已完成',
            stopped: '会诊已停止',
            failed: '会诊执行失败'
          }
          contentText = stateLabels[msg.content.state] || msg.content.state || ''
          break
        default:
          if (msg.content.text) contentText = msg.content.text
          else if (msg.content.content) contentText = msg.content.content
          else if (msg.content.message) contentText = msg.content.message
          else contentText = ''
      }
    }

    return {
      content: contentText,
      time: msg.created_at ? new Date(msg.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : '',
      type: msgType,
    }
  }).filter(msg => msg.content)
}

// 加载分享数据
async function loadSharedData() {
  const token = route.params.token
  if (!token) {
    loadError.value = '无效的分享链接'
    loading.value = false
    return
  }

  const result = await conversationsStore.fetchConversationByToken(token)
  if (!result.success) {
    loadError.value = result.error || '分享链接无效或已过期'
    loading.value = false
    return
  }

  const data = result.data

  // 密码保护检查
  if (data.requires_password) {
    requiresPassword.value = true
    loading.value = false
    return
  }

  extractData(data)
  loading.value = false
}

function extractData(data) {
  sessionData.value = data

  // 提取对话信息
  const conversation = data.conversation
  conversationTitle.value = conversation?.title || '虚拟会诊'

  // 提取会话状态
  const session = data.session
  leaderState.value = session?.state || 'idle'

  // 提取 Leader 消息
  const rawMessages = data.messages || []
  leaderMessages.value = parseMessages(rawMessages)

  // 提取专家结果
  const rawAgentResults = data.agent_results || []
  agentResults.value = rawAgentResults.map(result => ({
    agent_id: result.agent_id,
    agent_name: result.agent_name,
    status: result.status,
    content: result.content,
    error: result.error,
  }))

  // 默认展开第一个完成的专家
  const completedAgents = agentResults.value.filter(a => isAgentCompleted(a) && a.content)
  if (completedAgents.length > 0) {
    activeAgentNames.value = completedAgents[0].agent_id
  }

  // 提取最终报告
  const reportData = data.final_report
  if (reportData) {
    finalReport.value = reportData.report || ''
  }
}

// 密码验证
async function verifyPassword() {
  if (!sharePassword.value) {
    showToast('请输入密码')
    return
  }

  verifying.value = true
  try {
    const token = route.params.token
    const result = await conversationsStore.verifySharePassword(token, sharePassword.value)
    if (result.success) {
      requiresPassword.value = false
      extractData(result.data)
    } else {
      showToast(result.error || '密码错误')
    }
  } catch (error) {
    showToast('验证失败')
  } finally {
    verifying.value = false
  }
}

async function retryLoad() {
  loadError.value = null
  loading.value = true
  await loadSharedData()
}

onMounted(() => {
  loadSharedData()
})
</script>

<style scoped>
.share-consultation {
  min-height: 100vh;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: var(--space-4);
}

.password-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: var(--space-4);
}

.password-card {
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-6) var(--space-5);
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.lock-icon {
  font-size: 40px;
  color: var(--primary-color);
}

.password-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.share-header {
  flex-shrink: 0;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: var(--glass-border);
  box-shadow: var(--glass-shadow);
  padding: var(--space-3) var(--space-4);
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
}

.share-icon {
  font-size: 24px;
  color: var(--primary-color);
  flex-shrink: 0;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.share-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.share-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-right {
  flex-shrink: 0;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: var(--text-xs);
}

.status-badge.status-active {
  background: var(--primary-alpha-10);
  color: var(--primary-color);
}

.status-badge.status-success {
  background: var(--status-normal-bg);
  color: var(--success-color);
}

.status-badge.status-error {
  background: var(--status-danger-bg);
  color: var(--danger-color);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.tab-bar {
  display: flex;
  flex-shrink: 0;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
  padding: 0 var(--space-3);
}

.tab {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.2s, border-color 0.2s;
}

.tab.active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

.tab:hover:not(.active) {
  color: var(--text-primary);
}

.share-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3);
}

/* Leader 消息 */
.message-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.message-item {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}

.message-item.message-highlight {
  border-left: 3px solid var(--primary-color);
}

.message-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-1);
}

.message-type {
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--primary-color);
}

.message-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.message-body {
  font-size: var(--text-sm);
  line-height: 1.7;
  color: var(--text-primary);
}

.message-plain {
  white-space: pre-wrap;
  word-break: break-word;
}

/* 专家报告 */
.agent-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.agent-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--bg-surface);
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.agent-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}

.agent-content {
  font-size: var(--text-sm);
  line-height: 1.7;
  color: var(--text-primary);
  padding: var(--space-2) 0;
}

.agent-error {
  font-size: var(--text-sm);
  color: var(--danger-color);
  padding: var(--space-2) 0;
}

/* 最终报告 */
.report-card {
  background: var(--bg-surface);
  border: 1px solid var(--primary-alpha-20);
  border-left: 3px solid var(--primary-color);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.report-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--primary-alpha-20);
}

.report-icon {
  font-size: 20px;
  color: var(--primary-color);
}

.report-title {
  font-size: var(--text-lg);
  font-weight: 600;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.report-content {
  font-size: var(--text-sm);
  line-height: 1.7;
  color: var(--text-primary);

  :deep(h1), :deep(h2), :deep(h3) {
    margin-top: 16px;
    margin-bottom: 8px;
    color: var(--text-primary);
  }

  :deep(h1) { font-size: 1.25rem; }
  :deep(h2) { font-size: 1.125rem; }
  :deep(h3) { font-size: 1rem; }

  :deep(p) {
    margin-bottom: 8px;
  }

  :deep(ul), :deep(ol) {
    padding-left: 20px;
    margin-bottom: 8px;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 8px;
  }

  :deep(table th),
  :deep(table td) {
    border: 1px solid var(--border-dark);
    padding: 6px 8px;
    font-size: 13px;
  }

  :deep(table th) {
    background: var(--bg-elevated);
    font-weight: 500;
  }
}

/* 底部 */
.share-footer {
  flex-shrink: 0;
  text-align: center;
  padding: var(--space-3);
  border-top: 1px solid var(--border-color);
  background: var(--bg-surface);
}

.footer-text {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

/* 响应式 */
@media (max-width: 768px) {
  .share-header {
    padding: var(--space-2) var(--space-3);
  }

  .report-card {
    padding: var(--space-3);
  }

  .report-content {
    font-size: var(--text-xs);

    :deep(h1) { font-size: 1.125rem; }
    :deep(h2) { font-size: 1rem; }
    :deep(h3) { font-size: 0.9375rem; }
  }
}
</style>
