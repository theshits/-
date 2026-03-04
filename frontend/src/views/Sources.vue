<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { 
  NButton, NDataTable, NModal, NForm, NFormItem, NInput, NInputNumber, 
  NSwitch, NSelect, NColorPicker, NSpace, NPopconfirm, NTag, useMessage 
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { sourcesApi, type EmissionSource } from '@/api'

const message = useMessage()
const sources = ref<EmissionSource[]>([])
const loading = ref(false)
const showModal = ref(false)
const editingSource = ref<EmissionSource | null>(null)
const formData = ref({
  name: '',
  latitude: 39.9,
  longitude: 116.4,
  height: 50,
  emission_rate: 10,
  pollutant_type: 'NO2',
  temperature: 400,
  velocity: 15,
  diameter: 2,
  marker_color: '#FF5722',
  is_active: true
})

const pollutantOptions = [
  { label: 'NO2 (二氧化氮)', value: 'NO2' },
  { label: 'SO2 (二氧化硫)', value: 'SO2' },
  { label: 'PM2.5', value: 'PM25' },
  { label: 'PM10', value: 'PM10' },
  { label: 'CO (一氧化碳)', value: 'CO' },
  { label: 'VOCs (挥发性有机物)', value: 'VOCs' }
]

const columns: DataTableColumns<EmissionSource> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '名称', key: 'name', width: 150 },
  { 
    title: '位置', 
    key: 'location',
    width: 200,
    render: (row) => `${row.latitude.toFixed(4)}, ${row.longitude.toFixed(4)}`
  },
  { title: '高度', key: 'height', width: 80 },
  { 
    title: '排放速率', 
    key: 'emission_rate',
    width: 120,
    render: (row) => `${row.emission_rate} g/s`
  },
  { title: '污染物', key: 'pollutant_type', width: 80 },
  { 
    title: '状态', 
    key: 'is_active',
    width: 80,
    render: (row) => h(NTag, { 
      type: row.is_active ? 'success' : 'default',
      size: 'small'
    }, { default: () => row.is_active ? '启用' : '禁用' })
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => h(NSpace, null, {
      default: () => [
        h(NButton, { 
          size: 'small', 
          onClick: () => editSource(row) 
        }, { default: () => '编辑' }),
        h(NPopconfirm, {
          onPositiveClick: () => deleteSource(row.id)
        }, {
          trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
          default: () => '确定删除该排放源吗？'
        })
      ]
    })
  }
]

const loadSources = async () => {
  loading.value = true
  try {
    const res = await sourcesApi.getAll()
    sources.value = res.data
  } catch (error) {
    message.error('加载排放源数据失败')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  editingSource.value = null
  formData.value = {
    name: '',
    latitude: 39.9,
    longitude: 116.4,
    height: 50,
    emission_rate: 10,
    pollutant_type: 'NO2',
    temperature: 400,
    velocity: 15,
    diameter: 2,
    marker_color: '#FF5722',
    is_active: true
  }
  showModal.value = true
}

const editSource = (source: EmissionSource) => {
  editingSource.value = source
  formData.value = {
    name: source.name,
    latitude: source.latitude,
    longitude: source.longitude,
    height: source.height,
    emission_rate: source.emission_rate,
    pollutant_type: source.pollutant_type,
    temperature: source.temperature,
    velocity: source.velocity,
    diameter: source.diameter,
    marker_color: source.marker_color,
    is_active: source.is_active
  }
  showModal.value = true
}

const saveSource = async () => {
  try {
    if (editingSource.value) {
      await sourcesApi.update(editingSource.value.id, formData.value)
      message.success('更新成功')
    } else {
      await sourcesApi.create(formData.value)
      message.success('创建成功')
    }
    showModal.value = false
    loadSources()
  } catch (error) {
    message.error('保存失败')
  }
}

const deleteSource = async (id: number) => {
  try {
    await sourcesApi.delete(id)
    message.success('删除成功')
    loadSources()
  } catch (error) {
    message.error('删除失败')
  }
}

onMounted(() => {
  loadSources()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">排放源管理</h1>
        <p class="page-subtitle">管理和配置污染排放源信息</p>
      </div>
      <n-button type="primary" @click="openCreateModal">
        + 新增排放源
      </n-button>
    </div>
    
    <div class="card">
      <n-data-table 
        :columns="columns" 
        :data="sources" 
        :loading="loading"
        :pagination="{ pageSize: 10 }"
      />
    </div>
    
    <n-modal 
      v-model:show="showModal" 
      :title="editingSource ? '编辑排放源' : '新增排放源'"
      preset="card"
      style="width: 600px;"
    >
      <n-form :model="formData" label-placement="left" label-width="100">
        <n-form-item label="名称" required>
          <n-input v-model:value="formData.name" placeholder="请输入排放源名称" />
        </n-form-item>
        
        <n-form-item label="纬度" required>
          <n-input-number 
            v-model:value="formData.latitude" 
            :min="-90" 
            :max="90" 
            :precision="6"
            style="width: 100%;"
          />
        </n-form-item>
        
        <n-form-item label="经度" required>
          <n-input-number 
            v-model:value="formData.longitude" 
            :min="-180" 
            :max="180" 
            :precision="6"
            style="width: 100%;"
          />
        </n-form-item>
        
        <n-form-item label="高度">
          <n-input-number 
            v-model:value="formData.height" 
            :min="0"
            style="width: 100%;"
          >
            <template #suffix>m</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="排放速率">
          <n-input-number 
            v-model:value="formData.emission_rate" 
            :min="0"
            style="width: 100%;"
          >
            <template #suffix>g/s</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="污染物类型">
          <n-select 
            v-model:value="formData.pollutant_type" 
            :options="pollutantOptions"
          />
        </n-form-item>
        
        <n-form-item label="烟气温度">
          <n-input-number 
            v-model:value="formData.temperature" 
            :min="200"
            style="width: 100%;"
          >
            <template #suffix>K</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="出口速度">
          <n-input-number 
            v-model:value="formData.velocity" 
            :min="0"
            style="width: 100%;"
          >
            <template #suffix>m/s</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="烟囱直径">
          <n-input-number 
            v-model:value="formData.diameter" 
            :min="0"
            style="width: 100%;"
          >
            <template #suffix>m</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="标记颜色">
          <n-color-picker v-model:value="formData.marker_color" />
        </n-form-item>
        
        <n-form-item label="启用状态">
          <n-switch v-model:value="formData.is_active" />
        </n-form-item>
      </n-form>
      
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="saveSource">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
</style>
