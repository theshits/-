# GNN-based NO2 Inversion Model

基于图神经网络(GNN)的NO2反演模型，利用TROPOMI卫星数据、地面站点数据和气象数据，通过气象传输边构建图结构，实现NO2浓度的反演预测。

## 项目结构

```
gnn/
├── config.py              # 配置文件加载器
├── config.yaml            # 模型和训练配置
├── data_processor.py      # TROPOMI数据处理
├── station_processor.py   # 地面站点和气象站点数据处理
├── data_integrator.py     # 数据集成和特征提取
├── graph_builder.py       # 基于气象传输的图构建
├── gnn_model.py          # GNN模型架构
├── trainer.py            # 训练和评估模块
├── main.py               # 主程序入口
├── prepare_data.py       # 生成示例数据
└── requirements.txt      # 依赖包列表
```

## 核心功能

### 1. 数据预处理
- **TROPOMI数据处理**: 加载NetCDF格式的TROPOMI NO2数据，进行质量筛选和特征提取
- **地面站点数据处理**: 处理地面NO2观测数据，支持时间重采样
- **气象站点数据处理**: 处理风速、风向、温度、湿度等气象数据，计算风矢量分量

### 2. 数据集成
- 空间网格化处理
- 多源数据时空匹配
- 节点特征和标签生成

### 3. 图构建
- **K近邻边**: 基于空间距离构建边
- **气象传输边**: 利用风速风向计算传输权重
- **时序边**: 构建时间维度上的连接

### 4. GNN模型
- **WeatherTransportGNN**: 结合GAT和GCN的混合模型
- **EdgeWeightedGNN**: 基于边权重的图卷积
- **SpatialTemporalGNN**: 时空图神经网络

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 准备数据

#### 使用示例数据
```bash
python prepare_data.py
```

#### 使用自己的数据
将数据文件放入对应目录:
- TROPOMI数据: `data/tropomi/` (NetCDF格式)
- 地面站点数据: `data/ground/` (CSV格式)
- 气象站点数据: `data/weather/` (CSV格式)

### 2. 训练模型

```bash
python main.py --mode train --config config.yaml --model_path models/best_model.pt
```

### 3. 评估模型

```bash
python main.py --mode evaluate --config config.yaml --model_path models/best_model.pt
```

### 4. 预测

```bash
python main.py --mode predict --config config.yaml --model_path models/best_model.pt
```

## 配置说明

在`config.yaml`中可以调整以下参数:

### 模型配置
- `model.name`: 模型类型 (WeatherTransportGNN, EdgeWeightedGNN, SpatialTemporalGNN)
- `model.hidden_dim`: 隐藏层维度
- `model.num_layers`: 网络层数
- `model.dropout`: Dropout比例
- `model.num_heads`: 注意力头数

### 数据配置
- `data.tropomi_path`: TROPOMI数据路径
- `data.ground_path`: 地面站点数据路径
- `data.weather_path`: 气象站点数据路径
- `data.spatial_resolution`: 空间分辨率(度)
- `data.time_resolution`: 时间分辨率

### 图配置
- `graph.edge_type`: 边类型
- `graph.k_neighbors`: K近邻数
- `graph.max_distance`: 最大距离(km)
- `graph.wind_weight`: 是否使用风权重
- `graph.temporal_window`: 时间窗口(小时)

### 训练配置
- `training.batch_size`: 批次大小
- `training.learning_rate`: 学习率
- `training.num_epochs`: 训练轮数
- `training.early_stopping_patience`: 早停耐心值
- `training.train_ratio`: 训练集比例
- `training.val_ratio`: 验证集比例
- `training.test_ratio`: 测试集比例

## 数据格式要求

### TROPOMI数据 (NetCDF)
必须包含以下变量:
- `latitude`: 纬度
- `longitude`: 经度
- `time`: 时间
- `nitrogendioxide_tropospheric_column` 或 `no2_tropospheric_column`: NO2柱浓度
- `qa_value`: 质量标识

### 地面站点数据 (CSV)
必须包含以下列:
- `latitude`: 纬度
- `longitude`: 经度
- `time` 或 `datetime`: 时间
- `no2` 或 `NO2`: NO2浓度

### 气象站点数据 (CSV)
建议包含以下列:
- `latitude`: 纬度
- `longitude`: 经度
- `time` 或 `datetime`: 时间
- `wind_speed` 或 `ws`: 风速
- `wind_direction` 或 `wd`: 风向
- `temperature` 或 `t2m`: 温度
- `humidity` 或 `rh`: 湿度
- `pressure` 或 `ps`: 气压

## 模型评估指标

- **RMSE**: 均方根误差
- **MAE**: 平均绝对误差
- **R2**: 决定系数
- **Bias**: 偏差

## 核心算法说明

### 气象传输边权重计算

基于风速和风向计算节点间的传输权重:

```
W = wind_speed * max(0, cos(θ)) / distance
```

其中:
- `wind_speed`: 风速
- `θ`: 风向与节点间连线的夹角
- `distance`: 节点间距离

### GNN模型架构

模型结合了图注意力网络(GAT)和图卷积网络(GCN):

1. **输入投影层**: 将原始特征投影到隐藏维度
2. **GAT层**: 使用注意力机制学习节点间关系
3. **GCN层**: 使用图卷积聚合邻居信息
4. **融合层**: 融合GAT和GCN的输出
5. **输出层**: 预测NO2浓度

## 输出结果

训练完成后会生成:
- `models/best_model.pt`: 最佳模型权重
- `predictions/predictions.csv`: 预测结果(包含经纬度、预测值和真实值)

## 注意事项

1. 确保数据文件路径正确
2. 根据实际数据调整配置参数
3. 训练前建议先使用示例数据测试流程
4. 如有GPU，模型会自动使用GPU加速

## 参考文献

- TROPOMI NO2数据产品文档
- 图神经网络在环境科学中的应用