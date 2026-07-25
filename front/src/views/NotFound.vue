<template>
  <div class="not-found">
    <div class="not-found-content">
      <van-icon name="warning-o" size="80" color="var(--primary-color)" />
      <h2 class="title">404</h2>
      <p class="description">抱歉，您访问的页面不存在</p>
      <van-button type="primary" round @click="router.replace('/')">
        返回首页
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.not-found {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: var(--space-4);
}

.not-found-content {
  text-align: center;
}

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--text-primary);
  margin-top: var(--space-4);
  margin-bottom: var(--space-2);
}

.description {
  font-size: var(--text-base);
  color: var(--text-secondary);
  margin-bottom: var(--space-6);
}
</style>
