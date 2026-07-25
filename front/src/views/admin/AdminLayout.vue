<template>
  <div class="admin-layout">
    <!-- 移动端侧边栏遮罩 -->
    <div v-if="isMobile && showMobileMenu" class="admin-overlay" @click="showMobileMenu = false" />

    <aside class="admin-sidebar" :class="{ collapsed: isCollapsed, 'mobile-open': isMobile && showMobileMenu }">
      <div class="sidebar-header" @click="isCollapsed ? toggleCollapse() : undefined">
        <van-icon name="shield-o" size="28" :style="{ color: 'var(--primary-color)' }" />
        <transition name="fade-text">
          <span v-if="!isCollapsed" class="sidebar-title">管理后台</span>
        </transition>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
          @click="isMobile && (showMobileMenu = false)"
        >
          <van-icon :name="item.icon" size="20" />
          <transition name="fade-text">
            <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
          </transition>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div v-if="!isMobile" class="nav-item" @click="toggleCollapse">
          <van-icon :name="isCollapsed ? 'expand-o' : 'collapse-o'" size="20" />
          <transition name="fade-text">
            <span v-if="!isCollapsed" class="nav-label">收起</span>
          </transition>
        </div>
        <router-link to="/home" class="nav-item">
          <van-icon name="arrow-left" size="20" />
          <transition name="fade-text">
            <span v-if="!isCollapsed" class="nav-label">返回前台</span>
          </transition>
        </router-link>
      </div>
    </aside>

    <main class="admin-content" :class="{ 'sidebar-collapsed': isCollapsed }">
      <div class="admin-topbar">
        <div class="topbar-left">
          <button v-if="isMobile" class="mobile-menu-btn" @click="showMobileMenu = true">
            <van-icon name="wap-nav" size="22" />
          </button>
          <span class="topbar-title">{{ currentPageTitle }}</span>
        </div>
        <div class="topbar-user">
          <van-icon name="manager-o" size="18" />
          <span>{{ userStore.userName }}</span>
        </div>
      </div>
      <div class="admin-page">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useResponsive } from '@/composables/useResponsive'

const route = useRoute()
const userStore = useUserStore()
const { isMobile } = useResponsive()
const isCollapsed = ref(false)
const showMobileMenu = ref(false)

// 切换到桌面端时自动关闭移动端菜单
watch(isMobile, (val) => {
  if (!val) showMobileMenu.value = false
})

const menuItems = [
  { path: '/admin/dashboard', icon: 'chart-trending-o', label: '仪表盘' },
  { path: '/admin/users', icon: 'friends-o', label: '用户管理' },
  { path: '/admin/indices', icon: 'search', label: '指标库管理' },
  { path: '/admin/categories', icon: 'apps-o', label: '分类管理' },
  { path: '/admin/llm-configs', icon: 'setting-o', label: 'LLM配置' },
  { path: '/admin/agentteams-config', icon: 'cluster-o', label: 'AgentTeams配置' },
]

const currentPageTitle = computed(() => {
  const item = menuItems.find(m => m.path === route.path)
  return item ? item.label : '管理后台'
})

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
  background: var(--bg-primary, #f5f5f5);
}

.admin-sidebar {
  width: 220px;
  background: var(--bg-surface, #fff);
  border-right: 1px solid var(--border-color, #ebedf0);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: var(--z-nav);
}

.admin-sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color, #ebedf0);
  min-height: 60px;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #323233);
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  padding: 8px 0;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  color: var(--text-secondary, #969799);
  text-decoration: none;
  transition: all 0.2s ease;
  cursor: pointer;
  white-space: nowrap;
}

.nav-item:hover {
  background: var(--bg-primary, #f5f5f5);
  color: var(--text-primary, #323233);
}

.nav-item.active {
  color: var(--primary-color, #1989fa);
  background: var(--primary-light, #e8f3fe);
}

.nav-label {
  font-size: 14px;
}

.sidebar-footer {
  border-top: 1px solid var(--border-color, #ebedf0);
  padding: 8px 0;
}

.admin-content {
  flex: 1;
  margin-left: 220px;
  transition: margin-left 0.3s ease;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.admin-content.sidebar-collapsed {
  margin-left: 64px;
}

.admin-topbar {
  height: 56px;
  background: var(--bg-surface, #fff);
  border-bottom: 1px solid var(--border-color, #ebedf0);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: var(--z-float);
}

.topbar-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #323233);
}

.topbar-user {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--text-secondary, #969799);
}

.admin-page {
  flex: 1;
  padding: 24px;
}

/* 移动端菜单按钮 */
.mobile-menu-btn {
  background: none;
  border: none;
  padding: 8px;
  margin-right: 8px;
  cursor: pointer;
  color: var(--text-primary, #323233);
  display: flex;
  align-items: center;
  min-width: 44px;
  min-height: 44px;
  justify-content: center;
}

.topbar-left {
  display: flex;
  align-items: center;
}

/* 移动端遮罩 */
.admin-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: calc(var(--z-nav) - 1);
}

/* 移动端响应式 */
@media (max-width: 767px) {
  .admin-sidebar {
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    z-index: var(--z-nav);
  }

  .admin-sidebar.mobile-open {
    transform: translateX(0);
    width: 220px;
  }

  .admin-content {
    margin-left: 0 !important;
  }

  .admin-topbar {
    padding: 0 12px;
  }

  .admin-page {
    padding: 12px;
  }

  .topbar-user span {
    display: none;
  }
}

/* 平板端：默认折叠侧边栏 */
@media (min-width: 768px) and (max-width: 1023px) {
  .admin-sidebar {
    width: 64px;
  }

  .admin-content {
    margin-left: 64px;
  }
}

.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity 0.2s ease;
}

.fade-text-enter-from,
.fade-text-leave-to {
  opacity: 0;
}
</style>
