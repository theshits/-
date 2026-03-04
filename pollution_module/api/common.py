"""
通用API函数
==========

框架无关的API核心逻辑
"""

from typing import Dict, Any, List, Optional
from ..simulation import run_simulation, SimulationResult
from ..contribution import calculate_contributions, format_contribution_report


def run_simulation_api(
    sources: List[Dict[str, Any]],
    receptors: List[Dict[str, Any]],
    meteorology: Dict[str, Any],
    grid_size: int = 50,
    domain_radius: float = 5000.0
) -> Dict[str, Any]:
    """
    运行扩散模拟API
    
    Args:
        sources: 排放源列表
        receptors: 受体点列表
        meteorology: 气象条件
        grid_size: 网格点数
        domain_radius: 模拟域半径
    
    Returns:
        API响应字典
    """
    try:
        result = run_simulation(
            sources=sources,
            receptors=receptors,
            meteorology=meteorology,
            grid_size=grid_size,
            domain_radius=domain_radius
        )
        
        return {
            'success': True,
            'data': {
                'concentrations': result.concentrations,
                'lat_grid': result.lat_grid,
                'lon_grid': result.lon_grid,
                'max_concentration': result.max_concentration,
                'grid_bounds': result.grid_bounds,
                'contributions': [
                    {
                        'source_name': c.source_name,
                        'concentration': c.concentration,
                        'percentage': c.percentage
                    }
                    for c in result.contributions
                ],
                'receptor_contributions': [
                    {
                        'receptor_name': rc.receptor_name,
                        'total_concentration': rc.total_concentration,
                        'source_contributions': [
                            {
                                'source_name': sc.source_name,
                                'concentration': sc.concentration,
                                'percentage': sc.percentage
                            }
                            for sc in rc.source_contributions
                        ]
                    }
                    for rc in result.receptor_contributions
                ]
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_contribution_api(
    source_concentrations: Dict[str, float],
    receptor_name: str = ""
) -> Dict[str, Any]:
    """
    获取贡献度分析API
    
    Args:
        source_concentrations: {源名称: 浓度} 字典
        receptor_name: 受体点名称
    
    Returns:
        API响应字典
    """
    try:
        contributions = calculate_contributions(source_concentrations, receptor_name)
        
        return {
            'success': True,
            'data': {
                'receptor_name': receptor_name,
                'contributions': [
                    {
                        'rank': c.rank,
                        'source_name': c.source_name,
                        'concentration': c.concentration,
                        'percentage': c.percentage
                    }
                    for c in contributions
                ],
                'report': format_contribution_report(contributions, receptor_name)
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def calculate_single_point_api(
    source: Dict[str, Any],
    receptor: Dict[str, Any],
    meteorology: Dict[str, Any]
) -> Dict[str, Any]:
    """
    计算单点浓度API
    
    Args:
        source: 排放源信息
        receptor: 受体点信息
        meteorology: 气象条件
    
    Returns:
        API响应字典
    """
    try:
        from ..gaussian_plume import GaussianPlumeModel
        
        model = GaussianPlumeModel(
            wind_speed=meteorology['wind_speed'],
            wind_direction=meteorology['wind_direction'],
            stability_class=meteorology.get('stability_class', 'D'),
            temperature=meteorology.get('temperature', 293.15),
            boundary_layer_height=meteorology.get('boundary_layer_height', 1000.0)
        )
        
        concentration = model.calculate_receptor_concentration(
            source_lat=source['lat'],
            source_lon=source['lon'],
            source_height=source.get('height', 50),
            emission_rate=source.get('emission_rate', 10),
            receptor_lat=receptor['lat'],
            receptor_lon=receptor['lon'],
            receptor_height=receptor.get('height', 0),
            flue_temp=source.get('flue_temp', 400.0),
            exit_velocity=source.get('exit_velocity', 10.0),
            diameter=source.get('diameter', 1.0)
        )
        
        return {
            'success': True,
            'data': {
                'source': source.get('name', '未命名源'),
                'receptor': receptor.get('name', '未命名受体'),
                'concentration': concentration,
                'unit': 'μg/m³'
            }
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
