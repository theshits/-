"""
高斯烟羽扩散模型
===============

基于稳态高斯烟羽方程计算污染物浓度分布
支持Pasquill-Gifford稳定度分类

核心公式:
    C(x,y,z) = Q/(2π·u·σy·σz) · exp[-y²/(2σy²)] · {exp[-(z-H)²/(2σz²)] + exp[-(z+H)²/(2σz²)]}

参数说明:
    C: 地面浓度 (μg/m³)
    Q: 排放速率 (g/s)
    u: 风速
    σy, σz: 扩散参数
    H: 有效烟囱高度
"""

import math
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class PlumeResult:
    """单点浓度计算结果"""
    concentration: float
    x: float
    y: float
    z: float
    sigma_y: float
    sigma_z: float


class GaussianPlumeModel:
    """
    高斯烟羽扩散模型
    
    使用方法:
        model = GaussianPlumeModel(
            wind_speed=3.0,
            wind_direction=45,
            stability_class='D'
        )
        
        # 计算单点浓度
        conc = model.calculate_concentration(
            x=1000, y=0, z=0,
            source_height=50,
            emission_rate=10
        )
        
        # 计算网格浓度场
        grid = model.calculate_grid_concentration(
            source_lat=39.9, source_lon=116.4,
            source_height=50, emission_rate=10,
            grid_bounds=(39.85, 39.95, 116.35, 116.45),
            grid_size=50
        )
    """
    
    PASQUILL_GIFFORD_PARAMS = {
        'A': {'ay': 0.527, 'by': 0.865, 'az': 0.28, 'bz': 0.90},
        'B': {'ay': 0.371, 'by': 0.866, 'az': 0.23, 'bz': 0.85},
        'C': {'ay': 0.209, 'by': 0.897, 'az': 0.22, 'bz': 0.80},
        'D': {'ay': 0.128, 'by': 0.905, 'az': 0.20, 'bz': 0.76},
        'E': {'ay': 0.098, 'by': 0.902, 'az': 0.15, 'bz': 0.73},
        'F': {'ay': 0.065, 'by': 0.902, 'az': 0.12, 'bz': 0.67}
    }
    
    def __init__(
        self,
        wind_speed: float,
        wind_direction: float,
        stability_class: str = 'D',
        temperature: float = 293.15,
        boundary_layer_height: float = 1000.0
    ):
        """
        初始化高斯烟羽模型
        
        Args:
            wind_speed: 风速
            wind_direction: 风向 (度, 气象风向, 风来自的方向, 北为0度顺时针)
            stability_class: 大气稳定度等级
            temperature: 环境温度 (K)
            boundary_layer_height: 边界层高度
        """
        self.wind_speed = max(wind_speed, 0.1)
        self.wind_direction = wind_direction % 360
        self.stability_class = stability_class.upper()
        self.temperature = temperature
        self.boundary_layer_height = boundary_layer_height
        
        if self.stability_class not in self.PASQUILL_GIFFORD_PARAMS:
            raise ValueError(f"无效的稳定度等级: {stability_class}, 有效值: A-F")
    
    def calculate_sigma(self, distance: float) -> Tuple[float, float]:
        """
        计算扩散参数 σy 和 σz (Pasquill-Gifford公式)
        
        Args:
            distance: 下风向距离
        
        Returns:
            (σy, σz): 横向和垂直扩散参数
        """
        params = self.PASQUILL_GIFFORD_PARAMS[self.stability_class]
        
        sigma_y = params['ay'] * (distance ** params['by'])
        sigma_z = params['az'] * (distance ** params['bz'])
        
        sigma_y = max(sigma_y, 1.0)
        sigma_z = max(sigma_z, 1.0)
        sigma_z = min(sigma_z, self.boundary_layer_height * 0.8)
        
        return sigma_y, sigma_z
    
    def calculate_effective_height(
        self,
        stack_height: float,
        emission_rate: float,
        flue_temp: float,
        exit_velocity: float,
        diameter: float
    ) -> float:
        """
        计算有效烟囱高度 (H = h + Δh)
        
        包括烟囱物理高度和烟气抬升高度
        
        Args:
            stack_height: 烟囱物理高度
            emission_rate: 排放速率
            flue_temp: 烟气温度 (K)
            exit_velocity: 烟气出口速度
            diameter: 烟囱直径
        
        Returns:
            有效烟囱高度
        """
        delta_T = flue_temp - self.temperature
        
        if delta_T <= 0:
            return stack_height
        
        g = 9.81
        F_b = g * exit_velocity * (diameter ** 2) / 4 * delta_T / self.temperature
        
        if F_b > 0:
            delta_h = 1.6 * (F_b ** (1/3)) * (self.wind_speed ** (-1)) * (stack_height ** (2/3))
        else:
            delta_h = 0
        
        F_m = exit_velocity * (diameter ** 2) / 4 * exit_velocity
        delta_h_momentum = 3 * diameter * exit_velocity / self.wind_speed
        delta_h = max(delta_h, delta_h_momentum)
        
        return stack_height + delta_h
    
    def calculate_concentration(
        self,
        x: float,
        y: float,
        z: float,
        source_height: float,
        emission_rate: float,
        effective_height: Optional[float] = None,
        flue_temp: float = 400.0,
        exit_velocity: float = 10.0,
        diameter: float = 1.0
    ) -> float:
        """
        计算单点浓度
        
        高斯烟羽方程:
        C = Q/(2π·u·σy·σz) · exp[-y²/(2σy²)] · {exp[-(z-H)²/(2σz²)] + exp[-(z+H)²/(2σz²)]}
        
        Args:
            x: 下风向距离
            y: 横风向距离
            z: 计算点高度
            source_height: 源高度
            emission_rate: 排放速率
            effective_height: 有效高度 (可选, 自动计算)
            flue_temp: 烟气温度 (K)
            exit_velocity: 烟气出口速度
            diameter: 烟囱直径
        
        Returns:
            浓度 (μg/m³)
        """
        if x <= 0:
            return 0.0
        
        sigma_y, sigma_z = self.calculate_sigma(x)
        
        if effective_height is None:
            effective_height = self.calculate_effective_height(
                source_height, emission_rate, flue_temp, exit_velocity, diameter
            )
        
        H = effective_height
        
        term1 = emission_rate / (2 * math.pi * self.wind_speed * sigma_y * sigma_z)
        
        term2 = math.exp(-y**2 / (2 * sigma_y**2))
        
        term3 = math.exp(-(z - H)**2 / (2 * sigma_z**2)) + math.exp(-(z + H)**2 / (2 * sigma_z**2))
        
        concentration = term1 * term2 * term3
        
        return concentration
    
    def calculate_receptor_concentration(
        self,
        source_lat: float,
        source_lon: float,
        source_height: float,
        emission_rate: float,
        receptor_lat: float,
        receptor_lon: float,
        receptor_height: float = 0.0,
        flue_temp: float = 400.0,
        exit_velocity: float = 10.0,
        diameter: float = 1.0
    ) -> float:
        """
        计算单个受体点的浓度 (经纬度坐标)
        
        Args:
            source_lat: 源纬度
            source_lon: 源经度
            source_height: 源高度
            emission_rate: 排放速率
            receptor_lat: 受体纬度
            receptor_lon: 受体经度
            receptor_height: 受体高度
            flue_temp: 烟气温度 (K)
            exit_velocity: 烟气出口速度
            diameter: 烟囱直径
        
        Returns:
            浓度 (μg/m³)
        """
        effective_height = self.calculate_effective_height(
            source_height, emission_rate, flue_temp, exit_velocity, diameter
        )
        
        wind_angle = math.radians(270 - self.wind_direction)
        
        lat_to_m = 111000
        lon_to_m = 111000 * math.cos(math.radians(source_lat))
        
        dy_lat = (receptor_lat - source_lat) * lat_to_m
        dx_lon = (receptor_lon - source_lon) * lon_to_m
        
        x_rotated = dx_lon * math.cos(wind_angle) + dy_lat * math.sin(wind_angle)
        y_rotated = -dx_lon * math.sin(wind_angle) + dy_lat * math.cos(wind_angle)
        
        if x_rotated <= 0:
            return 0.0
        
        return self.calculate_concentration(
            x=x_rotated,
            y=y_rotated,
            z=receptor_height,
            source_height=source_height,
            emission_rate=emission_rate,
            effective_height=effective_height
        )
    
    def calculate_grid_concentration(
        self,
        source_lat: float,
        source_lon: float,
        source_height: float,
        emission_rate: float,
        grid_bounds: Tuple[float, float, float, float],
        grid_size: int = 50,
        flue_temp: float = 400.0,
        exit_velocity: float = 10.0,
        diameter: float = 1.0
    ) -> Dict[str, Any]:
        """
        计算网格浓度场
        
        Args:
            source_lat: 源纬度
            source_lon: 源经度
            source_height: 源高度
            emission_rate: 排放速率
            grid_bounds: 网格边界
            grid_size: 网格点数
            flue_temp: 烟气温度 (K)
            exit_velocity: 烟气出口速度
            diameter: 烟囱直径
        
        Returns:
            {
                'concentrations': 二维浓度数组,
                'lat_grid': 纬度网格,
                'lon_grid': 经度网格,
                'max_concentration': 最大浓度,
                'total_mass': 总质量
            }
        """
        lat_min, lat_max, lon_min, lon_max = grid_bounds
        
        lat_step = (lat_max - lat_min) / (grid_size - 1)
        lon_step = (lon_max - lon_min) / (grid_size - 1)
        
        concentrations = [[0.0] * grid_size for _ in range(grid_size)]
        lat_grid = [lat_min + i * lat_step for i in range(grid_size)]
        lon_grid = [lon_min + j * lon_step for j in range(grid_size)]
        
        effective_height = self.calculate_effective_height(
            source_height, emission_rate, flue_temp, exit_velocity, diameter
        )
        
        for i, lat in enumerate(lat_grid):
            for j, lon in enumerate(lon_grid):
                concentrations[i][j] = self.calculate_receptor_concentration(
                    source_lat=source_lat,
                    source_lon=source_lon,
                    source_height=source_height,
                    emission_rate=emission_rate,
                    receptor_lat=lat,
                    receptor_lon=lon,
                    effective_height=effective_height
                )
        
        flat_conc = [c for row in concentrations for c in row]
        
        return {
            'concentrations': concentrations,
            'lat_grid': lat_grid,
            'lon_grid': lon_grid,
            'max_concentration': max(flat_conc),
            'total_mass': sum(flat_conc)
        }


class StabilityClassifier:
    """
    大气稳定度分类器
    
    基于风速和太阳辐射/云量确定Pasquill稳定度等级
    """
    
    @staticmethod
    def classify(
        wind_speed: float,
        solar_radiation: Optional[float] = None,
        cloud_cover: Optional[float] = None,
        is_daytime: bool = True
    ) -> str:
        """
        确定大气稳定度等级
        
        Args:
            wind_speed: 风速
            solar_radiation: 太阳辐射强度 (W/m²)
            cloud_cover: 云量 (0-1)
            is_daytime: 是否白天
        
        Returns:
            稳定度等级 (A-F)
        """
        if solar_radiation is not None:
            if solar_radiation > 700:
                insolation = 'strong'
            elif solar_radiation > 350:
                insolation = 'moderate'
            else:
                insolation = 'slight'
            
            if wind_speed < 2:
                if insolation == 'strong':
                    return 'A'
                elif insolation == 'moderate':
                    return 'A-B'
                else:
                    return 'B'
            elif wind_speed < 3:
                if insolation == 'strong':
                    return 'A-B'
                elif insolation == 'moderate':
                    return 'B'
                else:
                    return 'C'
            elif wind_speed < 5:
                if insolation == 'strong':
                    return 'B'
                elif insolation == 'moderate':
                    return 'B-C'
                else:
                    return 'C'
            elif wind_speed < 6:
                if insolation == 'strong':
                    return 'C'
                else:
                    return 'C-D'
            else:
                return 'D'
        
        elif cloud_cover is not None:
            if is_daytime:
                if cloud_cover < 0.3:
                    insolation = 'strong'
                elif cloud_cover < 0.7:
                    insolation = 'moderate'
                else:
                    insolation = 'slight'
                
                return StabilityClassifier.classify(wind_speed, solar_radiation=None, 
                                                    cloud_cover=cloud_cover, is_daytime=is_daytime)
            else:
                if cloud_cover < 0.3:
                    return 'F'
                elif cloud_cover < 0.7:
                    return 'E'
                else:
                    return 'D'
        
        else:
            return 'D'
    
    @staticmethod
    def get_description(stability_class: str) -> str:
        """获取稳定度等级描述"""
        descriptions = {
            'A': '极不稳定 - 强对流，强日照弱风',
            'B': '不稳定 - 中等日照',
            'C': '弱不稳定 - 弱日照',
            'D': '中性 - 阴天或夜间中等风速',
            'E': '弱稳定 - 夜间弱风',
            'F': '稳定 - 晴朗夜间微风'
        }
        return descriptions.get(stability_class.upper(), '未知')
