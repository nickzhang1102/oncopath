<template>
  <div class="table-section">
    <div class="table-card">
      <div class="table-header">
        <h3>{{ indexName }} - 历史数据</h3>
      </div>
      <div class="table-content">
        <van-loading v-if="loading" size="24px" vertical>加载中...</van-loading>
        <div v-else-if="tableData.length === 0" class="empty-data">
          <van-empty description="暂无数据">
            <van-button
              v-if="isEditable"
              round
              type="primary"
              class="empty-add-btn"
              @click="$emit('add')"
            >
              添加第一条数据
            </van-button>
          </van-empty>
        </div>
        <div v-else ref="tableRef" class="data-table" :class="{ scrollable: isScrollable }">
          <table>
            <thead>
              <tr>
                <th class="col-date">检查日期</th>
                <th class="col-value">指标值</th>
                <th class="col-status">状态</th>
                <th class="col-comment">备注</th>
                <th v-if="isEditable" class="col-actions">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in tableData" :key="index">
                <td class="col-date">{{ formatDate(item.medical_date) }}</td>
                <td :class="['col-value', getValueClass(item.index_status)]">{{ item.index_value }}</td>
                <td class="col-status">
                  <span :class="['status-tag', getStatusClass(item.index_status)]">
                    {{ getStatusText(item.index_status) }}
                  </span>
                </td>
                <td class="col-comment">
                  <div v-if="item.comment && item.comment.length > 10" class="expandable-comment">
                    <span :class="['comment-text', {'expanded': expandedComments[index]}]">
                      {{ item.comment }}
                    </span>
                    <span class="expand-btn" @click.stop="toggleComment(index)">
                      {{ expandedComments[index] ? '收起' : '展开' }}
                    </span>
                  </div>
                  <div v-else>{{ item.comment || '-' }}</div>
                </td>
                <td v-if="isEditable" class="col-actions">
                  <div class="action-buttons">
                    <van-button
                      size="mini"
                      type="primary"
                      icon="edit"
                      @click.stop="$emit('edit', item, index)"
                    />
                    <van-button
                      size="mini"
                      type="danger"
                      icon="delete"
                      @click.stop="$emit('delete', item, index)"
                    />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue';

const props = defineProps({
  indexName: {
    type: String,
    required: true
  },
  tableData: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  isEditable: {
    type: Boolean,
    default: false
  }
});

defineEmits(['add', 'edit', 'delete']);

const tableRef = ref(null);
const isScrollable = ref(false);

function checkScrollable() {
  nextTick(() => {
    if (tableRef.value) {
      isScrollable.value = tableRef.value.scrollWidth > tableRef.value.clientWidth;
    }
  });
}

watch(() => props.tableData, checkScrollable, { immediate: true });

const expandedComments = ref({});

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
};

// 获取数值样式类
const getValueClass = (status) => {
  switch (status) {
    case 'high': return 'value-high';
    case 'low': return 'value-low';
    default: return 'value-normal';
  }
};

// 获取状态样式类
const getStatusClass = (status) => {
  switch (status) {
    case 'high': return 'status-tag--high';
    case 'low': return 'status-tag--low';
    default: return 'status-tag--normal';
  }
};

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'high': return '偏高';
    case 'low': return '偏低';
    default: return '正常';
  }
};

// 切换备注展开/收起状态
const toggleComment = (index) => {
  expandedComments.value[index] = !expandedComments.value[index];
};
</script>

<style scoped>
.table-section {
  position: relative;
  z-index: 2;
  margin-bottom: 16px;
}

.table-card {
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  overflow: hidden;
}

.table-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--primary-alpha-10);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
}

.table-content {
  padding: 16px;
}

/* 表格样式 */
.data-table {
  overflow-x: auto;
  width: 100%;
  position: relative;
}

/* 移动端滚动提示：右侧渐变遮罩 */
@media (max-width: 767px) {
  .data-table::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 24px;
    background: linear-gradient(to right, transparent, var(--bg-surface, #fff));
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.3s;
  }

  .data-table.scrollable::after {
    opacity: 1;
  }
}

.data-table table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table th {
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-weight: 500;
  padding: 12px 8px;
  text-align: left;
  border-bottom: 1px solid var(--primary-alpha-10);
}

.data-table td {
  padding: 12px 8px;
  border-bottom: 1px solid var(--primary-alpha-5);
  color: var(--text-primary);
}

.data-table tr:hover {
  background: var(--bg-elevated);
}

/* 数值样式 */
.value-normal {
  color: var(--success-color);
  font-weight: 600;
}

.value-high {
  color: var(--danger-color);
  font-weight: 600;
}

.value-low {
  color: var(--warning-color);
  font-weight: 600;
}

/* 状态标签 */
.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}


/* 备注展开/收起 */
.expandable-comment {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 4px;
}

.comment-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 150px;
  transition: all 0.3s;
}

.comment-text.expanded {
  white-space: normal;
  overflow: visible;
  max-width: none;
}

.expand-btn {
  color: var(--primary-color);
  cursor: pointer;
  font-size: 12px;
  margin-left: 5px;
  white-space: nowrap;
  user-select: none;
  flex-shrink: 0;
}

.expand-btn:hover {
  text-decoration: underline;
}

/* 表格列宽设置 */
.col-date {
  width: 80px;
}

.col-value {
  text-align: center;
  width: 70px;
}

.col-status {
  width: 60px;
}

.col-comment {
  min-width: 80px;
}

.col-actions {
  width: 80px;
  text-align: center;
}

.action-buttons {
  display: flex;
  gap: 5px;
  justify-content: center;
}

.action-buttons .van-button {
  padding: 8px;
  min-width: 44px;
  min-height: 44px;
}

/* 空数据状态 */
.empty-data {
  padding: 30px 0;
  text-align: center;
}

.empty-add-btn {
  margin-top: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .table-header h3 {
    font-size: 16px;
  }

  .table-content {
    padding: 15px;
  }

  .data-table {
    font-size: 12px;
  }

  .data-table th, .data-table td {
    padding: 8px 6px;
  }

  .col-actions {
    width: 60px;
  }

  .action-buttons .van-button {
    min-width: 44px;
    min-height: 44px;
    padding: 10px;
  }
}

@media (max-width: 480px) {
  .table-header {
    padding: 15px;
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .table-content {
    padding: 10px;
  }

  .data-table {
    font-size: 12px;
  }

  .data-table th, .data-table td {
    padding: 6px 4px;
  }

  .status-tag {
    font-size: 12px;
    padding: 2px 6px;
  }

  .col-actions {
    width: 50px;
  }

  .action-buttons {
    gap: 3px;
  }

  .action-buttons .van-button {
    min-width: 44px;
    min-height: 44px;
    padding: 11px;
  }
}
</style>
