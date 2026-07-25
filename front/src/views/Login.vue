<template>
  <div class="login-page">
    <div class="login-header">
      <div class="login-logo">
        <van-icon name="shield-o" size="48" :style="{ color: 'var(--primary-color)' }" />
      </div>
      <h1 class="login-title">OncoPath</h1>
      <p class="login-subtitle">智能分析 · 健康管理</p>
    </div>

    <!-- 登录/注册表单 -->
    <van-form v-if="mode === 'login' || mode === 'register'" @submit="handleSubmit" class="login-form">
      <van-cell-group inset>
        <van-field
          v-model="form.username"
          name="username"
          label="用户名"
          placeholder="请输入用户名"
          :rules="[{ required: true, message: '请输入用户名' }]"
        />
        <van-field
          v-model="form.password"
          type="password"
          name="password"
          label="密码"
          placeholder="请输入密码"
          :rules="[{ required: true, message: '请输入密码' }]"
        />
        <van-field
          v-if="mode === 'register'"
          v-model="form.confirmPassword"
          type="password"
          name="confirmPassword"
          label="确认密码"
          placeholder="请再次输入密码"
          :rules="[{ required: true, message: '请再次输入密码' }, { validator: validateConfirmPassword, message: '两次密码不一致' }]"
        />
      </van-cell-group>

      <div class="login-actions">
        <van-button
          round
          block
          type="primary"
          native-type="submit"
          :loading="loading"
          :loading-text="mode === 'register' ? '注册中...' : '登录中...'"
        >
          {{ mode === 'register' ? '注册' : '登录' }}
        </van-button>
      </div>
    </van-form>

    <!-- 忘记密码 - 步骤1：输入用户名获取令牌 -->
    <van-form v-else-if="mode === 'forgot'" @submit="handleForgotPassword" class="login-form">
      <van-cell-group inset>
        <van-field
          v-model="forgotForm.username"
          name="username"
          label="用户名"
          placeholder="请输入注册时的用户名"
          :rules="[{ required: true, message: '请输入用户名' }]"
        />
      </van-cell-group>
      <div class="login-actions">
        <van-button round block type="primary" native-type="submit" :loading="loading" loading-text="提交中...">
          获取重置码
        </van-button>
      </div>
    </van-form>

    <!-- 忘记密码 - 步骤2：输入重置码和新密码 -->
    <van-form v-else-if="mode === 'reset'" @submit="handleResetPassword" class="login-form">
      <van-cell-group inset>
        <van-field
          v-model="resetForm.resetToken"
          name="resetToken"
          label="重置码"
          placeholder="请输入6位重置码"
          maxlength="6"
          :rules="[{ required: true, message: '请输入重置码' }]"
        />
        <van-field
          v-model="resetForm.newPassword"
          type="password"
          name="newPassword"
          label="新密码"
          placeholder="请输入新密码（6位以上）"
          :rules="[{ required: true, message: '请输入新密码' }]"
        />
        <van-field
          v-model="resetForm.confirmPassword"
          type="password"
          name="confirmPassword"
          label="确认密码"
          placeholder="请再次输入新密码"
          :rules="[{ required: true, message: '请再次输入新密码' }, { validator: validateResetConfirmPassword, message: '两次密码不一致' }]"
        />
      </van-cell-group>
      <div class="login-actions">
        <van-button round block type="primary" native-type="submit" :loading="loading" loading-text="重置中...">
          重置密码
        </van-button>
      </div>
    </van-form>

    <div class="login-switch">
      <template v-if="mode === 'login'">
        <span @click="mode = 'forgot'">忘记密码？</span>
        <span @click="switchMode('register')">没有账号？立即注册</span>
      </template>
      <template v-else-if="mode === 'register'">
        <span @click="switchMode('login')">已有账号？返回登录</span>
      </template>
      <template v-else>
        <span @click="switchMode('login')">返回登录</span>
      </template>
    </div>

    <div class="login-footer">
      <p>© 2026 OncoPath</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '@/stores/user'
import { userApi } from '@/api/user'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const mode = ref('login') // login | register | forgot | reset
const form = ref({
  username: '',
  password: '',
  confirmPassword: '',
})
const forgotForm = ref({ username: '' })
const resetForm = ref({
  resetToken: '',
  newPassword: '',
  confirmPassword: '',
})

function switchMode(newMode) {
  mode.value = newMode
  form.value = { username: '', password: '', confirmPassword: '' }
  forgotForm.value = { username: '' }
  resetForm.value = { resetToken: '', newPassword: '', confirmPassword: '' }
}

function validateConfirmPassword() {
  return form.value.password === form.value.confirmPassword
}

function validateResetConfirmPassword() {
  return resetForm.value.newPassword === resetForm.value.confirmPassword
}

function extractError(error) {
  const detail = error.response?.data?.detail
  if (!detail) return '操作失败'
  if (typeof detail === 'string') return detail
  // FastAPI 422 校验错误: [{msg, loc, type}, ...]
  if (Array.isArray(detail)) {
    return detail.map(e => {
      const field = e.loc?.slice(1).join('.') || ''
      return field ? `${field}: ${e.msg}` : e.msg
    }).join('; ')
  }
  return JSON.stringify(detail)
}

async function handleSubmit() {
  if (mode.value === 'register') {
    await handleRegister()
  } else {
    await handleLogin()
  }
}

async function handleLogin() {
  loading.value = true
  try {
    await userStore.login({ username: form.value.username, password: form.value.password })
    showToast('登录成功')
    router.replace('/home')
  } catch (error) {
    showToast(extractError(error))
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  try {
    await userApi.register({ username: form.value.username, password: form.value.password })
    await userStore.login({ username: form.value.username, password: form.value.password })
    showToast('注册成功')
    router.replace('/home')
  } catch (error) {
    showToast(extractError(error))
  } finally {
    loading.value = false
  }
}

async function handleForgotPassword() {
  loading.value = true
  try {
    const data = await userApi.forgotPassword({ username: forgotForm.value.username })
    showToast('如果用户名存在，重置验证码已发送')
    mode.value = 'reset'
  } catch (error) {
    showToast(extractError(error))
  } finally {
    loading.value = false
  }
}

async function handleResetPassword() {
  loading.value = true
  try {
    await userApi.resetPassword({
      username: forgotForm.value.username,
      reset_token: resetForm.value.resetToken,
      new_password: resetForm.value.newPassword,
    })
    showToast('密码重置成功，请登录')
    mode.value = 'login'
    form.value.username = forgotForm.value.username
    form.value.password = ''
  } catch (error) {
    showToast(extractError(error))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: var(--space-6);
  background: linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-surface) 100%);
}

.login-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.login-logo {
  width: 80px;
  height: 80px;
  margin: 0 auto var(--space-4);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-alpha-10);
  border-radius: 50%;
}

.login-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.login-subtitle {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.login-form {
  margin-bottom: var(--space-6);
}

.login-actions {
  margin-top: var(--space-6);
  padding: 0 var(--space-4);
}

.login-switch {
  display: flex;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.login-switch span {
  color: var(--primary-color);
  font-size: var(--text-sm);
  cursor: pointer;
}

.login-footer {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

@media (min-width: 768px) {
  .login-page {
    max-width: 480px;
    margin: 0 auto;
  }
}
</style>
