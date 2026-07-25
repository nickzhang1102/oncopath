<template>
  <div class="chart-section">
    <div class="chart-card">
      <div class="chart-header">
        <h3>{{ compareMode ? '指标对比分析' : indexName + ' - 趋势分析' }}</h3>
      </div>
      <div class="chart-content">
        <van-loading v-if="loading" size="24px" vertical>加载中...</van-loading>
        <div v-else-if="!compareMode && chartData.length === 0" class="empty-data">
          <van-empty description="暂无数据" />
        </div>
        <div v-else-if="compareMode && Object.keys(multiData).length === 0" class="empty-data">
          <van-empty description="暂无对比数据" />
        </div>
        <div v-else ref="chartContainer" class="chart-container"></div>
      </div>
      
      <!-- 变化率分析图表（对比模式下不显示） -->
      <div v-if="!compareMode && chartData.length >= 2" class="secondary-chart-section">
        <div class="chart-header">
          <h3>变化率分析</h3>
        </div>
        <div class="chart-content">
          <div ref="secondaryChartContainer" class="secondary-chart-container"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick, onUnmounted } from 'vue';
import { getThemeColors, hexToRgba } from '@/styles/theme-colors';
import echarts from '@/utils/echarts';

const props = defineProps({
  indexName: {
    type: String,
    required: true
  },
  chartData: {
    type: Array,
    required: true
  },
  loading: {
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
  compareMode: {
    type: Boolean,
    default: false
  },
  multiData: {
    type: Object,
    default: () => ({})
  }
});

const chartContainer = ref(null);
const secondaryChartContainer = ref(null);
let chartInstance = null;
let secondaryChartInstance = null;

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

// 初始化主图表
const initChart = () => {
  if (!chartContainer.value) return;

  const colors = getThemeColors();

  // 销毁旧图表
  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartContainer.value);

  let option;

  if (props.compareMode && Object.keys(props.multiData).length > 0) {
    // ===== 对比模式 =====
    option = initCompareChart(colors);
  } else {
    // ===== 单指标模式 =====
    if (props.chartData.length === 0) return;
    option = initSingleChart(colors);
  }

  chartInstance.setOption(option, true);

  // 初始化变化率图表（仅单指标模式）
  if (!props.compareMode) {
    initSecondaryChart();
  }

  // 添加dataZoom事件监听，实现联动
  chartInstance.on('dataZoom', function(params) {
    if (secondaryChartInstance && !params.batch) {
      if (chartInstance._dataZoomTimer) {
        clearTimeout(chartInstance._dataZoomTimer);
      }

      chartInstance._dataZoomTimer = setTimeout(() => {
        secondaryChartInstance.dispatchAction({
          type: 'dataZoom',
          start: params.start,
          end: params.end
        });
      }, 100);
    }
  });

  // 响应式调整
  window.addEventListener('resize', handleResize);
};

// 单指标图表配置
const initSingleChart = (colors) => {
  const sortedData = [...props.chartData].sort((a, b) => new Date(a.date) - new Date(b.date));
  const dates = sortedData.map(item => formatDate(item.date));
  const values = sortedData.map(item => parseFloat(item.value) || 0);

  return {
    title: {
      text: `${props.indexName} 趋势图`,
      left: 'center',
      textStyle: {
        color: colors.primary,
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      enterable: true,
      position: function(pos, params, dom, rect, size) {
        const obj = { top: 10 };
        obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
        return obj;
      },
      formatter: function(params) {
        const param = params[0];
        const dataIndex = param.dataIndex;
        const dataItem = sortedData[dataIndex];

        let result = `<div style="margin-bottom: 5px; font-weight: bold;">${param.axisValue}</div>`;
        result += `<div style="margin: 2px 0;">
          <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${param.color};"></span>
          ${param.seriesName}: ${param.value}
        </div>`;

        if (dataItem && dataItem.comment) {
          const comment = dataItem.comment.length > 15
            ? dataItem.comment.substring(0, 15) + '...'
            : dataItem.comment;
          result += `<div style="margin-top: 5px; padding-top: 5px; border-top: 1px solid var(--border-dark); color: ${colors.textSecondary}; font-size: 12px;">
            备注: ${comment}
          </div>`;
        }

        return result;
      }
    },
    legend: {
      data: [props.indexName],
      right: 10,
      top: 30,
      textStyle: {
        color: colors.textSecondary,
        fontSize: 12
      }
    },
    grid: {
      left: '10%',
      right: '3%',
      bottom: '20%',
      top: '20%'
    },
    dataZoom: [
      {
        type: 'slider',
        start: 0
      },
      {
        start: 0
      }
    ],
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: colors.textSecondary
      },
      axisLine: {
        lineStyle: {
          color: colors.borderLight || colors.borderColor
        }
      }
    },
    yAxis: {
      type: 'value',
      scale: false,
      min: function(value) {
        if (props.referenceMin != null) {
          return Math.min(value.min, props.referenceMin);
        }
        return value.min;
      },
      max: function(value) {
        if (props.referenceMax != null) {
          return Math.max(value.max, props.referenceMax);
        }
        return value.max;
      },
      axisLabel: {
        formatter: function(value) {
          return Number(value).toFixed(2);
        },
        fontSize: 10,
        color: colors.textSecondary
      },
      splitLine: {
        lineStyle: {
          color: colors.borderLight || colors.borderColor
        }
      }
    },
    series: [{
      name: props.indexName,
      data: values.map(v => parseFloat(v.toFixed(2))),
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: {
        color: colors.primary,
        width: 2
      },
      itemStyle: {
        color: colors.primary
      },
      ...(props.referenceMin !== null && props.referenceMin !== undefined &&
          props.referenceMax !== null && props.referenceMax !== undefined ? {
        markArea: {
          silent: true,
          itemStyle: {
            color: hexToRgba(colors.success, 0.1),
            borderColor: hexToRgba(colors.success, 0.3),
            borderWidth: 1,
            borderType: 'dashed'
          },
          label: {
            show: true,
            position: 'insideTopRight',
            formatter: '正常范围',
            color: colors.success,
            fontSize: 10
          },
          data: [[
            { yAxis: props.referenceMin },
            { yAxis: props.referenceMax }
          ]]
        }
      } : {})
    }]
  };
};

// 多指标对比图表配置
const initCompareChart = (colors) => {
  const indexNames = Object.keys(props.multiData);
  const lineColors = [colors.primary, colors.danger];

  // 收集所有日期并排序
  const allDates = new Set();
  indexNames.forEach(name => {
    const dataList = props.multiData[name];
    if (Array.isArray(dataList)) {
      dataList.forEach(item => {
        if (item.medical_date) {
          allDates.add(formatDate(item.medical_date));
        }
      });
    }
  });
  const dates = Array.from(allDates).sort((a, b) => {
    return new Date(a) - new Date(b);
  });

  // 为每个指标生成 series
  const series = [];
  const legendData = [];

  indexNames.forEach((name, idx) => {
    const dataList = props.multiData[name] || [];
    const dataMap = {};

    dataList.forEach(item => {
      if (item.medical_date) {
        const dateKey = formatDate(item.medical_date);
        dataMap[dateKey] = parseFloat(item.index_value) || null;
      }
    });

    const values = dates.map(date => dataMap[date] !== undefined ? dataMap[date] : null);
    const color = lineColors[idx % lineColors.length];

    legendData.push(name);
    series.push({
      name: name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      yAxisIndex: idx,
      data: values,
      connectNulls: true,
      lineStyle: {
        color: color,
        width: 2
      },
      itemStyle: {
        color: color
      }
    });
  });

  // 生成 yAxis 配置
  const yAxes = indexNames.map((name, idx) => {
    const color = lineColors[idx % lineColors.length];
    return {
      type: 'value',
      name: name,
      position: idx === 0 ? 'left' : 'right',
      axisLabel: {
        formatter: function(value) {
          return Number(value).toFixed(2);
        },
        fontSize: 10,
        color: color
      },
      axisLine: {
        show: true,
        lineStyle: {
          color: color
        }
      },
      nameTextStyle: {
        color: color,
        fontSize: 11
      },
      splitLine: {
        show: idx === 0,
        lineStyle: {
          color: colors.borderLight || colors.borderColor
        }
      }
    };
  });

  return {
    title: {
      text: '指标对比趋势图',
      left: 'center',
      textStyle: {
        color: colors.primary,
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      position: function(pos, params, dom, rect, size) {
        const obj = { top: 10 };
        obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
        return obj;
      },
      formatter: function(params) {
        let result = `<div style="margin-bottom: 5px; font-weight: bold;">${params[0].axisValue}</div>`;
        params.forEach(param => {
          const color = param.color;
          result += `<div style="margin: 2px 0;">
            <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${color};"></span>
            ${param.seriesName}: ${param.value !== null && param.value !== undefined ? param.value : '-'}
          </div>`;
        });
        return result;
      }
    },
    legend: {
      data: legendData,
      right: 10,
      top: 30,
      textStyle: {
        color: colors.textSecondary,
        fontSize: 12
      }
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '20%',
      top: '20%'
    },
    dataZoom: [
      {
        type: 'slider',
        start: 0
      },
      {
        start: 0
      }
    ],
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: colors.textSecondary
      },
      axisLine: {
        lineStyle: {
          color: colors.borderLight || colors.borderColor
        }
      }
    },
    yAxis: yAxes,
    series: series
  };
};

// 初始化变化率图表
const initSecondaryChart = () => {
  if (!secondaryChartContainer.value || props.chartData.length < 2) return;

  const colors = getThemeColors();

  if (secondaryChartInstance) {
    secondaryChartInstance.dispose();
  }

  secondaryChartInstance = echarts.init(secondaryChartContainer.value);

  // 计算变化率数据
  const sortedData = [...props.chartData].sort((a, b) =>
    new Date(a.date) - new Date(b.date));

  const dates = sortedData.map(item => formatDate(item.date));
  const values = sortedData.map(item => parseFloat(item.value) || 0);

  // 计算变化率
  const changeRates = [];
  for (let i = 1; i < values.length; i++) {
    const prevValue = values[i-1];
    const currentValue = values[i];
    const changeRate = prevValue !== 0 ? ((currentValue - prevValue) / prevValue * 100) : 0;
    changeRates.push(parseFloat(changeRate.toFixed(2)));
  }

  // 变化率图表配置
  const option = {
    title: {
      text: '指标变化率',
      left: 'center',
      textStyle: {
        color: colors.primary,
        fontSize: 16,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      formatter: '{b}: {c}%'
    },
    legend: {
      data: ['变化率'],
      right: 10,
      top: 0,
      textStyle: {
        color: colors.textSecondary,
        fontSize: 12
      }
    },
    grid: {
      left: '10%',
      right: '3%',
      bottom: '20%',
      top: '20%'
    },
    dataZoom: [
      {
        type: 'slider',
        start: 0,
        show: false,
        disabled: true,
        zoomLock: true
      },
      {
        start: 0,
        show: false,
        zoomLock: true
      }
    ],
    xAxis: {
      type: 'category',
      data: dates.slice(1),
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        color: colors.textSecondary
      },
      axisLine: {
        lineStyle: {
          color: colors.borderLight || colors.borderColor
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: function(value) {
          return Number(value).toFixed(2) + '%';
        },
        fontSize: 10,
        color: colors.textSecondary
      },
      splitLine: {
        lineStyle: {
          color: colors.borderLight || colors.borderColor
        }
      }
    },
    series: [{
      name: '变化率',
      type: 'bar',
      data: changeRates,
      itemStyle: {
        color: function(params) {
          return params.data >= 0 ? colors.danger : colors.success;
        }
      }
    }]
  };

  secondaryChartInstance.setOption(option);
};

// 响应式调整
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize();
  }
  if (secondaryChartInstance) {
    secondaryChartInstance.resize();
  }
};

// 监听数据变化
watch(() => props.chartData, () => {
  nextTick(() => {
    initChart();
  });
}, { deep: true });

// 监听对比数据变化
watch(() => props.multiData, () => {
  nextTick(() => {
    if (props.compareMode && Object.keys(props.multiData).length > 0) {
      initChart();
    }
  });
}, { deep: true });

// 组件挂载时初始化
onMounted(() => {
  nextTick(() => {
    initChart();
  });
});

// 组件卸载时销毁图表
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose();
  }
  if (secondaryChartInstance) {
    secondaryChartInstance.dispose();
  }
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.chart-section {
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

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--primary-alpha-10);
}

.chart-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
}

.chart-content {
  padding: 16px;
}

.chart-container {
  width: 100%;
  height: 380px;
}

.empty-data {
  padding: 30px 0;
  text-align: center;
}

/* 第二个图表样式 */
.secondary-chart-section {
  border-top: 1px solid var(--primary-alpha-10);
}

.secondary-chart-container {
  height: 280px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-header h3 {
    font-size: 16px;
  }

  .chart-content {
    padding: 15px;
  }

  .chart-container {
    height: 330px;
  }
  
  .secondary-chart-container {
    height: 250px;
  }
}

@media (max-width: 480px) {
  .chart-header {
    padding: 15px;
  }

  .chart-content {
    padding: 10px;
  }

  .chart-container {
    height: 280px;
  }
  
  .secondary-chart-container {
    height: 220px;
  }
}
</style>
