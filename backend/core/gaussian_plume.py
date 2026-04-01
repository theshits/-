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
        boundary_layer_height: float = 1000.0,
        humidity: float = 50.0,
        cloud_cover: float = 0.0,
        precipitation: float = 0.0
    ):
        """Lambda = a × precipitation^b + 1e-5  # 背景清除
Lambda × (1 + 0.1 ×
        初始化高斯烟羽模型
        
        Args:
            wind_speed: 风速
            wind_direction: 风向 (度, 气象风向, 风来自的方向)
            stability_class: 大气稳定度等级
            temperature: 环境温度 (K)
            boundary_layer_height: 边界层高度
            humidity: 相对湿度 (%)
            cloud_cover: 云量 (0-10)
            precipitation: 降水强度 (mm/h)
        """
        self.wind_speed = max(wind_speed, 0.1)
        self.wind_direction = wind_direction
        self.stability_class = stability_class.upper()
        self.temperature = temperature
        self.boundary_layer_height = boundary_layer_height
        self.humidity = humidity
        self.cloud_cover = cloud_cover
        self.precipitation = precipitation
        
        if self.stability_class not in self.PASQUILL_GIFFORD_PARAMS:
            raise ValueError(f"无效的稳定度等级: {stability_class}")
    
    def calculate_gravitational_settling_velocity(self, pollutant_type: str = 'PM2.5') -> float:
        """
        计算重力沉降速度
        
        基于污染物类型返回重力沉降速度
        
        Args:
            pollutant_type: 污染物类型
        
        Returns:
            重力沉降速度
        """
        vg_dict = {
            'PM2.5': 0.0002,
            'PM10': 0.018,
            'TSP': 0.05,
            'VOCs': 0.0,
            'NOx': 0.0,
            'SO2': 0.0,
            'CO': 0.0,
            'O3': 0.0
        }
        
        return vg_dict.get(pollutant_type, 0.0002)
    
    def calculate_effective_mixing_height(self) -> float:
        """
        计算有效混合高度
        
        基于边界层高度和稳定度计算有效混合高度
        
        Returns:
            有效混合高度
        """
        mixing_factors = {
            'A': 1.0,
            'B': 0.9,
            'C': 0.8,
            'D': 0.6,
            'E': 0.4,
            'F': 0.2
        }
        
        mixing_factor = mixing_factors.get(self.stability_class, 0.6)
        H_eff = self.boundary_layer_height * mixing_factor
        
        return H_eff
    
    def calculate_dry_deposition_velocity(self, pollutant_type: str = 'PM2.5') -> float:
        """
        计算干沉降速度（WRF模型思路）
        
        使用阻力模型：vd = vg + 1/(Ra + Rb + Rc)
        
        Args:
            pollutant_type: 污染物类型
        
        Returns:
            干沉降速度
        """
        kappa = 0.4
        
        stability_factors = {
            'A': 0.5,
            'B': 0.7,
            'C': 1.0,
            'D': 1.5,
            'E': 2.0,
            'F': 3.0
        }
        
        stability_factor = stability_factors.get(self.stability_class, 1.5)
        Ra = stability_factor / (kappa * self.wind_speed + 1e-6)
        
        pollutant_params = {
            'PM2.5': (100, 200),
            'PM10': (50, 100),
            'TSP': (30, 80),
            'VOCs': (200, 800),
            'NOx': (150, 500),
            'SO2': (150, 400),
            'CO': (200, 600),
            'O3': (150, 600)
        }
        
        Rb, Rc = pollutant_params.get(pollutant_type, (100, 200))
        
        vd_turbulent = 1.0 / (Ra + Rb + Rc)
        
        vg = self.calculate_gravitational_settling_velocity(pollutant_type)
        
        vd = vd_turbulent + vg
        
        vd *= (1 + 0.2 * self.humidity / 100)
        
        if pollutant_type in ['VOCs', 'NOx', 'SO2']:
            temp_factor = 1 + 0.01 * (self.temperature - 293.15)
            vd *= temp_factor
        
        return vd
    
    def calculate_wet_scavenging_coefficient(self, pollutant_type: str = 'PM2.5') -> float:
        """
        计算湿沉降清除系数（WRF模型思路）
        
        使用scavenging系数：Λ = a * precipitation^b + background_scavenging
        
        Args:
            pollutant_type: 污染物类型
        
        Returns:
            湿沉降清除系数 (1/s)
        """
        scavenging_params = {
            'PM2.5': (1e-5, 0.8),
            'PM10': (2e-5, 0.8),
            'TSP': (3e-5, 0.8),
            'VOCs': (1e-6, 0.7),
            'NOx': (5e-6, 0.7),
            'SO2': (8e-6, 0.7),
            'CO': (1e-7, 0.6),
            'O3': (5e-6, 0.7)
        }
        
        a, b = scavenging_params.get(pollutant_type, (1e-5, 0.8))
        
        Lambda = a * (self.precipitation ** b) if self.precipitation > 0 else 0.0
        
        background_scavenging = 1e-5
        Lambda += background_scavenging
        
        cloud_factor = 1 + 0.1 * self.cloud_cover
        Lambda *= cloud_factor
        
        return Lambda
    
    def calculate_deposition_coefficient(self, distance: float, pollutant_type: str = 'PM2.5') -> float:
        """
        计算沉降衰减系数（WRF模型思路）
        
        k_total = k_dry + Λ
        decay = exp(-k_total * distance / wind_speed)
        
        Args:
            distance: 下风向距离
            pollutant_type: 污染物类型
        
        Returns:
            衰减系数 (0-1)
        """
        vd = self.calculate_dry_deposition_velocity(pollutant_type)
        
        k_dry = vd / self.boundary_layer_height
        
        Lambda = self.calculate_wet_scavenging_coefficient(pollutant_type)
        
        k_total = k_dry + Lambda
        
        decay_factor = np.exp(-k_total * distance / self.wind_speed)
        
        return decay_factor
    
    def calculate_chemical_decay(self, distance: float, pollutant_type: str = 'PM2.5') -> float:
        """
        计算化学转化衰减
        
        考虑温度、湿度、云量对化学反应速率的影响
        不同污染物有不同的基础化学转化速率
        
        Args:
            distance: 下风向距离
            pollutant_type: 污染物类型
        
        Returns:
            衰减系数 (0-1)
        """
        chemical_rates = {
            'PM2.5': 2e-5,
            'PM10': 1e-5,
            'TSP': 5e-6,
            'VOCs': 3e-4,
            'NOx': 1.5e-4,
            'SO2': 8e-5,
            'CO': 1e-6,
            'O3': 1e-4
        }
        
        k_base = chemical_rates.get(pollutant_type, 2e-5)
        
        temp_factor = np.exp((self.temperature - 298) / 20)
        
        humidity_factor = 1 + (self.humidity - 50) / 200
        
        cloud_factor = 1 + self.cloud_cover / 50
        
        if pollutant_type in ['VOCs', 'NOx', 'O3']:
            temp_factor *= 1.5
            humidity_factor *= 1.3
        
        k_effective = k_base * temp_factor * humidity_factor * cloud_factor
        
        travel_time = distance / self.wind_speed
        
        decay_factor = np.exp(-k_effective * travel_time)
        
        return decay_factor
    
    def calculate_total_decay(self, distance: float, pollutant_type: str = 'PM2.5') -> float:
        """
        计算总衰减系数
        
        综合沉降衰减和化学转化衰减
        
        Args:
            distance: 下风向距离
            pollutant_type: 污染物类型 (默认PM2.5)
        
        Returns:
            总衰减系数 (0-1)
        """
        deposition_decay = self.calculate_deposition_coefficient(distance, pollutant_type)
        chemical_decay = self.calculate_chemical_decay(distance, pollutant_type)
        
        total_decay = deposition_decay * chemical_decay
        
        return total_decay
    
    def calculate_max_diffusion_distance(self) -> float:
        """
        计算最大扩散距离
        
        基于边界层高度和稳定度计算最大有效扩散距离
        使用Turner公式
        
        Returns:
            最大扩散距离
        """
        stability_factors = {
            'A': 1.5,
            'B': 1.3,
            'C': 1.1,
            'D': 1.0,
            'E': 0.8,
            'F': 0.6
        }
        
        factor = stability_factors.get(self.stability_class, 1.0)
        
        max_distance = factor * self.boundary_layer_height * 10
        
        return max_distance
    
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
        
        sigma_y = max(sigma_y, 1.0)
        sigma_z = max(sigma_z, 1.0)
        
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
        effective_height: Optional[float] = None,
        pollutant_type: str = 'PM2.5'
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
            pollutant_type: 污染物类型 (默认PM2.5)
        
        Returns:
            浓度 (μg/m³)
        """
        if x <= 0:
            return 0.0
        
        max_distance = self.calculate_max_diffusion_distance()
        if x > max_distance:
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
        
        total_decay = self.calculate_total_decay(x, pollutant_type)
        concentration = concentration * total_decay
        
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
        receptor_height: float = 0.0,
        pollutant_type: str = 'PM2.5'
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
            pollutant_type: 污染物类型 (默认PM2.5)
        
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
        
        max_distance = self.calculate_max_diffusion_distance()
        
        for i, lat in enumerate(grid_lat):
            for j, lon in enumerate(grid_lon):
                dy_lat = (lat - source_lat) * lat_to_m
                dx_lon = (lon - source_lon) * lon_to_m
                
                x_rotated = dx_lon * np.cos(wind_angle) + dy_lat * np.sin(wind_angle)
                y_rotated = -dx_lon * np.sin(wind_angle) + dy_lat * np.cos(wind_angle)
                
                if x_rotated > 0 and x_rotated <= max_distance:
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
        diameter: float = 1.0,
        pollutant_type: str = 'PM2.5'
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
            pollutant_type: 污染物类型 (默认PM2.5)
        
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
            effective_height=effective_height,
            pollutant_type=pollutant_type
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
        receptor_height: float = 0.0,
        max_concentration: float = None,
        is_equivalent: bool = False,
        pollutant_type: str = 'PM2.5'
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
            max_concentration: 等效面源最大浓度 (可选)
            is_equivalent: 是否为等效面源
            pollutant_type: 污染物类型 (默认PM2.5)
        
        Returns:
            浓度场数组
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
        
        max_distance = self.calculate_max_diffusion_distance()
        
        half_length = area_length / 2
        half_width = area_width / 2
        
        for i, lat in enumerate(grid_lat):
            for j, lon in enumerate(grid_lon):
                dy_lat = (lat - center_lat) * lat_to_m
                dx_lon = (lon - center_lon) * lon_to_m
                
                x_rotated = dx_lon * np.cos(wind_angle) + dy_lat * np.sin(wind_angle)
                y_rotated = -dx_lon * np.sin(wind_angle) + dy_lat * np.cos(wind_angle)
                
                x_eff = x_rotated + x_virtual
                
                if x_eff <= 0:
                    concentration_field[i, j] = 0.0
                    continue
                
                if x_eff > max_distance:
                    concentration_field[i, j] = 0.0
                    continue
                
                in_source = (abs(dx_lon) <= half_length and abs(dy_lat) <= half_width)
                
                sigma_y, sigma_z = self.calculate_sigma(x_eff)
                sigma_y_eff = np.sqrt(sigma_y**2 + sigma_y0**2)
                sigma_z_eff = np.sqrt(sigma_z**2 + sigma_z0**2)
                
                emission_rate_ug = emission_rate * 1e6
                
                H = area_height
                
                term1 = emission_rate_ug / (2 * np.pi * self.wind_speed * sigma_y_eff * sigma_z_eff)
                term2 = np.exp(-y_rotated**2 / (2 * sigma_y_eff**2))
                term3 = np.exp(-(receptor_height - H)**2 / (2 * sigma_z_eff**2)) + np.exp(-(receptor_height + H)**2 / (2 * sigma_z_eff**2))
                
                conc = term1 * term2 * term3
                
                total_decay = self.calculate_total_decay(x_eff, pollutant_type)
                conc = conc * total_decay
                
                if is_equivalent and max_concentration is not None and in_source:
                    conc = min(conc, max_concentration)
                
                concentration_field[i, j] = conc
        
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
        receptor_height: float = 0.0,
        concentration: float = None,
        is_equivalent: bool = False,
        pollutant_type: str = 'PM2.5'
    ) -> float:
        """
        计算矩形面源对单个受体点的浓度
        
        对于等效面源，当受体点位于面源内部时，直接返回测量浓度
        对于等效面源，计算结果不超过测量浓度
        
        Args:
            pollutant_type: 污染物类型 (默认PM2.5)
        """
        lat_to_m = 111000
        lon_to_m = 111000 * np.cos(np.radians(center_lat))
        
        dy = (receptor_lat - center_lat) * lat_to_m
        dx = (receptor_lon - center_lon) * lon_to_m
        
        half_length = area_length / 2
        half_width = area_width / 2
        
        sigma_y0 = area_width / 4.3
        if sigma_z0 is None:
            sigma_z0 = area_height / 2.15 if area_height > 0 else 1.0
        
        params = self.PASQUILL_GIFFORD_PARAMS[self.stability_class]
        
        x_virtual_y = (sigma_y0 / params['ay']) ** (1 / params['by']) if params['ay'] > 0 else 0
        x_virtual_z = (sigma_z0 / params['az']) ** (1 / params['bz']) if params['az'] > 0 else 0
        x_virtual = max(x_virtual_y, x_virtual_z)
        
        wind_angle = np.radians(270 - self.wind_direction)
        
        x_rotated = dx * np.cos(wind_angle) + dy * np.sin(wind_angle)
        y_rotated = -dx * np.sin(wind_angle) + dy * np.cos(wind_angle)
        
        x_eff = x_rotated + x_virtual
        
        if x_eff <= 0:
            return 0.0
        
        in_source = (abs(dx) <= half_length and abs(dy) <= half_width)
        
        sigma_y, sigma_z = self.calculate_sigma(x_eff)
        sigma_y_eff = np.sqrt(sigma_y**2 + sigma_y0**2)
        sigma_z_eff = np.sqrt(sigma_z**2 + sigma_z0**2)
        
        emission_rate_ug = emission_rate * 1e6
        
        H = area_height
        
        term1 = emission_rate_ug / (2 * np.pi * self.wind_speed * sigma_y_eff * sigma_z_eff)
        term2 = np.exp(-y_rotated**2 / (2 * sigma_y_eff**2))
        term3 = np.exp(-(receptor_height - H)**2 / (2 * sigma_z_eff**2)) + np.exp(-(receptor_height + H)**2 / (2 * sigma_z_eff**2))
        
        result = term1 * term2 * term3
        
        total_decay = self.calculate_total_decay(x_eff, pollutant_type)
        result = result * total_decay
        
        if is_equivalent and concentration is not None and in_source:
            result = min(result, concentration)
        
        return result
    
    def calculate_concentration_at_height(
        self,
        ground_concentration: float,
        source_height: float,
        receptor_height: float,
        distance: float = None,
        wind_speed: float = None
    ) -> float:
        """
        根据地面/源高度浓度计算不同高度的浓度（考虑垂直扩散）
        
        Args:
            ground_concentration: 地面/源高度处的测量浓度 (μg/m³)
            source_height: 源高度
            receptor_height: 受体高度
            distance: 计算距离，用于估算垂直扩散参数
            wind_speed: 风速，默认使用模型风速
        
        Returns:
            指定高度的浓度 (μg/m³)
        """
        if wind_speed is None:
            wind_speed = self.wind_speed
        
        if receptor_height <= source_height:
            return ground_concentration
        
        if distance is None or distance <= 0:
            distance = 50.0
        
        sigma_z = self.calculate_sigma(distance)[1]
        
        if sigma_z <= 0:
            sigma_z = 1.0
        
        H = source_height
        z = receptor_height
        
        vertical_ratio = np.exp(-(z - H)**2 / (2 * sigma_z**2))
        
        height_concentration = ground_concentration * vertical_ratio
        
        return max(0, height_concentration)
    
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
        receptor_height: float = 0.0,
        pollutant_type: str = 'PM2.5'
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
            pollutant_type: 污染物类型 (默认PM2.5)
        
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
                receptor_height=receptor_height,
                pollutant_type=pollutant_type
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
        receptor_height: float = 0.0,
        pollutant_type: str = 'PM2.5'
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
                receptor_height=receptor_height,
                pollutant_type=pollutant_type
            )
            
            total_conc += seg_conc
        
        return total_conc
    
    def calculate_emission_rate_from_concentration(
        self,
        x: float,
        y: float,
        z: float,
        source_height: float,
        concentration: float,
        effective_height: Optional[float] = None
    ) -> float:
        """
        从浓度反推排放速率（高斯烟羽方程的逆运算）
        
        高斯烟羽方程:
        C = Q/(2π·u·σy·σz) · exp[-y²/(2σy²)] · {exp[-(z-H)²/(2σz²)] + exp[-(z+H)²/(2σz²)]}
        
        反推排放速率:
        Q = C · 2π·u·σy·σz / {exp[-y²/(2σy²)] · {exp[-(z-H)²/(2σz²)] + exp[-(z+H)²/(2σz²)]}}
        
        Args:
            x: 下风向距离
            y: 横风向距离
            z: 计算点高度
            source_height: 源高度
            concentration: 浓度 (μg/m³)
            effective_height: 有效高度 (可选, 自动计算)
        
        Returns:
            排放速率
        """
        if x <= 0:
            raise ValueError("下风向距离必须大于0")
        
        if concentration <= 0:
            return 0.0
        
        sigma_y, sigma_z = self.calculate_sigma(x)
        
        if effective_height is None:
            effective_height = source_height
        
        H = effective_height
        
        term2 = np.exp(-y**2 / (2 * sigma_y**2))
        term3 = np.exp(-(z - H)**2 / (2 * sigma_z**2)) + np.exp(-(z + H)**2 / (2 * sigma_z**2))
        
        if term2 * term3 < 1e-30:
            raise ValueError("计算点位置过于偏离烟羽中心，无法准确反推排放速率")
        
        emission_rate_ug = concentration * 2 * np.pi * self.wind_speed * sigma_y * sigma_z / (term2 * term3)
        
        emission_rate = emission_rate_ug / 1e6
        
        return emission_rate
    
    def calculate_equivalent_emission_rate(
        self,
        concentration: float,
        area_length: float,
        area_width: float,
        area_height: float
    ) -> float:
        """
        计算等效面源的排放速率（经验公式）
        
        使用工程经验公式：Q = C × U × H × W
        
        Args:
            concentration: 测量浓度 (μg/m³)
            area_length: 面源长度
            area_width: 面源宽度
            area_height: 面源高度
        
        Returns:
            等效排放速率
        """
        concentration_g = concentration / 1e6
        
        Q = concentration_g * self.wind_speed * area_height * np.sqrt(area_length * area_width)
        
        return Q
    
    def calculate_emission_rate_from_receptor(
        self,
        source_lat: float,
        source_lon: float,
        source_height: float,
        receptor_lat: float,
        receptor_lon: float,
        concentration: float,
        receptor_height: float = 0.0,
        temperature: float = 400.0,
        velocity: float = 10.0,
        diameter: float = 1.0
    ) -> float:
        """
        从受体点浓度反推等效排放速率
        
        Args:
            source_lat: 源纬度
            source_lon: 源经度
            source_height: 源高度
            receptor_lat: 受体纬度
            receptor_lon: 受体经度
            concentration: 浓度 (μg/m³)
            receptor_height: 受体高度
            temperature: 烟气温度 (K)
            velocity: 烟气出口速度
            diameter: 烟囱直径
        
        Returns:
            等效排放速率
        """
        effective_height = self.calculate_effective_height(
            source_height, 1.0, temperature, velocity, diameter
        )
        
        wind_angle = np.radians(270 - self.wind_direction)
        
        lat_to_m = 111000
        lon_to_m = 111000 * np.cos(np.radians(source_lat))
        
        dy_lat = (receptor_lat - source_lat) * lat_to_m
        dx_lon = (receptor_lon - source_lon) * lon_to_m
        
        x_rotated = dx_lon * np.cos(wind_angle) + dy_lat * np.sin(wind_angle)
        y_rotated = -dx_lon * np.sin(wind_angle) + dy_lat * np.cos(wind_angle)
        
        if x_rotated <= 0:
            x_rotated = 100.0
            y_rotated = 0.0
        
        return self.calculate_emission_rate_from_concentration(
            x=x_rotated,
            y=y_rotated,
            z=receptor_height,
            source_height=source_height,
            concentration=concentration,
            effective_height=effective_height
        )


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
