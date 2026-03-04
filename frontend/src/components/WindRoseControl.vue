<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import * as echarts from 'echarts'
import { meteorologyApi, type Meteorology } from '@/api'

const props = defineProps<{
  meteorologyId: number
}>()

const emit = defineEmits<{
  (e: 'direction-change', direction: number): void
  (e: 'speed-change', speed: number): void
}>()

const chartRef = ref<HTMLElement | null>(null)
const chart = ref<echarts.ECharts | null>(null)
const meteorology = ref<Meteorology | null>(null)
const windDirection = ref(0)
const windSpeed = ref(2)

const directionLabels = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

const loadMeteorology = async () => {
  try {
    const res = await meteorologyApi.get(props.meteorologyId)
    meteorology.value = res.data
    windDirection.value = res.data.wind_direction
    windSpeed.value = res.data.wind_speed
    updateChart()
  } catch (error) {
    console.error('Failed to load meteorology:', error)
  }
}

const initChart = () => {
  if (!chartRef.value) return
  
  chart.value = echarts.init(chartRef.value)
  
  const option: echarts.EChartsOption = {
    polar: {
      center: ['50%', '50%'],
      radius: '85%'
    },
    angleAxis: {
      type: 'category',
      data: directionLabels,
      startAngle: 90,
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      },
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      axisLabel: {
        color: '#666',
        fontSize: 11
      }
    },
    radiusAxis: {
      min: 0,
      max: 20,
      splitLine: {
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.05)'
        }
      },
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      axisLabel: {
        show: false
      }
    },
    series: [
      {
        type: 'scatter',
        coordinateSystem: 'polar',
        data: [[windDirection.value, windSpeed.value]],
        symbolSize: 20,
        itemStyle: {
          color: '#007AFF',
          shadowBlur: 10,
          shadowColor: 'rgba(0, 122, 255, 0.5)'
        },
        emphasis: {
          itemStyle: {
            color: '#0066DD'
          }
        }
      },
      {
        type: 'line',
        coordinateSystem: 'polar',
        data: getWindArrowData(),
        symbol: 'none',
        lineStyle: {
          color: '#007AFF',
          width: 3
        }
      }
    ],
    graphic: [
      {
        type: 'circle',
        shape: {
          cx: '50%',
          cy: '50%',
          r: 5
        },
        style: {
          fill: '#007AFF'
        }
      }
    ]
  }
  
  chart.value.setOption(option)
  
  chart.value.on('click', (params: any) => {
    if (params.componentType === 'series' && params.seriesIndex === 0) {
      return
    }
  })
  
  chart.value.getZr().on('click', (params: any) => {
    const pointInPixel = [params.offsetX, params.offsetY]
    if (chart.value && chart.value.containPixel('grid', pointInPixel)) {
      const pointInGrid = chart.value.convertFromPixel('grid', pointInPixel)
      const angle = pointInGrid[0]
      const radius = pointInGrid[1]
      
      windDirection.value = Math.round(angle)
      windSpeed.value = Math.round(Math.min(Math.max(radius, 0.5), 20) * 10) / 10
      
      updateChart()
      emit('direction-change', windDirection.value)
      emit('speed-change', windSpeed.value)
      
      saveChanges()
    }
  })
}

const getWindArrowData = () => {
  const angle = windDirection.value
  const speed = windSpeed.value
  
  const angleRad = (90 - angle) * Math.PI / 180
  const x = speed * Math.cos(angleRad)
  const y = speed * Math.sin(angleRad)
  
  return [[0, 0], [angle, speed]]
}

const updateChart = () => {
  if (!chart.value) return
  
  chart.value.setOption({
    series: [
      {
        data: [[windDirection.value, windSpeed.value]]
      },
      {
        data: getWindArrowData()
      }
    ]
  })
}

const saveChanges = async () => {
  if (!meteorology.value) return
  
  try {
    await meteorologyApi.update(props.meteorologyId, {
      wind_direction: windDirection.value,
      wind_speed: windSpeed.value
    })
  } catch (error) {
    console.error('Failed to save changes:', error)
  }
}

const handleDirectionInput = (value: number) => {
  windDirection.value = Math.min(360, Math.max(0, value))
  updateChart()
  saveChanges()
}

const handleSpeedInput = (value: number) => {
  windSpeed.value = Math.min(20, Math.max(0.1, value))
  updateChart()
  saveChanges()
}

onMounted(() => {
  loadMeteorology()
  initChart()
})

watch(() => props.meteorologyId, () => {
  loadMeteorology()
})

watch([windDirection, windSpeed], () => {
  emit('direction-change', windDirection.value)
  emit('speed-change', windSpeed.value)
})
</script>

<template>
  <div class="wind-rose-control">
    <div ref="chartRef" class="wind-chart"></div>
    
    <div class="controls">
      <div class="control-row">
        <label>风向 (°)</label>
        <input 
          type="number" 
          :value="windDirection" 
          @input="handleDirectionInput(Number(($event.target as HTMLInputElement).value))"
          min="0" 
          max="360"
          class="control-input"
        />
      </div>
      <div class="control-row">
        <label>风速</label>
        <input 
          type="number" 
          :value="windSpeed" 
          @input="handleSpeedInput(Number(($event.target as HTMLInputElement).value))"
          min="0.1" 
          max="20"
          step="0.1"
          class="control-input"
        />
      </div>
    </div>
    
    <p class="hint">💡 点击雷达图可快速设置风向风速</p>
  </div>
</template>

<style scoped>
.wind-rose-control {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.wind-chart {
  width: 100%;
  height: 200px;
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.control-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-row label {
  font-size: 13px;
  color: var(--text-secondary);
}

.control-input {
  width: 80px;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.control-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.hint {
  font-size: 12px;
  color: var(--text-secondary);
  text-align: center;
  margin: 0;
}
</style>
