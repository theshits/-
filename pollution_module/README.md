# 污染扩散模拟模块

> 独立、可插拔的空气污染扩散模拟模块，支持快速集成到任何Python项目

---

## 📦 模块结构

```
pollution_module/
├── __init__.py              # 模块入口
├── gaussian_plume.py        # 高斯扩散模型核心算法
├── simulation.py            # 模拟运行接口
├── contribution.py          # 贡献度分析
├── api/                     # API适配器
│   ├── __init__.py
│   ├── common.py            # 通用API逻辑
│   ├── fastapi_adapter.py   # FastAPI适配器
│   └── flask_adapter.py     # Flask适配器
└── static/
    └── pollution-components.js  # 前端可视化组件
```

---

## 🚀 快速开始

### 安装

将 `pollution_module` 文件夹复制到你的项目中。

### 基础用法

```python
from pollution_module import run_simulation

# 定义排放源
sources = [
    {
        'name': '电厂',
        'lat': 39.9,
        'lon': 116.4,
        'height': 100,          # 烟囱高度
        'emission_rate': 50,    # 排放速率
        'flue_temp': 400,       # 烟气温度
        'exit_velocity': 15,    # 出口速度
        'diameter': 2           # 烟囱直径
    }
]

# 定义受体点
receptors = [
    {'name': '监测站A', 'lat': 39.91, 'lon': 116.41},
    {'name': '监测站B', 'lat': 39.92, 'lon': 116.42}
]

# 定义气象条件
meteorology = {
    'wind_speed': 3.0,         # 风速
    'wind_direction': 45,      # 风向 (度)
    'stability_class': 'D',    # 稳定度等级
    'temperature': 293.15,     # 温度 (K)
    'boundary_layer_height': 1000  # 边界层高度
}

# 运行模拟
result = run_simulation(sources, receptors, meteorology)

# 获取结果
print(f"最大浓度: {result.max_concentration} μg/m³")
print(f"贡献度排名: {result.contributions}")
```

---

## 🔌 集成方式

### 方式一：FastAPI 集成

```python
from fastapi import FastAPI
from pollution_module.api import create_fastapi_router

app = FastAPI()

# 添加污染扩散API路由
app.include_router(
    create_fastapi_router(), 
    prefix='/api/pollution'
)
```

**API端点：**
- `POST /api/pollution/simulate` - 运行扩散模拟
- `POST /api/pollution/single-point` - 计算单点浓度
- `POST /api/pollution/contributions` - 计算贡献度
- `GET /api/pollution/stability-classes` - 获取稳定度说明

---

### 方式二：Flask 集成

```python
from flask import Flask
from pollution_module.api import create_flask_blueprint

app = Flask(__name__)

# 注册污染扩散蓝图
app.register_blueprint(
    create_flask_blueprint(), 
    url_prefix='/api/pollution'
)
```

---

### 方式三：Django 集成

在 `urls.py` 中添加：

```python
from django.urls import path
from pollution_module.api.common import run_simulation_api

urlpatterns = [
    path('api/pollution/simulate', lambda r: JsonResponse(
        run_simulation_api(
            sources=r.POST.get('sources'),
            receptors=r.POST.get('receptors'),
            meteorology=r.POST.get('meteorology')
        )
    )),
]
```

---

### 方式四：直接调用（无框架）

```python
from pollution_module import GaussianPlumeModel

# 创建模型实例
model = GaussianPlumeModel(
    wind_speed=3.0,
    wind_direction=45,
    stability_class='D'
)

# 计算单点浓度
concentration = model.calculate_receptor_concentration(
    source_lat=39.9,
    source_lon=116.4,
    source_height=50,
    emission_rate=10,
    receptor_lat=39.91,
    receptor_lon=116.41
)

print(f"浓度: {concentration} μg/m³")
```

---

## 🎨 前端集成

### 引入依赖

```html
<!-- Leaflet 地图 -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<!-- ECharts 图表 (可选) -->
<script src="https://unpkg.com/echarts@5.4.3/dist/echarts.min.js"></script>

<!-- 污染扩散组件 -->
<script src="/static/pollution-components.js"></script>
```

### 使用地图可视化组件

```html
<div id="pollution-map" style="height: 500px;"></div>

<script>
// 初始化可视化组件
const viz = new PollutionVisualization({
    container: 'pollution-map',
    apiBase: '/api/pollution',
    center: { lat: 39.9, lon: 116.4 }
});

// 运行模拟
const sources = [
    { name: '电厂', lat: 39.9, lon: 116.4, height: 100, emission_rate: 50 }
];

const receptors = [
    { name: '站点A', lat: 39.91, lon: 116.41 }
];

const meteorology = {
    wind_speed: 3.0,
    wind_direction: 45,
    stability_class: 'D'
};

viz.runSimulation(sources, receptors, meteorology)
    .then(result => {
        console.log('模拟完成', result);
    });
</script>
```

### 使用风向雷达控件

```html
<canvas id="wind-rose" width="200" height="200"></canvas>

<script>
const windRose = new WindRoseControl('wind-rose', {
    direction: 0,
    speed: 2,
    onChange: (direction, speed) => {
        console.log(`风向: ${direction}°, 风速: ${speed} m/s`);
    }
});
</script>
```

### 使用贡献度图表

```html
<div id="contribution-chart" style="height: 300px;"></div>

<script>
const chart = new ContributionChart('contribution-chart');

// 设置数据
chart.setData([
    { source_name: '电厂', concentration: 15.5, percentage: 45.2 },
    { source_name: '钢厂', concentration: 10.2, percentage: 29.8 },
    { source_name: '化工厂', concentration: 8.6, percentage: 25.0 }
]);
</script>
```

---

## 📊 数据格式

### 排放源

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 源名称 |
| lat | float | 是 | 纬度 |
| lon | float | 是 | 经度 |
| height | float | 否 | 烟囱高度，默认50 |
| emission_rate | float | 否 | 排放速率，默认10 |
| flue_temp | float | 否 | 烟气温度(K)，默认400 |
| exit_velocity | float | 否 | 出口速度，默认10 |
| diameter | float | 否 | 烟囱直径，默认1 |

### 受体点

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 否 | 受体点名称 |
| lat | float | 是 | 纬度 |
| lon | float | 是 | 经度 |
| height | float | 否 | 受体高度，默认0 |

### 气象条件

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| wind_speed | float | 是 | 风速 |
| wind_direction | float | 是 | 风向 (度, 0=北) |
| stability_class | string | 否 | 稳定度等级 A-F，默认D |
| temperature | float | 否 | 温度(K)，默认293.15 |
| boundary_layer_height | float | 否 | 边界层高度，默认1000 |

---

## 🌤️ 稳定度等级

| 等级 | 描述 | 适用条件 |
|------|------|----------|
| A | 极不稳定 | 强日照、弱风 |
| B | 不稳定 | 中等日照 |
| C | 弱不稳定 | 弱日照 |
| D | 中性 | 阴天或夜间 |
| E | 弱稳定 | 夜间弱风 |
| F | 稳定 | 晴朗夜间微风 |

---

## 📐 核心算法

### 高斯烟羽方程

```
C(x,y,z) = Q/(2π·u·σy·σz) · exp[-y²/(2σy²)] · {exp[-(z-H)²/(2σz²)] + exp[-(z+H)²/(2σz²)]}
```

其中：
- C: 地面浓度 (μg/m³)
- Q: 排放速率
- u: 风速
- σy, σz: 扩散参数 (Pasquill-Gifford)
- H: 有效烟囱高度

---

## 📋 完整示例

```python
# example.py
from pollution_module import run_simulation, GaussianPlumeModel, StabilityClassifier

# 示例1: 完整模拟
sources = [
    {'name': '电厂', 'lat': 39.9, 'lon': 116.4, 'height': 100, 'emission_rate': 50},
    {'name': '钢厂', 'lat': 39.91, 'lon': 116.42, 'height': 80, 'emission_rate': 30}
]

receptors = [
    {'name': '站点A', 'lat': 39.905, 'lon': 116.41},
    {'name': '站点B', 'lat': 39.915, 'lon': 116.43}
]

meteorology = {
    'wind_speed': 3.0,
    'wind_direction': 45,
    'stability_class': 'D'
}

result = run_simulation(sources, receptors, meteorology)

print("=== 模拟结果 ===")
print(f"最大浓度: {result.max_concentration:.2f} μg/m³")
print("\n=== 源贡献度 ===")
for c in result.contributions:
    print(f"  {c.source_name}: {c.percentage:.1f}%")

print("\n=== 受体点分析 ===")
for rc in result.receptor_contributions:
    print(f"\n{rc.receptor_name} (总浓度: {rc.total_concentration:.2f}):")
    for sc in rc.source_contributions[:3]:
        print(f"  {sc.source_name}: {sc.percentage:.1f}%")

# 示例2: 单点计算
model = GaussianPlumeModel(wind_speed=3.0, wind_direction=45, stability_class='D')
conc = model.calculate_receptor_concentration(
    source_lat=39.9, source_lon=116.4,
    source_height=50, emission_rate=10,
    receptor_lat=39.91, receptor_lon=116.41
)
print(f"\n单点浓度: {conc:.4f} μg/m³")

# 示例3: 自动确定稳定度
stability = StabilityClassifier.classify(
    wind_speed=3.0,
    solar_radiation=500,
    is_daytime=True
)
print(f"\n自动稳定度: {stability} - {StabilityClassifier.get_description(stability)}")
```

---

## 🔧 依赖

### Python后端
- 无外部依赖（仅使用Python标准库）

### 前端组件
- Leaflet (地图)
- ECharts (图表，可选)

---

## 📞 技术支持

如有问题，请参考源码注释或联系开发团队。
