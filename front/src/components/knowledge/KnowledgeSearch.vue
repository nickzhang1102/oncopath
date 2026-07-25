<template>
  <div class="search-section">
    <div class="search-bar">
      <van-icon name="search" size="16" class="search-icon" />
      <input
        v-model="searchKeyword"
        type="text"
        class="search-input"
        placeholder="搜索文档..."
        @keydown.enter="handleSearch"
      />
      <van-icon
        v-if="searchKeyword"
        name="cross"
        size="14"
        class="clear-icon"
        @click="handleSearchClear"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue', 'search', 'clear', 'advanced-search'])

const searchKeyword = ref(props.modelValue)

watch(() => props.modelValue, (v) => { searchKeyword.value = v })
watch(searchKeyword, (v) => { emit('update:modelValue', v) })

const handleSearch = () => { emit('search', searchKeyword.value) }
const handleSearchClear = () => { searchKeyword.value = ''; emit('clear') }
</script>

<style scoped>
.search-section {
  margin-bottom: 16px;
}

.search-bar {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 12px;
  background: var(--bg-elevated);
  border-radius: 10px;
  border: 1px solid transparent;
  transition: border-color 0.2s, background 0.2s;
}

.search-bar:focus-within {
  background: var(--bg-surface);
  border-color: var(--primary-color);
}

.search-icon {
  color: var(--text-tertiary);
  flex-shrink: 0;
  margin-right: 8px;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--text-primary);
  min-width: 0;
}

.search-input::placeholder {
  color: var(--text-tertiary);
}

.clear-icon {
  color: var(--text-tertiary);
  cursor: pointer;
  flex-shrink: 0;
  padding: 4px;
  margin-right: -4px;
  transition: color 0.15s;
}

.clear-icon:hover {
  color: var(--text-secondary);
}

@media (max-width: 768px) {
  .search-bar {
    height: 36px;
    padding: 0 10px;
    border-radius: 8px;
  }

  .search-input {
    font-size: 13px;
  }
}
</style>
