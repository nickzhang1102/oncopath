<template>
  <div class="profile-password">
    <BackButton title="修改密码" />

    <div class="form-section">
      <van-cell-group inset>
        <van-field
          v-model="form.old_password"
          type="password"
          label="旧密码"
          placeholder="请输入旧密码"
          :rules="[{ required: true, message: '请输入旧密码' }]"
        />
        <van-field
          v-model="form.new_password"
          type="password"
          label="新密码"
          placeholder="请输入新密码（8位以上，含字母和数字）"
          :rules="[
            { required: true, message: '请输入新密码' },
            { pattern: passwordPattern, message: '密码需至少8位，且包含字母和数字' }
          ]"
        />
        <van-field
          v-model="form.confirm_password"
          type="password"
          label="确认密码"
          placeholder="请再次输入新密码"
          :rules="[
            { required: true, message: '请确认新密码' },
            { validator: validateConfirmPassword, message: '两次输入的密码不一致' }
          ]"
        />
      </van-cell-group>

      <!-- 密码提示 -->
      <div class="password-tips">
        <p class="tip-title">密码要求：</p>
        <ul class="tip-list">
          <li>密码长度至少8位</li>
          <li>必须包含字母和数字</li>
          <li>必须包含特殊字符（如 !@#$% 等）</li>
          <li>新密码不能与旧密码相同</li>
        </ul>
      </div>

      <!-- 提交按钮 -->
      <div class="submit-section">
        <van-button
          round
          block
          type="primary"
          :loading="loading"
          @click="handleSubmit"
        >
          确认修改
        </van-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { showToast, showSuccessToast, showDialog } from 'vant'
import { userApi } from '@/api/user'
import { useUserStore } from '@/stores/user'
import BackButton from '@/components/index-detail/BackButton.vue'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// 密码复杂度正则：至少8位，包含字母和数字（与后端校验口径一致，特殊字符可选）
const passwordPattern = /^(?=.*[a-zA-Z])(?=.*\d).{8,128}$/

function validateConfirmPassword() {
  return form.confirm_password === form.new_password
}

async function handleSubmit() {
  // 基本验证
  if (!form.old_password) {
    showToast('请输入旧密码')
    return
  }
  if (!form.new_password) {
    showToast('请输入新密码')
    return
  }
  if (!passwordPattern.test(form.new_password)) {
    showToast('密码需至少8位，且包含字母和数字')
    return
  }
  if (form.new_password !== form.confirm_password) {
    showToast('两次输入的密码不一致')
    return
  }

  loading.value = true
  try {
    await userApi.changePassword({
      old_password: form.old_password,
      new_password: form.new_password
    })
    
    await showDialog({
      title: '成功',
      message: '密码修改成功，请重新登录',
    })
    
    // 清除全部登录状态，跳转到登录页
    userStore.logout(true)
    router.replace('/login')
  } catch (error) {
    showToast(error.response?.data?.detail || '修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-password {
  min-height: 100vh;
  background: var(--bg-primary);
}

.form-section {
  padding-top: var(--space-4);
}

.password-tips {
  margin: var(--space-4);
  padding: var(--space-3);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
}

.tip-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.tip-list {
  margin: 0;
  padding-left: var(--space-4);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.tip-list li {
  margin-bottom: var(--space-1);
}

.submit-section {
  padding: var(--space-6) var(--space-4);
}

@media (max-width: 480px) {
  .password-tips {
    margin: var(--space-3);
    padding: var(--space-2);
  }

  .submit-section {
    padding: var(--space-4) var(--space-3);
  }
}

@media (min-width: 768px) {
  .profile-password {
    max-width: 600px;
    margin: 0 auto;
    padding: var(--space-6);
  }
}
</style>