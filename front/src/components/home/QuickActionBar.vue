<template>
  <div class="quick-action-bar">
    <div class="action-item" @click="handleAction('upload')">
      <div class="action-icon upload-icon"><van-icon name="upgrade" /></div>
      <span class="action-text">上传报告</span>
    </div>
    <div class="action-item" @click="handleAction('search')">
      <div class="action-icon search-icon"><van-icon name="search" /></div>
      <span class="action-text">全局搜索</span>
    </div>
    <div class="action-item" @click="handleAction('knowledge')">
      <div class="action-icon knowledge-icon"><van-icon name="bookmark-o" /></div>
      <span class="action-text">知识库</span>
    </div>
    <div class="action-item" @click="handleAction('treatment')">
      <div class="action-icon treatment-icon"><van-icon name="gem-o" /></div>
      <span class="action-text">添加治疗</span>
    </div>
    <div class="action-item" @click="handleAction('status')">
      <div class="action-icon status-icon"><van-icon name="smile-o" /></div>
      <span class="action-text">补充状态</span>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const emit = defineEmits(['action'])

function handleAction(action) {
  switch (action) {
    case 'upload':
      router.push('/home/image-report?tab=upload')
      break
    case 'search':
      router.push('/home/search')
      break
    case 'knowledge':
      router.push('/home/knowledge')
      break
    case 'treatment':
      router.push('/home/treatment')
      break
    case 'status':
      router.push('/home/status')
      break
  }
  emit('action', action)
}
</script>

<style scoped>
.quick-action-bar {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  align-items: center;
  gap: 4px;
  background: var(--bg-surface-alpha);
  padding: 16px 12px;
  border-radius: 16px;
  box-shadow: 0 4px 16px var(--primary-alpha-10);
  backdrop-filter: blur(10px);
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  padding: 8px 6px;
  border-radius: 12px;
  min-width: 0;
}

.action-item:hover {
  transform: translateY(-2px);
  background: var(--primary-alpha-8);
}

.action-item:active {
  transform: scale(0.95);
}

.action-icon {
  font-size: 28px;
  margin-bottom: 6px;
  transition: transform 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-icon .van-icon {
  font-size: 28px;
}

.action-item:hover .action-icon {
  transform: scale(1.1);
}

.action-text {
  font-size: 13px;
  font-weight: 500;
  color: var(--primary-color);
  white-space: nowrap;
}

/* 图标动画效果 */
.upload-icon {
  animation: float 3s ease-in-out infinite;
}

.search-icon {
  animation: pulse 2.5s ease-in-out infinite;
}

.knowledge-icon {
  animation: float 3s ease-in-out infinite 0.5s;
}

.treatment-icon {
  animation: pulse 2s ease-in-out infinite;
}

.status-icon {
  animation: bounce 2s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-2px); }
}

@media (max-width: 430px) {
  .quick-action-bar {
    gap: 2px;
    padding: 12px 8px 12px 56px;
  }
  .action-item {
    padding: 6px 6px;
    min-width: 0;
    flex: 1;
  }

  .action-icon {
    font-size: 22px;
  }

  .action-text {
    font-size: 11px;
  }
}
</style>
