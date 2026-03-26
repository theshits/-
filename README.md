# 大气污染扩散模拟系统

基于高斯烟羽模型的大气污染扩散模拟系统，支持点源、面源、线源和等效面源的扩散计算。

## 功能特性

- **排放源管理**：支持点源、面源、线源、等效面源四种排放源类型
- **气象条件管理**：支持风向、风速、大气稳定度等气象参数配置
- **受体点管理**：支持添加多个受体点，并设置高度参数
- **扩散模拟**：
  - 单一风向模拟
  - 全局模拟（支持8/16/32/64风向加权组合）
- **结果展示**：
  - 浓度场热力图
  - 受体点浓度贡献分析
  - 污染物浓度分布

## 技术架构

- **后端**：FastAPI + SQLAlchemy
- **前端**：HTML + JavaScript + Leaflet地图
- **核心算法**：高斯烟羽扩散模型

## 项目结构

```
gnn/
├── backend/               # 后端代码
│   ├── api/               # API接口
│   │   ├── sources.py     # 排放源管理
│   │   ├── receptors.py   # 受体点管理
│   │   ├── meteorology.py # 气象条件管理
│   │   ├── simulation.py  # 模拟计算
│   │   └── map.py         # 地图服务
│   ├── core/              # 核心算法
│   │   └── gaussian_plume.py  # 高斯扩散模型
│   ├── models/            # 数据模型
│   │   ├── models.py      # 数据库模型
│   │   └── schemas.py     # Pydantic模型
│   ├── templates/         # HTML模板
│   ├── main.py            # 应用入口
│   ├── database.py        # 数据库配置
│   └── requirements.txt   # Python依赖
├── shp/                   # 地图边界数据
├── start_server.bat       # 启动服务器脚本
├── stop_server.bat        # 关闭服务器脚本
└── README.md
```

## 快速开始

### 环境要求

- Python 3.10+
- pip

### 安装步骤

1. **克隆项目**
```bash
git clone <项目地址>
cd gnn
```

2. **安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

3. **启动服务器**

双击运行 `start_server.bat` 或在终端执行：
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

4. **访问系统**

打开浏览器访问：http://localhost:8080

### 关闭服务器

双击运行 `stop_server.bat` 或在运行服务器的终端按 `Ctrl + C`

## 使用说明

### 1. 排放源管理

- 支持新增、编辑、删除排放源
- 支持批量导入/导出排放源
- 支持四种排放源类型：
  - **点源**：烟囱等点状排放源
  - **面源**：厂房、堆场等面状排放源
  - **线源**：道路等线状排放源
  - **等效面源**：已知浓度的监测点，系统自动计算等效排放速率

### 2. 气象条件

- 设置风向（0-360度）
- 设置风速（m/s）
- 选择大气稳定度（A-F）

### 3. 受体点管理

- 添加监测受体点
- 设置受体点位置和高度
- 查看各排放源对受体点的浓度贡献

### 4. 扩散模拟

- **单一风向模拟**：选择特定气象条件进行模拟
- **全局模拟**：设置多个风向风速组合及权重，进行加权模拟

## 高斯扩散模型

系统采用高斯烟羽模型进行污染物扩散计算：

$$C(x,y,z) = \frac{Q}{2\pi u \sigma_y \sigma_z} \exp\left(-\frac{y^2}{2\sigma_y^2}\right) \left[\exp\left(-\frac{(z-H)^2}{2\sigma_z^2}\right) + \exp\left(-\frac{(z+H)^2}{2\sigma_z^2}\right)\right]$$

其中：
- C：浓度 (μg/m³)
- Q：排放速率 (g/s)
- u：风速 (m/s)
- σy, σz：水平和垂直扩散参数
- H：有效源高度 (m)

## 依赖说明

```
fastapi>=0.104.0      # Web框架
uvicorn>=0.24.0       # ASGI服务器
sqlalchemy>=2.0.0     # ORM
pydantic>=2.0.0       # 数据验证
numpy>=1.24.0         # 数值计算
scipy>=1.10.0         # 科学计算
python-multipart>=0.0.6  # 文件上传
jinja2>=3.0.0         # 模板引擎
geopandas>=0.14.0     # 地理数据处理
pyproj>=3.6.0         # 坐标转换
shapely>=2.0.0        # 几何操作
```

## 许可证

MIT License
