<template>
  <div class="compare-chart-section">
    <div class="chart-card">
      <!-- 指标勾选区域 -->
      <div class="chart-select-bar">
        <span class="select-label">图表指标：</span>
        <div class="select-items">
          <label
            v-for="idx in indexes"
            :key="idx.index_id"
            class="select-item"
            :class="{ active: isSelected(idx.index_id) }"
          >
            <van-checkbox
              :model-value="isSelected(idx.index_id)"
              @update:model-value="toggleSelect(idx.index_id)"
              shape="square"
              icon-size="16px"
            >
              {{ idx.index_name }}
            </van-checkbox>
          </label>
        </div>
      </div>

      <div class="chart-content">
        <van-loading v-if="loading" size="24px" vertical>加载中...</van-loading>
        <div v-else-if="selectedIndexIds.length === 0" class="empty-hint">
          请勾选 1-2 个指标查看趋势
        </div>
        <div v-else ref="chartContainer" class="chart-container"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { showToast } from 'vant';
import { getThemeColors, hexToRgba } from '@/styles/theme-colors';
import echarts from '@/utils/echarts';

const props = defineProps({
  indexes: { type: Array, required: true },
  alignedData: { type: Array, required: true },
  loading: { type: Boolean, default: false },
});

const chartContainer = ref(null);
const selectedIndexIds = ref([]);
let chartInstance = null;

// 默认勾选前 2 个
watch(() => props.indexes, (newIndexes) => {
  if (newIndexes.length > 0 && selectedIndexIds.value.length === 0) {
    selectedIndexIds.value = newIndexes.slice(0, 2).map(i => i.index_id);
  }
}, { immediate: true });

const isSelected = (id) => selectedIndexIds.value.includes(id);

const toggleSelect = (id) => {
  const idx = selectedIndexIds.value.indexOf(id);
  if (idx > -1) {
    selectedIndexIds.value.splice(idx, 1);
  } else {
    if (selectedIndexIds.value.length >= 2) {
      showToast('图表最多同时显示 2 个指标');
      return;
    }
    selectedIndexIds.value.push(id);
  }
};

// 第一个颜色使用项目主题主色，第二个使用 danger 色
const getSeriesColors = (colors) => [colors.primary, colors.danger];

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
};

const renderChart = () => {
  if (!chartContainer.value) return;
  if (selectedIndexIds.value.length === 0) return;

  if (chartInstance) chartInstance.dispose();
  chartInstance = echarts.init(chartContainer.value);

  const colors = getThemeColors();
  const seriesColors = getSeriesColors(colors);
  const selected = props.indexes.filter(i => selectedIndexIds.value.includes(i.index_id));
  const sortedData = [...props.alignedData].reverse();
  const dates = sortedData.map(r => formatDate(r.date));

  const series = selected.map((idx, si) => {
    const values = sortedData.map(r => {
      const v = r.values[String(idx.index_id)];
      return v !== null && v !== undefined ? parseFloat(v) : null;
    });
    const color = seriesColors[si % seriesColors.length];
    const markArea = (idx.reference_min != null && idx.reference_max != null) ? {
      markArea: {
        silent: true,
        itemStyle: {
          color: hexToRgba(si === 0 ? colors.success : colors.warning, 0.08),
          borderColor: hexToRgba(si === 0 ? colors.success : colors.warning, 0.25),
          borderWidth: 1,
          borderType: 'dashed',
        },
        label: {
          show: true,
          position: 'insideTopRight',
          formatter: `${idx.index_name}正常范围`,
          color: si === 0 ? colors.success : colors.warning,
          fontSize: 10,
        },
        data: [[{ yAxis: idx.reference_min }, { yAxis: idx.reference_max }]],
      },
    } : {};

    return {
      name: idx.index_name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      yAxisIndex: si,
      data: values,
      connectNulls: true,
      lineStyle: { color, width: 2 },
      itemStyle: { color },
      ...markArea,
    };
  });

  const yAxes = selected.map((idx, si) => {
    const color = seriesColors[si % seriesColors.length];
    return {
      type: 'value',
      name: idx.index_unit || idx.index_name,
      position: si === 0 ? 'left' : 'right',
      scale: false,
      min: function (value) {
        if (idx.reference_min != null) {
          return Math.min(value.min, idx.reference_min);
        }
        return value.min;
      },
      max: function (value) {
        if (idx.reference_max != null) {
          return Math.max(value.max, idx.reference_max);
        }
        return value.max;
      },
      axisLabel: {
        formatter: (v) => Number(v).toFixed(2),
        fontSize: 10,
        color,
      },
      axisLine: { show: true, lineStyle: { color } },
      nameTextStyle: { color, fontSize: 11 },
      splitLine: { show: si === 0, lineStyle: { color: colors.borderLight || colors.borderColor } },
    };
  });

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params) => {
        let html = `<div style="margin-bottom:4px;font-weight:bold">${params[0].axisValue}</div>`;
        params.forEach(p => {
          const val = p.value != null ? p.value : '-';
          html += `<div style="margin:2px 0">
            <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background:${p.color}"></span>
            ${p.seriesName}: ${val}
          </div>`;
        });
        return html;
      },
    },
    legend: {
      data: selected.map(i => i.index_name),
      right: 10,
      top: 10,
      textStyle: { color: colors.textSecondary, fontSize: 12 },
    },
    grid: { left: '10%', right: '10%', bottom: '15%', top: '18%' },
    dataZoom: [{ type: 'slider', start: 0 }, { start: 0 }],
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 45, fontSize: 10, color: colors.textSecondary },
      axisLine: { lineStyle: { color: colors.borderLight || colors.borderColor } },
    },
    yAxis: yAxes,
    series,
  }, true);

  window.addEventListener('resize', handleResize);
};

const handleResize = () => { chartInstance?.resize(); };

watch(selectedIndexIds, () => { nextTick(renderChart); }, { deep: true });
watch(() => props.alignedData, () => { nextTick(renderChart); }, { deep: true });

onMounted(() => { nextTick(renderChart); });

onUnmounted(() => {
  if (chartInstance) chartInstance.dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.compare-chart-section {
  position: relative;
  z-index: 2;
  margin-bottom: 16px;
}

.chart-card {
  background: var(--bg-surface);
  border-radius: 12px;
  box-shadow: 0 2px 8px var(--primary-alpha-8);
  overflow: hidden;
}

.chart-select-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--primary-alpha-10);
}

.select-label {
  font-size: 13px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.select-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.select-item {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.chart-content {
  padding: 16px;
}

.chart-container {
  width: 100%;
  height: 380px;
}

.empty-hint {
  text-align: center;
  padding: 40px 0;
  color: var(--text-tertiary);
  font-size: 14px;
}

@media (max-width: 480px) {
  .chart-container {
    height: 300px;
  }
  .chart-select-bar {
    padding: 10px 12px;
  }
}
</style>
