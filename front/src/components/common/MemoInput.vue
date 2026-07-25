<template>
  <div class="memo-input">
    <div class="memo-title">{{ title }}</div>
    
    <!-- 备忘录列表 -->
    <div class="memo-list">
      <div
        v-for="(item, index) in memoItems"
        :key="index"
        class="memo-item"
      >
        <div class="memo-time">
          <van-field
            v-model="item.time"
            placeholder="时间"
            type="time"
            :input-align="'center'"
            class="time-input"
            @change="onMemoChange"
          />
        </div>
        <div class="memo-event">
          <van-field
            v-model="item.event"
            placeholder="事件描述"
            class="event-input"
            @change="onMemoChange"
          />
        </div>
        <van-icon
          name="delete-o"
          class="delete-btn"
          @click="removeMemoItem(index)"
        />
      </div>
    </div>

    <!-- 添加按钮 -->
    <div class="add-btn" @click="addMemoItem">
      <van-icon name="plus" />
      <span>添加时间点</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '详细记录'
  },
  modelValue: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

// 本地数据
const memoItems = ref([])

// 初始化
watch(() => props.modelValue, (newVal) => {
  if (newVal && newVal.length > 0) {
    memoItems.value = [...newVal]
  } else {
    memoItems.value = []
  }
}, { immediate: true, deep: true })

// 添加时间点
function addMemoItem() {
  const now = new Date()
  const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
  
  memoItems.value.push({
    time: currentTime,
    event: ''
  })
  
  onMemoChange()
}

// 删除时间点
function removeMemoItem(index) {
  memoItems.value.splice(index, 1)
  onMemoChange()
}

// 数据变化时通知父组件
function onMemoChange() {
  const validItems = memoItems.value.filter(item => item.event || item.time)
  emit('update:modelValue', validItems)
  emit('change', validItems)
}

// 暴露方法
defineExpose({
  addMemoItem,
  getMemoItems: () => memoItems.value
})
</script>

<style scoped>
.memo-input {
  background: var(--primary-alpha-3);
  border-radius: 12px;
  padding: 12px;
}

.memo-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--primary-color);
  margin-bottom: 12px;
}

.memo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.memo-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-surface);
  border-radius: 8px;
  padding: 8px;
}

.memo-time {
  width: 90px;
  flex-shrink: 0;
}

.time-input {
  padding: 0;
}

.time-input :deep(.van-field__control) {
  font-size: 13px;
  text-align: center;
}

.memo-event {
  flex: 1;
}

.event-input {
  padding: 0;
}

.event-input :deep(.van-field__control) {
  font-size: 13px;
}

.delete-btn {
  font-size: 18px;
  color: var(--danger-color);
  cursor: pointer;
  padding: 4px;
  flex-shrink: 0;
}

.add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 10px;
  border: 1px dashed var(--primary-alpha-30);
  border-radius: 8px;
  cursor: pointer;
  color: var(--primary-color);
  font-size: 13px;
  transition: all 0.2s;
}

.add-btn:hover {
  background: var(--primary-alpha-8);
  border-color: var(--primary-color);
}
</style>