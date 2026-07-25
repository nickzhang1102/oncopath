<template>
  <div class="dashboard-card patient-overview">
    <div class="card-header">
      <van-icon name="user-circle-o" class="header-icon" />
      <span class="header-title">患者概览</span>
    </div>
    <div class="patient-info">
      <div class="info-row">
        <span class="info-label">姓名</span>
        <span class="info-value">{{ data.patient_name || '未设置' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">年龄</span>
        <span class="info-value">{{ data.age != null ? data.age + '岁' : '-' }}</span>
      </div>
      <div class="info-row">
        <span class="info-label">性别</span>
        <span class="info-value">{{ genderLabel }}</span>
      </div>
      <div v-if="data.id_card" class="info-row">
        <span class="info-label">身份证</span>
        <span class="info-value">{{ data.id_card }}</span>
      </div>
      <div v-if="data.patient_phone" class="info-row">
        <span class="info-label">手机号</span>
        <span class="info-value">{{ data.patient_phone }}</span>
      </div>
      <div v-if="data.emergency_contact" class="info-row">
        <span class="info-label">紧急联系人</span>
        <span class="info-value">{{ emergencyContactLabel }}</span>
      </div>
      <div v-if="data.medical_history" class="info-row diagnosis">
        <span class="info-label">病史</span>
        <span class="info-value">{{ data.medical_history }}</span>
      </div>
      <div v-if="data.allergies" class="info-row diagnosis">
        <span class="info-label">过敏史</span>
        <span class="info-value">{{ data.allergies }}</span>
      </div>
    </div>
    <div v-if="data.active_medication_count > 0" class="med-summary">
      <van-icon name="gem-o" size="14" />
      <span>当前用药 {{ data.active_medication_count }} 种</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, required: true },
})

const genderLabel = computed(() => {
  const m = { male: '男', female: '女' }
  return m[props.data.gender] || props.data.gender || '-'
})

const emergencyContactLabel = computed(() => {
  const name = props.data.emergency_contact || ''
  const phone = props.data.emergency_phone || ''
  if (name && phone) return `${name} ${phone}`
  return name || phone
})
</script>

<style scoped>
.patient-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.info-row.diagnosis .info-value {
  text-align: right;
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.info-label {
  color: var(--text-secondary);
}

.info-value {
  color: var(--text-primary);
  font-weight: 500;
}

.med-summary {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--primary-alpha-10);
  font-size: 12px;
  color: var(--success-color);
}
</style>
