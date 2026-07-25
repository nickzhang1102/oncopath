import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { userApi } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  // State
  const token = ref(localStorage.getItem('token'))
  const refreshToken = ref(localStorage.getItem('refreshToken'))

  // userInfo 不再持久化到 localStorage，每次从 API 获取
  const userInfo = ref(null)
  const error = ref(null)
  const loading = ref(false)

  // Getters
  const isLoggedIn = computed(() => !!token.value)
  const userId = computed(() => userInfo.value?.account_id)
  const userName = computed(() => userInfo.value?.account_name || userInfo.value?.username)

  // Actions
  async function login(credentials) {
    error.value = null
    loading.value = true
    try {
      const response = await userApi.login(credentials)
      setToken(response.access_token, response.refresh_token)
      await fetchUserInfo()
      return response
    } catch (e) {
      error.value = e.message || '登录失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  function setToken(access, refresh) {
    token.value = access
    refreshToken.value = refresh
    localStorage.setItem('token', access)
    localStorage.setItem('refreshToken', refresh)
  }

  async function fetchUserInfo() {
    loading.value = true
    try {
      const data = await userApi.getProfile()
      userInfo.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function logout(skipApi = false) {
    if (!skipApi && token.value) {
      try {
        await userApi.logout()
      } catch (e) {
        // 后端登出失败仍继续本地清理
      }
    }
    // 清除本地状态
    token.value = null
    refreshToken.value = null
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('currentPatientId')
  }

  return {
    token,
    refreshToken,
    userInfo,
    error,
    loading,
    isLoggedIn,
    userId,
    userName,
    login,
    logout,
    setToken,
    fetchUserInfo,
  }
})
