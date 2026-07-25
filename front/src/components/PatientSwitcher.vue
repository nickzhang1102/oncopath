<template>
  <div class="patient-switcher" ref="switcherRef">
    <!-- 桌面端：自定义弹出面板 -->
    <template v-if="isDesktop">
      <div
        class="patient-trigger"
        :class="{ 'patient-trigger--active': showPopup }"
        @click="showPopup = !showPopup"
      >
        <van-icon name="user-circle-o" size="20" />
        <span class="patient-trigger__name">{{ currentPatientName }}</span>
        <van-icon :name="showPopup ? 'arrow-up' : 'arrow-down'" size="14" />
      </div>
      <van-popup
        v-model:show="showPopup"
        :style="popupStyle"
        position="top"
        :overlay="true"
        overlay-class="patient-overlay"
        @click-overlay="showPopup = false"
      >
        <div class="patient-list">
          <div
            v-for="patient in patientStore.patientList"
            :key="patient.patient_id"
            class="patient-item"
            :class="{ 'patient-item--active': patient.patient_id === currentPatientId }"
            @click="switchPatient(patient)"
          >
            <van-icon name="user-circle-o" size="24" />
            <div class="patient-item__info">
              <div class="patient-item__name">{{ patient.patient_name }}</div>
              <div class="patient-item__meta">
                {{ patient.gender === 'male' ? '男' : '女' }}
                <span v-if="patient.is_primary" class="patient-item__primary">主患者</span>
              </div>
            </div>
            <van-icon
              v-if="patient.patient_id === currentPatientId"
              name="success"
              :style="{ color: 'var(--primary-color)' }"
            />
          </div>
        </div>
      </van-popup>
    </template>

    <!-- 移动端：保留 dropdown-menu -->
    <template v-else>
      <van-dropdown-menu :close-on-click-outside="true" z-index="2000">
        <van-dropdown-item :title="currentPatientName" ref="dropdownRef">
          <div class="patient-list">
            <div
              v-for="patient in patientStore.patientList"
              :key="patient.patient_id"
              class="patient-item"
              :class="{ 'patient-item--active': patient.patient_id === currentPatientId }"
              @click="switchPatient(patient)"
            >
              <van-icon name="user-circle-o" size="24" />
              <div class="patient-item__info">
                <div class="patient-item__name">{{ patient.patient_name }}</div>
                <div class="patient-item__meta">
                  {{ patient.gender === 'male' ? '男' : '女' }}
                  <span v-if="patient.is_primary" class="patient-item__primary">主患者</span>
                </div>
              </div>
              <van-icon
                v-if="patient.patient_id === currentPatientId"
                name="success"
                color="var(--primary-color)"
              />
            </div>
          </div>
        </van-dropdown-item>
      </van-dropdown-menu>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'

const patientStore = usePatientStore()
const { isDesktop } = useResponsive()
const dropdownRef = ref(null)
const switcherRef = ref(null)
const showPopup = ref(false)
const popupStyle = ref({})

const currentPatientId = computed(() => patientStore.currentPatient?.patient_id)

const currentPatientName = computed(() => {
  return patientStore.currentPatient?.patient_name || '选择患者'
})

async function switchPatient(patient) {
  if (patientStore.currentPatient?.patient_id === patient.patient_id) {
    showPopup.value = false
    return
  }
  try {
    await patientStore.switchPatient(patient.patient_id)
  } catch (e) {
    // fallback: 直接设置本地状态
    patientStore.setCurrentPatient(patient)
  }
  // 切换后关闭面板
  showPopup.value = false
  dropdownRef.value?.toggle(false)
}

// 桌面端：动态计算弹出位置
function updatePopupPosition() {
  if (!isDesktop.value || !switcherRef.value) return

  const rect = switcherRef.value.getBoundingClientRect()
  popupStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${Math.min(rect.width, 320)}px`,
    borderRadius: 'var(--radius-lg)',
    boxShadow: '0 8px 24px var(--primary-alpha-12)',
    overflow: 'hidden',
  }
}

// 监听 popup 打开时计算位置
watch(showPopup, (val) => {
  if (val) {
    nextTick(() => updatePopupPosition())
  }
})
</script>

<style scoped>
.patient-switcher {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-color);
}

/* 桌面端触发按钮 */
.patient-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  cursor: pointer;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  background: var(--bg-surface);
  transition: all 0.2s ease;
  user-select: none;
}

.patient-trigger:hover {
  background: var(--primary-alpha-5);
  border-color: var(--primary-color);
}

.patient-trigger--active {
  background: var(--primary-alpha-8);
  border-color: var(--primary-color);
}

.patient-trigger__name {
  flex: 1;
  font-weight: 500;
  color: var(--text-primary);
  font-size: var(--text-sm);
}

.patient-list {
  padding: var(--space-2);
  max-height: 400px;
  overflow-y: auto;
}

.patient-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  transition: background 0.2s;
  cursor: pointer;
}

.patient-item:active {
  background: var(--bg-elevated);
}

.patient-item:hover {
  background: var(--bg-elevated);
}

.patient-item--active {
  background: var(--primary-alpha-5);
}

.patient-item__info {
  flex: 1;
}

.patient-item__name {
  font-weight: 500;
  color: var(--text-primary);
}

.patient-item__meta {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-top: 2px;
}

.patient-item__primary {
  background: var(--primary-color);
  color: white;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  margin-left: var(--space-2);
}

/* 桌面端增强 */
@media (min-width: 768px) {
  .patient-switcher {
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-color);
    border-bottom: 1px solid var(--border-color);
    box-shadow: 0 2px 8px var(--primary-alpha-6);
  }

  .patient-item {
    padding: var(--space-3) var(--space-4);
  }

  .patient-item:hover {
    background: var(--primary-alpha-8);
  }

  .patient-item--active:hover {
    background: var(--primary-alpha-10);
  }
}
</style>

<!-- 全局样式：遮罩轻量化 -->
<style>
.patient-overlay {
  background: transparent !important;
}
</style>
