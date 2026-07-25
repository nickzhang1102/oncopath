<template>
  <div class="compare-table-section">
    <div class="table-card">
      <div class="table-header">
        <h3>对比数据</h3>
      </div>
      <div class="table-content">
        <van-loading v-if="loading" size="24px" vertical>加载中...</van-loading>
        <div v-else-if="alignedData.length === 0" class="empty-data">
          <van-empty description="暂无数据" />
        </div>
        <div v-else class="data-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th class="col-date">检查日期</th>
                <th
                  v-for="idx in indexes"
                  :key="idx.index_id"
                  class="col-value"
                >
                  {{ idx.index_name }}
                  <span v-if="idx.index_unit" class="unit-hint">{{ idx.index_unit }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in alignedData" :key="i">
                <td class="col-date">{{ formatDate(row.date) }}</td>
                <td
                  v-for="idx in indexes"
                  :key="idx.index_id"
                  class="col-value"
                >
                  {{ row.values[String(idx.index_id)] ?? '-' }}
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
defineProps({
  indexes: {
    type: Array,
    required: true,
  },
  alignedData: {
    type: Array,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
};
</script>

<style scoped>
.compare-table-section {
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

.empty-data {
  padding: 30px 0;
  text-align: center;
}

.data-table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  white-space: nowrap;
}

.data-table th {
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-weight: 500;
  padding: 12px 10px;
  text-align: center;
  border-bottom: 1px solid var(--primary-alpha-10);
  position: sticky;
  top: 0;
  z-index: 1;
}

.data-table td {
  padding: 10px;
  border-bottom: 1px solid var(--primary-alpha-5);
  color: var(--text-primary);
  text-align: center;
}

.data-table tr:hover {
  background: var(--bg-elevated);
}

.col-date {
  text-align: left !important;
  font-weight: 500;
  color: var(--text-secondary);
  min-width: 90px;
  position: sticky;
  left: 0;
  background: var(--bg-surface);
  z-index: 2;
}

.data-table thead .col-date {
  background: var(--bg-elevated);
  z-index: 3;
}

.col-value {
  min-width: 80px;
}

.unit-hint {
  display: block;
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: 400;
}

@media (max-width: 480px) {
  .table-content {
    padding: 10px;
  }
  .data-table th,
  .data-table td {
    padding: 8px 6px;
    font-size: 12px;
  }
  .col-date {
    min-width: 75px;
  }
  .col-value {
    min-width: 65px;
  }
}
</style>
