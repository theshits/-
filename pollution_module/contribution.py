"""
贡献度分析模块
=============

计算各排放源对受体点的污染贡献度

使用示例:
    from pollution_module import calculate_contributions
    
    contributions = calculate_contributions(
        source_concentrations={'电厂': 15.5, '钢厂': 8.2, '化工厂': 3.1},
        receptor_name='监测站A'
    )
    
    for c in contributions:
        print(f"{c['source']}: {c['percentage']:.1f}%")
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ContributionResult:
    """贡献度结果"""
    source_name: str
    concentration: float
    percentage: float
    rank: int


def calculate_contributions(
    source_concentrations: Dict[str, float],
    receptor_name: str = ""
) -> List[ContributionResult]:
    """
    计算贡献度排名
    
    Args:
        source_concentrations: {源名称: 浓度} 字典
        receptor_name: 受体点名称（可选）
    
    Returns:
        按贡献度排序的结果列表
    """
    total = sum(source_concentrations.values())
    
    if total == 0:
        return [
            ContributionResult(
                source_name=name,
                concentration=conc,
                percentage=0.0,
                rank=i+1
            )
            for i, (name, conc) in enumerate(source_concentrations.items())
        ]
    
    sorted_sources = sorted(
        source_concentrations.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    results = []
    for rank, (name, conc) in enumerate(sorted_sources, 1):
        percentage = (conc / total * 100)
        results.append(ContributionResult(
            source_name=name,
            concentration=conc,
            percentage=percentage,
            rank=rank
        ))
    
    return results


def calculate_cumulative_contribution(
    contributions: List[ContributionResult],
    threshold: float = 80.0
) -> Dict[str, Any]:
    """
    计算累积贡献度
    
    找出贡献度累积达到阈值的源
    
    Args:
        contributions: 贡献度结果列表
        threshold: 累积阈值（默认80%）
    
    Returns:
        {
            'sources': 达到阈值的源列表,
            'cumulative_percentage': 累积百分比,
            'source_count': 源数量
        }
    """
    cumulative = 0.0
    sources = []
    
    for c in contributions:
        sources.append(c.source_name)
        cumulative += c.percentage
        if cumulative >= threshold:
            break
    
    return {
        'sources': sources,
        'cumulative_percentage': cumulative,
        'source_count': len(sources)
    }


def format_contribution_report(
    contributions: List[ContributionResult],
    receptor_name: str = "",
    top_n: int = 10
) -> str:
    """
    格式化贡献度报告
    
    Args:
        contributions: 贡献度结果列表
        receptor_name: 受体点名称
        top_n: 显示前N个源
    
    Returns:
        格式化的报告字符串
    """
    lines = []
    lines.append("=" * 50)
    if receptor_name:
        lines.append(f"受体点: {receptor_name}")
    lines.append("污染源贡献度排名")
    lines.append("=" * 50)
    lines.append(f"{'排名':<6}{'源名称':<20}{'浓度':<12}{'贡献度':<10}")
    lines.append("-" * 50)
    
    for c in contributions[:top_n]:
        lines.append(f"{c.rank:<6}{c.source_name:<20}{c.concentration:<12.4f}{c.percentage:<10.2f}%")
    
    lines.append("=" * 50)
    
    return "\n".join(lines)


def aggregate_contributions(
    contributions_list: List[List[ContributionResult]]
) -> List[ContributionResult]:
    """
    聚合多个受体点的贡献度
    
    Args:
        contributions_list: 多个受体点的贡献度列表
    
    Returns:
        聚合后的贡献度结果
    """
    aggregated = {}
    
    for contributions in contributions_list:
        for c in contributions:
            if c.source_name not in aggregated:
                aggregated[c.source_name] = 0.0
            aggregated[c.source_name] += c.concentration
    
    return calculate_contributions(aggregated)


def get_top_contributors(
    contributions: List[ContributionResult],
    n: int = 5
) -> List[ContributionResult]:
    """
    获取前N个主要贡献源
    
    Args:
        contributions: 贡献度结果列表
        n: 数量
    
    Returns:
        前N个贡献源
    """
    return contributions[:n]


def calculate_source_impact_radius(
    source_concentration: float,
    threshold: float = 1.0
) -> Dict[str, float]:
    """
    估算源影响半径
    
    基于浓度衰减估算影响范围
    
    Args:
        source_concentration: 源的最大浓度
        threshold: 阈值浓度
    
    Returns:
        {
            'max_concentration': 最大浓度,
            'threshold': 阈值,
            'estimated_radius': 估算半径
        }
    """
    if source_concentration <= threshold:
        return {
            'max_concentration': source_concentration,
            'threshold': threshold,
            'estimated_radius': 0.0
        }
    
    ratio = source_concentration / threshold
    estimated_radius = 1000 * (ratio ** 0.5)
    
    return {
        'max_concentration': source_concentration,
        'threshold': threshold,
        'estimated_radius': estimated_radius
    }
