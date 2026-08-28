<template>
  <footer class="at-status-bar">
    <div class="status-left">
      <span :class="['status-dot', online ? 'online' : 'offline']" />
      <span class="status-text" :title="statusTitle">
        虚拟会诊引擎 AgentTeams {{ statusText }}
      </span>
    </div>
    <!-- 项目一句话简介（仅桌面端显示，移动端只保留状态） -->
    <span class="status-intro">
      开源多智能体系统：多个 AI 医生模拟 MDT 多学科会诊，协作分析病情并出具综合报告
    </span>
    <a
      class="repo-link"
      :href="repoUrl"
      target="_blank"
      rel="noopener noreferrer"
      @click.stop
    >
      <van-icon name="link-o" />
      <span>GitHub</span>
    </a>
  </footer>
</template>

<script setup>
import { computed } from 'vue'
import { AGENTTEAMS_REPO_URL } from '@/utils/agentteamsErrorUx'

const props = defineProps({
  availability: {
    type: Object,
    default: null,
  },
})

// agentTeams 开源仓库地址（与后端 DEFAULT_UPSELL.cta_url 保持一致）
const repoUrl = AGENTTEAMS_REPO_URL

// 已连接 = 已配置 + 已启用 + 后端探测可达；协议版本不兼容时同样视为不可用。
const online = computed(() => Boolean(
  props.availability?.configured
  && props.availability?.enabled
  && props.availability?.reachable
  && props.availability?.protocol_version,
))

const statusText = computed(() => {
  const availability = props.availability
  if (!availability?.configured || !availability?.enabled) return '未部署'
  if (!availability?.reachable) return '暂不可达'
  if (!availability?.protocol_version) return '版本不兼容'
  return '已连接'
})

const statusTitle = computed(() => {
  const availability = props.availability
  if (!availability?.configured || !availability?.enabled) {
    return 'AgentTeams 未配置或未启用'
  }
  if (!availability?.reachable) return 'AgentTeams 服务当前不可达，请检查部署或稍后重试'
  if (!availability?.protocol_version) {
    return 'AgentTeams 协议版本与 OncoPath 不兼容，请升级 AgentTeams'
  }
  return `AgentTeams 协议版本 v${availability.protocol_version}`
})
</script>

<style scoped>
.at-status-bar {
  /* 固定在 Oncopath 全局页脚上方：sticky 钉住视口，margin-top:auto 在内容不足时贴底 */
  position: sticky;
  bottom: var(--footer-height);
  z-index: 5; /* 高于列表卡片，低于 tabbar(--z-nav)/页脚(900) */
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  max-width: 1100px;
  width: 100%;
  margin-top: auto;
  padding: var(--space-4) var(--space-4) var(--space-2);
  background: var(--bg-primary); /* 不透明背景，滚动时防止内容透出 */
  border-top: 1px solid var(--border-color);
}

/* 移动端 (/home 含 tabbar)：抬升到 tabbar + 页脚之上，与 AppFooter.above-tabbar 对齐 */
@media (max-width: 767.98px) {
  .at-status-bar {
    bottom: calc(var(--tabbar-height) + var(--footer-height));
  }
}

.status-left {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.online {
  background: var(--success-color);
  box-shadow: 0 0 6px var(--success-color);
}

.status-dot.offline {
  background: var(--text-quaternary);
}

.status-text {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-intro {
  flex: 1;
  min-width: 0;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.repo-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  font-size: var(--text-xs);
  color: var(--primary-color);
  text-decoration: none;
}

.repo-link:hover {
  text-decoration: underline;
}

@media (max-width: 480px) {
  /* 移动端简化：只保留引擎连接状态，简介与仓库链接不在小屏展示 */
  .status-intro,
  .repo-link {
    display: none;
  }
}
</style>
