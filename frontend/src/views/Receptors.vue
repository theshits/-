<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { 
  NButton, NDataTable, NModal, NForm, NFormItem, NInput, NInputNumber, 
  NSwitch, NColorPicker, NSpace, NPopconfirm, NTag, useMessage 
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { receptorsApi, type Receptor } from '@/api'

const message = useMessage()
const receptors = ref<Receptor[]>([])
const loading = ref(false)
const showModal = ref(false)
const editingReceptor = ref<Receptor | null>(null)
const formData = ref({
  name: '',
  latitude: 39.9,
  longitude: 116.4,
  height: 0,
  marker_color: '#2196F3',
  is_active: true
})

const columns: DataTableColumns<Receptor> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '名称', key: 'name', width: 200 },
  { 
    title: '位置', 
    key: 'location',
    width: 220,
    render: (row) => `${row.latitude.toFixed(4)}, ${row.longitude.toFixed(4)}`
  },
  { title: '高度', key: 'height', width: 100 },
  { 
    title: '状态', 
    key: 'is_active',
    width: 100,
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
          onClick: () => editReceptor(row) 
        }, { default: () => '编辑' }),
        h(NPopconfirm, {
          onPositiveClick: () => deleteReceptor(row.id)
        }, {
          trigger: () => h(NButton, { size: 'small', type: 'error' }, { default: () => '删除' }),
          default: () => '确定删除该受体点吗？'
        })
      ]
    })
  }
]

const loadReceptors = async () => {
  loading.value = true
  try {
    const res = await receptorsApi.getAll()
    receptors.value = res.data
  } catch (error) {
    message.error('加载受体点数据失败')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  editingReceptor.value = null
  formData.value = {
    name: '',
    latitude: 39.9,
    longitude: 116.4,
    height: 0,
    marker_color: '#2196F3',
    is_active: true
  }
  showModal.value = true
}

const editReceptor = (receptor: Receptor) => {
  editingReceptor.value = receptor
  formData.value = {
    name: receptor.name,
    latitude: receptor.latitude,
    longitude: receptor.longitude,
    height: receptor.height,
    marker_color: receptor.marker_color,
    is_active: receptor.is_active
  }
  showModal.value = true
}

const saveReceptor = async () => {
  try {
    if (editingReceptor.value) {
      await receptorsApi.update(editingReceptor.value.id, formData.value)
      message.success('更新成功')
    } else {
      await receptorsApi.create(formData.value)
      message.success('创建成功')
    }
    showModal.value = false
    loadReceptors()
  } catch (error) {
    message.error('保存失败')
  }
}

const deleteReceptor = async (id: number) => {
  try {
    await receptorsApi.delete(id)
    message.success('删除成功')
    loadReceptors()
  } catch (error) {
    message.error('删除失败')
  }
}

onMounted(() => {
  loadReceptors()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">受体点管理</h1>
        <p class="page-subtitle">管理和配置监测站点/受体点信息</p>
      </div>
      <n-button type="primary" @click="openCreateModal">
        + 新增受体点
      </n-button>
    </div>
    
    <div class="card">
      <n-data-table 
        :columns="columns" 
        :data="receptors" 
        :loading="loading"
        :pagination="{ pageSize: 10 }"
      />
    </div>
    
    <n-modal 
      v-model:show="showModal" 
      :title="editingReceptor ? '编辑受体点' : '新增受体点'"
      preset="card"
      style="width: 500px;"
    >
      <n-form :model="formData" label-placement="left" label-width="80">
        <n-form-item label="名称" required>
          <n-input v-model:value="formData.name" placeholder="请输入受体点名称" />
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
          <n-button type="primary" @click="saveReceptor">保存</n-button>
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
