from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models.models import Meteorology
from backend.models.schemas import (
    MeteorologyCreate, 
    MeteorologyUpdate, 
    MeteorologyResponse
)

router = APIRouter()

@router.get("/", response_model=List[MeteorologyResponse])
def get_meteorologies(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    meteorologies = db.query(Meteorology).offset(skip).limit(limit).all()
    return meteorologies

@router.get("/{met_id}", response_model=MeteorologyResponse)
def get_meteorology(met_id: int, db: Session = Depends(get_db)):
    meteorology = db.query(Meteorology).filter(Meteorology.id == met_id).first()
    if not meteorology:
        raise HTTPException(status_code=404, detail="气象场未找到")
    return meteorology

@router.post("/", response_model=MeteorologyResponse)
def create_meteorology(meteorology: MeteorologyCreate, db: Session = Depends(get_db)):
    db_meteorology = Meteorology(**meteorology.model_dump())
    db.add(db_meteorology)
    db.commit()
    db.refresh(db_meteorology)
    return db_meteorology

@router.put("/{met_id}", response_model=MeteorologyResponse)
def update_meteorology(
    met_id: int, 
    meteorology: MeteorologyUpdate, 
    db: Session = Depends(get_db)
):
    db_meteorology = db.query(Meteorology).filter(Meteorology.id == met_id).first()
    if not db_meteorology:
        raise HTTPException(status_code=404, detail="气象场未找到")
    
    update_data = meteorology.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_meteorology, key, value)
    
    db.commit()
    db.refresh(db_meteorology)
    return db_meteorology

@router.delete("/{met_id}")
def delete_meteorology(met_id: int, db: Session = Depends(get_db)):
    db_meteorology = db.query(Meteorology).filter(Meteorology.id == met_id).first()
    if not db_meteorology:
        raise HTTPException(status_code=404, detail="气象场未找到")
    
    db.delete(db_meteorology)
    db.commit()
    return {"message": "气象场已删除", "id": met_id}

@router.post("/batch", response_model=List[MeteorologyResponse])
def create_meteorologies_batch(
    meteorologies: List[MeteorologyCreate], 
    db: Session = Depends(get_db)
):
    db_meteorologies = [Meteorology(**met.model_dump()) for met in meteorologies]
    db.add_all(db_meteorologies)
    db.commit()
    for met in db_meteorologies:
        db.refresh(met)
    return db_meteorologies
