"""
污染扩散模拟模块
===============

独立、可插拔的空气污染扩散模拟模块
支持高斯烟羽模型，可集成到任何Python项目

使用示例:
    from pollution_module import GaussianPlumeModel, run_simulation
    
    # 方式1: 直接使用模型类
    model = GaussianPlumeModel(
        wind_speed=3.0,
        wind_direction=45,
        stability_class='D'
    )
    concentration = model.calculate_concentration(x=1000, y=0, z=0, source_height=50, emission_rate=10)
    
    # 方式2: 一键运行模拟
    result = run_simulation(
        sources=[{'lat': 39.9, 'lon': 116.4, 'height': 50, 'emission_rate': 10}],
        receptors=[{'lat': 39.91, 'lon': 116.41}],
        meteorology={'wind_speed': 3.0, 'wind_direction': 45, 'stability_class': 'D'}
    )
"""

from .gaussian_plume import GaussianPlumeModel, StabilityClassifier
from .simulation import run_simulation, SimulationResult
from .contribution import calculate_contributions

__version__ = '1.0.0'
__all__ = [
    'GaussianPlumeModel',
    'StabilityClassifier', 
    'run_simulation',
    'SimulationResult',
    'calculate_contributions'
]
