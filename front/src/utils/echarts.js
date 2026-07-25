/**
 * echarts 按需导入
 * 只引入常用的图表和组件，减少打包体积
 */
import * as echarts from 'echarts/core'

// 图表类型
import { LineChart, BarChart, PieChart } from 'echarts/charts'

// 组件
import {
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
} from 'echarts/components'

// 渲染器
import { CanvasRenderer } from 'echarts/renderers'

// 注册
echarts.use([
  LineChart,
  BarChart,
  PieChart,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  TitleComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  CanvasRenderer,
])

export default echarts
export { echarts }