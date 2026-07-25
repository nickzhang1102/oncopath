<template>
  <div v-if="isDesktop" class="desktop-page-header">
    <van-button icon="arrow-left" size="small" plain type="primary" @click="goBack">
      返回
    </van-button>
    <h1>{{ title }}</h1>
  </div>
  <van-nav-bar
    v-else
    :title="title"
    left-text="返回"
    left-arrow
    @click-left="goBack"
    fixed
    placeholder
    :safe-area-inset-top="true"
  />
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'

const props = defineProps({
  title: {
    type: String,
    default: ''
  }
});

const router = useRouter()
const { isDesktop } = useResponsive()

const goBack = () => {
  router.back()
}
</script>

<style scoped>
.desktop-page-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-light);
}

.desktop-page-header h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
}

:deep(.van-nav-bar) {
  background: var(--bg-surface-alpha);
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  z-index: 10;
}

:deep(.van-nav-bar__title) {
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
}

:deep(.van-nav-bar__text) {
  color: var(--primary-color);
}

:deep(.van-icon-arrow-left) {
  color: var(--primary-color);
}
</style>
