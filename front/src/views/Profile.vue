<template>
  <div class="profile-view">
    <!-- 子路由渲染区域 -->
    <router-view v-slot="{ Component }">
      <template v-if="Component">
        <component :is="Component" />
      </template>
      <template v-else>
        <!-- 默认显示个人中心主页 -->
        <div class="profile-main">
          <!-- 用户信息 -->
          <div class="user-info">
            <van-image
              v-if="userStore.userInfo?.wechat_avatar"
              round
              width="52"
              height="52"
              :src="userStore.userInfo.wechat_avatar"
            />
            <div v-else class="avatar-fallback">
              <van-icon name="user-o" size="32" />
            </div>
            <h2 class="user-name">{{ userStore.userName }}</h2>
          </div>

          <!-- 当前病人信息区域 -->
          <div class="patient-section">
            <div class="patient-card">
              <div class="patient-header">
                <div class="patient-icon">
                  <van-icon name="user-circle-o" size="24" />
                </div>
                <div class="patient-info">
                  <h3 class="patient-name">{{ currentPatientName }}</h3>
                  <div class="patient-details">{{ currentPatientDetails }}</div>
                </div>
              </div>
              <div class="patient-actions">
                <van-button
                  class="manage-btn"
                  @click="goToPatientManagement"
                  icon="orders-o"
                  type="primary"
                  size="small"
                  round
                >
                  病人管理
                </van-button>
              </div>
            </div>
          </div>

          <!-- 功能列表 -->
          <!-- 健康管理 -->
          <van-cell-group inset class="function-list">
            <van-cell title="随访提醒" icon="clock-o" is-link to="/home/follow-up" />
            <van-cell title="数据导出" icon="down" is-link to="/home/profile/export" />
          </van-cell-group>

          <!-- 功能列表 -->
          <van-cell-group inset class="function-list">
            <van-cell title="个人信息" icon="user-o" is-link to="/home/profile/info" />
            <van-cell title="修改密码" icon="lock" is-link to="/home/profile/password" />
            <van-cell :title="`外观模式 · ${themeLabel}`" icon="brush-o" is-link @click="showThemePicker = true" />
            <van-cell title="消息通知" icon="bell" is-link to="/home/profile/notifications" />
            <van-cell title="隐私设置" icon="shield-o" is-link to="/home/profile/privacy" />
            <van-cell title="AI 模型配置" icon="setting-o" is-link to="/home/profile/ai-config" />
            <van-cell title="帮助中心" icon="question-o" is-link to="/home/profile/help" />
            <van-cell title="关于我们" icon="info-o" is-link to="/home/profile/about" />
            <van-cell title="支持作者" icon="gift-o" is-link @click="showSponsor = true" />
          </van-cell-group>

          <!-- 支持作者弹窗 -->
          <van-popup
            v-model:show="showSponsor"
            :position="isDesktop ? 'center' : 'bottom'"
            :round="!isDesktop"
            :style="isDesktop ? 'width: 420px; border-radius: var(--radius-lg);' : ''"
          >
            <div class="sponsor-panel">
              <span class="sponsor-close" @click="showSponsor = false">✕</span>
              <p class="sponsor-title">如果 OncoPath 对你有帮助，欢迎<em>请作者喝一杯咖啡</em></p>
              <p class="sponsor-subtitle">每一份支持都是持续维护的动力，真的很重要！</p>
              <div class="sponsor-qr-row">
                <figure class="sponsor-qr">
                  <img :src="wechatQr" alt="微信赞赏码">
                  <figcaption>💚 微信</figcaption>
                </figure>
                <figure class="sponsor-qr">
                  <img :src="alipayQr" alt="支付宝收款码">
                  <figcaption>💙 支付宝</figcaption>
                </figure>
              </div>
              <p class="sponsor-star-tip">⭐ 去 GitHub 点个 Star，同样是对作者的支持</p>
            </div>
          </van-popup>

          <!-- 主题选择器 -->
          <van-popup
            v-model:show="showThemePicker"
            :position="isDesktop ? 'center' : 'bottom'"
            :round="!isDesktop"
            :style="isDesktop ? 'width: 360px; border-radius: var(--radius-lg); overflow: hidden;' : ''"
          >
            <div class="theme-picker">
              <div class="theme-picker__title">外观模式</div>
              <div class="theme-picker__options">
                <div
                  v-for="action in themeActions"
                  :key="action.value"
                  class="theme-picker__option"
                  :class="{ 'theme-picker__option--active': currentTheme === action.value }"
                  @click="onThemeSelect(action)"
                >
                  <van-icon
                    :name="currentTheme === action.value ? 'success' : 'circle'"
                    :class="{ 'active-icon': currentTheme === action.value }"
                  />
                  <span>{{ action.name }}</span>
                </div>
              </div>
            </div>
          </van-popup>

          <!-- 退出登录 -->
          <div class="logout-section">
            <van-button round block type="danger" plain @click="handleLogout">
              退出登录
            </van-button>
          </div>

          <!-- 版本信息 -->
          <div class="version-info">
            <p>版本 2.0.0</p>
          </div>
        </div>
      </template>
    </router-view>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { showDialog } from 'vant'
import { useUserStore } from '@/stores/user'
import { usePatientStore } from '@/stores/patient'
import { useTheme } from '@/composables/useTheme'
import { useResponsive } from '@/composables/useResponsive'
import wechatQr from '@/assets/sponsor/wechat.jpg'
import alipayQr from '@/assets/sponsor/alipay.jpg'

const router = useRouter()
const userStore = useUserStore()
const patientStore = usePatientStore()

const { currentTheme, setTheme } = useTheme()
const { isDesktop } = useResponsive()

// 主题选择
const showThemePicker = ref(false)

// 支持作者弹窗
const showSponsor = ref(false)

const themeLabel = computed(() => ({
  light: '浅色',
  dark: '深色',
  system: '跟随系统',
}[currentTheme.value]))

const themeActions = [
  { name: '浅色', value: 'light' },
  { name: '深色', value: 'dark' },
  { name: '跟随系统', value: 'system' },
]

function onThemeSelect(action) {
  setTheme(action.value)
  showThemePicker.value = false
}

// 当前病人信息
const currentPatientName = computed(() => {
  return patientStore.currentPatient?.patient_name || '未选择患者'
})

const currentPatientDetails = computed(() => {
  const patient = patientStore.currentPatient
  if (!patient) return '请在病人管理中添加或选择患者'

  const details = []
  if (patient.age !== null && patient.age !== undefined) details.push(`${patient.age}岁`)
  if (patient.gender === 'male') details.push('男')
  else if (patient.gender === 'female') details.push('女')
  if (patient.is_primary) details.push('主患者')

  return details.length > 0 ? details.join(' · ') : '暂无详细信息'
})

// 跳转到病人管理页面
function goToPatientManagement() {
  router.push('/home/patient-management')
}

async function handleLogout() {
  try {
    await showDialog({
      title: '提示',
      message: '确定要退出登录吗？',
    })
    await userStore.logout()
    router.replace('/login')
  } catch {
    // 取消退出
  }
}
</script>

<style scoped>
.profile-view {
  min-height: 100vh;
  background: var(--bg-primary);
}

.profile-main {
  padding: var(--space-4);
  padding-bottom: var(--safe-bottom);
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-4) 0;
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-4);
}

.user-name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-top: var(--space-2);
}

.avatar-fallback {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--primary-alpha-10);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
}

/* 病人信息区域 */
.patient-section {
  margin-bottom: var(--space-4);
}

.patient-card {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  padding: var(--space-4);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 4px 12px var(--primary-alpha-30);
}

.patient-header {
  display: flex;
  align-items: center;
  flex: 1;
}

.patient-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: var(--space-3);
  color: var(--bg-surface);
}

.patient-info {
  flex: 1;
}

.patient-name {
  color: var(--bg-surface);
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0 0 4px 0;
}

.patient-details {
  color: rgba(255, 255, 255, 0.85);
  font-size: var(--text-sm);
}

.patient-actions {
  margin-left: var(--space-3);
}

.manage-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: var(--bg-surface);
}

.function-list {
  margin-bottom: var(--space-4);
}

.theme-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.logout-section {
  padding: var(--space-4);
}

/* 主题选择器 */
.theme-picker {
  padding: 20px;
}

.theme-picker__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: center;
  margin-bottom: 16px;
}

.theme-picker__options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.theme-picker__option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: 14px;
  color: var(--text-primary);
  transition: background 0.2s;
  min-height: 44px;
}

.theme-picker__option:active {
  background: var(--primary-alpha-8);
}

.theme-picker__option--active {
  background: var(--primary-alpha-5);
  color: var(--primary-color);
  font-weight: 500;
}

.active-icon {
  color: var(--primary-color);
}

/* 支持作者弹窗 */
.sponsor-panel {
  position: relative;
  padding: 24px 20px calc(20px + env(safe-area-inset-bottom, 0px));
  text-align: center;
}

.sponsor-close {
  position: absolute;
  top: 12px;
  right: 16px;
  font-size: 15px;
  color: var(--text-tertiary);
  cursor: pointer;
}

.sponsor-title {
  margin: 0 12px;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.6;
}

.sponsor-title em {
  font-style: normal;
  color: var(--primary-color);
}

.sponsor-subtitle {
  margin: 6px 0 16px;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.sponsor-qr-row {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.sponsor-qr {
  margin: 0;
  padding: 8px;
  background: var(--bg-surface);
  border: 1px solid var(--primary-alpha-15);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.sponsor-qr img {
  display: block;
  width: 132px;
  height: 132px;
  object-fit: cover;
  border-radius: var(--radius-sm);
}

.sponsor-qr figcaption {
  margin-top: 6px;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--text-primary);
}

.sponsor-star-tip {
  margin: 14px 0 0;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.version-info {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-4);
}

/* 桌面端布局 */
@media (min-width: 768px) {
  .profile-main {
    max-width: 800px;
    margin: 0 auto;
    padding: var(--space-6);
    padding-bottom: var(--space-6);
  }

  .function-list :deep(.van-cell-group__inset) {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: var(--space-2);
  }

  .function-list :deep(.van-cell) {
    justify-content: center;
    text-align: center;
  }
}
</style>