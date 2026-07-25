<template>
  <van-dialog
    v-model:show="showDialog"
    :title="isEditing ? '编辑数据' : '添加数据'"
    confirm-button-text="保存"
    show-cancel-button
    @confirm="saveData"
  >
    <div class="dialog-content">
      <van-form required="auto">
        <van-cell-group inset>
          <van-field
            v-if="!commentOnly"
            v-model="localFormData.medical_date"
            is-link
            name="medical_date"
            label="检查日期"
            placeholder="选择检查日期"
            @click="showDatePicker = true"
            :rules="[{ required: true, message: '请选择日期' }]"
          />
          
          <van-field
            v-if="!commentOnly"
            v-model="localFormData.index_value"
            clearable
            type="number"
            name="index_value"
            label="指标值"
            placeholder="请输入指标值"
            :rules="[{ required: true, message: '请输入指标值' }]"
          />
          
          <van-field
            v-if="!commentOnly"
            v-model="localFormData.index_unit"
            clearable
            name="index_unit"
            label="指标单位"
            placeholder="请输入指标单位"
          />

          <van-field
            v-if="!commentOnly"
            v-model="localFormData.reference_value"
            clearable
            name="reference_value"
            label="参考范围"
            placeholder="请输入参考范围"
          />

          <van-field
            v-if="!commentOnly"
            v-model="localFormData.index_status"
            name="index_status"
            label="指标状态"
            placeholder="请选择指标状态"
            :rules="[{ required: true, message: '请选择指标状态' }]"
          >
            <template #input>
              <van-radio-group v-model="localFormData.index_status" direction="horizontal">
                <van-radio name="high">偏高</van-radio>
                <van-radio name="normal">正常</van-radio>
                <van-radio name="low">偏低</van-radio>
              </van-radio-group>
            </template>
          </van-field>

          <van-field
            v-model="localFormData.comment"
            rows="2"
            autosize
            clearable
            type="textarea"
            maxlength="50"
            name="comment"
            label="备注"
            placeholder="请输入备注信息"
            show-word-limit
          />
        </van-cell-group>
      </van-form>
    </div>
  </van-dialog>

  <!-- 日期选择器 -->
  <van-popup v-model:show="showDatePicker" :position="isDesktop ? 'center' : 'bottom'" :class="isDesktop ? 'desktop-popup-sm' : ''">
    <van-date-picker
      v-model="selectedDate"
      title="选择检查日期"
      :min-date="minDate"
      :max-date="maxDate"
      @confirm="onDateConfirm"
      @cancel="showDatePicker = false"
    />
  </van-popup>
</template>

<script setup>
import { ref, watch } from 'vue'
import { showNotify } from 'vant'
import { useResponsive } from '@/composables/useResponsive'

const { isDesktop } = useResponsive()

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  formData: {
    type: Object,
    default: () => ({})
  },
  isEditing: {
    type: Boolean,
    default: false
  },
  referenceMax: {
    type: Number,
    default: null
  },
  referenceMin: {
    type: Number,
    default: null
  },
  commentOnly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'save'])

const showDialog = ref(props.modelValue)
const showDatePicker = ref(false)
const localFormData = ref({ ...props.formData })
const selectedDate = ref([])
const minDate = ref(new Date(2020, 0, 1))
const maxDate = ref(new Date())

// 监听外部传入的显示状态
watch(() => props.modelValue, (newVal) => {
  showDialog.value = newVal
})

// 监听内部显示状态变化
watch(() => showDialog.value, (newVal) => {
  emit('update:modelValue', newVal)
})

// 监听外部传入的表单数据
watch(() => props.formData, (newVal) => {
  localFormData.value = { ...newVal }
  if (newVal.medical_date) {
    const date = new Date(newVal.medical_date)
    selectedDate.value = [
      date.getFullYear().toString(),
      (date.getMonth() + 1).toString().padStart(2, '0'),
      date.getDate().toString().padStart(2, '0')
    ]
  } else {
    const today = new Date()
    selectedDate.value = [
      today.getFullYear().toString(),
      (today.getMonth() + 1).toString().padStart(2, '0'),
      today.getDate().toString().padStart(2, '0')
    ]
  }
}, { deep: true })

// 格式化日期
const formatDate = (date) => {
  if (!date) return ''
  if (typeof date === 'string') {
    date = new Date(date)
  }
  if (!(date instanceof Date) || isNaN(date.getTime())) {
    return ''
  }
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

// 日期确认
const onDateConfirm = (value) => {
  try {
    let dateValues
    if (value && typeof value === 'object' && value.selectedValues) {
      dateValues = value.selectedValues
    } else if (Array.isArray(value)) {
      dateValues = value
    } else if (value instanceof Date) {
      localFormData.value.medical_date = formatDate(value)
      showDatePicker.value = false
      return
    } else {
      localFormData.value.medical_date = formatDate(new Date())
      showDatePicker.value = false
      return
    }
    
    if (Array.isArray(dateValues) && dateValues.length >= 3) {
      const year = parseInt(dateValues[0])
      const month = parseInt(dateValues[1]) - 1
      const day = parseInt(dateValues[2])
      
      if (!isNaN(year) && !isNaN(month) && !isNaN(day)) {
        const date = new Date(year, month, day)
        localFormData.value.medical_date = formatDate(date)
      } else {
        localFormData.value.medical_date = formatDate(new Date())
      }
    }
  } catch (error) {
    console.error('Error processing date:', error)
    localFormData.value.medical_date = formatDate(new Date())
  }
  
  showDatePicker.value = false
}

// 根据参考值计算状态
const calculateStatus = (value) => {
  const val = parseFloat(value)
  if (props.referenceMax !== null && props.referenceMax !== undefined && val > props.referenceMax) {
    return 'high'
  } else if (props.referenceMin !== null && props.referenceMin !== undefined && val < props.referenceMin) {
    return 'low'
  }
  return 'normal'
}

// 保存数据
const saveData = () => {
  if (!props.commentOnly) {
    if (!localFormData.value.medical_date) {
      showNotify({ type: 'warning', message: '请选择日期' })
      return false
    }

    if (!localFormData.value.index_value) {
      showNotify({ type: 'warning', message: '请输入指标值' })
      return false
    }

    const data = {
      ...localFormData.value,
      index_value: parseFloat(localFormData.value.index_value),
      index_status: localFormData.value.index_status || calculateStatus(localFormData.value.index_value)
    }

    emit('save', data)
    return true
  } else {
    const data = {
      medical_id: localFormData.value.medical_id,
      comment: localFormData.value.comment
    }

    emit('save', data)
    return true
  }
}
</script>

<style scoped>
.dialog-content {
  padding: 16px 0;
}
</style>