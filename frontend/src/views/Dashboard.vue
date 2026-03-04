<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { NButton, NSelect, NCard, NSpin, NEmpty, NGrid, NGi, NStatistic, NProgress } from 'naive-ui'
import { sourcesApi, receptorsApi, meteorologyApi, simulationApi, type EmissionSource, type Receptor, type Meteorology, type SimulationResult } from '@/api'
import WindRoseControl from '@/components/WindRoseControl.vue'
import ContributionChart from '@/components/ContributionChart.vue'

const mapContainer = ref<HTMLElement | null>(null)
const map = ref<L.Map | null>(null)
const sources = ref<EmissionSource[]>([])
const receptors = ref<Receptor[]>([])
const meteorologies = ref<Meteorology[]>([])
const selectedMeteorologyId = ref<number | null>(null)
const simulationResult = ref<SimulationResult | null>(null)
const loading = ref(false)
const plumeLayer = ref<L.Layer | null>(null)
const sourceMarkers = ref<L.Marker[]>([])
const receptorMarkers = ref<L.Marker[]>([])

const meteorologyOptions = computed(() => 
  meteorologies.value.map(m => ({
    label: `${m.name} - 风速: ${m.wind_speed}m/s, 风向: ${m.wind_direction}°`,
    value: m.id
  }))
)

const initMap = () => {
  if (!mapContainer.value) return
  
  map.value = L.map(mapContainer.value, {
    center: [39.9, 116.4],
    zoom: 11,
    zoomControl: true
  })
  
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
  }).addTo(map.value)
}

const createCustomIcon = (color: string, type: 'source' | 'receptor') => {
  const svg = type === 'source' 
    ? `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}" width="32" height="32">
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        <circle cx="12" cy="6" r="3" fill="${color}" opacity="0.5"/>
      </svg>`
    : `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}" width="32" height="32">
        <path d="M12 2L4.5 20.29l.71.71L12 18l6.79 3 .71-.71z"/>
      </svg>`
  
  return L.divIcon({
    html: svg,
    className: 'custom-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 32]
  })
}

const updateMarkers = () => {
  if (!map.value) return
  
  sourceMarkers.value.forEach(marker => marker.remove())
  receptorMarkers.value.forEach(marker => marker.remove())
  
  sourceMarkers.value = []
  receptorMarkers.value = []
  
  sources.value.forEach(source => {
    if (!source.is_active) return
    
    const marker = L.marker([source.latitude, source.longitude], {
      icon: createCustomIcon(source.marker_color, 'source')
    }).addTo(map.value!)
    
    marker.bindPopup(`
      <div style="min-width: 200px;">
        <h3 style="margin: 0 0 8px; font-size: 16px;">${source.name}</h3>
        <p style="margin: 4px 0; color: #666;">📍 位置: ${source.latitude.toFixed(4)}, ${source.longitude.toFixed(4)}</p>
        <p style="margin: 4px 0; color: #666;">📏 高度: ${source.height}m</p>
        <p style="margin: 4px 0; color: #666;">💨 排放速率: ${source.emission_rate} g/s</p>
        <p style="margin: 4px 0; color: #666;">🌡️ 温度: ${source.temperature}K</p>
      </div>
    `)
    
    sourceMarkers.value.push(marker)
  })
  
  receptors.value.forEach(receptor => {
    if (!receptor.is_active) return
    
    const marker = L.marker([receptor.latitude, receptor.longitude], {
      icon: createCustomIcon(receptor.marker_color, 'receptor')
    }).addTo(map.value!)
    
    marker.bindPopup(`
      <div style="min-width: 200px;">
        <h3 style="margin: 0 0 8px; font-size: 16px;">${receptor.name}</h3>
        <p style="margin: 4px 0; color: #666;">📍 位置: ${receptor.latitude.toFixed(4)}, ${receptor.longitude.toFixed(4)}</p>
        <p style="margin: 4px 0; color: #666;">📏 高度: ${receptor.height}m</p>
      </div>
    `)
    
    receptorMarkers.value.push(marker)
  })
  
  fitMapToBounds()
}

const fitMapToBounds = () => {
  if (!map.value) return
  
  const bounds: L.LatLngBoundsExpression = []
  
  sources.value.forEach(s => bounds.push([s.latitude, s.longitude]))
  receptors.value.forEach(r => bounds.push([r.latitude, r.longitude]))
  
  if (bounds.length > 0) {
    map.value.fitBounds(bounds as L.LatLngBoundsExpression, { padding: [50, 50] })
  }
}

const runSimulation = async () => {
  if (!selectedMeteorologyId.value) return
  
  loading.value = true
  try {
    const result = await simulationApi.run({
      meteorology_id: selectedMeteorologyId.value,
      grid_resolution: 100,
      domain_size: 10000
    })
    
    simulationResult.value = result.data
    visualizePlume(result.data)
  } catch (error) {
    console.error('Simulation failed:', error)
  } finally {
    loading.value = false
  }
}

const visualizePlume = (result: SimulationResult) => {
  if (!map.value) return
  
  if (plumeLayer.value) {
    plumeLayer.value.remove()
  }
  
  const { concentrations, grid_lat, grid_lon } = result
  
  const maxConc = Math.max(...concentrations.flat())
  if (maxConc === 0) return
  
  const contourLevels = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
  const colors = ['#E3F2FD', '#90CAF9', '#42A5F5', '#1E88E5', '#1565C0', '#0D47A1']
  
  const layers: L.Polygon[] = []
  
  for (let levelIdx = 0; levelIdx < contourLevels.length; levelIdx++) {
    const threshold = contourLevels[levelIdx] * maxConc
    const points: [number, number][] = []
    
    for (let i = 0; i < grid_lat.length; i++) {
      for (let j = 0; j < grid_lon.length; j++) {
        if (concentrations[i][j] >= threshold) {
          points.push([grid_lat[i], grid_lon[j]])
        }
      }
    }
    
    if (points.length > 2) {
      const polygon = L.polygon(points as [number, number][], {
        color: colors[levelIdx],
        fillColor: colors[levelIdx],
        fillOpacity: 0.3,
        weight: 1
      })
      layers.push(polygon)
    }
  }
  
  plumeLayer.value = L.layerGroup(layers.reverse())
  plumeLayer.value.addTo(map.value)
}

const handleWindDirectionChange = (direction: number) => {
  console.log('Wind direction changed:', direction)
}

const loadData = async () => {
  try {
    const [sourcesRes, receptorsRes, meteorologiesRes] = await Promise.all([
      sourcesApi.getAll(),
      receptorsApi.getAll(),
      meteorologyApi.getAll()
    ])
    
    sources.value = sourcesRes.data
    receptors.value = receptorsRes.data
    meteorologies.value = meteorologiesRes.data
    
    if (meteorologies.value.length > 0) {
      selectedMeteorologyId.value = meteorologies.value[0].id
    }
    
    updateMarkers()
  } catch (error) {
    console.error('Failed to load data:', error)
  }
}

onMounted(() => {
  initMap()
  loadData()
})

watch([sources, receptors], () => {
  updateMarkers()
})
</script>

<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="page-title">空气污染扩散模拟平台</h1>
        <p class="page-subtitle">基于高斯扩散模型的实时污染扩散可视化</p>
      </div>
      <div class="header-right">
        <n-select
          v-model:value="selectedMeteorologyId"
          :options="meteorologyOptions"
          placeholder="选择气象场"
          style="width: 300px;"
        />
        <n-button type="primary" :loading="loading" @click="runSimulation">
          运行模拟
        </n-button>
      </div>
    </div>
    
    <div class="dashboard-content">
      <div class="map-section">
        <div ref="mapContainer" class="map-container"></div>
      </div>
      
      <div class="sidebar">
        <n-card title="气象控制" size="small" class="control-card">
          <wind-rose-control 
            v-if="selectedMeteorologyId"
            :meteorology-id="selectedMeteorologyId"
            @direction-change="handleWindDirectionChange"
          />
        </n-card>
        
        <n-card title="数据统计" size="small" class="stats-card">
          <n-grid :cols="2" :x-gap="12" :y-gap="12">
            <n-gi>
              <n-statistic label="排放源" :value="sources.filter(s => s.is_active).length" />
            </n-gi>
            <n-gi>
              <n-statistic label="受体点" :value="receptors.filter(r => r.is_active).length" />
            </n-gi>
          </n-grid>
        </n-card>
        
        <n-card v-if="simulationResult" title="贡献度排名" size="small" class="contribution-card">
          <contribution-chart :data="simulationResult.contributions" />
        </n-card>
        
        <n-empty v-else description="请运行模拟查看结果" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.dashboard-header {
  padding: 20px 24px;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  flex: 1;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.dashboard-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.map-section {
  flex: 1;
  position: relative;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.sidebar {
  width: 320px;
  padding: 16px;
  background: var(--bg-primary);
  border-left: 1px solid var(--border-color);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.control-card,
.stats-card,
.contribution-card {
  margin-bottom: 0;
}

:deep(.custom-marker) {
  background: transparent;
  border: none;
}

:deep(.leaflet-popup-content-wrapper) {
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
}

:deep(.leaflet-popup-content) {
  margin: 12px 16px;
}
</style>
