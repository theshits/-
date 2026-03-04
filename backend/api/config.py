from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models.models import MarkerConfig
from backend.models.schemas import (
    MarkerConfigCreate, 
    MarkerConfigUpdate, 
    MarkerConfigResponse
)

router = APIRouter()

@router.get("/", response_model=List[MarkerConfigResponse])
def get_marker_configs(db: Session = Depends(get_db)):
    configs = db.query(MarkerConfig).all()
    return configs

@router.get("/{config_type}", response_model=MarkerConfigResponse)
def get_marker_config(config_type: str, db: Session = Depends(get_db)):
    config = db.query(MarkerConfig).filter(MarkerConfig.type == config_type).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置未找到")
    return config

@router.post("/", response_model=MarkerConfigResponse)
def create_marker_config(config: MarkerConfigCreate, db: Session = Depends(get_db)):
    existing = db.query(MarkerConfig).filter(MarkerConfig.type == config.type).first()
    if existing:
        raise HTTPException(status_code=400, detail="该类型配置已存在")
    
    db_config = MarkerConfig(**config.model_dump())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config

@router.put("/{config_type}", response_model=MarkerConfigResponse)
def update_marker_config(
    config_type: str, 
    config: MarkerConfigUpdate, 
    db: Session = Depends(get_db)
):
    db_config = db.query(MarkerConfig).filter(MarkerConfig.type == config_type).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="配置未找到")
    
    update_data = config.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)
    
    db.commit()
    db.refresh(db_config)
    return db_config
