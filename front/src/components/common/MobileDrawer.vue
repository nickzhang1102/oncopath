<template>
  <van-popup
    v-model:show="visible"
    position="left"
    :style="{ width: '280px', height: '100%' }"
    class="mobile-drawer-popup"
  >
    <div class="mobile-drawer">
      <!-- Logo 区域 -->
      <div class="drawer-header">
        <div class="drawer-logo">
          <van-icon name="shield-o" size="24" :style="{ color: 'var(--primary-color)' }" />
          <span class="logo-text">OncoPath</span>
        </div>
        <button class="drawer-close" @click="close" title="关闭">
          <van-icon name="cross" size="18" />
        </button>
      </div>

      <!-- 当前患者信息 -->
      <div class="drawer-patient" v-if="currentPatient">
        <div class="patient-avatar">
          <van-icon name="user-circle-o" size="24" />
        </div>
        <div class="patient-info">
          <div class="patient-name">{{ currentPatient.patient_name }}</div>
          <div class="patient-meta">
            {{ currentPatient.gender === 'male' ? '男' : '女' }}
            <span v-if="currentPatient.age">{{ currentPatient.age }}岁</span>
          </div>
        </div>
      </div>

      <!-- 导航菜单 -->
      <nav class="drawer-nav">
        <div v-for="group in NAV_GROUPS" :key="group.key" class="nav-group">
          <div class="nav-group-label">{{ group.label }}</div>
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
            @click="!item.external && close()"
          >
            <van-icon :name="item.icon" size="20" />
            <span class="nav-label">{{ item.label }}</span>
          </component>
        </div>
      </nav>
    </div>
  </van-popup>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import { NAV_GROUPS } from '@/styles/navigation'

const route = useRoute()
const patientStore = usePatientStore()

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:show', 'close'])

const visible = computed({
  get: () => props.show,
  set: (val) => {
    emit('update:show', val)
    if (!val) emit('close')
  }
})

const currentPatient = computed(() => patientStore.currentPatient)

function isActive(path) {
  return route.path.startsWith(path)
}

function close() {
  visible.value = false
}
</script>

<style scoped>
.mobile-drawer-popup {
  background: transparent;
}

.mobile-drawer {
  height: 100%;
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 16px var(--primary-alpha-15);
}

/* Header */
.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-color);
  min-height: 56px;
}

.drawer-logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.logo-text {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
}

.drawer-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-elevated);
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.drawer-close:hover {
  background: var(--primary-alpha-8);
  color: var(--primary-color);
}

/* Patient */
.drawer-patient {
  display: flex;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  gap: var(--space-3);
  border-bottom: 1px solid var(--border-color);
  background: var(--primary-alpha-3);
}

.patient-avatar {
  flex-shrink: 0;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
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

/* Navigation */
.drawer-nav {
  flex: 1;
  padding: var(--space-2) 0;
  overflow-y: auto;
}

.nav-group {
  margin-bottom: var(--space-2);
}

.nav-group-label {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
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
}

/* Scrollbar */
.drawer-nav::-webkit-scrollbar {
  width: 4px;
}

.drawer-nav::-webkit-scrollbar-track {
  background: transparent;
}

.drawer-nav::-webkit-scrollbar-thumb {
  background: var(--primary-alpha-15);
  border-radius: 2px;
}

.drawer-nav::-webkit-scrollbar-thumb:hover {
  background: var(--primary-alpha-30);
}
</style>
