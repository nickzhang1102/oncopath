<template>
  <van-config-provider :theme="resolvedTheme">
    <div id="app">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
      <!-- 全局底部状态栏（版本/GitHub/赞助/协议/署名） -->
      <AppFooter />
    </div>
  </van-config-provider>
</template>

<script setup>
import { onMounted, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { usePatientStore } from '@/stores/patient'
import { useNotificationStore } from '@/stores/notification'
import { useTheme } from '@/composables/useTheme'
import AppFooter from '@/components/common/AppFooter.vue'

const userStore = useUserStore()
const notificationStore = useNotificationStore()
const { resolvedTheme } = useTheme()

onMounted(() => {
  // 应用启动时检查登录状态
  if (userStore.isLoggedIn && userStore.token) {
    // 尝试获取用户信息以验证 token 是否有效
    userStore.fetchUserInfo().catch(() => {
      // Token 无效，清除登录状态
      userStore.logout()
    })
    // 建立 SSE 通知连接
    notificationStore.connectSSE?.()
  }
})

// 监听登录状态变化
watch(() => userStore.isLoggedIn, (loggedIn) => {
  if (loggedIn && userStore.token) {
    notificationStore.connectSSE?.()
  } else {
    // 登出：终止所有会话级状态，防止跨账号数据残留（患者列表/通知/轮询/SSE）
    notificationStore.disconnectSSE?.()
    notificationStore.stopPolling?.()
    notificationStore.notifications = []
    notificationStore.unreadCount = 0
    usePatientStore().clearPatients()
  }
})
</script>

<style>
@import '@/styles/responsive.css';

#app {
  width: 100%;
  min-height: 100vh;
  background: var(--bg-primary);
  /* 全局底部状态栏占位补偿，防止页面内容被遮挡 */
  padding-bottom: var(--footer-height);
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 滑动动画 */
.slide-left-enter-active,
.slide-left-leave-active,
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease;
}

.slide-left-enter-from {
  transform: translateX(100%);
}

.slide-left-leave-to {
  transform: translateX(-100%);
}

.slide-right-enter-from {
  transform: translateX(-100%);
}

.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
