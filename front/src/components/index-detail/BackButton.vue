<template>
  <div v-if="isDesktop" class="desktop-page-header">
    <van-button icon="arrow-left" size="small" plain type="primary" @click="goBack">
      返回
    </van-button>
    <div class="header-titles">
      <h1>{{ title }}</h1>
      <p v-if="subtitle" class="header-subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.right" class="header-actions">
      <slot name="right" />
    </div>
  </div>
  <van-nav-bar
    v-else
    :title="title"
    left-text="返回"
    left-arrow
    fixed
    placeholder
    :safe-area-inset-top="true"
    @click-left="goBack"
  >
    <template v-if="subtitle" #title>
      <div class="nav-title-stack">
        <span class="nav-title-text">{{ title }}</span>
        <span class="nav-subtitle-text">{{ subtitle }}</span>
      </div>
    </template>
    <template v-if="$slots.right" #right>
      <slot name="right" />
    </template>
  </van-nav-bar>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  subtitle: {
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
  /* 统一抬头到页面顶部的间距（各页面容器不再重复提供） */
  padding-top: var(--space-6);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-light);
}

.header-titles {
  flex: 1;
  min-width: 0;
}

.desktop-page-header h1 {
  margin: 0;
  color: var(--text-primary);
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
}

.header-subtitle {
  margin: 2px 0 0;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  line-height: 1.4;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* 移动端两行标题（标题 + 副标题） */
.nav-title-stack {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.2;
}

.nav-title-text {
  font-size: 16px;
  font-weight: 600;
}

.nav-subtitle-text {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-top: 1px;
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
  max-width: 70%;
}

:deep(.van-nav-bar__text) {
  color: var(--primary-color);
}

:deep(.van-icon-arrow-left) {
  color: var(--primary-color);
}
</style>
