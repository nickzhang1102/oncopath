<template>
  <div class="admin-users">
    <!-- 搜索栏 -->
    <div class="toolbar">
      <van-search
        v-model="searchText"
        placeholder="搜索用户名或显示名"
        @search="onSearch"
        @clear="onClear"
      />
      <van-dropdown-menu class="status-filter">
        <van-dropdown-item v-model="statusFilter" :options="statusOptions" @change="onFilterChange" />
      </van-dropdown-menu>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <table class="data-table">
        <thead>
          <tr>
            <th class="sortable" @click="onSort('account_name')">
              用户名 <span class="sort-indicator">{{ sortIcon('account_name') }}</span>
            </th>
            <th>用户ID</th>
            <th class="sortable" @click="onSort('status')">
              状态 <span class="sort-indicator">{{ sortIcon('status') }}</span>
            </th>
            <th>手机号</th>
            <th>患者数</th>
            <th class="sortable" @click="onSort('created_at')">
              注册时间 <span class="sort-indicator">{{ sortIcon('created_at') }}</span>
            </th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="center-text"><van-loading size="24px" color="var(--primary-color)" /></td>
          </tr>
          <tr v-else-if="items.length === 0">
            <td colspan="7" class="center-text">暂无数据</td>
          </tr>
          <tr v-for="user in items" :key="user.account_id" v-else>
            <td class="name-cell">{{ user.account_name || user.username }}</td>
            <td class="mono">{{ user.username }}</td>
            <td>
              <van-tag :type="user.status === 'active' ? 'success' : 'danger'" size="medium">
                {{ user.status === 'active' ? '正常' : '已禁用' }}
              </van-tag>
              <van-tag v-if="user.account_type === 'admin'" type="warning" plain size="small" style="margin-left:4px">管理员</van-tag>
            </td>
            <td>{{ user.phone || '-' }}</td>
            <td>{{ user.patient_count }}</td>
            <td>{{ formatDate(user.created_at) }}</td>
            <td class="action-cell">
              <van-button
                v-if="user.account_id !== currentAdminId"
                :type="user.status === 'active' ? 'warning' : 'success'"
                size="mini"
                plain
                @click="onToggleStatus(user)"
              >
                {{ user.status === 'active' ? '禁用' : '启用' }}
              </van-button>
              <van-button
                v-if="user.account_id !== currentAdminId"
                type="primary"
                size="mini"
                plain
                @click="onResetPassword(user)"
              >
                重置密码
              </van-button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <van-button size="mini" :disabled="!hasPrev" @click="onPrevPage">上一页</van-button>
      <span class="page-info">{{ page }} / {{ totalPages || 1 }} (共 {{ total }} 条)</span>
      <van-button size="mini" :disabled="!hasNext" @click="onNextPage">下一页</van-button>
      <select class="page-size-select" :value="pageSize" @change="onPageSizeChange">
        <option v-for="s in pageSizeOptions" :key="s" :value="s">{{ s }}条/页</option>
      </select>
    </div>

    <!-- 重置密码弹窗 -->
    <van-dialog
      v-model:show="resetPwdVisible"
      title="重置密码"
      show-cancel-button
      :before-close="onResetPwdConfirm"
    >
      <div style="padding: 16px;">
        <van-field
          v-model="resetPwdValue"
          type="password"
          label="新密码"
          placeholder="请输入新密码（至少6位）"
        />
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { showConfirmDialog } from 'vant'
import { adminApi } from '@/api/admin'
import { useUserStore } from '@/stores/user'
import { useSortableTable } from '@/composables/useSortableTable'
import dayjs from 'dayjs'

const userStore = useUserStore()

const searchText = ref('')
const statusFilter = ref('')
const statusOptions = [
  { text: '全部状态', value: '' },
  { text: '正常', value: 'active' },
  { text: '已禁用', value: 'inactive' },
]

const resetPwdVisible = ref(false)
const resetPwdValue = ref('')
const resetPwdUser = ref(null)

const currentAdminId = computed(() => userStore.userInfo?.account_id)

const {
  sortBy, sortOrder, page, pageSize, total, totalPages,
  items, loading, toggleSort, sortIcon,
  hasNext, hasPrev, goToPage, load, setPageSize,
} = useSortableTable(adminApi.getAdminUsers, {
  defaultSortBy: 'created_at',
  defaultSortOrder: 'desc',
})

const pageSizeOptions = [10, 20, 50, 100]
function onPageSizeChange(e) {
  setPageSize(Number(e.target.value))
  loadData()
}

function formatDate(dt) {
  return dt ? dayjs(dt).format('YYYY-MM-DD HH:mm') : '-'
}

function buildExtraParams() {
  const params = {}
  if (searchText.value) params.search = searchText.value
  if (statusFilter.value) params.status = statusFilter.value
  return params
}

function loadData() {
  load(buildExtraParams())
}

function resetAndLoad() {
  page.value = 1
  loadData()
}

function onSearch() { resetAndLoad() }
function onClear() { searchText.value = ''; resetAndLoad() }
function onFilterChange() { resetAndLoad() }

async function onToggleStatus(user) {
  const newStatus = user.status === 'active' ? 'inactive' : 'active'
  const action = newStatus === 'active' ? '启用' : '禁用'
  try {
    await showConfirmDialog({
      title: `确认${action}`,
      message: `确定要${action}用户 "${user.account_name || user.username}" 吗？`,
    })
    await adminApi.updateUserStatus(user.account_id, { status: newStatus })
    loadData()
  } catch (e) {
    if (e !== 'cancel') console.error(`${action}用户失败:`, e)
  }
}

function onResetPassword(user) {
  resetPwdUser.value = user
  resetPwdValue.value = ''
  resetPwdVisible.value = true
}

function onResetPwdConfirm(action) {
  if (action === 'confirm') {
    if (!resetPwdValue.value || resetPwdValue.value.length < 6) return Promise.resolve(false)
    return adminApi.resetUserPassword(resetPwdUser.value.account_id, {
      new_password: resetPwdValue.value,
    }).then(() => { return true }).catch(() => Promise.resolve(false))
  }
  return Promise.resolve(true)
}

function onSort(field) {
  toggleSort(field)
  loadData()
}

function onPrevPage() {
  if (hasPrev.value) { goToPage(page.value - 1); loadData() }
}

function onNextPage() {
  if (hasNext.value) { goToPage(page.value + 1); loadData() }
}

onMounted(() => { loadData() })
</script>

<style scoped>
.admin-users {
  padding: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  background: var(--bg-surface, #fff);
  border-bottom: 1px solid var(--border-color, #ebedf0);
}

.toolbar .van-search {
  flex: 1;
  padding: 8px 12px;
}

.status-filter {
  flex-shrink: 0;
  width: 120px;
}

.table-wrapper {
  overflow-x: auto;
  background: var(--bg-surface, #fff);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border-color, #ebedf0);
  white-space: nowrap;
}

.data-table th {
  background: var(--bg-primary, #f5f5f5);
  font-weight: 600;
  color: var(--text-primary, #323233);
  position: sticky;
  top: 0;
}

.data-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.data-table th.sortable:hover {
  color: var(--primary-color, #1989fa);
}

.sort-indicator {
  font-size: 12px;
  color: var(--primary-color, #1989fa);
}

.data-table tbody tr:hover {
  background: var(--bg-primary, #f5f5f5);
}

.center-text {
  text-align: center;
  color: var(--text-secondary, #969799);
  padding: 40px 0 !important;
}

.name-cell {
  font-weight: 500;
  color: var(--text-primary, #323233);
}

.mono {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary, #969799);
}

.action-cell {
  display: flex;
  gap: 4px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-surface, #fff);
  border-top: 1px solid var(--border-color, #ebedf0);
}

.page-info {
  font-size: 13px;
  color: var(--text-secondary, #969799);
}

.page-size-select {
  font-size: 12px;
  padding: 2px 4px;
  border: 1px solid var(--border-color, #ebedf0);
  border-radius: 4px;
  background: var(--bg-surface, #fff);
  color: var(--text-primary);
  outline: none;
  cursor: pointer;
}
</style>