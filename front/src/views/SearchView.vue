<template>
  <div class="search-view">
    <!-- 统一页面抬头 -->
    <BackButton title="全局搜索" />

    <div class="search-bar">
      <van-search
        v-model="keyword"
        placeholder="搜索指标、药品、报告..."
        show-action
        @search="handleSearch"
        @clear="clearResults"
      >
        <template #action><span @click="$router.back()">取消</span></template>
      </van-search>
    </div>

    <van-loading v-if="loading" class="loading-center" />
    <div v-else-if="searched && results.total === 0" class="empty-state">
      <van-empty description="未找到相关内容" />
    </div>

    <div v-else-if="results.items?.length" class="result-list">
      <div class="result-header">找到 {{ results.total }} 条结果</div>
      <div v-for="(item, idx) in results.items" :key="idx" class="result-item" @click="navigateTo(item)">
        <div class="result-module">
          <van-tag :type="moduleTagType(item.module)">{{ moduleLabel(item.module) }}</van-tag>
        </div>
        <div class="result-title">{{ item.title }}</div>
        <div class="result-subtitle">{{ item.subtitle }}</div>
        <div v-if="item.date" class="result-date">{{ item.date }}</div>
      </div>
    </div>

    <div v-else-if="!searched" class="search-history">
      <div v-if="searchHistory.length" class="history-section">
        <div class="history-header">
          <span>搜索历史</span>
          <van-icon name="delete-o" @click="clearHistory" />
        </div>
        <div class="history-tags">
          <van-tag v-for="(word, i) in searchHistory" :key="i" size="medium" plain @click="keyword = word; handleSearch()">{{ word }}</van-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { usePatientStore } from '@/stores/patient'
import searchApi from '@/api/search'
import BackButton from '@/components/index-detail/BackButton.vue'

const router = useRouter()
const patientStore = usePatientStore()
const keyword = ref('')
const loading = ref(false)
const searched = ref(false)
const results = ref({})
const HISTORY_KEY = 'search_history'
const searchHistory = ref(JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'))

function moduleLabel(m) {
  return { check: '检验', exam: '检查', pathology: '病理', medication: '用药', timeline: '时间线' }[m] || m
}
function moduleTagType(m) {
  return { check: 'primary', exam: 'success', pathology: 'warning', medication: 'info', timeline: 'default' }[m] || 'default'
}

async function handleSearch() {
  if (!keyword.value.trim() || !patientStore.currentPatient) return
  addToHistory(keyword.value.trim())
  loading.value = true
  searched.value = true
  try {
    results.value = await searchApi.search({ patient_id: patientStore.currentPatient.patient_id, keyword: keyword.value.trim() })
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    loading.value = false
  }
}

function addToHistory(word) {
  const h = searchHistory.value.filter(x => x !== word)
  h.unshift(word)
  searchHistory.value = h.slice(0, 20)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(searchHistory.value))
}
function clearHistory() { searchHistory.value = []; localStorage.removeItem(HISTORY_KEY) }
function clearResults() { searched.value = false; results.value = {} }

function navigateTo(item) {
  const map = {
    check: item.id ? `/home/indicator/history?index_id=${item.id}` : '/home/index',
    exam: '/home/exam-reports',
    pathology: '/home/pathology-reports',
    medication: '/home/medication',
    timeline: '/home/timeline',
  }
  router.push(map[item.module] || '/home/main')
}
</script>

<style scoped>
.search-view { min-height: 100vh; background: var(--bg-primary); }
.search-bar { position: sticky; top: 0; z-index: 10; background: var(--bg-surface); }
.loading-center { display: flex; justify-content: center; padding: 60px; }
.empty-state { display: flex; align-items: center; justify-content: center; min-height: 40vh; }
.result-header { padding: 12px 16px; font-size: 13px; color: var(--text-tertiary); }
.result-list { padding-bottom: var(--safe-bottom); }
.result-item { background: var(--bg-surface); margin: 0 16px 8px; padding: 14px; border-radius: 10px; cursor: pointer; }
.result-item:active { background: var(--bg-elevated); }
.result-module { margin-bottom: 6px; }
.result-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.result-subtitle { font-size: 13px; color: var(--text-secondary); }
.result-date { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
.search-history { padding: 20px 16px; }
.history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-size: 14px; font-weight: 600; color: var(--text-primary); }
.history-tags { display: flex; flex-wrap: wrap; gap: 8px; }

@media (min-width: 768px) {
  .search-view {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px 0;
  }
  .search-bar {
    border-radius: var(--radius-lg);
    margin-bottom: var(--space-3);
  }
  .result-item {
    border: 1px solid var(--border-color);
  }
}
</style>