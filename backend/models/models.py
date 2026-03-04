from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.database import Base

class EmissionSource(Base):
    __tablename__ = "emission_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    height = Column(Float, nullable=False, default=0.0)
    
    temperature = Column(Float, default=400.0)
    velocity = Column(Float, default=15.0)
    diameter = Column(Float, default=2.0)
    
    marker_symbol = Column(String(50), default="factory")
    marker_color = Column(String(20), default="#FF5722")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    pollutants = relationship("PollutantEmission", back_populates="source", cascade="all, delete-orphan")

class PollutantEmission(Base):
    __tablename__ = "pollutant_emissions"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("emission_sources.id"), nullable=False)
    
    pollutant_type = Column(String(50), nullable=False)
    emission_rate = Column(Float, nullable=False, default=0.0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    source = relationship("EmissionSource", back_populates="pollutants")

POLLUTANT_TYPES = {
    'PM2.5': {'name': 'PM2.5', 'unit': 'g/s', 'description': '细颗粒物'},
    'PM10': {'name': 'PM10', 'unit': 'g/s', 'description': '可吸入颗粒物'},
    'VOCs': {'name': 'VOCs', 'unit': 'g/s', 'description': '挥发性有机物'},
    'SO2': {'name': 'SO2', 'unit': 'g/s', 'description': '二氧化硫'},
    'NOx': {'name': 'NOx', 'unit': 'g/s', 'description': '氮氧化物'},
    'CO': {'name': 'CO', 'unit': 'g/s', 'description': '一氧化碳'},
}

MARKER_SYMBOLS = {
    'factory': {'name': '工厂', 'icon': '🏭'},
    'chimney': {'name': '烟囱', 'icon': '🏭'},
    'industry': {'name': '工业', 'icon': '⚙️'},
    'power': {'name': '电厂', 'icon': '⚡'},
    'chemical': {'name': '化工厂', 'icon': '🧪'},
    'circle': {'name': '圆形', 'icon': '●'},
    'square': {'name': '方形', 'icon': '■'},
    'triangle': {'name': '三角形', 'icon': '▲'},
    'diamond': {'name': '菱形', 'icon': '◆'},
    'star': {'name': '星形', 'icon': '★'},
}

class Receptor(Base):
    __tablename__ = "receptors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    height = Column(Float, nullable=False, default=0.0)
    
    marker_symbol = Column(String(50), default="monitor")
    marker_color = Column(String(20), default="#2196F3")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class Meteorology(Base):
    __tablename__ = "meteorology"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    
    wind_speed = Column(Float, nullable=False, default=2.0)
    wind_direction = Column(Float, nullable=False, default=0.0)
    
    boundary_layer_height = Column(Float, default=1000.0)
    stability_class = Column(String(1), default="D")
    
    temperature = Column(Float, default=293.15)
    humidity = Column(Float, default=50.0)
    
    record_time = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class MarkerConfig(Base):
    __tablename__ = "marker_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False)
    symbol = Column(String(50), default="circle")
    color = Column(String(20), default="#FF5722")
    size = Column(Integer, default=10)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
