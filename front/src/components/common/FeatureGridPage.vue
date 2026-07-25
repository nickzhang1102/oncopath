<template>
  <div class="feature-grid-page">
    <BackgroundAnimation />

    <div class="content-section">
      <div class="content-card">
        <h1 class="page-title">{{ title }}</h1>
        <p class="page-subtitle">{{ subtitle }}</p>
      </div>
    </div>

    <div class="function-section">
      <div class="function-grid">
        <div
          v-for="item in items"
          :key="item.path || item.label"
          class="function-card"
          @click="handleClick(item)"
        >
          <div class="function-icon" :class="item.iconClass">
            <van-icon :name="item.icon" />
          </div>
          <h3>{{ item.label }}</h3>
          <p>{{ item.description }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'

const BackgroundAnimation = defineAsyncComponent(() => import('@/components/index-detail/BackgroundAnimation.vue'))

const router = useRouter()

const props = defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, required: true },
  items: {
    type: Array,
    required: true,
    // { icon, label, description, path?, external?, iconClass? }
  }
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
.feature-grid-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 20px;
  position: relative;
  padding-bottom: var(--safe-bottom);
  box-sizing: border-box;
}

.content-section {
  position: relative;
  z-index: 2;
  margin-top: 20px;
}

.content-card {
  background: var(--bg-surface-alpha);
  padding: 20px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 10px 25px var(--primary-alpha-10);
  backdrop-filter: blur(10px);
}

.page-title {
  color: var(--primary-color);
  font-size: 20px;
  font-weight: 600;
  margin: 8px 0;
}

.page-subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 10px 0;
}

.function-section {
  position: relative;
  z-index: 2;
  margin-top: 20px;
}

.function-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 15px;
}

.function-card {
  background: var(--bg-surface-alpha);
  padding: 20px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 8px 20px var(--primary-alpha-10);
  transition: all 0.3s ease;
  cursor: pointer;
}

.function-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 25px var(--primary-alpha-15);
}

.function-icon {
  font-size: 28px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.function-icon :deep(.van-icon) {
  font-size: 28px;
}

.function-card h3 {
  color: var(--primary-color);
  font-size: 16px;
  margin: 10px 0 5px;
}

.function-card p {
  color: var(--text-secondary);
  font-size: 13px;
  margin: 0;
}

@media (min-width: 768px) {
  .feature-grid-page {
    padding: var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
  }

  .function-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1024px) {
  .function-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
