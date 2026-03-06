import numpy as np
from typing import Tuple, Optional
import math

class GaussianPlumeModel:
    """
    高斯烟羽扩散模型
    
    基于稳态高斯烟羽方程计算地面浓度分布
    支持Pasquill-Gifford稳定度分类
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
            wind_direction: 风向 (度, 气象风向, 风来自的方向)
            stability_class: 大气稳定度等级
            temperature: 环境温度 (K)
            boundary_layer_height: 边界层高度
        """
        self.wind_speed = max(wind_speed, 0.1)
        self.wind_direction = wind_direction
        self.stability_class = stability_class.upper()
        self.temperature = temperature
        self.boundary_layer_height = boundary_layer_height
        
        if self.stability_class not in self.PASQUILL_GIFFORD_PARAMS:
            raise ValueError(f"无效的稳定度等级: {stability_class}")
    
    def calculate_sigma(self, distance: float) -> Tuple[float, float]:
        """
        计算扩散参数 σy 和 σz
        
        使用Pasquill-Gifford经验公式
        
        Args:
            distance: 下风向距离
        
        Returns:
            (σy, σz): 横向和垂直扩散参数
        """
        params = self.PASQUILL_GIFFORD_PARAMS[self.stability_class]
        
        sigma_y = params['ay'] * (distance ** params['by'])
        sigma_z = params['az'] * (distance ** params['bz'])
        
        sigma_z = min(sigma_z, self.boundary_layer_height * 0.8)
        
        return sigma_y, sigma_z
    
    def calculate_effective_height(
        self,
        stack_height: float,
        emission_rate: float,
        temperature: float,
        velocity: float,
        diameter: float
    ) -> float:
        """
        计算有效烟囱高度
        
        包括烟囱物理高度和烟气抬升高度
        
        Args:
            stack_height: 烟囱物理高度
            emission_rate: 排放速率
            temperature: 烟气温度 (K)
            velocity: 烟气出口速度
            diameter: 烟囱直径
        
        Returns:
            有效烟囱高度
        """
        delta_T = temperature - self.temperature
        
        buoyancy_flux = 9.81 * velocity * (diameter ** 2) / 4 * delta_T / self.temperature
        
        momentum_flux = velocity * (diameter ** 2) / 4 * velocity
        
        if buoyancy_flux > 0:
            delta_h = 1.6 * (buoyancy_flux ** (1/3)) * (self.wind_speed ** (-1)) * (stack_height ** (2/3))
        else:
            delta_h = 0
        
        momentum_rise = 3 * diameter * velocity / self.wind_speed
        delta_h = max(delta_h, momentum_rise)
        
        return stack_height + delta_h
    
    def calculate_concentration(
        self,
        x: float,
        y: float,
        z: float,
        source_height: float,
        emission_rate: float,
        effective_height: Optional[float] = None
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
        
        Returns:
            浓度 (μg/m³)
        """
        if x <= 0:
            return 0.0
        
        sigma_y, sigma_z = self.calculate_sigma(x)
        
        if effective_height is None:
            effective_height = source_height
        
        H = effective_height
        
        emission_rate_ug = emission_rate * 1e6
        
        term1 = emission_rate_ug / (2 * np.pi * self.wind_speed * sigma_y * sigma_z)
        
        term2 = np.exp(-y**2 / (2 * sigma_y**2))
        
        term3 = np.exp(-(z - H)**2 / (2 * sigma_z**2)) + np.exp(-(z + H)**2 / (2 * sigma_z**2))
        
        concentration = term1 * term2 * term3
        
        return concentration
    
    def calculate_concentration_field(
        self,
        source_lat: float,
        source_lon: float,
        source_height: float,
        emission_rate: float,
        grid_lat: np.ndarray,
        grid_lon: np.ndarray,
        temperature: float = 400.0,
        velocity: float = 10.0,
        diameter: float = 1.0,
        receptor_height: float = 0.0
    ) -> np.ndarray:
        """
        计算网格浓度场
        
        Args:
            source_lat: 源纬度
            source_lon: 源经度
            source_height: 源高度
            emission_rate: 排放速率
            grid_lat: 网格纬度数组
            grid_lon: 网格经度数组
            temperature: 烟气温度 (K)
            velocity: 烟气出口速度
            diameter: 烟囱直径
            receptor_height: 受体高度
        
        Returns:
            浓度场 (μg/m³)
        """
        effective_height = self.calculate_effective_height(
            source_height, emission_rate, temperature, velocity, diameter
        )
        
        wind_angle = np.radians(270 - self.wind_direction)
        
        lat_to_m = 111000
        lon_to_m = 111000 * np.cos(np.radians(source_lat))
        
        concentration_field = np.zeros((len(grid_lat), len(grid_lon)))
        
        for i, lat in enumerate(grid_lat):
            for j, lon in enumerate(grid_lon):
                dy_lat = (lat - source_lat) * lat_to_m
                dx_lon = (lon - source_lon) * lon_to_m
                
                x_rotated = dx_lon * np.cos(wind_angle) + dy_lat * np.sin(wind_angle)
                y_rotated = -dx_lon * np.sin(wind_angle) + dy_lat * np.cos(wind_angle)
                
                if x_rotated > 0:
                    concentration_field[i, j] = self.calculate_concentration(
                        x=x_rotated,
                        y=y_rotated,
                        z=receptor_height,
                        source_height=source_height,
                        emission_rate=emission_rate,
                        effective_height=effective_height
                    )
        
        return concentration_field
    
    def calculate_receptor_concentration(
        self,
        source_lat: float,
        source_lon: float,
        source_height: float,
        emission_rate: float,
        receptor_lat: float,
        receptor_lon: float,
        receptor_height: float = 0.0,
        temperature: float = 400.0,
        velocity: float = 10.0,
        diameter: float = 1.0
    ) -> float:
        """
        计算单个受体点的浓度
        
        Args:
            source_lat: 源纬度
            source_lon: 源经度
            source_height: 源高度
            emission_rate: 排放速率
            receptor_lat: 受体纬度
            receptor_lon: 受体经度
            receptor_height: 受体高度
            temperature: 烟气温度 (K)
            velocity: 烟气出口速度
            diameter: 烟囱直径
        
        Returns:
            浓度 (μg/m³)
        """
        effective_height = self.calculate_effective_height(
            source_height, emission_rate, temperature, velocity, diameter
        )
        
        wind_angle = np.radians(270 - self.wind_direction)
        
        lat_to_m = 111000
        lon_to_m = 111000 * np.cos(np.radians(source_lat))
        
        dy_lat = (receptor_lat - source_lat) * lat_to_m
        dx_lon = (receptor_lon - source_lon) * lon_to_m
        
        x_rotated = dx_lon * np.cos(wind_angle) + dy_lat * np.sin(wind_angle)
        y_rotated = -dx_lon * np.sin(wind_angle) + dy_lat * np.cos(wind_angle)
        
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
    
    def calculate_area_source_concentration_field(
        self,
        center_lat: float,
        center_lon: float,
        area_length: float,
        area_width: float,
        area_height: float,
        emission_rate: float,
        grid_lat: np.ndarray,
        grid_lon: np.ndarray,
        sigma_z0: Optional[float] = None,
        receptor_height: float = 0.0
    ) -> np.ndarray:
        """
        计算矩形面源浓度场（虚拟点源法）
        
        Args:
            center_lat: 面源中心纬度
            center_lon: 面源中心经度
            area_length: 面源长度
            area_width: 面源宽度
            area_height: 面源高度
            emission_rate: 总排放速率
            grid_lat: 网格纬度数组
            grid_lon: 网格经度数组
            sigma_z0: 初始垂直扩散参数 (可选, 自动计算)
            receptor_height: 受体高度
        
        Returns:
            浓度场 (μg/m³)
        """
        sigma_y0 = area_width / 4.3
        if sigma_z0 is None:
            sigma_z0 = area_height / 2.15 if area_height > 0 else 1.0
        
        params = self.PASQUILL_GIFFORD_PARAMS[self.stability_class]
        
        x_virtual_y = (sigma_y0 / params['ay']) ** (1 / params['by']) if params['ay'] > 0 else 0
        x_virtual_z = (sigma_z0 / params['az']) ** (1 / params['bz']) if params['az'] > 0 else 0
        x_virtual = max(x_virtual_y, x_virtual_z)
        
        wind_angle = np.radians(270 - self.wind_direction)
        
        lat_to_m = 111000
        lon_to_m = 111000 * np.cos(np.radians(center_lat))
        
        concentration_field = np.zeros((len(grid_lat), len(grid_lon)))
        
        for i, lat in enumerate(grid_lat):
            for j, lon in enumerate(grid_lon):
                dy_lat = (lat - center_lat) * lat_to_m
                dx_lon = (lon - center_lon) * lon_to_m
                
                x_rotated = dx_lon * np.cos(wind_angle) + dy_lat * np.sin(wind_angle)
                y_rotated = -dx_lon * np.sin(wind_angle) + dy_lat * np.cos(wind_angle)
                
                x_eff = x_rotated + x_virtual
                
                if x_eff > 0:
                    sigma_y, sigma_z = self.calculate_sigma(x_eff)
                    sigma_y_eff = np.sqrt(sigma_y**2 - sigma_y0**2) if sigma_y > sigma_y0 else sigma_y
                    sigma_z_eff = np.sqrt(sigma_z**2 - sigma_z0**2) if sigma_z > sigma_z0 else sigma_z
                    
                    emission_rate_ug = emission_rate * 1e6
                    
                    H = area_height
                    
                    term1 = emission_rate_ug / (2 * np.pi * self.wind_speed * sigma_y_eff * sigma_z_eff)
                    term2 = np.exp(-y_rotated**2 / (2 * sigma_y_eff**2))
                    term3 = np.exp(-(receptor_height - H)**2 / (2 * sigma_z_eff**2)) + np.exp(-(receptor_height + H)**2 / (2 * sigma_z_eff**2))
                    
                    concentration_field[i, j] = term1 * term2 * term3
        
        return concentration_field
    
    def calculate_area_source_receptor_concentration(
        self,
        center_lat: float,
        center_lon: float,
        area_length: float,
        area_width: float,
        area_height: float,
        emission_rate: float,
        receptor_lat: float,
        receptor_lon: float,
        sigma_z0: Optional[float] = None,
        receptor_height: float = 0.0
    ) -> float:
        """
        计算矩形面源对单个受体点的浓度
        """
        sigma_y0 = area_width / 4.3
        if sigma_z0 is None:
            sigma_z0 = area_height / 2.15 if area_height > 0 else 1.0
        
        params = self.PASQUILL_GIFFORD_PARAMS[self.stability_class]
        
        x_virtual_y = (sigma_y0 / params['ay']) ** (1 / params['by']) if params['ay'] > 0 else 0
        x_virtual_z = (sigma_z0 / params['az']) ** (1 / params['bz']) if params['az'] > 0 else 0
        x_virtual = max(x_virtual_y, x_virtual_z)
        
        wind_angle = np.radians(270 - self.wind_direction)
        
        lat_to_m = 111000
        lon_to_m = 111000 * np.cos(np.radians(center_lat))
        
        dy_lat = (receptor_lat - center_lat) * lat_to_m
        dx_lon = (receptor_lon - center_lon) * lon_to_m
        
        x_rotated = dx_lon * np.cos(wind_angle) + dy_lat * np.sin(wind_angle)
        y_rotated = -dx_lon * np.sin(wind_angle) + dy_lat * np.cos(wind_angle)
        
        x_eff = x_rotated + x_virtual
        
        if x_eff <= 0:
            return 0.0
        
        sigma_y, sigma_z = self.calculate_sigma(x_eff)
        sigma_y_eff = np.sqrt(sigma_y**2 - sigma_y0**2) if sigma_y > sigma_y0 else sigma_y
        sigma_z_eff = np.sqrt(sigma_z**2 - sigma_z0**2) if sigma_z > sigma_z0 else sigma_z
        
        emission_rate_ug = emission_rate * 1e6
        
        H = area_height
        
        term1 = emission_rate_ug / (2 * np.pi * self.wind_speed * sigma_y_eff * sigma_z_eff)
        term2 = np.exp(-y_rotated**2 / (2 * sigma_y_eff**2))
        term3 = np.exp(-(receptor_height - H)**2 / (2 * sigma_z_eff**2)) + np.exp(-(receptor_height + H)**2 / (2 * sigma_z_eff**2))
        
        return term1 * term2 * term3
    
    def calculate_line_source_concentration_field(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        line_width: float,
        line_height: float,
        emission_rate: float,
        grid_lat: np.ndarray,
        grid_lon: np.ndarray,
        segment_length: float = 10.0,
        sigma_z0: Optional[float] = None,
        receptor_height: float = 0.0
    ) -> np.ndarray:
        """
        计算直线线源浓度场（分段点源法）
        
        Args:
            start_lat: 起点纬度
            start_lon: 起点经度
            end_lat: 终点纬度
            end_lon: 终点经度
            line_width: 线源宽度
            line_height: 线源高度
            emission_rate: 总排放速率
            grid_lat: 网格纬度数组
            grid_lon: 网格经度数组
            segment_length: 分段长度
            sigma_z0: 初始垂直扩散参数 (可选, 自动计算)
            receptor_height: 受体高度
        
        Returns:
            浓度场 (μg/m³)
        """
        lat_to_m = 111000
        lon_to_m = 111000 * np.cos(np.radians((start_lat + end_lat) / 2))
        
        dx = (end_lon - start_lon) * lon_to_m
        dy = (end_lat - start_lat) * lat_to_m
        line_length = np.sqrt(dx**2 + dy**2)
        
        num_segments = max(1, int(line_length / segment_length))
        segment_emission = emission_rate / num_segments
        
        if sigma_z0 is None:
            sigma_z0 = line_height / 2.15 if line_height > 0 else 2.0
        
        sigma_y0 = line_width / 4.3
        
        concentration_field = np.zeros((len(grid_lat), len(grid_lon)))
        
        for seg in range(num_segments):
            t = (seg + 0.5) / num_segments
            seg_lat = start_lat + t * (end_lat - start_lat)
            seg_lon = start_lon + t * (end_lon - start_lon)
            
            seg_conc = self.calculate_area_source_concentration_field(
                center_lat=seg_lat,
                center_lon=seg_lon,
                area_length=segment_length,
                area_width=line_width,
                area_height=line_height,
                emission_rate=segment_emission,
                grid_lat=grid_lat,
                grid_lon=grid_lon,
                sigma_z0=sigma_z0,
                receptor_height=receptor_height
            )
            
            concentration_field += seg_conc
        
        return concentration_field
    
    def calculate_line_source_receptor_concentration(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        line_width: float,
        line_height: float,
        emission_rate: float,
        receptor_lat: float,
        receptor_lon: float,
        segment_length: float = 10.0,
        sigma_z0: Optional[float] = None,
        receptor_height: float = 0.0
    ) -> float:
        """
        计算直线线源对单个受体点的浓度
        """
        lat_to_m = 111000
        lon_to_m = 111000 * np.cos(np.radians((start_lat + end_lat) / 2))
        
        dx = (end_lon - start_lon) * lon_to_m
        dy = (end_lat - start_lat) * lat_to_m
        line_length = np.sqrt(dx**2 + dy**2)
        
        num_segments = max(1, int(line_length / segment_length))
        segment_emission = emission_rate / num_segments
        
        if sigma_z0 is None:
            sigma_z0 = line_height / 2.15 if line_height > 0 else 2.0
        
        total_conc = 0.0
        
        for seg in range(num_segments):
            t = (seg + 0.5) / num_segments
            seg_lat = start_lat + t * (end_lat - start_lat)
            seg_lon = start_lon + t * (end_lon - start_lon)
            
            seg_conc = self.calculate_area_source_receptor_concentration(
                center_lat=seg_lat,
                center_lon=seg_lon,
                area_length=segment_length,
                area_width=line_width,
                area_height=line_height,
                emission_rate=segment_emission,
                receptor_lat=receptor_lat,
                receptor_lon=receptor_lon,
                sigma_z0=sigma_z0,
                receptor_height=receptor_height
            )
            
            total_conc += seg_conc
        
        return total_conc


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
            else:
                if cloud_cover < 0.3:
                    return 'F'
                elif cloud_cover < 0.7:
                    return 'E'
                else:
                    return 'D'
            
            return StabilityClassifier.classify(wind_speed, solar_radiation=None, 
                                                cloud_cover=cloud_cover, is_daytime=is_daytime)
        
        else:
            return 'D'


def calculate_contribution_ranking(
    sources: list,
    concentrations: list
) -> list:
    """
    计算污染源贡献排名
    
    Args:
        sources: 排放源列表
        concentrations: 各源贡献浓度列表
    
    Returns:
        排序后的贡献列表
    """
    total = sum(concentrations)
    
    contributions = []
    for source, conc in zip(sources, concentrations):
        contributions.append({
            'source_id': source['id'],
            'source_name': source['name'],
            'concentration': conc,
            'percentage': (conc / total * 100) if total > 0 else 0
        })
    
    contributions.sort(key=lambda x: x['concentration'], reverse=True)
    
    return contributions
