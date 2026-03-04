<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

interface ContributionData {
  source_id: number
  source_name: string
  concentration: number
  percentage: number
}

const props = defineProps<{
  data: ContributionData[]
}>()

const chartRef = ref<HTMLElement | null>(null)
const chart = ref<echarts.ECharts | null>(null)

const initChart = () => {
  if (!chartRef.value) return
  
  chart.value = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chart.value || !props.data?.length) return
  
  const sortedData = [...props.data].sort((a, b) => b.percentage - a.percentage).slice(0, 10)
  
  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const item = params[0]
        return `${item.name}<br/>贡献度: ${item.value.toFixed(2)}%`
      }
    },
    grid: {
      left: '3%',
      right: '8%',
      top: '3%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}%',
        fontSize: 11,
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      }
    },
    yAxis: {
      type: 'category',
      data: sortedData.map(d => d.source_name).reverse(),
      axisLabel: {
        fontSize: 11,
        color: '#333'
      },
      axisTick: {
        show: false
      },
      axisLine: {
        show: false
      }
    },
    series: [
      {
        type: 'bar',
        data: sortedData.map(d => d.percentage).reverse(),
        barWidth: '60%',
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#007AFF' },
            { offset: 1, color: '#5AC8FA' }
          ])
        },
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#0066DD' },
              { offset: 1, color: '#007AFF' }
            ])
          }
        },
        label: {
          show: true,
          position: 'right',
          formatter: '{c}%',
          fontSize: 11,
          color: '#666'
        }
      }
    ]
  }
  
  chart.value.setOption(option)
}

onMounted(() => {
  initChart()
})

watch(() => props.data, () => {
  updateChart()
}, { deep: true })
</script>

<template>
  <div class="contribution-chart">
    <div v-if="data && data.length > 0" ref="chartRef" class="chart-container"></div>
    <div v-else class="empty-state">
      <p>暂无贡献度数据</p>
    </div>
  </div>
</template>

<style scoped>
.contribution-chart {
  width: 100%;
}

.chart-container {
  width: 100%;
  height: 250px;
}

.empty-state {
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
