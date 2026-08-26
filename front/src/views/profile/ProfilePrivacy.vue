<template>
  <div class="profile-privacy">
    <BackButton title="隐私设置" />

    <!-- 数据分享设置 -->
    <div class="settings-section">
      <div class="section-title">数据分享</div>
      <van-cell-group inset>
        <van-cell title="允许数据用于系统优化" center>
          <template #right-icon>
            <van-switch
              v-model="settings.data_sharing_enabled"
              :loading="loading"
              @change="handleUpdate"
            />
          </template>
        </van-cell>
      </van-cell-group>
      <p class="section-tip">开启后，您的脱敏数据将帮助我们优化系统服务</p>
    </div>

    <!-- 通知设置 -->
    <div class="settings-section">
      <div class="section-title">通知设置</div>
      <van-cell-group inset>
        <van-cell title="接收系统通知" center>
          <template #right-icon>
            <van-switch
              v-model="settings.notification_enabled"
              :loading="loading"
              @change="handleUpdate"
            />
          </template>
        </van-cell>
        <van-cell title="邮件通知" center>
          <template #right-icon>
            <van-switch
              v-model="settings.email_notification"
              :loading="loading"
              @change="handleUpdate"
            />
          </template>
        </van-cell>
        <van-cell title="短信通知" center>
          <template #right-icon>
            <van-switch
              v-model="settings.sms_notification"
              :loading="loading"
              @change="handleUpdate"
            />
          </template>
        </van-cell>
      </van-cell-group>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { userApi } from '@/api/user'
import BackButton from '@/components/index-detail/BackButton.vue'

const loading = ref(false)
const settings = reactive({
  data_sharing_enabled: true,
  notification_enabled: true,
  email_notification: false,
  sms_notification: false
})

onMounted(async () => {
  await loadSettings()
})

async function loadSettings() {
  try {
    const res = await userApi.getPrivacySettings()
    Object.assign(settings, res)
  } catch (error) {
    showToast('加载设置失败')
  }
}

async function handleUpdate() {
  loading.value = true
  try {
    await userApi.updatePrivacySettings(settings)
    showSuccessToast('设置已保存')
  } catch (error) {
    showToast('保存失败')
    // 恢复原设置
    await loadSettings()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-privacy {
  min-height: 100vh;
  background: var(--bg-primary);
}

.settings-section {
  margin-bottom: var(--space-4);
}

.section-title {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.section-tip {
  padding: 0 var(--space-4);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-2);
}

@media (max-width: 480px) {
  .section-title {
    padding: var(--space-2) var(--space-3);
  }

  .section-tip {
    padding: 0 var(--space-3);
  }
}

@media (min-width: 768px) {
  .profile-privacy {
    max-width: 600px;
    margin: 0 auto;
    padding: 0 var(--space-6) var(--space-6);
  }
}
</style>