from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PollutantEmissionBase(BaseModel):
    pollutant_type: str
    emission_rate: float = 0.0

class PollutantEmissionCreate(PollutantEmissionBase):
    pass

class PollutantEmissionUpdate(BaseModel):
    pollutant_type: Optional[str] = None
    emission_rate: Optional[float] = None

class PollutantEmissionResponse(PollutantEmissionBase):
    id: int
    source_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EmissionSourceBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    height: float = 0.0
    temperature: float = 400.0
    velocity: float = 15.0
    diameter: float = 2.0
    marker_symbol: str = "factory"
    marker_color: str = "#FF5722"
    is_active: bool = True

class EmissionSourceCreate(EmissionSourceBase):
    pollutants: List[PollutantEmissionCreate] = []

class EmissionSourceUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    height: Optional[float] = None
    temperature: Optional[float] = None
    velocity: Optional[float] = None
    diameter: Optional[float] = None
    marker_symbol: Optional[str] = None
    marker_color: Optional[str] = None
    is_active: Optional[bool] = None
    pollutants: Optional[List[PollutantEmissionCreate]] = None

class EmissionSourceResponse(EmissionSourceBase):
    id: int
    pollutants: List[PollutantEmissionResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReceptorBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    height: float = 0.0
    marker_symbol: str = "monitor"
    marker_color: str = "#2196F3"
    is_active: bool = True

class ReceptorCreate(ReceptorBase):
    pass

class ReceptorUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    height: Optional[float] = None
    marker_symbol: Optional[str] = None
    marker_color: Optional[str] = None
    is_active: Optional[bool] = None

class ReceptorResponse(ReceptorBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MeteorologyBase(BaseModel):
    name: str
    wind_speed: float = 2.0
    wind_direction: float = 0.0
    boundary_layer_height: float = 1000.0
    stability_class: str = "D"
    temperature: float = 293.15
    humidity: float = 50.0
    record_time: Optional[datetime] = None

class MeteorologyCreate(MeteorologyBase):
    pass

class MeteorologyUpdate(BaseModel):
    name: Optional[str] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    boundary_layer_height: Optional[float] = None
    stability_class: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    record_time: Optional[datetime] = None

class MeteorologyResponse(MeteorologyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MarkerConfigBase(BaseModel):
    type: str
    symbol: str = "circle"
    color: str = "#FF5722"
    size: int = 10

class MarkerConfigCreate(MarkerConfigBase):
    pass

class MarkerConfigUpdate(BaseModel):
    symbol: Optional[str] = None
    color: Optional[str] = None
    size: Optional[int] = None

class MarkerConfigResponse(MarkerConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class SimulationRequest(BaseModel):
    meteorology_id: int
    source_ids: Optional[List[int]] = None
    receptor_ids: Optional[List[int]] = None
    pollutant_type: Optional[str] = None
    grid_resolution: float = 100.0
    domain_size: float = 10000.0

class ContributionResult(BaseModel):
    source_id: int
    source_name: str
    concentration: float
    percentage: float

class SimulationResult(BaseModel):
    concentrations: List[List[float]]
    grid_lat: List[float]
    grid_lon: List[float]
    contributions: List[dict]
    receptor_contributions: dict[str, dict[str, List[dict]]]
    pollutant_concentrations: Optional[dict[str, List[List[float]]]] = None
    available_pollutants: Optional[List[str]] = None

class PollutantTypeInfo(BaseModel):
    type: str
    name: str
    unit: str
    description: str

class MarkerSymbolInfo(BaseModel):
    symbol: str
    name: str
    icon: str
