<script setup lang="ts">
import { ref, onMounted, h, watch } from 'vue'
import { 
  NButton, NDataTable, NModal, NForm, NFormItem, NInput, NInputNumber, 
  NSelect, NSpace, NPopconfirm, NTag, NDatePicker, useMessage, NCard, NGrid, NGi 
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { meteorologyApi, type Meteorology } from '@/api'
import WindRoseControl from '@/components/WindRoseControl.vue'

const message = useMessage()
const meteorologies = ref<Meteorology[]>([])
const loading = ref(false)
const showModal = ref(false)
const editingMet = ref<Meteorology | null>(null)
const selectedMetId = ref<number | null>(null)
const formData = ref({
  name: '',
  wind_speed: 2.0,
  wind_direction: 0,
  boundary_layer_height: 1000,
  stability_class: 'D',
  temperature: 293.15,
  humidity: 50,
  record_time: Date.now()
})

const stabilityOptions = [
  { label: 'A - 极不稳定 (强对流)', value: 'A' },
  { label: 'B - 不稳定', value: 'B' },
  { label: 'C - 弱不稳定', value: 'C' },
  { label: 'D - 中性', value: 'D' },
  { label: 'E - 弱稳定', value: 'E' },
  { label: 'F - 稳定', value: 'F' }
]

const columns: DataTableColumns<Meteorology> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '名称', key: 'name', width: 150 },
  { 
    title: '风速', 
    key: 'wind_speed',
    width: 100,
    render: (row) => `${row.wind_speed} m/s`
  },
  { 
    title: '风向', 
    key: 'wind_direction',
    width: 100,
    render: (row) => `${row.wind_direction}°`
  },
  { title: '稳定度', key: 'stability_class', width: 80 },
  { 
    title: '边界层高度', 
    key: 'boundary_layer_height',
    width: 120,
    render: (row) => `${row.boundary_layer_height} m`
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    render: (row) => h(NSpace, null, {
      default: () => [
        h(NButton, { 
          size: 'small', 
          onClick: () => editMeteorology(row) 
        }, { default: () => '编辑' }),
        h(NPopconfirm, {
          onPositiveClick: () => deleteMeteorology(row.id)
        }, {
          trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
          default: () => '确定删除该气象场吗？'
        })
      ]
    })
  }
]

const loadMeteorologies = async () => {
  loading.value = true
  try {
    const res = await meteorologyApi.getAll()
    meteorologies.value = res.data
    if (meteorologies.value.length > 0 && !selectedMetId.value) {
      selectedMetId.value = meteorologies.value[0].id
    }
  } catch (error) {
    message.error('加载气象场数据失败')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  editingMet.value = null
  formData.value = {
    name: '',
    wind_speed: 2.0,
    wind_direction: 0,
    boundary_layer_height: 1000,
    stability_class: 'D',
    temperature: 293.15,
    humidity: 50,
    record_time: Date.now()
  }
  showModal.value = true
}

const editMeteorology = (met: Meteorology) => {
  editingMet.value = met
  formData.value = {
    name: met.name,
    wind_speed: met.wind_speed,
    wind_direction: met.wind_direction,
    boundary_layer_height: met.boundary_layer_height,
    stability_class: met.stability_class,
    temperature: met.temperature,
    humidity: met.humidity,
    record_time: new Date(met.record_time).getTime()
  }
  showModal.value = true
}

const saveMeteorology = async () => {
  try {
    const data = {
      ...formData.value,
      record_time: new Date(formData.value.record_time).toISOString()
    }
    
    if (editingMet.value) {
      await meteorologyApi.update(editingMet.value.id, data)
      message.success('更新成功')
    } else {
      await meteorologyApi.create(data)
      message.success('创建成功')
    }
    showModal.value = false
    loadMeteorologies()
  } catch (error) {
    message.error('保存失败')
  }
}

const deleteMeteorology = async (id: number) => {
  try {
    await meteorologyApi.delete(id)
    message.success('删除成功')
    loadMeteorologies()
  } catch (error) {
    message.error('删除失败')
  }
}

onMounted(() => {
  loadMeteorologies()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">气象场管理</h1>
        <p class="page-subtitle">管理和配置气象条件参数</p>
      </div>
      <n-button type="primary" @click="openCreateModal">
        + 新增气象场
      </n-button>
    </div>
    
    <n-grid :cols="3" :x-gap="20">
      <n-gi :span="2">
        <div class="card">
          <n-data-table 
            :columns="columns" 
            :data="meteorologies" 
            :loading="loading"
            :row-key="(row: Meteorology) => row.id"
            :row-class-name="(row: Meteorology) => row.id === selectedMetId ? 'selected-row' : ''"
            @update:checked-row-keys="(keys: any) => selectedMetId = keys[0]"
            @update:row-click="(row: Meteorology) => selectedMetId = row.id"
          />
        </div>
      </n-gi>
      
      <n-gi :span="1">
        <n-card title="风向风速控制" size="small">
          <div v-if="selectedMetId" class="control-panel">
            <wind-rose-control :meteorology-id="selectedMetId" />
            
            <div class="quick-actions">
              <n-button 
                v-for="dir in [{label: 'N', value: 0}, {label: 'E', value: 90}, {label: 'S', value: 180}, {label: 'W', value: 270}]"
                :key="dir.value"
                size="small"
                @click="() => {}"
                style="margin: 4px;"
              >
                {{ dir.label }}
              </n-button>
            </div>
          </div>
          <div v-else class="empty-hint">
            请选择一个气象场进行编辑
          </div>
        </n-card>
        
        <n-card title="稳定度说明" size="small" style="margin-top: 16px;">
          <div class="stability-info">
            <div class="stability-item">
              <n-tag type="error" size="small">A</n-tag>
              <span>极不稳定，强日照、弱风</span>
            </div>
            <div class="stability-item">
              <n-tag type="warning" size="small">B</n-tag>
              <span>不稳定，中等日照</span>
            </div>
            <div class="stability-item">
              <n-tag type="info" size="small">C</n-tag>
              <span>弱不稳定，弱日照</span>
            </div>
            <div class="stability-item">
              <n-tag type="default" size="small">D</n-tag>
              <span>中性，阴天或夜间</span>
            </div>
            <div class="stability-item">
              <n-tag type="success" size="small">E</n-tag>
              <span>弱稳定，夜间弱风</span>
            </div>
            <div class="stability-item">
              <n-tag type="success" size="small">F</n-tag>
              <span>稳定，晴朗夜间</span>
            </div>
          </div>
        </n-card>
      </n-gi>
    </n-grid>
    
    <n-modal 
      v-model:show="showModal" 
      :title="editingMet ? '编辑气象场' : '新增气象场'"
      preset="card"
      style="width: 600px;"
    >
      <n-form :model="formData" label-placement="left" label-width="100">
        <n-form-item label="名称" required>
          <n-input v-model:value="formData.name" placeholder="请输入气象场名称" />
        </n-form-item>
        
        <n-form-item label="风速">
          <n-input-number 
            v-model:value="formData.wind_speed" 
            :min="0.1" 
            :max="30"
            :precision="1"
            style="width: 100%;"
          >
            <template #suffix>m/s</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="风向">
          <n-input-number 
            v-model:value="formData.wind_direction" 
            :min="0" 
            :max="360"
            style="width: 100%;"
          >
            <template #suffix>°</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="边界层高度">
          <n-input-number 
            v-model:value="formData.boundary_layer_height" 
            :min="100"
            style="width: 100%;"
          >
            <template #suffix>m</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="稳定度等级">
          <n-select 
            v-model:value="formData.stability_class" 
            :options="stabilityOptions"
          />
        </n-form-item>
        
        <n-form-item label="温度">
          <n-input-number 
            v-model:value="formData.temperature" 
            :min="200"
            :precision="1"
            style="width: 100%;"
          >
            <template #suffix>K</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="湿度">
          <n-input-number 
            v-model:value="formData.humidity" 
            :min="0" 
            :max="100"
            style="width: 100%;"
          >
            <template #suffix>%</template>
          </n-input-number>
        </n-form-item>
        
        <n-form-item label="记录时间">
          <n-date-picker 
            v-model:value="formData.record_time" 
            type="datetime"
            style="width: 100%;"
          />
        </n-form-item>
      </n-form>
      
      <template #footer>
        <n-space justify="end">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="saveMeteorology">保存</n-button>
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

.control-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
}

.empty-hint {
  text-align: center;
  color: var(--text-secondary);
  padding: 20px;
}

.stability-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stability-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

:deep(.selected-row) {
  background-color: rgba(0, 122, 255, 0.1) !important;
}

:deep(.n-data-table-tr) {
  cursor: pointer;
}
</style>
