<template>
  <footer class="at-status-bar">
    <div class="status-left">
      <span :class="['status-dot', online ? 'online' : 'offline']" />
      <span class="status-text">
        虚拟会诊引擎 AgentTeams {{ online ? '已连接' : '未部署' }}
      </span>
    </div>
    <a
      class="repo-link"
      :href="repoUrl"
      target="_blank"
      rel="noopener noreferrer"
      @click.stop
    >
      <van-icon name="link-o" />
      <span>{{ repoHost }}</span>
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
const repoHost = repoUrl.replace(/^https?:\/\//, '')

const online = computed(() => Boolean(
  props.availability?.configured && props.availability?.enabled,
))
</script>

<style scoped>
.at-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  max-width: 1100px;
  margin: var(--space-4) auto 0;
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--border-color);
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
  .at-status-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
  }
}
</style>
