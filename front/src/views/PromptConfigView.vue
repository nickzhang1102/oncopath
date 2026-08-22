<template>
  <div class="prompt-config" :class="{ 'is-desktop': isDesktop }">
    <!-- 导航栏 -->
    <van-nav-bar
      title="提示词配置"
      left-text="返回"
      left-arrow
      @click-left="router.back()"
      fixed
      placeholder
      :safe-area-inset-top="true"
    />

    <!-- 无患者提示 -->
    <div v-if="!patientId" class="empty-patient">
      <van-icon name="warning-o" size="40" color="var(--warning-color)" />
      <p>请先选择患者</p>
    </div>

    <template v-else>
      <div class="config-content">
        <!-- 时间范围 -->
        <div class="config-card compact">
          <div class="card-header">
            <div class="card-indicator"></div>
            <span class="card-title">数据时间范围</span>
          </div>
          <div class="time-range-control">
            <van-stepper
              v-model="timeRangeDays"
              :min="7"
              :max="365"
              theme="round"
              button-size="22px"
              class="blue-stepper"
            />
            <span class="time-unit">天</span>
          </div>
        </div>

        <!-- 按分组渲染配置项 -->
        <div v-for="group in configGroups" :key="group.label" class="config-group">
          <div class="group-label">{{ group.label }}</div>
          <div
            v-for="item in group.items"
            :key="item.id"
            :class="['config-card', 'item-card', { active: item.enabled, disabled: !item.enabled }]"
          >
            <div class="item-header">
              <div class="item-left">
                <span class="item-name">{{ item.name }}</span>
              </div>
              <van-switch v-model="item.enabled" size="20px" active-color="var(--primary-color)" />
            </div>

            <!-- lab 类型参数 -->
            <template v-if="item.enabled && item.type === 'lab'">
              <div class="param-row">
                <div class="param-block">
                  <span class="param-label">指标种数</span>
                  <van-stepper v-model="item.indicatorCount" :min="1" :max="50" theme="round" button-size="18px" class="blue-stepper" />
                </div>
                <div class="param-block">
                  <span class="param-label">报告份数</span>
                  <van-stepper v-model="item.recentCount" :min="1" :max="10" theme="round" button-size="18px" class="blue-stepper" />
                </div>
              </div>
            </template>

            <!-- exam 类型参数 -->
            <template v-if="item.enabled && item.type === 'exam'">
              <div class="param-row">
                <div class="param-block">
                  <span class="param-label">报告份数</span>
                  <van-stepper v-model="item.recentCount" :min="1" :max="10" theme="round" button-size="18px" class="blue-stepper" />
                </div>
                <div class="param-block">
                  <span class="param-label">所见截断</span>
                  <van-stepper v-model="item.findingsLimit" :min="100" :max="2000" :step="100" theme="round" button-size="18px" class="blue-stepper" />
                </div>
              </div>
            </template>

            <!-- record 类型参数 -->
            <template v-if="item.enabled && item.type === 'record'">
              <div class="param-row">
                <div class="param-block">
                  <span class="param-label">最近条数</span>
                  <van-stepper v-model="item.recentCount" :min="5" :max="100" theme="round" button-size="18px" class="blue-stepper" />
                </div>
                <div class="param-block">
                  <span class="param-label">截断字数</span>
                  <van-stepper v-model="item.contentLimit" :min="200" :max="5000" :step="100" theme="round" button-size="18px" class="blue-stepper" />
                </div>
              </div>
            </template>

            <!-- treatment 类型参数 -->
            <template v-if="item.enabled && item.type === 'treatment'">
              <div class="param-row">
                <div class="param-block">
                  <span class="param-label">最近条数</span>
                  <van-stepper v-model="item.recentCount" :min="5" :max="50" theme="round" button-size="18px" class="blue-stepper" />
                </div>
              </div>
            </template>

            <!-- medication_record 类型参数 -->
            <template v-if="item.enabled && item.type === 'medication_record'">
              <div class="param-row">
                <div class="param-block">
                  <span class="param-label">最近条数</span>
                  <van-stepper v-model="item.recentCount" :min="5" :max="50" theme="round" button-size="18px" class="blue-stepper" />
                </div>
              </div>
            </template>

            <!-- status 类型参数 -->
            <template v-if="item.enabled && item.type === 'status'">
              <div class="param-row">
                <div class="param-block">
                  <span class="param-label">最近条数</span>
                  <van-stepper v-model="item.recentCount" :min="5" :max="100" theme="round" button-size="18px" class="blue-stepper" />
                </div>
                <div class="param-block">
                  <span class="param-label">截断字数</span>
                  <van-stepper v-model="item.contentLimit" :min="200" :max="5000" :step="100" theme="round" button-size="18px" class="blue-stepper" />
                </div>
              </div>
            </template>

            <!-- timeline 类型参数 -->
            <template v-if="item.enabled && item.type === 'timeline'">
              <div class="param-row">
                <div class="param-block">
                  <span class="param-label">最近条数</span>
                  <van-stepper v-model="item.recentCount" :min="5" :max="50" theme="round" button-size="18px" class="blue-stepper" />
                </div>
              </div>
            </template>

            <!-- custom 类型参数 -->
            <template v-if="item.enabled && item.type === 'custom'">
              <van-field
                v-model="item.customText"
                type="textarea"
                rows="3"
                :placeholder="item.name === '诊断要求' ? '请输入诊断要求' : '请输入自定义内容'"
                class="config-textarea"
              />
            </template>
          </div>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="bottom-actions">
        <van-button
          plain
          class="action-btn preview-btn"
          :loading="previewing"
          @click="handlePreview"
        >
          <template #default>
            <van-icon name="eye-o" />
            预览
          </template>
        </van-button>
        <van-button
          type="primary"
          class="action-btn save-btn"
          :loading="saving"
          @click="handleSave"
        >
          <template #default>
            <van-icon name="success" />
            保存配置
          </template>
        </van-button>
      </div>
    </template>

    <!-- 预览弹窗 -->
    <van-popup
      v-model:show="showPreview"
      :position="isDesktop ? 'center' : 'bottom'"
      :style="previewPopupStyle"
      round
      overlay-class="preview-overlay"
    >
      <div class="preview-content">
        <div class="preview-header">
          <span class="preview-title">提示词预览</span>
          <span class="preview-close" @click="showPreview = false">关闭</span>
        </div>
        <div class="preview-text" v-html="previewHtml"></div>
      </div>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { usePatientStore } from '@/stores/patient'
import { useResponsive } from '@/composables/useResponsive'
import { getPromptConfig, savePromptConfig, previewPromptConfig } from '@/api/prompt'
import { sanitizeHtml } from '@/utils/sanitize'

const router = useRouter()
const patientStore = usePatientStore()
const { isDesktop } = useResponsive()

const patientId = computed(() => patientStore.currentPatient?.patient_id || patientStore.currentPatient?.id || 0)
const timeRangeDays = ref(60)
const configItems = ref([])
const saving = ref(false)
const previewing = ref(false)
const showPreview = ref(false)
const previewText = ref('')

const previewHtml = computed(() => sanitizeHtml(previewText.value.replace(/\n/g, '<br>')))

const previewPopupStyle = computed(() => {
  if (isDesktop.value) {
    return { width: '560px', maxHeight: '80vh', height: 'auto', borderRadius: '12px' }
  }
  // 移动端: 高度扣除 tabbar(50px) 避免底部被遮挡
  return { height: 'calc(80vh - 50px)', zIndex: 10000 }
})

// 按类型分组
const configGroups = computed(() => {
  const overviewItems = configItems.value.filter(i => ['info', 'history'].includes(i.type))
  const labItems = configItems.value.filter(i => i.type === 'lab')
  const reportItems = configItems.value.filter(i => ['pathology', 'exam'].includes(i.type))
  const treatmentItems = configItems.value.filter(i => ['treatment', 'medication_record', 'status', 'timeline'].includes(i.type))
  const customItems = configItems.value.filter(i => i.type === 'custom')
  // record 类型兼容旧配置，归入治疗与记录分组
  const recordItems = configItems.value.filter(i => i.type === 'record')
  if (recordItems.length) treatmentItems.push(...recordItems)

  const groups = []
  if (overviewItems.length) groups.push({ label: '病人概况', items: overviewItems })
  if (labItems.length) groups.push({ label: '检验指标', items: labItems })
  if (reportItems.length) groups.push({ label: '报告数据', items: reportItems })
  if (treatmentItems.length) groups.push({ label: '治疗与记录', items: treatmentItems })
  if (customItems.length) groups.push({ label: '自定义', items: customItems })
  return groups
})

onMounted(async () => {
  // 读取侧边栏状态，设置工具条偏移量（Home.vue 通过 v-model + watch 同步到 localStorage）
  const collapsed = localStorage.getItem('sidebar-collapsed') === 'true'
  const sidebarWidth = collapsed ? 64 : 220
  document.documentElement.style.setProperty('--sidebar-offset', sidebarWidth + 'px')

  if (!patientId.value) return
  await loadConfig()
})

async function loadConfig() {
  try {
    const res = await getPromptConfig(patientId.value)
    if (res.status === 'success' && res.data) {
      timeRangeDays.value = res.data.time_range_days || 60
      configItems.value = (res.data.user_content_config || []).map(item => ({
        ...item,
        enabled: item.enabled ?? true,
      }))
    }
  } catch (e) {
    console.error('加载配置失败:', e)
    showToast('加载配置失败')
  }
}

async function handleSave() {
  saving.value = true
  try {
    const res = await savePromptConfig({
      patient_id: patientId.value,
      time_range_days: timeRangeDays.value,
      user_content_config: configItems.value,
    })
    if (res.status === 'success') {
      showToast('保存成功')
    } else {
      showToast(res.message || '保存失败')
    }
  } catch (e) {
    console.error('保存失败:', e)
    showToast('保存失败')
  } finally {
    saving.value = false
  }
}

async function handlePreview() {
  previewing.value = true
  try {
    const res = await previewPromptConfig({
      patient_id: patientId.value,
      time_range_days: timeRangeDays.value,
      user_content_config: configItems.value.filter(item => item.enabled),
    })
    if (res.status === 'success' && res.data) {
      previewText.value = res.data.prompt || ''
      if (!previewText.value) {
        showToast('暂无预览内容')
        return
      }
      showPreview.value = true
    } else {
      showToast('预览失败')
    }
  } catch (e) {
    console.error('预览失败:', e)
    showToast('预览失败')
  } finally {
    previewing.value = false
  }
}
</script>

<style scoped>
/* 使用项目主色调 */
.prompt-config {
  min-height: 100vh;
  background: var(--bg-primary);
  /* 移动端: tabbar ~50px + 底部操作栏 66px + 安全间距 */
  padding-bottom: calc(50px + 66px + env(safe-area-inset-bottom, 0px) + 12px);
}

.prompt-config :deep(.van-nav-bar) {
  background: var(--bg-surface-alpha);
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  z-index: 10;
}

.prompt-config :deep(.van-nav-bar__title) {
  color: var(--primary-color);
  font-weight: 600;
  font-size: 16px;
}

.prompt-config :deep(.van-nav-bar__text) {
  color: var(--primary-color);
}

.prompt-config :deep(.van-icon-arrow-left) {
  color: var(--primary-color);
}

.prompt-config.is-desktop :deep(.van-nav-bar) {
  max-width: 640px;
  margin: 0 auto;
}

.prompt-config.is-desktop {
  /* 桌面端无 tabbar，flex 布局使 sticky 底部生效 */
  /* --bottom-bar-height 补偿固定操作栏高度 */
  --bottom-bar-height: 74px;
  padding-bottom: calc(var(--bottom-bar-height) + var(--space-4));
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.is-desktop .config-content {
  flex: 1;
  max-width: 640px;
  margin: 0 auto;
  padding: 16px 16px 0;
  width: 100%;
}

.empty-patient {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.empty-patient p {
  margin-top: 12px;
  font-size: var(--text-sm);
}

.config-content {
  padding: 12px 12px 0;
}

/* ===== 通用卡片 ===== */
.config-card {
  background: var(--bg-surface);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--primary-alpha-6);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 10px;
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}

.config-card.compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.compact .card-header {
  margin-bottom: 0;
}

.card-indicator {
  width: 4px;
  height: 16px;
  background: var(--primary-color);
  border-radius: 2px;
  flex-shrink: 0;
}
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ===== 时间范围控件 ===== */
.time-range-control {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--primary-alpha-8);
  border-radius: 20px;
  padding: 4px 12px 4px 4px;
}

.time-unit {
  font-size: 13px;
  font-weight: 500;
  color: var(--primary-color);
}

/* ===== 配置项分组 ===== */
.config-group {
  margin-bottom: 4px;
}

.group-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  padding: 8px 4px 4px;
}

/* ===== 配置项卡片 ===== */
.item-card {
  padding: 12px 14px;
  transition: all 0.2s ease;
}

.item-card.active {
  background: var(--bg-surface-alpha);
  border-color: var(--primary-alpha-20);
  box-shadow: 0 2px 6px var(--primary-alpha-6);
}

.item-card.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--primary-color);
  border-radius: 2px 0 0 2px;
}

.item-card.disabled {
  opacity: 0.55;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.disabled .item-name {
  color: var(--text-tertiary);
}

/* ===== 参数行 ===== */
.param-row {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--primary-alpha-15);
}

.param-block {
  flex: 1;
  background: var(--primary-alpha-4);
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-label {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ===== 蓝色 Stepper 覆盖 ===== */
.blue-stepper :deep(.van-stepper__minus),
.blue-stepper :deep(.van-stepper__plus) {
  background: var(--primary-color);
  color: var(--bg-surface);
  border: none;
}

.blue-stepper :deep(.van-stepper__input) {
  color: var(--primary-color);
  font-weight: 600;
}

/* ===== textarea 样式 ===== */
.config-textarea :deep(.van-field__control) {
  background: var(--primary-alpha-3);
  border: 1px solid var(--primary-alpha-8);
  border-radius: 8px;
  padding: 10px;
}

/* ===== 底部操作栏 ===== */
.bottom-actions {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  display: flex;
  gap: 10px;
  background: var(--bg-surface-alpha);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow: 0 -2px 8px var(--primary-alpha-6);
  z-index: 100;
  /* 移动端: 避开 tabbar */
  bottom: 50px;
}

.is-desktop .bottom-actions {
  /* 桌面端: fixed 贴底，left 避开侧边栏 */
  position: fixed;
  bottom: 0;
  left: var(--sidebar-offset, 220px);
  right: 0;
  padding: 16px 24px;
  padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-color);
  box-shadow: 0 -4px 20px var(--primary-alpha-10);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  z-index: 100;
}

.action-btn {
  border-radius: 12px;
  height: 42px;
  font-weight: 500;
}

.is-desktop .action-btn {
  height: 42px;
  font-size: 14px;
  font-weight: 600;
  border-radius: 12px;
}

.is-desktop .action-btn :deep(.van-icon) {
  margin-right: 6px;
  font-size: 14px;
}

.preview-btn {
  flex: 1;
  color: var(--primary-color);
  border-color: var(--primary-alpha-20);
  background: var(--primary-alpha-8);
}

.is-desktop .preview-btn {
  flex: 0 0 auto;
  width: 140px;
  border-color: var(--primary-alpha-30);
  background: var(--primary-alpha-10);
  transition: all 0.2s ease;
}

.is-desktop .preview-btn:active {
  background: var(--primary-alpha-20);
}

.save-btn {
  flex: 2;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  border: none;
  box-shadow: 0 4px 12px var(--primary-alpha-30);
}

.is-desktop .save-btn {
  flex: 0 0 auto;
  width: 140px;
  font-size: 14px;
  box-shadow: 0 6px 20px var(--primary-alpha-30);
}

/* ===== 预览弹窗 ===== */
.preview-content {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  color: var(--text-primary);
  max-height: 80vh;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.preview-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-color);
}

.preview-close {
  font-size: 14px;
  color: var(--primary-color);
  cursor: pointer;
  flex-shrink: 0;
}

.preview-text {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  max-height: calc(80vh - 46px);
}
</style>
