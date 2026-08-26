<template>
  <div class="profile-info">
    <BackButton title="个人信息" />

    <!-- 头像 -->
    <div class="avatar-section">
      <van-image
        round
        width="80"
        height="80"
        :src="userStore.userInfo?.wechat_avatar || defaultAvatar"
      />
      <p class="avatar-tip">头像通过微信同步</p>
    </div>

    <!-- 表单 -->
    <van-cell-group inset class="form-section">
      <van-field
        v-model="form.username"
        label="用户名"
        readonly
        disabled
      />
      <van-field
        v-model="form.account_name"
        label="昵称"
        placeholder="请输入昵称"
        :rules="[{ required: false, message: '请输入昵称' }]"
      />
      <van-field
        v-model="form.phone"
        label="手机号"
        placeholder="请输入手机号"
        type="tel"
        :rules="[{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }]"
      />
    </van-cell-group>

    <!-- 保存按钮 -->
    <div class="save-section">
      <van-button
        round
        block
        type="primary"
        :loading="loading"
        @click="handleSave"
      >
        保存修改
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api/user'
import BackButton from '@/components/index-detail/BackButton.vue'

const userStore = useUserStore()
const loading = ref(false)
const defaultAvatar = 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg'

const form = reactive({
  username: '',
  account_name: '',
  phone: ''
})

onMounted(async () => {
  await loadProfile()
})

async function loadProfile() {
  try {
    const res = await userApi.getUserProfile()
    form.username = res.username
    form.account_name = res.account_name || ''
    form.phone = res.phone || ''
  } catch (error) {
    showToast('加载用户信息失败')
  }
}

async function handleSave() {
  // 验证手机号
  if (form.phone && !/^1[3-9]\d{9}$/.test(form.phone)) {
    showToast('请输入正确的手机号')
    return
  }

  loading.value = true
  try {
    await userApi.updateUserProfile({
      account_name: form.account_name || null,
      phone: form.phone || null
    })
    showSuccessToast('保存成功')
    // 更新store
    await userStore.fetchUserInfo()
  } catch (error) {
    showToast(error.response?.data?.detail || '保存失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-info {
  min-height: 100vh;
  background: var(--bg-primary);
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-6) 0;
  background: var(--bg-surface);
}

.avatar-tip {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-2);
}

.form-section {
  margin-top: var(--space-4);
}

.save-section {
  padding: var(--space-6) var(--space-4);
}

@media (max-width: 480px) {
  .avatar-section {
    padding: var(--space-4) 0;
  }

  .save-section {
    padding: var(--space-4) var(--space-3);
  }
}

@media (min-width: 768px) {
  .profile-info {
    max-width: 600px;
    margin: 0 auto;
    padding: 0 var(--space-6) var(--space-6);
  }
}
</style>