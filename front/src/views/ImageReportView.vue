<template>
  <div class="image-report-view">
    <!-- 动态背景元素 -->
    <div class="bg-animation">
      <div class="floating-cross" v-for="n in 8" :key="n" :style="{animationDelay: n * 0.6 + 's'}">+</div>
      <div class="floating-circle" v-for="n in 6" :key="n" :style="{animationDelay: n * 0.8 + 's'}"></div>
      <div class="floating-heart" v-for="n in 4" :key="n" :style="{animationDelay: n * 1.2 + 's'}">♥</div>
    </div>

    <div class="content-wrapper">
      <!-- 统一页面抬头 -->
      <BackButton title="上传报告" />

      <!-- 未选择患者时的空状态 -->
      <div v-if="!hasPatient" class="empty-patient">
        <van-empty description="请先选择患者" image="search">
          <van-button type="primary" class="bottom-button" @click="router.push('/home/patient-management')">
            选择患者
          </van-button>
        </van-empty>
      </div>

      <!-- 标签页切换 -->
      <van-tabs v-else v-model:active="activeTab" sticky :offset-top="isDesktop ? 0 : 46">
        <van-tab title="上传报告">
          <ImageUpload @upload-completed="onUploadCompleted" />
        </van-tab>

        <van-tab title="报告列表">
          <ImageTimeline ref="imageTimelineRef" :patient-id="currentPatientId" :initial-ocr-status="route.query.ocr_status" />
        </van-tab>

        <van-tab title="统计分析">
          <ImageStats ref="imageStatsRef" :patient-id="currentPatientId" />
        </van-tab>
      </van-tabs>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'
import { showToast } from 'vant'
import ImageTimeline from '@/components/image-report/ImageTimeline.vue'
import ImageUpload from '@/components/image-report/ImageUpload.vue'
import ImageStats from '@/components/image-report/ImageStats.vue'
import BackButton from '@/components/index-detail/BackButton.vue'

const router = useRouter()
const route = useRoute()
const patientStore = usePatientStore()
const { isDesktop } = useResponsive()

const imageTimelineRef = ref(null)
const imageStatsRef = ref(null)

const activeTab = ref(0)

const currentPatientId = computed(() => {
  const currentPatient = patientStore.currentPatient
  return currentPatient ? currentPatient.patient_id : null
})

const hasPatient = computed(() => !!currentPatientId.value)

onMounted(() => {
  if (route.query.tab) {
    const tabMap = { upload: 0, list: 1, stats: 2 }
    activeTab.value = tabMap[route.query.tab] || 0
  }
  if (route.query.ocr_status) {
    activeTab.value = 1
  }
})

watch(() => route.query.tab, (newTab) => {
  if (newTab) {
    const tabMap = { upload: 0, list: 1, stats: 2 }
    activeTab.value = tabMap[newTab] || 0
  }
})

watch(activeTab, async (newTab) => {
  // tab 0: 上传报告, tab 1: 报告列表, tab 2: 统计分析
  if (newTab === 1 && imageTimelineRef.value) {
    await imageTimelineRef.value.refreshData()
  } else if (newTab === 2 && imageStatsRef.value) {
    await imageStatsRef.value.refreshData()
  }
})

// 上传完成后导航到OCR确认页面
const onUploadCompleted = (reportId) => {
  router.push(`/home/image-report/${reportId}/review`)
}
</script>

<style scoped>
.image-report-view {
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-primary) 0%, var(--border-color) 100%);
  position: relative;
  /* 不使用 overflow-x:hidden，避免裁剪下拉面板内容 */
  -webkit-overflow-scrolling: touch;
}

/* 动态背景元素 */
.bg-animation {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.floating-cross {
  position: absolute;
  color: var(--primary-alpha-6);
  font-size: 18px;
  font-weight: bold;
  animation: float 8s ease-in-out infinite;
}

.floating-cross:nth-child(1) { top: 8%; left: 10%; }
.floating-cross:nth-child(2) { top: 20%; right: 15%; }
.floating-cross:nth-child(3) { top: 50%; left: 5%; }
.floating-cross:nth-child(4) { top: 70%; right: 10%; }
.floating-cross:nth-child(5) { top: 35%; left: 85%; }
.floating-cross:nth-child(6) { bottom: 30%; left: 20%; }
.floating-cross:nth-child(7) { bottom: 10%; right: 25%; }
.floating-cross:nth-child(8) { top: 85%; left: 65%; }

.floating-circle {
  position: absolute;
  width: 14px;
  height: 14px;
  border: 2px solid var(--primary-alpha-6);
  border-radius: 50%;
  animation: pulse 6s ease-in-out infinite;
}

.floating-circle:nth-child(9) { top: 15%; left: 55%; }
.floating-circle:nth-child(10) { top: 60%; right: 30%; }
.floating-circle:nth-child(11) { bottom: 20%; left: 70%; }
.floating-circle:nth-child(12) { top: 40%; right: 8%; }
.floating-circle:nth-child(13) { bottom: 40%; left: 40%; }
.floating-circle:nth-child(14) { top: 80%; right: 50%; }

.floating-heart {
  position: absolute;
  color: var(--primary-alpha-4);
  font-size: 16px;
  animation: heartbeat 5s ease-in-out infinite;
}

.floating-heart:nth-child(15) { top: 25%; left: 25%; }
.floating-heart:nth-child(16) { top: 65%; right: 20%; }
.floating-heart:nth-child(17) { bottom: 15%; left: 75%; }
.floating-heart:nth-child(18) { top: 90%; left: 45%; }

@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-12px) rotate(180deg); }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.06; }
  50% { transform: scale(1.2); opacity: 0.12; }
}

@keyframes heartbeat {
  0%, 100% { transform: scale(1); }
  25% { transform: scale(1.05); }
  50% { transform: scale(1); }
  75% { transform: scale(1.02); }
}

/* 页面内容 */
.content-wrapper {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding-bottom: var(--safe-bottom);
}

/* 空状态 */
.empty-patient {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.bottom-button {
  min-width: 160px;
  padding: 12px 24px;
}

:deep(.van-icon-arrow-left) {
  color: var(--primary-color);
}

:deep(.van-tabs__wrap) {
  background: var(--bg-surface-alpha);
  box-shadow: 0 8px 20px var(--primary-alpha-10);
  backdrop-filter: blur(10px);
  z-index: 99;
}

:deep(.van-tabs__nav) {
  background: transparent;
}

:deep(.van-tab) {
  color: var(--text-secondary);
}

:deep(.van-tab--active) {
  color: var(--primary-color);
  font-weight: 600;
}

:deep(.van-tabs__line) {
  background: var(--primary-color);
}

:deep(.van-tabs__content) {
  position: relative;
  z-index: 1;
  overflow-x: hidden;
}

/* 响应式设计 */
@media (max-width: 480px) {
  .image-report-view {
    padding: 0;
  }

  :deep(.van-tabs__content) {
    overflow-x: hidden;
    overflow-y: auto;
  }

  :deep(.van-tab__panel) {
    overflow-x: hidden;
    overflow-y: auto;
  }
}

/* 桌面端侧边栏适配 + 居中限宽 */
@media (min-width: 768px) {
  .image-report-view {
    padding: var(--space-6);
    padding-bottom: var(--space-6);
    max-width: 1000px;
    margin: 0 auto;
  }

}
</style>