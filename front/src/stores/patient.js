import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { patientApi } from '@/api/patient'

export const usePatientStore = defineStore('patient', () => {
  // State
  const patientList = ref([])
  const currentPatient = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const loaded = ref(false)

  // Getters
  const primaryPatient = computed(() =>
    patientList.value.find(p => p.is_primary)
  )

  const patientCount = computed(() => patientList.value.length)

  const hasPatients = computed(() => patientList.value.length > 0)

  // Actions
  async function fetchPatientList() {
    loading.value = true
    error.value = null
    try {
      const data = await patientApi.getPatientList()
      patientList.value = data
      loaded.value = true
      // 恢复之前选中的患者（实时读 localStorage，避免跨会话的过期闭包值）
      const savedPatientId = localStorage.getItem('currentPatientId')
      if (!currentPatient.value && savedPatientId) {
        const saved = data.find(p => String(p.patient_id) === savedPatientId)
        if (saved) {
          currentPatient.value = saved
        }
      }
      // 如果没有当前患者，自动选择主患者或第一个
      if (!currentPatient.value && data.length > 0) {
        const primary = data.find(p => p.is_primary)
        setCurrentPatient(primary || data[0])
      }
      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function setCurrentPatient(patient) {
    currentPatient.value = patient
    localStorage.setItem('currentPatientId', String(patient.patient_id))
  }

  async function switchPatient(patientId) {
    error.value = null
    try {
      // 调用后端切换接口
      await patientApi.switchPatient(patientId)

      // 从本地列表中找到患者并设置为当前患者
      const patient = patientList.value.find(p => p.patient_id === patientId)
      if (patient) {
        setCurrentPatient(patient)
      }

      return patient
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function createPatient(data) {
    error.value = null
    try {
      const patient = await patientApi.createPatient(data)
      // 刷新列表
      await fetchPatientList()
      return patient
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function updatePatient(patientId, data) {
    error.value = null
    try {
      const patient = await patientApi.updatePatient(patientId, data)
      // 刷新列表
      await fetchPatientList()
      return patient
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function deletePatient(patientId) {
    error.value = null
    try {
      const result = await patientApi.deletePatient(patientId)

      // 从列表中移除
      patientList.value = patientList.value.filter(p => p.patient_id !== patientId)

      // 如果删除的是当前患者，切换到主患者或第一个
      if (currentPatient.value?.patient_id === patientId) {
        const primary = patientList.value.find(p => p.is_primary)
        if (primary) {
          setCurrentPatient(primary)
        } else if (patientList.value.length > 0) {
          setCurrentPatient(patientList.value[0])
        } else {
          currentPatient.value = null
          localStorage.removeItem('currentPatientId')
        }
      }

      return result
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  async function getPatientById(patientId) {
    // 先从本地列表查找
    const local = patientList.value.find(p => p.patient_id === patientId)
    if (local) return local

    // 否则从服务器获取
    return await patientApi.getPatient(patientId)
  }

  function clearPatients() {
    patientList.value = []
    currentPatient.value = null
    error.value = null
    loaded.value = false
    localStorage.removeItem('currentPatientId')
  }

  function clearPatientData() {
    clearPatients()
  }

  return {
    patientList,
    currentPatient,
    loading,
    error,
    loaded,
    primaryPatient,
    patientCount,
    hasPatients,
    fetchPatientList,
    setCurrentPatient,
    switchPatient,
    createPatient,
    updatePatient,
    deletePatient,
    getPatientById,
    clearPatients,
    clearPatientData,
  }
})