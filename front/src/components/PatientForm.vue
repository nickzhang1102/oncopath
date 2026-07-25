<template>
  <van-popup
    v-model:show="visible"
    :position="isDesktop ? 'center' : 'bottom'"
    :round="!isDesktop"
    :class="isDesktop ? 'desktop-popup-lg' : ''"
    :style="!isDesktop ? { height: '90%' } : ''"
    closeable
    close-icon-position="top-right"
    @close="handleClose"
  >
    <div class="patient-form">
      <div class="form-header">
        <h2>{{ isEdit ? '编辑病人信息' : '添加病人' }}</h2>
      </div>
      
      <van-form @submit="handleSubmit" class="form-content">
        <van-cell-group inset>
          <van-field
            v-model="formData.patient_name"
            name="patient_name"
            label="姓名"
            placeholder="请输入病人姓名"
            required
            maxlength="50"
            :rules="[{ required: true, message: '请输入病人姓名' }]"
          />

          <van-field
            v-model="formData.patient_phone"
            name="patient_phone"
            label="手机号"
            placeholder="请输入手机号（选填）"
            type="tel"
            :rules="[{ validator: validatePhone, message: '请输入正确的手机号' }]"
          />

          <van-field
            v-model="formData.id_card"
            name="id_card"
            label="身份证号"
            placeholder="请输入身份证号（选填）"
            maxlength="18"
            :rules="[{ validator: validateIdCard, message: '请输入正确的身份证号' }]"
            @blur="checkIdCard"
          />
          
          <van-field name="gender" label="性别">
            <template #input>
              <van-radio-group v-model="formData.gender" direction="horizontal">
                <van-radio name="male">男</van-radio>
                <van-radio name="female">女</van-radio>
              </van-radio-group>
            </template>
          </van-field>

          <van-field
            v-model="formData.birth_date"
            name="birth_date"
            label="出生日期"
            placeholder="请选择出生日期"
            readonly
            clickable
            @click="showBirthDatePicker = true"
          />
          
          <van-field
            v-model="formData.emergency_contact"
            name="emergency_contact"
            label="紧急联系人"
            placeholder="请输入紧急联系人"
          />
          
          <van-field
            v-model="formData.emergency_phone"
            name="emergency_phone"
            label="紧急联系电话"
            placeholder="请输入紧急联系电话"
            type="tel"
          />
          
          <van-field
            v-model="formData.medical_history"
            name="medical_history"
            label="病史"
            placeholder="请输入病史信息"
            type="textarea"
            rows="3"
          />
          
          <van-field
            v-model="formData.allergies"
            name="allergies"
            label="过敏史"
            placeholder="请输入过敏史"
            type="textarea"
            rows="2"
          />
          
          <van-field
            v-model="formData.current_medications"
            name="current_medications"
            label="当前用药"
            placeholder="请输入当前用药情况"
            type="textarea"
            rows="2"
          />
          
          <van-field
            v-model="formData.notes"
            name="notes"
            label="备注"
            placeholder="请输入备注信息"
            type="textarea"
            rows="2"
          />
        </van-cell-group>
        
        <div class="form-actions">
          <van-button 
            round 
            block 
            type="primary" 
            native-type="submit"
            :loading="loading"
          >
            {{ isEdit ? '更新' : '添加' }}
          </van-button>
        </div>
      </van-form>
    </div>

    <!-- 出生日期选择器 -->
    <van-popup v-model:show="showBirthDatePicker" :position="isDesktop ? 'center' : 'bottom'" :round="!isDesktop" :class="isDesktop ? 'desktop-popup-sm' : ''">
      <van-date-picker
        v-model="birthDateValue"
        title="选择出生日期"
        :min-date="minDate"
        :max-date="maxDate"
        @confirm="onDateConfirm"
        @cancel="showBirthDatePicker = false"
      />
    </van-popup>
  </van-popup>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { showToast } from 'vant'
import { patientApi } from '@/api/patient'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop } = useResponsive()

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  patient: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:show', 'success'])

const visible = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
})

const isEdit = computed(() => !!props.patient)
const loading = ref(false)
const showBirthDatePicker = ref(false)

// 日期范围
const maxDate = new Date()
const minDate = new Date(1900, 0, 1)

// 出生日期选择器值
const birthDateValue = ref([
  new Date().getFullYear().toString(),
  (new Date().getMonth() + 1).toString().padStart(2, '0'),
  new Date().getDate().toString().padStart(2, '0')
])

// 表单数据
const formData = reactive({
  patient_name: '',
  patient_phone: '',
  id_card: '',
  gender: 'male',
  birth_date: '',
  emergency_contact: '',
  emergency_phone: '',
  medical_history: '',
  allergies: '',
  current_medications: '',
  notes: ''
})

// 验证函数
function validatePhone(value) {
  if (!value) return true // 选填字段，空值通过验证
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(value)
}

function validateIdCard(value) {
  if (!value) return true // 选填字段，空值通过验证
  const idCardRegex = /^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/
  return idCardRegex.test(value)
}

// 重置表单
function resetForm() {
  Object.assign(formData, {
    patient_name: '',
    patient_phone: '',
    id_card: '',
    gender: 'male',
    birth_date: '',
    emergency_contact: '',
    emergency_phone: '',
    medical_history: '',
    allergies: '',
    current_medications: '',
    notes: ''
  })
  birthDateValue.value = [
    new Date().getFullYear().toString(),
    (new Date().getMonth() + 1).toString().padStart(2, '0'),
    new Date().getDate().toString().padStart(2, '0')
  ]
}

// 监听病人数据变化
watch(() => props.patient, async (newPatient) => {
  if (newPatient) {
    // 编辑模式：从 /edit 端点获取明文敏感字段
    try {
      const editData = await patientApi.getPatientForEdit(newPatient.patient_id)
      Object.assign(formData, {
        patient_name: editData.patient_name || '',
        patient_phone: editData.patient_phone || '',
        id_card: editData.id_card || '',
        gender: editData.gender || 'male',
        birth_date: editData.birth_date || '',
        emergency_contact: editData.emergency_contact || '',
        emergency_phone: editData.emergency_phone || '',
        medical_history: editData.medical_history || '',
        allergies: editData.allergies || '',
        current_medications: editData.current_medications || '',
        notes: editData.notes || ''
      })

      // 设置出生日期选择器值
      if (editData.birth_date) {
        const parts = editData.birth_date.split('-')
        birthDateValue.value = parts
      }
    } catch (error) {
      // 回退：使用传入的脱敏数据
      Object.assign(formData, {
        patient_name: newPatient.patient_name || '',
        patient_phone: newPatient.patient_phone || '',
        id_card: newPatient.id_card || '',
        gender: newPatient.gender || 'male',
        birth_date: newPatient.birth_date || '',
        emergency_contact: newPatient.emergency_contact || '',
        emergency_phone: newPatient.emergency_phone || '',
        medical_history: newPatient.medical_history || '',
        allergies: newPatient.allergies || '',
        current_medications: newPatient.current_medications || '',
        notes: newPatient.notes || ''
      })

      if (newPatient.birth_date) {
        const parts = newPatient.birth_date.split('-')
        birthDateValue.value = parts
      }
    }
  } else {
    resetForm()
  }
}, { immediate: true })

// 日期选择确认
function onDateConfirm({ selectedValues }) {
  formData.birth_date = `${selectedValues[0]}-${selectedValues[1]}-${selectedValues[2]}`
  showBirthDatePicker.value = false
}

// 检查身份证号
async function checkIdCard() {
  if (!formData.id_card || isEdit.value) return

  // 验证身份证号格式
  if (!validateIdCard(formData.id_card)) {
    return
  }

  try {
    const data = await patientApi.findByIdCard(formData.id_card)
    if (data && data.patients && data.patients.length > 0) {
      showToast('检测到已有相同身份证号的病人')
    }
  } catch (error) {
    // 身份证号不存在，可以继续添加
  }
}

// 提交表单
async function handleSubmit() {
  // 基本验证
  if (!formData.patient_name.trim()) {
    showToast('请输入病人姓名')
    return
  }

  // 验证手机号格式
  if (formData.patient_phone && !validatePhone(formData.patient_phone)) {
    showToast('请输入正确的手机号格式')
    return
  }

  // 验证身份证号格式
  if (formData.id_card && !validateIdCard(formData.id_card)) {
    showToast('请输入正确的身份证号格式')
    return
  }

  loading.value = true

  try {
    let data
    if (isEdit.value) {
      data = await patientApi.updatePatient(props.patient.patient_id, formData)
    } else {
      data = await patientApi.createPatient(formData)
    }

    showToast(isEdit.value ? '更新成功' : '添加成功')
    emit('success', data)
    handleClose()
  } catch (error) {
    console.error('提交表单错误:', error)
    const errorMessage = error.response?.data?.detail || error.response?.data?.message || '操作失败，请重试'
    showToast(errorMessage)
  } finally {
    loading.value = false
  }
}

// 关闭弹窗
function handleClose() {
  visible.value = false
  if (!isEdit.value) {
    resetForm()
  }
}
</script>

<style scoped>
.patient-form {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.form-header {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid var(--border-color);
}

.form-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
}

.form-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.form-actions {
  padding: 20px;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-color);
}

/* 必填字段样式 */
:deep(.van-field__label) {
  font-weight: 500;
}

:deep(.van-field--required .van-field__label::before) {
  content: '*';
  color: var(--danger-color);
  margin-right: 4px;
}
</style>