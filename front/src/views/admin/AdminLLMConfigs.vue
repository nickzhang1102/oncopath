<template>
  <div class="admin-llm-configs">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <van-loading size="32px" color="var(--primary-color)" vertical>加载中...</van-loading>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-state">
      <van-icon name="warning-o" size="48" color="var(--danger-color)" />
      <p>{{ error }}</p>
      <van-button size="small" type="primary" @click="loadConfigs">重试</van-button>
    </div>

    <template v-else>
      <!-- 顶部操作栏 -->
      <div class="action-bar">
        <span class="action-hint">修改保存后需重载生效</span>
        <van-button
          type="primary"
          size="small"
          icon="replay"
          :loading="reloading"
          @click="handleReload"
        >
          重载配置
        </van-button>
      </div>

      <!-- 三个 Tab -->
      <van-tabs v-model:active="activeTab" animated>
        <van-tab v-for="group in groups" :key="group.key" :title="group.label">
          <div class="group-card">
            <!-- 卡片顶部：标题 + 按钮 -->
            <div class="card-top">
              <span class="card-title">{{ group.label }}配置</span>
              <div class="card-top-right">
                <van-button
                  size="small"
                  :type="editingGroup === group.key ? 'primary' : 'default'"
                  :icon="editingGroup === group.key ? 'passed' : 'edit'"
                  @click="editingGroup === group.key ? saveGroup(group.key) : startEdit(group.key)"
                >
                  {{ editingGroup === group.key ? '保存' : '编辑' }}
                </van-button>
                <van-button
                  size="small"
                  plain
                  icon="search"
                  :loading="testingGroup === group.key"
                  @click="testGroup(group.key)"
                >
                  测试
                </van-button>
              </div>
            </div>

            <!-- 配置字段列表 -->
            <div class="field-list">
              <div
                v-for="cfg in groupConfigs(group.key)"
                :key="cfg.config_key"
                class="field-row"
              >
                <label class="field-label">
                  {{ cfg.display_name }}
                  <van-tag v-if="cfg.is_secret" type="warning" size="small" plain>敏感</van-tag>
                </label>

                <!-- 查看模式 -->
                <template v-if="editingGroup !== group.key">
                  <span class="field-value" :class="{ masked: cfg.is_secret }">
                    {{ cfg.config_value || '(空)' }}
                  </span>
                </template>

                <!-- 编辑模式 -->
                <template v-else>
                  <van-field
                    v-model="editForm[cfg.config_key]"
                    :type="cfg.is_secret ? 'password' : 'text'"
                    :placeholder="cfg.is_secret ? '留空则不修改' : cfg.display_name"
                    size="small"
                    class="field-input"
                  />
                </template>
              </div>
            </div>

            <!-- 测试结果 -->
            <div v-if="testResults[group.key]" class="test-result" :class="testResults[group.key].success ? 'test-ok' : 'test-fail'">
              <van-icon :name="testResults[group.key].success ? 'checked' : 'warning-o'" />
              <span>{{ testResults[group.key].message }}</span>
            </div>
          </div>
        </van-tab>
      </van-tabs>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { adminApi } from '@/api/admin'

const loading = ref(true)
const error = ref(null)
const configs = ref([])
const activeTab = ref(0)
const reloading = ref(false)
const testingGroup = ref('')
const editingGroup = ref('')
const editForm = reactive({})
const testResults = reactive({})

const groups = [
  { key: 'consultation', label: '会诊' },
  { key: 'interpretation', label: '解读' },
  { key: 'ocr', label: 'OCR' },
]

function groupConfigs(groupKey) {
  return configs.value.filter(c => c.config_group === groupKey)
}

async function loadConfigs() {
  loading.value = true
  error.value = null
  try {
    const res = await adminApi.getLLMConfigs()
    configs.value = res.items || []
  } catch (e) {
    error.value = e.response?.data?.detail || '加载配置失败'
  } finally {
    loading.value = false
  }
}

function startEdit(groupKey) {
  editingGroup.value = groupKey
  const items = groupConfigs(groupKey)
  for (const cfg of items) {
    // 敏感字段编辑时留空（不回填掩码值）
    editForm[cfg.config_key] = cfg.is_secret ? '' : cfg.config_value
  }
}

async function saveGroup(groupKey) {
  const items = groupConfigs(groupKey)
  try {
    for (const cfg of items) {
      const newVal = editForm[cfg.config_key]
      // 敏感字段空值 → 不修改，传回掩码值
      const payload = {
        config_value: (cfg.is_secret && !newVal) ? cfg.config_value : newVal,
      }
      const res = await adminApi.updateLLMConfig(cfg.config_key, payload)
      const idx = configs.value.findIndex(c => c.config_key === cfg.config_key)
      if (idx !== -1) configs.value[idx] = res
    }
    editingGroup.value = ''
    showSuccessToast('保存成功')
  } catch (e) {
    showToast(e.response?.data?.detail || '保存失败')
  }
}

async function testGroup(groupKey) {
  testingGroup.value = groupKey
  testResults[groupKey] = null
  try {
    const res = await adminApi.testLLMConfig(groupKey)
    testResults[groupKey] = res
  } catch (e) {
    testResults[groupKey] = { success: false, message: e.response?.data?.detail || '测试失败' }
  } finally {
    testingGroup.value = ''
  }
}

async function handleReload() {
  reloading.value = true
  try {
    const res = await adminApi.reloadLLMConfigs()
    if (res.reloaded_groups?.length) {
      showSuccessToast(res.message)
    } else {
      showToast(res.message)
    }
  } catch (e) {
    showToast(e.response?.data?.detail || '重载失败')
  } finally {
    reloading.value = false
  }
}

onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.admin-llm-configs {
  max-width: 900px;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: 12px;
  color: var(--text-secondary);
}

.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.action-hint {
  font-size: 12px;
  color: var(--text-tertiary, #999);
}

.group-card {
  background: var(--bg-surface, #fff);
  border-radius: 12px;
  padding: 16px;
  margin: 12px 0;
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.card-top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.field-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 36px;
}

.field-label {
  flex-shrink: 0;
  width: 130px;
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.field-value {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
  word-break: break-all;
  font-family: monospace;
}

.field-value.masked {
  color: var(--text-tertiary, #999);
}

.field-input {
  flex: 1;
  padding: 0;
}

.field-input :deep(.van-field__control) {
  font-size: 13px;
  font-family: monospace;
}

.test-result {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
}

.test-ok {
  background: var(--success-alpha-10, #f0fff4);
  color: var(--success-color, #07c160);
}

.test-fail {
  background: var(--danger-alpha-10, #fff1f0);
  color: var(--danger-color, #ee0a24);
}

/* 响应式 */
@media (max-width: 768px) {
  .field-label {
    width: 100px;
  }
}
</style>