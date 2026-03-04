<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NConfigProvider, NLayout, NLayoutSider, NLayoutContent, NMenu, NIcon } from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import {
  MapOutline,
  LocationOutline,
  FlagOutline,
  CloudOutline
} from '@vicons/ionicons5'

const router = useRouter()
const route = useRoute()
const collapsed = ref(false)

const renderIcon = (icon: any) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  {
    label: '主界面',
    key: '/',
    icon: renderIcon(MapOutline)
  },
  {
    label: '排放源管理',
    key: '/sources',
    icon: renderIcon(LocationOutline)
  },
  {
    label: '受体点管理',
    key: '/receptors',
    icon: renderIcon(FlagOutline)
  },
  {
    label: '气象场管理',
    key: '/meteorology',
    icon: renderIcon(CloudOutline)
  }
]

const activeKey = computed(() => route.path)

const handleMenuClick = (key: string) => {
  router.push(key)
}
</script>

<template>
  <n-config-provider>
    <n-layout has-sider style="height: 100vh;">
      <n-layout-sider
        bordered
        collapse-mode="width"
        :collapsed-width="64"
        :width="220"
        :collapsed="collapsed"
        show-trigger
        @collapse="collapsed = true"
        @expand="collapsed = false"
        style="background: var(--bg-primary);"
      >
        <div class="logo-container">
          <div class="logo-icon">🌬️</div>
          <span v-if="!collapsed" class="logo-text">污染扩散模拟</span>
        </div>
        <n-menu
          :value="activeKey"
          :collapsed="collapsed"
          :collapsed-width="64"
          :collapsed-icon-size="22"
          :options="menuOptions"
          @update:value="handleMenuClick"
        />
      </n-layout-sider>
      <n-layout-content style="background: var(--bg-secondary);">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-config-provider>
</template>

<style scoped>
.logo-container {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 8px;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
}
</style>
