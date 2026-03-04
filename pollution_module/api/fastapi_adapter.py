"""
FastAPI适配器
============

将污染扩散模块集成到FastAPI应用

使用示例:
    from fastapi import FastAPI
    from pollution_module.api import create_fastapi_router
    
    app = FastAPI()
    app.include_router(create_fastapi_router(), prefix='/api/pollution')
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .common import run_simulation_api, get_contribution_api, calculate_single_point_api


class SourceSchema(BaseModel):
    """排放源数据模型"""
    name: str = Field(default="", description="源名称")
    lat: float = Field(..., description="纬度")
    lon: float = Field(..., description="经度")
    height: float = Field(default=50, description="烟囱高度
    emission_rate: float = Field(default=10, description="排放速率
    flue_temp: float = Field(default=400, description="烟气温度 (K)")
    exit_velocity: float = Field(default=10, description="出口速度
    diameter: float = Field(default=1, description="烟囱直径


class ReceptorSchema(BaseModel):
    """受体点数据模型"""
    name: str = Field(default="", description="受体点名称")
    lat: float = Field(..., description="纬度")
    lon: float = Field(..., description="经度")
    height: float = Field(default=0, description="受体高度


class MeteorologySchema(BaseModel):
    """气象数据模型"""
    wind_speed: float = Field(..., description="风速", ge=0.1, le=30)
    wind_direction: float = Field(..., description="风向 (度)", ge=0, le=360)
    stability_class: str = Field(default="D", description="稳定度等级")
    temperature: float = Field(default=293.15, description="温度 (K)")
    boundary_layer_height: float = Field(default=1000, description="边界层高度


class SimulationRequest(BaseModel):
    """模拟请求模型"""
    sources: List[SourceSchema]
    receptors: List[ReceptorSchema]
    meteorology: MeteorologySchema
    grid_size: int = Field(default=50, ge=10, le=200)
    domain_radius: float = Field(default=5000, ge=100, le=50000)


class SinglePointRequest(BaseModel):
    """单点计算请求模型"""
    source: SourceSchema
    receptor: ReceptorSchema
    meteorology: MeteorologySchema


class ContributionRequest(BaseModel):
    """贡献度计算请求模型"""
    source_concentrations: Dict[str, float]
    receptor_name: str = ""


def create_router() -> APIRouter:
    """
    创建FastAPI路由器
    
    Returns:
        APIRouter实例
    """
    router = APIRouter(tags=["污染扩散模拟"])
    
    @router.post("/simulate")
    async def simulate(request: SimulationRequest) -> Dict[str, Any]:
        """
        运行扩散模拟
        
        计算多源多受体场景的污染物浓度分布和贡献度
        """
        sources = [s.model_dump() for s in request.sources]
        receptors = [r.model_dump() for r in request.receptors]
        meteorology = request.meteorology.model_dump()
        
        result = run_simulation_api(
            sources=sources,
            receptors=receptors,
            meteorology=meteorology,
            grid_size=request.grid_size,
            domain_radius=request.domain_radius
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    
    @router.post("/single-point")
    async def calculate_single_point(request: SinglePointRequest) -> Dict[str, Any]:
        """
        计算单点浓度
        
        计算单个排放源对单个受体点的浓度贡献
        """
        result = calculate_single_point_api(
            source=request.source.model_dump(),
            receptor=request.receptor.model_dump(),
            meteorology=request.meteorology.model_dump()
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    
    @router.post("/contributions")
    async def get_contributions(request: ContributionRequest) -> Dict[str, Any]:
        """
        计算贡献度排名
        
        计算各污染源的贡献度百分比
        """
        result = get_contribution_api(
            source_concentrations=request.source_concentrations,
            receptor_name=request.receptor_name
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    
    @router.get("/stability-classes")
    async def get_stability_classes() -> Dict[str, Any]:
        """
        获取稳定度等级说明
        """
        from ..gaussian_plume import StabilityClassifier
        
        classes = {}
        for cls in ['A', 'B', 'C', 'D', 'E', 'F']:
            classes[cls] = StabilityClassifier.get_description(cls)
        
        return {
            'success': True,
            'data': classes
        }
    
    @router.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "healthy", "module": "pollution_module"}
    
    return router
