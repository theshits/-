from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
import logging
from backend.database import get_db
from backend.models.models import EmissionSource, PollutantEmission, POLLUTANT_TYPES, MARKER_SYMBOLS
from backend.models.schemas import (
    EmissionSourceCreate, 
    EmissionSourceUpdate, 
    EmissionSourceResponse,
    PollutantEmissionResponse,
    PollutantTypeInfo,
    MarkerSymbolInfo
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[EmissionSourceResponse])
def get_sources(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    sources = db.query(EmissionSource).offset(skip).limit(limit).all()
    return sources

@router.get("/pollutant-types/", response_model=List[PollutantTypeInfo])
def get_pollutant_types():
    return [
        PollutantTypeInfo(
            type=k,
            name=v['name'],
            unit=v['unit'],
            description=v['description']
        )
        for k, v in POLLUTANT_TYPES.items()
    ]

@router.get("/marker-symbols/", response_model=List[MarkerSymbolInfo])
def get_marker_symbols():
    return [
        MarkerSymbolInfo(
            symbol=k,
            name=v['name'],
            icon=v['icon']
        )
        for k, v in MARKER_SYMBOLS.items()
    ]

@router.post("/", response_model=EmissionSourceResponse)
def create_source(source: EmissionSourceCreate, db: Session = Depends(get_db)):
    try:
        source_data = source.model_dump(exclude={'pollutants'})
        db_source = EmissionSource(**source_data)
        db.add(db_source)
        db.flush()
        
        for pollutant in source.pollutants:
            db_pollutant = PollutantEmission(
                source_id=db_source.id,
                pollutant_type=pollutant.pollutant_type,
                emission_rate=pollutant.emission_rate
            )
            db.add(db_pollutant)
        
        db.commit()
        db.refresh(db_source)
        return db_source
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"创建排放源失败: {e}")
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"创建排放源失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

@router.post("/batch", response_model=List[EmissionSourceResponse])
def create_sources_batch(
    sources: List[EmissionSourceCreate], 
    db: Session = Depends(get_db)
):
    db_sources = []
    for source in sources:
        source_data = source.model_dump(exclude={'pollutants'})
        db_source = EmissionSource(**source_data)
        db.add(db_source)
        db.flush()
        
        for pollutant in source.pollutants:
            db_pollutant = PollutantEmission(
                source_id=db_source.id,
                pollutant_type=pollutant.pollutant_type,
                emission_rate=pollutant.emission_rate
            )
            db.add(db_pollutant)
        
        db_sources.append(db_source)
    
    db.commit()
    for source in db_sources:
        db.refresh(source)
    return db_sources

@router.get("/{source_id}", response_model=EmissionSourceResponse)
def get_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(EmissionSource).filter(EmissionSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="排放源未找到")
    return source

@router.put("/{source_id}", response_model=EmissionSourceResponse)
def update_source(
    source_id: int, 
    source: EmissionSourceUpdate, 
    db: Session = Depends(get_db)
):
    db_source = db.query(EmissionSource).filter(EmissionSource.id == source_id).first()
    if not db_source:
        raise HTTPException(status_code=404, detail="排放源未找到")
    
    update_data = source.model_dump(exclude_unset=True, exclude={'pollutants'})
    for key, value in update_data.items():
        setattr(db_source, key, value)
    
    if source.pollutants is not None:
        db.query(PollutantEmission).filter(PollutantEmission.source_id == source_id).delete()
        
        for pollutant in source.pollutants:
            db_pollutant = PollutantEmission(
                source_id=source_id,
                pollutant_type=pollutant.pollutant_type,
                emission_rate=pollutant.emission_rate
            )
            db.add(db_pollutant)
    
    db.commit()
    db.refresh(db_source)
    return db_source

@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    db_source = db.query(EmissionSource).filter(EmissionSource.id == source_id).first()
    if not db_source:
        raise HTTPException(status_code=404, detail="排放源未找到")
    
    db.delete(db_source)
    db.commit()
    return {"message": "排放源已删除", "id": source_id}

@router.post("/{source_id}/pollutants/", response_model=PollutantEmissionResponse)
def add_pollutant(
    source_id: int,
    pollutant_type: str,
    emission_rate: float,
    db: Session = Depends(get_db)
):
    db_source = db.query(EmissionSource).filter(EmissionSource.id == source_id).first()
    if not db_source:
        raise HTTPException(status_code=404, detail="排放源未找到")
    
    if pollutant_type not in POLLUTANT_TYPES:
        raise HTTPException(status_code=400, detail="无效的污染物类型")
    
    existing = db.query(PollutantEmission).filter(
        PollutantEmission.source_id == source_id,
        PollutantEmission.pollutant_type == pollutant_type
    ).first()
    
    if existing:
        existing.emission_rate = emission_rate
        db.commit()
        db.refresh(existing)
        return existing
    
    db_pollutant = PollutantEmission(
        source_id=source_id,
        pollutant_type=pollutant_type,
        emission_rate=emission_rate
    )
    db.add(db_pollutant)
    db.commit()
    db.refresh(db_pollutant)
    return db_pollutant

@router.delete("/{source_id}/pollutants/{pollutant_id}")
def delete_pollutant(
    source_id: int,
    pollutant_id: int,
    db: Session = Depends(get_db)
):
    db_pollutant = db.query(PollutantEmission).filter(
        PollutantEmission.id == pollutant_id,
        PollutantEmission.source_id == source_id
    ).first()
    
    if not db_pollutant:
        raise HTTPException(status_code=404, detail="污染物排放记录未找到")
    
    db.delete(db_pollutant)
    db.commit()
    return {"message": "污染物排放记录已删除", "id": pollutant_id}
