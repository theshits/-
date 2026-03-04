"""
模拟运行模块
===========

提供一键式模拟接口，简化多源多受体场景的计算

使用示例:
    from pollution_module import run_simulation
    
    result = run_simulation(
        sources=[
            {'name': '电厂', 'lat': 39.9, 'lon': 116.4, 'height': 100, 'emission_rate': 50}
        ],
        receptors=[
            {'name': '站点A', 'lat': 39.91, 'lon': 116.41}
        ],
        meteorology={
            'wind_speed': 3.0,
            'wind_direction': 45,
            'stability_class': 'D'
        }
    )
    
    print(result.contributions)  # 各源贡献度
    print(result.receptor_contributions)  # 各受体点的源贡献
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from .gaussian_plume import GaussianPlumeModel


@dataclass
class SourceInfo:
    """排放源信息"""
    name: str
    lat: float
    lon: float
    height: float
    emission_rate: float
    flue_temp: float = 400.0
    exit_velocity: float = 10.0
    diameter: float = 1.0


@dataclass
class ReceptorInfo:
    """受体点信息"""
    name: str
    lat: float
    lon: float
    height: float = 0.0


@dataclass
class MeteorologyInfo:
    """气象信息"""
    wind_speed: float
    wind_direction: float
    stability_class: str = 'D'
    temperature: float = 293.15
    boundary_layer_height: float = 1000.0


@dataclass
class SourceContribution:
    """单源贡献"""
    source_name: str
    concentration: float
    percentage: float


@dataclass
class ReceptorContribution:
    """受体点贡献分析"""
    receptor_name: str
    total_concentration: float
    source_contributions: List[SourceContribution]


@dataclass
class SimulationResult:
    """模拟结果"""
    concentrations: List[List[float]]
    lat_grid: List[float]
    lon_grid: List[float]
    max_concentration: float
    contributions: List[SourceContribution]
    receptor_contributions: List[ReceptorContribution]
    grid_bounds: tuple


def run_simulation(
    sources: List[Dict[str, Any]],
    receptors: List[Dict[str, Any]],
    meteorology: Dict[str, Any],
    grid_size: int = 50,
    domain_radius: float = 5000.0,
    custom_grid_bounds: Optional[tuple] = None
) -> SimulationResult:
    """
    运行污染扩散模拟
    
    Args:
        sources: 排放源列表
            [{'name': '源1', 'lat': 39.9, 'lon': 116.4, 'height': 50, 'emission_rate': 10, ...}]
        
        receptors: 受体点列表
            [{'name': '站点1', 'lat': 39.91, 'lon': 116.41, 'height': 0}]
        
        meteorology: 气象条件
            {'wind_speed': 3.0, 'wind_direction': 45, 'stability_class': 'D', ...}
        
        grid_size: 网格点数
        domain_radius: 模拟域半径
        custom_grid_bounds: 自定义网格边界
    
    Returns:
        SimulationResult: 模拟结果
    """
    source_list = [
        SourceInfo(
            name=s.get('name', f'源{i+1}'),
            lat=s['lat'],
            lon=s['lon'],
            height=s.get('height', 50),
            emission_rate=s.get('emission_rate', 10),
            flue_temp=s.get('flue_temp', 400.0),
            exit_velocity=s.get('exit_velocity', 10.0),
            diameter=s.get('diameter', 1.0)
        )
        for i, s in enumerate(sources)
    ]
    
    receptor_list = [
        ReceptorInfo(
            name=r.get('name', f'受体{i+1}'),
            lat=r['lat'],
            lon=r['lon'],
            height=r.get('height', 0)
        )
        for i, r in enumerate(receptors)
    ]
    
    met = MeteorologyInfo(
        wind_speed=meteorology['wind_speed'],
        wind_direction=meteorology['wind_direction'],
        stability_class=meteorology.get('stability_class', 'D'),
        temperature=meteorology.get('temperature', 293.15),
        boundary_layer_height=meteorology.get('boundary_layer_height', 1000.0)
    )
    
    model = GaussianPlumeModel(
        wind_speed=met.wind_speed,
        wind_direction=met.wind_direction,
        stability_class=met.stability_class,
        temperature=met.temperature,
        boundary_layer_height=met.boundary_layer_height
    )
    
    if custom_grid_bounds:
        grid_bounds = custom_grid_bounds
    else:
        all_lats = [s.lat for s in source_list] + [r.lat for r in receptor_list]
        all_lons = [s.lon for s in source_list] + [r.lon for r in receptor_list]
        
        center_lat = sum(all_lats) / len(all_lats)
        center_lon = sum(all_lons) / len(all_lons)
        
        lat_radius = domain_radius / 111000
        lon_radius = domain_radius / (111000 * 0.866)
        
        grid_bounds = (
            center_lat - lat_radius,
            center_lat + lat_radius,
            center_lon - lon_radius,
            center_lon + lon_radius
        )
    
    lat_min, lat_max, lon_min, lon_max = grid_bounds
    lat_step = (lat_max - lat_min) / (grid_size - 1)
    lon_step = (lon_max - lon_min) / (grid_size - 1)
    
    lat_grid = [lat_min + i * lat_step for i in range(grid_size)]
    lon_grid = [lon_min + j * lon_step for j in range(grid_size)]
    
    total_concentrations = [[0.0] * grid_size for _ in range(grid_size)]
    source_grids = []
    
    for source in source_list:
        source_grid = [[0.0] * grid_size for _ in range(grid_size)]
        
        for i, lat in enumerate(lat_grid):
            for j, lon in enumerate(lon_grid):
                conc = model.calculate_receptor_concentration(
                    source_lat=source.lat,
                    source_lon=source.lon,
                    source_height=source.height,
                    emission_rate=source.emission_rate,
                    receptor_lat=lat,
                    receptor_lon=lon,
                    flue_temp=source.flue_temp,
                    exit_velocity=source.exit_velocity,
                    diameter=source.diameter
                )
                source_grid[i][j] = conc
                total_concentrations[i][j] += conc
        
        source_grids.append((source, source_grid))
    
    flat_conc = [c for row in total_concentrations for c in row]
    max_conc = max(flat_conc)
    
    source_totals = []
    for source, grid in source_grids:
        total = sum(c for row in grid for c in row)
        source_totals.append((source, total))
    
    grand_total = sum(t for _, t in source_totals)
    
    contributions = []
    for source, total in source_totals:
        percentage = (total / grand_total * 100) if grand_total > 0 else 0
        contributions.append(SourceContribution(
            source_name=source.name,
            concentration=total,
            percentage=percentage
        ))
    
    contributions.sort(key=lambda x: x.concentration, reverse=True)
    
    receptor_contributions = []
    for receptor in receptor_list:
        receptor_source_contribs = []
        total_at_receptor = 0.0
        
        for source, grid in source_grids:
            i = min(range(grid_size), key=lambda x: abs(lat_grid[x] - receptor.lat))
            j = min(range(grid_size), key=lambda x: abs(lon_grid[x] - receptor.lon))
            
            conc = grid[i][j]
            total_at_receptor += conc
            
            receptor_source_contribs.append((source.name, conc))
        
        source_contribs = []
        for source_name, conc in receptor_source_contribs:
            pct = (conc / total_at_receptor * 100) if total_at_receptor > 0 else 0
            source_contribs.append(SourceContribution(
                source_name=source_name,
                concentration=conc,
                percentage=pct
            ))
        
        source_contribs.sort(key=lambda x: x.concentration, reverse=True)
        
        receptor_contributions.append(ReceptorContribution(
            receptor_name=receptor.name,
            total_concentration=total_at_receptor,
            source_contributions=source_contribs
        ))
    
    return SimulationResult(
        concentrations=total_concentrations,
        lat_grid=lat_grid,
        lon_grid=lon_grid,
        max_concentration=max_conc,
        contributions=contributions,
        receptor_contributions=receptor_contributions,
        grid_bounds=grid_bounds
    )


def run_single_source_simulation(
    source: Dict[str, Any],
    meteorology: Dict[str, Any],
    grid_size: int = 50,
    domain_radius: float = 5000.0
) -> SimulationResult:
    """
    单源扩散模拟（简化接口）
    
    Args:
        source: 单个排放源
        meteorology: 气象条件
        grid_size: 网格点数
        domain_radius: 模拟域半径
    
    Returns:
        SimulationResult
    """
    return run_simulation(
        sources=[source],
        receptors=[],
        meteorology=meteorology,
        grid_size=grid_size,
        domain_radius=domain_radius
    )
