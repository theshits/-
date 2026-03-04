import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface EmissionSource {
  id: number
  name: string
  latitude: number
  longitude: number
  height: number
  emission_rate: number
  pollutant_type: string
  temperature: number
  velocity: number
  diameter: number
  marker_symbol: string
  marker_color: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Receptor {
  id: number
  name: string
  latitude: number
  longitude: number
  height: number
  marker_symbol: string
  marker_color: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Meteorology {
  id: number
  name: string
  wind_speed: number
  wind_direction: number
  boundary_layer_height: number
  stability_class: string
  temperature: number
  humidity: number
  record_time: string
  created_at: string
  updated_at: string
}

export interface SimulationResult {
  concentrations: number[][]
  grid_lat: number[]
  grid_lon: number[]
  contributions: Array<{
    source_id: number
    source_name: string
    concentration: number
    percentage: number
  }>
  receptor_contributions: Record<string, Array<{
    source_id: number
    source_name: string
    concentration: number
    percentage: number
  }>>
}

export const sourcesApi = {
  getAll: () => api.get<EmissionSource[]>('/sources/'),
  get: (id: number) => api.get<EmissionSource>(`/sources/${id}`),
  create: (data: Partial<EmissionSource>) => api.post<EmissionSource>('/sources/', data),
  update: (id: number, data: Partial<EmissionSource>) => api.put<EmissionSource>(`/sources/${id}`, data),
  delete: (id: number) => api.delete(`/sources/${id}`),
  batchCreate: (data: Partial<EmissionSource>[]) => api.post<EmissionSource[]>('/sources/batch', data)
}

export const receptorsApi = {
  getAll: () => api.get<Receptor[]>('/receptors/'),
  get: (id: number) => api.get<Receptor>(`/receptors/${id}`),
  create: (data: Partial<Receptor>) => api.post<Receptor>('/receptors/', data),
  update: (id: number, data: Partial<Receptor>) => api.put<Receptor>(`/receptors/${id}`, data),
  delete: (id: number) => api.delete(`/receptors/${id}`),
  batchCreate: (data: Partial<Receptor>[]) => api.post<Receptor[]>('/receptors/batch', data)
}

export const meteorologyApi = {
  getAll: () => api.get<Meteorology[]>('/meteorology/'),
  get: (id: number) => api.get<Meteorology>(`/meteorology/${id}`),
  create: (data: Partial<Meteorology>) => api.post<Meteorology>('/meteorology/', data),
  update: (id: number, data: Partial<Meteorology>) => api.put<Meteorology>(`/meteorology/${id}`, data),
  delete: (id: number) => api.delete(`/meteorology/${id}`)
}

export const simulationApi = {
  run: (data: {
    meteorology_id: number
    source_ids?: number[]
    receptor_ids?: number[]
    grid_resolution?: number
    domain_size?: number
  }) => api.post<SimulationResult>('/simulation/run', data),
  
  preview: (meteorologyId: number, sourceId: number, domainSize?: number, gridResolution?: number) => 
    api.get(`/simulation/preview/${meteorologyId}/${sourceId}`, {
      params: { domain_size: domainSize, grid_resolution: gridResolution }
    })
}

export const configApi = {
  getMarkerConfigs: () => api.get('/config/'),
  getMarkerConfig: (type: string) => api.get(`/config/${type}`),
  updateMarkerConfig: (type: string, data: { symbol?: string; color?: string; size?: number }) => 
    api.put(`/config/${type}`, data)
}

export default api
