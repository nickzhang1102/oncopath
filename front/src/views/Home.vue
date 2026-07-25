<template>
  <div class="home-view" :class="{ 'has-sidebar': isDesktop }">
    <!-- 桌面端侧边栏 -->
    <DesktopSidebar v-if="isDesktop" v-model="sidebarCollapsed" />

    <!-- 主要内容区 -->
    <div class="content-area" :class="{ 'sidebar-expanded': isDesktop && !sidebarCollapsed, 'sidebar-collapsed': isDesktop && sidebarCollapsed }">
      <router-view v-slot="{ Component }">
        <keep-alive :include="cachedViews">
          <component :is="Component" :key="$route.fullPath" />
        </keep-alive>
      </router-view>
    </div>

    <!-- 移动端 Drawer 触发按钮（左上角浮动） -->
    <button v-if="showDrawerTrigger" class="drawer-trigger-btn" @click="openDrawer" title="打开导航">
      <van-icon name="wap-nav" size="20" />
    </button>

    <!-- 移动端侧边 Drawer -->
    <MobileDrawer v-if="!isDesktop" v-model:show="showDrawer" @close="onDrawerClose" />

    <!-- 移动端底部导航 -->
    <div v-if="!isDesktop" class="tabbar-wrapper">
      <van-tabbar v-model="activeTab" route fixed class="tabbar-medical">
        <template v-for="(item, index) in MOBILE_TABBAR_ITEMS" :key="item.path">
          <!-- 中间上传按钮特殊样式 -->
          <div v-if="item.isCenter" class="tabbar-center-spacer" @click="goUpload">
            <div class="tabbar-center-btn">
              <van-icon :name="item.icon" size="24" color="var(--color-white)" />
            </div>
            <span class="tabbar-center-label">{{ item.label }}</span>
          </div>
          <!-- 普通导航项 -->
          <van-tabbar-item
            v-else
            :to="item.path"
            :icon="item.icon"
            :badge="item.path === '/home/profile' ? notificationStore.unreadCount || '' : undefined"
          >
            {{ item.label }}
          </van-tabbar-item>
        </template>
      </van-tabbar>
    </div>

  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResponsive } from '@/composables/useResponsive'
import { useNotificationStore } from '@/stores/notification'
import DesktopSidebar from '@/components/common/DesktopSidebar.vue'
import MobileDrawer from '@/components/common/MobileDrawer.vue'
import { MOBILE_TABBAR_ITEMS } from '@/styles/navigation'

const route = useRoute()
const router = useRouter()
const { isDesktop } = useResponsive()
const notificationStore = useNotificationStore()

const activeTab = ref(0)
const cachedViews = ['Main', 'Timeline', 'ConsultationList', 'Knowledge', 'IndexView', 'AbnormalIndicators']
const showDrawerTrigger = computed(() => !isDesktop.value && route.path === '/home/main')

// Drawer 状态
const showDrawer = ref(false)

function openDrawer() {
  showDrawer.value = true
}

function onDrawerClose() {
  showDrawer.value = false
}

function goUpload() {
  router.push('/home/image-report')
}

// 侧边栏收起状态（与 DesktopSidebar v-model 同步，持久化到 localStorage）
const sidebarCollapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')

watch(sidebarCollapsed, (val) => {
  localStorage.setItem('sidebar-collapsed', val)
})

onMounted(() => {
  notificationStore.fetchUnreadCount()
  // SSE 未连接时才启动轮询降级
  if (!notificationStore.sseConnected) {
    notificationStore.startPolling()
  }
})

onUnmounted(() => {
  notificationStore.stopPolling()
})

// 移动端 Tabbar 路由映射：tab index → 路径前缀列表
// 新布局：[主页] [时间线] [上传(中间)] [会诊] [我的]
const tabRouteMap = [
  [                                                         // 0: 主页（含原病情子页面+新功能）
    '/home/main', '/home/medical', '/home/reports', '/home/exam-reports',
    '/home/pathology-reports', '/home/treatment', '/home/status',
    '/home/image-report', '/home/index', '/home/abnormal-indicators',
    '/home/indicator/history', '/home/news', '/home/knowledge', '/home/medication',
    '/home/follow-up', '/home/search'
  ],
  ['/home/timeline'],                                       // 1: 时间线
  [],                                                       // 2: 上传（中间按钮，不关联路由）
  [                                                         // 3: 会诊
    '/home/consultation', '/home/consultation/prompt-config'
  ],
  ['/home/profile', '/home/patient-management']             // 4: 我的
]

// 根据路由更新激活标签
watch(
  () => route.path,
  (path) => {
    const matchedTab = tabRouteMap.findIndex(prefixes =>
      prefixes.some(p => path.includes(p))
    )
    activeTab.value = matchedTab >= 0 ? matchedTab : 0
  },
  { immediate: true }
)
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  background: var(--bg-primary);
}

.content-area {
  transition: padding-left 0.3s ease;
}

/* 桌面端侧边栏偏移 */
@media (min-width: 768px) {
  .content-area.sidebar-expanded {
    padding-left: var(--sidebar-width-expanded);
  }

  .content-area.sidebar-collapsed {
    padding-left: var(--sidebar-width-collapsed);
  }
}

.tabbar-wrapper {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: var(--z-nav);
}

.tabbar-medical {
  background: var(--bg-surface-alpha);
  backdrop-filter: blur(10px);
  border-top: 1px solid var(--border-color);
}

.tabbar-medical :deep(.van-tabbar-item--active) {
  color: var(--primary-color);
}

:deep(.van-tabbar) {
  z-index: var(--z-nav) !important;
}

/* 中间上传按钮 */
.tabbar-center-spacer {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 4px 0 2px;
  position: relative;
  min-width: 0;
}

.tabbar-center-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: -20px;
  box-shadow: 0 2px 8px var(--primary-alpha-30);
  transition: transform 0.2s;
}

.tabbar-center-btn:active {
  transform: scale(0.92);
}

.tabbar-center-label {
  font-size: 10px;
  color: var(--text-secondary);
  margin-top: 2px;
}

/* Drawer 触发按钮（移动端左上角浮动） */
.drawer-trigger-btn {
  position: fixed;
  top: 16px;
  left: 16px;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-surface-alpha);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  color: var(--text-primary);
  cursor: pointer;
  z-index: 100;
  transition: all 0.2s;
  box-shadow: 0 2px 8px var(--primary-alpha-10);
}

.drawer-trigger-btn:hover {
  background: var(--primary-alpha-8);
  color: var(--primary-color);
}

.drawer-trigger-btn:active {
  transform: scale(0.95);
}

/* 桌面端滚动优化 */
@media (min-width: 768px) {
  .content-area {
    min-height: 100vh;
  }

  .drawer-trigger-btn {
    display: none;
  }
}
</style>
