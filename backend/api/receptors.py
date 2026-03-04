from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models.models import Receptor
from backend.models.schemas import (
    ReceptorCreate, 
    ReceptorUpdate, 
    ReceptorResponse
)

router = APIRouter()

@router.get("/", response_model=List[ReceptorResponse])
def get_receptors(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    receptors = db.query(Receptor).offset(skip).limit(limit).all()
    return receptors

@router.get("/{receptor_id}", response_model=ReceptorResponse)
def get_receptor(receptor_id: int, db: Session = Depends(get_db)):
    receptor = db.query(Receptor).filter(Receptor.id == receptor_id).first()
    if not receptor:
        raise HTTPException(status_code=404, detail="受体点未找到")
    return receptor

@router.post("/", response_model=ReceptorResponse)
def create_receptor(receptor: ReceptorCreate, db: Session = Depends(get_db)):
    db_receptor = Receptor(**receptor.model_dump())
    db.add(db_receptor)
    db.commit()
    db.refresh(db_receptor)
    return db_receptor

@router.put("/{receptor_id}", response_model=ReceptorResponse)
def update_receptor(
    receptor_id: int, 
    receptor: ReceptorUpdate, 
    db: Session = Depends(get_db)
):
    db_receptor = db.query(Receptor).filter(Receptor.id == receptor_id).first()
    if not db_receptor:
        raise HTTPException(status_code=404, detail="受体点未找到")
    
    update_data = receptor.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_receptor, key, value)
    
    db.commit()
    db.refresh(db_receptor)
    return db_receptor

@router.delete("/{receptor_id}")
def delete_receptor(receptor_id: int, db: Session = Depends(get_db)):
    db_receptor = db.query(Receptor).filter(Receptor.id == receptor_id).first()
    if not db_receptor:
        raise HTTPException(status_code=404, detail="受体点未找到")
    
    db.delete(db_receptor)
    db.commit()
    return {"message": "受体点已删除", "id": receptor_id}

@router.post("/batch", response_model=List[ReceptorResponse])
def create_receptors_batch(
    receptors: List[ReceptorCreate], 
    db: Session = Depends(get_db)
):
    db_receptors = [Receptor(**receptor.model_dump()) for receptor in receptors]
    db.add_all(db_receptors)
    db.commit()
    for receptor in db_receptors:
        db.refresh(receptor)
    return db_receptors
