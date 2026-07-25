<template>
  <div class="feature-grid-section">
    <div class="section-header">
      <h3 class="section-title">{{ title }}</h3>
    </div>
    <div class="feature-grid">
      <div
        v-for="item in items"
        :key="item.path || item.label"
        class="feature-item"
        @click="handleClick(item)"
      >
        <div class="feature-icon">
          <van-icon :name="item.icon" size="22" />
        </div>
        <span class="feature-label">{{ item.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

defineProps({
  title: { type: String, required: true },
  items: {
    type: Array,
    required: true,
    // { icon, label, path?, external? }
  },
})

function handleClick(item) {
  if (item.external) {
    window.open(item.path, '_blank')
  } else if (item.path) {
    router.push(item.path)
  }
}
</script>

<style scoped>
.feature-grid-section {
  background: var(--bg-surface-alpha);
  border-radius: var(--radius-xl);
  padding: 16px;
  box-shadow: 0 4px 16px var(--primary-alpha-10);
  backdrop-filter: blur(10px);
}

.section-header {
  margin-bottom: 12px;
}

.section-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 4px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.feature-item:active {
  background: var(--primary-alpha-8);
  transform: scale(0.95);
}

.feature-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  background: var(--primary-alpha-8);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  margin-bottom: 6px;
  transition: transform 0.2s;
}

.feature-item:active .feature-icon {
  transform: scale(0.9);
}

.feature-label {
  font-size: 12px;
  color: var(--text-primary);
  text-align: center;
  line-height: 1.3;
}
</style>
