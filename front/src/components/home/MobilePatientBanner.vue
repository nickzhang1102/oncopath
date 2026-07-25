<template>
  <div class="mobile-patient-banner" @click="handleClick">
    <div class="banner-left">
      <span class="patient-name">{{ data.patient_name || '未设置' }}</span>
      <span class="patient-meta">{{ metaText }}</span>
    </div>
    <div class="banner-right">
      <span v-if="data.diagnosis" class="diagnosis-text">{{ data.diagnosis }}</span>
      <span v-if="data.active_medication_count > 0" class="med-badge">
        <van-icon name="gem-o" size="12" />
        用药 {{ data.active_medication_count }} 种
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  data: { type: Object, required: true },
})

const router = useRouter()

const genderLabel = { male: '男', female: '女' }

const metaText = computed(() => {
  const parts = []
  if (props.data.age != null) parts.push(`${props.data.age}岁`)
  if (props.data.gender) parts.push(genderLabel[props.data.gender] || props.data.gender)
  return parts.join(' ') || '-'
})

function handleClick() {
  router.push('/home/patient-management')
}
</script>

<style scoped>
.mobile-patient-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--bg-surface-alpha);
  padding: 12px 16px;
  border-radius: var(--radius-xl);
  box-shadow: 0 4px 16px var(--primary-alpha-10);
  cursor: pointer;
  transition: background 0.2s;
  min-height: 48px;
}

.mobile-patient-banner:active {
  background: var(--primary-alpha-8);
}

.banner-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.patient-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}

.patient-meta {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.banner-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.diagnosis-text {
  font-size: 12px;
  color: var(--primary-color);
  background: var(--primary-alpha-8);
  padding: 3px 8px;
  border-radius: var(--radius-md);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.med-badge {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: var(--success-color);
  background: var(--status-normal-bg);
  padding: 3px 8px;
  border-radius: var(--radius-md);
  white-space: nowrap;
}
</style>