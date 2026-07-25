<template>
  <aside class="desktop-sidebar" :class="{ collapsed: modelValue }">
    <!-- Logo 区域 -->
    <div class="sidebar-logo" @click="modelValue ? toggleCollapse() : undefined">
      <van-icon v-if="modelValue" name="wap-nav" size="24" :style="{ color: 'var(--primary-color)' }" />
      <van-icon v-else name="shield-o" size="28" :style="{ color: 'var(--primary-color)' }" />
      <transition name="fade-text">
        <span v-if="!modelValue" class="logo-text">OncoPath</span>
      </transition>
    </div>

    <!-- 当前患者信息 -->
    <div class="sidebar-patient" v-if="currentPatient">
      <div class="patient-avatar">
        <van-icon name="user-circle-o" size="24" />
      </div>
      <transition name="fade-text">
        <div v-if="!modelValue" class="patient-info">
          <div class="patient-name">{{ currentPatient.patient_name }}</div>
          <div class="patient-meta">
            {{ currentPatient.gender === 'male' ? '男' : '女' }}
            <span v-if="currentPatient.age">{{ currentPatient.age }}岁</span>
          </div>
        </div>
      </transition>
    </div>

    <!-- 导航菜单 -->
    <nav class="sidebar-nav">
      <div v-for="group in navGroups" :key="group.label" class="nav-group">
        <transition name="fade-text">
          <div v-if="!modelValue" class="nav-group-label">{{ group.label }}</div>
        </transition>
        <component
          v-for="item in group.items"
          :key="item.path"
          :is="item.external ? 'a' : 'router-link'"
          v-bind="item.external
            ? { href: item.path, target: '_blank', rel: 'noopener noreferrer' }
            : { to: item.path }
          "
          class="nav-item"
          :class="{ active: !item.external && isActive(item.path) }"
          :title="item.label"
        >
          <van-icon :name="item.icon" size="22" />
          <transition name="fade-text">
            <span v-if="!modelValue" class="nav-label">{{ item.label }}</span>
          </transition>
        </component>
      </div>
    </nav>

    <!-- 收起/展开按钮 -->
    <div class="sidebar-footer">
      <button v-if="modelValue" class="expand-btn" @click="toggleCollapse" title="展开菜单">
        <van-icon name="arrow" size="16" />
      </button>
      <button v-else class="collapse-btn" @click="toggleCollapse" title="收起菜单">
        <van-icon name="arrow-left" size="18" />
        <span class="collapse-label">收起菜单</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import {
  MEDICAL_NAV_ITEMS, AI_NAV_ITEMS,
  MANAGEMENT_NAV_ITEMS, OTHER_NAV_ITEMS,
} from '@/styles/navigation'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const route = useRoute()
const patientStore = usePatientStore()

const currentPatient = computed(() => patientStore.currentPatient)

const navGroups = [
  {
    label: '首页',
    items: [
      { path: '/home/main', icon: 'home-o', label: '主页' },
      { path: '/home/timeline', icon: 'clock-o', label: '时间线' },
    ]
  },
  {
    label: '医疗',
    items: MEDICAL_NAV_ITEMS
  },
  {
    label: 'AI',
    items: AI_NAV_ITEMS
  },
  {
    label: '管理',
    items: MANAGEMENT_NAV_ITEMS
  },
  {
    label: '其他',
    items: [
      ...OTHER_NAV_ITEMS,
      { path: '/home/profile', icon: 'user-o', label: '我的' },
    ]
  },
]

function isActive(path) {
  return route.path.startsWith(path)
}

function toggleCollapse() {
  emit('update:modelValue', !props.modelValue)
}
</script>

<style scoped>
.desktop-sidebar {
  position: fixed;
  left: 0;
  top: 0;
  height: 100vh;
  width: var(--sidebar-width-expanded);
  background: var(--bg-surface);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: var(--z-nav);
  transition: width 0.3s ease;
  box-shadow: 2px 0 8px var(--primary-alpha-6);
}

.desktop-sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

/* Logo */
.sidebar-logo {
  display: flex;
  align-items: center;
  padding: var(--space-4);
  gap: var(--space-3);
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  min-height: 64px;
}

.logo-text {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
}

/* 当前患者信息 */
.sidebar-patient {
  display: flex;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  gap: var(--space-3);
  border-bottom: 1px solid var(--border-color);
  background: var(--primary-alpha-3);
  min-height: 52px;
}

.patient-avatar {
  flex-shrink: 0;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}

.patient-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.patient-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.patient-meta {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-top: 1px;
}

/* 导航 */
.sidebar-nav {
  flex: 1;
  padding: var(--space-2) 0;
  overflow-y: auto;
}

.nav-group {
  margin-bottom: var(--space-1);
}

.nav-group-label {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  gap: var(--space-3);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
  margin: 2px var(--space-2);
  border-radius: var(--radius-md);
}

.nav-item:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--primary-alpha-8);
  color: var(--primary-color);
  border-left-color: var(--primary-color);
  font-weight: 500;
}

.nav-label {
  font-size: var(--text-sm);
  white-space: nowrap;
  overflow: hidden;
}

/* 收起状态下导航项居中 */
.collapsed .nav-item {
  justify-content: center;
  padding: var(--space-3);
  margin: 2px var(--space-1);
}

.collapsed .sidebar-logo {
  justify-content: center;
  padding: var(--space-3);
}

.collapsed .patient-avatar {
  width: auto;
  height: auto;
}

/* 底部 */
.sidebar-footer {
  border-top: 1px solid var(--border-color);
  padding: var(--space-2);
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  width: 100%;
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
}

.collapse-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

.expand-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--primary-alpha-8);
  border: 1px solid var(--primary-alpha-20);
  color: var(--primary-color);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all 0.2s ease;
  margin: 0 auto;
  transform: rotate(0deg);
}

.expand-btn:hover {
  background: var(--primary-alpha-15);
  border-color: var(--primary-color);
}

.collapse-label {
  font-size: var(--text-sm);
  white-space: nowrap;
  overflow: hidden;
}

.collapsed .sidebar-footer {
  display: flex;
  justify-content: center;
}

/* 文字渐隐动画 */
.fade-text-enter-active,
.fade-text-leave-active {
  transition: opacity 0.2s ease;
}

.fade-text-enter-from,
.fade-text-leave-to {
  opacity: 0;
}

/* 滚动条样式 */
.sidebar-nav::-webkit-scrollbar {
  width: 4px;
}

.sidebar-nav::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: var(--primary-alpha-15);
  border-radius: 2px;
}

.sidebar-nav::-webkit-scrollbar-thumb:hover {
  background: var(--primary-alpha-30);
}
</style>
