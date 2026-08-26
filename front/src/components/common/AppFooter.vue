<template>
  <footer class="app-footer" :class="{ 'above-tabbar': isMobileWithTabbar }">
    <!-- 桌面端完整状态栏 -->
    <template v-if="isDesktop">
      <span class="footer-brand">OncoPath<strong v-if="version"> v{{ version }}</strong></span>
      <span class="footer-divider">|</span>
      <a class="footer-link" :href="REPO_URL" target="_blank" rel="noopener">GitHub</a>
      <span class="footer-divider">|</span>
      <button class="footer-sponsor" @click="showSponsor = true">💜 赞助支持</button>
      <span class="footer-divider">|</span>
      <span class="footer-meta">© 2026 Apache-2.0</span>
      <span class="footer-divider">|</span>
      <span class="footer-meta">Made with ❤️ by nickzhang1102</span>
    </template>

    <!-- 移动端细条 -->
    <template v-else>
      <span class="footer-meta">OncoPath<template v-if="version"> v{{ version }}</template></span>
      <span class="footer-dot">·</span>
      <button class="footer-sponsor" @click="showSponsor = true">💜 赞助支持</button>
    </template>

    <SponsorPopup v-model:show="showSponsor" />
  </footer>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import { useAppVersion } from '@/composables/useAppVersion'
import SponsorPopup from '@/components/common/SponsorPopup.vue'

const REPO_URL = 'https://github.com/nickzhang1102/oncopath'

const route = useRoute()
const { isDesktop } = useResponsive()
const { version, fetchVersion } = useAppVersion()

const showSponsor = ref(false)

// 移动端 /home/* 布局内有 tabbar，状态栏需抬升到 tabbar 上方
const isMobileWithTabbar = computed(() =>
  !isDesktop.value && route.path.startsWith('/home')
)

onMounted(() => {
  fetchVersion()
})
</script>

<style scoped>
.app-footer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 900; /* 低于 --z-nav(1000)：桌面端被不透明侧边栏自然遮挡，移动端位于 tabbar 之下 */
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: var(--footer-height);
  padding: 4px 12px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-color);
  font-size: 12px;
  color: var(--text-tertiary);
}

.app-footer.above-tabbar {
  bottom: var(--tabbar-height);
}

.footer-brand {
  color: var(--text-secondary);
  font-weight: 600;
}

.footer-brand strong {
  color: var(--text-tertiary);
  font-weight: 500;
}

.footer-divider {
  color: var(--border-color);
}

.footer-dot {
  color: var(--text-tertiary);
}

.footer-link {
  color: var(--text-secondary);
  text-decoration: none;
}

.footer-link:hover {
  color: var(--primary-color);
}

.footer-sponsor {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border: 1px solid var(--primary-alpha-15);
  border-radius: 999px;
  background: var(--primary-alpha-5);
  color: var(--primary-color);
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.footer-sponsor:hover,
.footer-sponsor:active {
  background: var(--primary-alpha-15);
}

.footer-meta {
  white-space: nowrap;
}
</style>
