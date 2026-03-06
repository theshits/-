from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import numpy as np
from backend.database import get_db
from backend.models.models import EmissionSource, Receptor, Meteorology
from backend.models.schemas import SimulationRequest, SimulationResult
from backend.core.gaussian_plume import GaussianPlumeModel

router = APIRouter()

@router.post("/run", response_model=SimulationResult)
def run_simulation(request: SimulationRequest, db: Session = Depends(get_db)):
    meteorology = db.query(Meteorology).filter(
        Meteorology.id == request.meteorology_id
    ).first()
    if not meteorology:
        raise HTTPException(status_code=404, detail="气象场未找到")
    
    if request.source_ids:
        sources = db.query(EmissionSource).filter(
            EmissionSource.id.in_(request.source_ids)
        ).all()
    else:
        sources = db.query(EmissionSource).filter(EmissionSource.is_active == True).all()
    
    if not sources:
        raise HTTPException(status_code=400, detail="没有可用的排放源")
    
    if request.receptor_ids:
        receptors = db.query(Receptor).filter(
            Receptor.id.in_(request.receptor_ids)
        ).all()
    else:
        receptors = db.query(Receptor).filter(Receptor.is_active == True).all()
    
    model = GaussianPlumeModel(
        wind_speed=meteorology.wind_speed,
        wind_direction=meteorology.wind_direction,
        stability_class=meteorology.stability_class,
        temperature=meteorology.temperature,
        boundary_layer_height=meteorology.boundary_layer_height
    )
    
    all_lats = [s.latitude for s in sources] + [r.latitude for r in receptors]
    all_lons = [s.longitude for s in sources] + [r.longitude for r in receptors]
    
    if not all_lats:
        raise HTTPException(status_code=400, detail="没有有效的坐标数据")
    
    min_lat, max_lat = min(all_lats), max(all_lats)
    min_lon, max_lon = min(all_lons), max(all_lons)
    
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    grid_resolution = request.grid_resolution
    domain_size = request.domain_size
    
    lat_span = max_lat - min_lat
    lon_span = max_lon - min_lon
    
    meters_per_degree = 111000
    required_lat_range = max(domain_size / meters_per_degree, lat_span * 1.5 + 0.1)
    required_lon_range = max(domain_size / (meters_per_degree * np.cos(np.radians(center_lat))), lon_span * 1.5 + 0.1)
    
    grid_points = int(max(required_lat_range, required_lon_range) * meters_per_degree / grid_resolution)
    grid_points = max(grid_points, 50)
    grid_points = min(grid_points, 500)
    
    grid_lat = np.linspace(center_lat - required_lat_range/2, center_lat + required_lat_range/2, grid_points)
    grid_lon = np.linspace(center_lon - required_lon_range/2, center_lon + required_lon_range/2, grid_points)
    
    total_concentration = np.zeros((grid_points, grid_points))
    source_contributions = []
    source_conc_fields = []
    source_pollutant_conc_fields = []
    pollutant_concentrations = {}
    all_pollutants = set()
    
    pollutant_type = request.pollutant_type
    
    for source in sources:
        source_pollutant_data = {}
        total_emission_rate = 0.0
        source_pollutants = []
        
        if source.pollutants:
            for p in source.pollutants:
                if pollutant_type:
                    if p.pollutant_type == pollutant_type:
                        total_emission_rate += p.emission_rate
                        source_pollutants.append(p.pollutant_type)
                        if p.pollutant_type not in source_pollutant_data:
                            source_pollutant_data[p.pollutant_type] = 0
                        source_pollutant_data[p.pollutant_type] += p.emission_rate
                        all_pollutants.add(p.pollutant_type)
                else:
                    total_emission_rate += p.emission_rate
                    source_pollutants.append(p.pollutant_type)
                    if p.pollutant_type not in source_pollutant_data:
                        source_pollutant_data[p.pollutant_type] = 0
                    source_pollutant_data[p.pollutant_type] += p.emission_rate
                    all_pollutants.add(p.pollutant_type)
        
        if total_emission_rate <= 0:
            continue
        
        source_conc = model.calculate_concentration_field(
            source_lat=source.latitude,
            source_lon=source.longitude,
            source_height=source.height,
            emission_rate=total_emission_rate,
            grid_lat=grid_lat,
            grid_lon=grid_lon,
            temperature=source.temperature,
            velocity=source.velocity,
            diameter=source.diameter
        )
        
        total_concentration += source_conc
        source_conc_fields.append(source_conc)
        
        source_p_conc = {}
        for p_type, p_rate in source_pollutant_data.items():
            if p_rate > 0:
                p_conc = model.calculate_concentration_field(
                    source_lat=source.latitude,
                    source_lon=source.longitude,
                    source_height=source.height,
                    emission_rate=p_rate,
                    grid_lat=grid_lat,
                    grid_lon=grid_lon,
                    temperature=source.temperature,
                    velocity=source.velocity,
                    diameter=source.diameter
                )
                source_p_conc[p_type] = p_conc
                if p_type not in pollutant_concentrations:
                    pollutant_concentrations[p_type] = np.zeros((grid_points, grid_points))
                pollutant_concentrations[p_type] += p_conc
        
        source_pollutant_conc_fields.append(source_p_conc)
        
        total_mass = np.sum(source_conc)
        source_contributions.append({
            "source_id": source.id,
            "source_name": source.name,
            "total_concentration": float(total_mass),
            "max_concentration": float(np.max(source_conc)),
            "pollutants": list(set(source_pollutants)) if source_pollutants else ["Unknown"]
        })
    
    receptor_contributions = {}
    for receptor in receptors:
        pollutant_receptor_data = {}
        
        for p_type in all_pollutants:
            p_source_data = []
            p_total = 0.0
            
            for source in sources:
                source_emission_rate = 0.0
                if source.pollutants:
                    for p in source.pollutants:
                        if p.pollutant_type == p_type:
                            source_emission_rate += p.emission_rate
                
                if source_emission_rate > 0:
                    conc = model.calculate_receptor_concentration(
                        source_lat=source.latitude,
                        source_lon=source.longitude,
                        source_height=source.height,
                        emission_rate=source_emission_rate,
                        receptor_lat=receptor.latitude,
                        receptor_lon=receptor.longitude,
                        receptor_height=receptor.height,
                        temperature=source.temperature,
                        velocity=source.velocity,
                        diameter=source.diameter
                    )
                    if conc < 1e-6:
                        conc = 0.0
                    p_total += conc
                    p_source_data.append({
                        "source_id": source.id,
                        "source_name": source.name,
                        "concentration": float(conc),
                        "pollutant": p_type
                    })
            
            for item in p_source_data:
                item["percentage"] = (item["concentration"] / p_total * 100) if p_total > 0 else 0
            
            p_source_data.sort(key=lambda x: x["concentration"], reverse=True)
            pollutant_receptor_data[p_type] = p_source_data
        
        receptor_contributions[receptor.name] = pollutant_receptor_data
    
    pollutant_conc_dict = {p: c.tolist() for p, c in pollutant_concentrations.items()}
    available_pollutants = list(all_pollutants) if all_pollutants else None
    
    return SimulationResult(
        concentrations=total_concentration.tolist(),
        grid_lat=grid_lat.tolist(),
        grid_lon=grid_lon.tolist(),
        contributions=[],
        receptor_contributions=receptor_contributions,
        pollutant_concentrations=pollutant_conc_dict if pollutant_conc_dict else None,
        available_pollutants=available_pollutants
    )

@router.get("/preview/{meteorology_id}/{source_id}")
def preview_plume(
    meteorology_id: int, 
    source_id: int, 
    domain_size: float = 5000.0,
    grid_resolution: float = 50.0,
    db: Session = Depends(get_db)
):
    meteorology = db.query(Meteorology).filter(
        Meteorology.id == meteorology_id
    ).first()
    if not meteorology:
        raise HTTPException(status_code=404, detail="气象场未找到")
    
    source = db.query(EmissionSource).filter(EmissionSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="排放源未找到")
    
    total_emission_rate = 0.0
    if source.pollutants:
        for p in source.pollutants:
            total_emission_rate += p.emission_rate
    
    if total_emission_rate <= 0:
        total_emission_rate = 1.0
    
    model = GaussianPlumeModel(
        wind_speed=meteorology.wind_speed,
        wind_direction=meteorology.wind_direction,
        stability_class=meteorology.stability_class,
        temperature=meteorology.temperature,
        boundary_layer_height=meteorology.boundary_layer_height
    )
    
    meters_per_degree = 111000
    grid_points = int(domain_size / grid_resolution)
    
    lat_range = domain_size / meters_per_degree
    lon_range = domain_size / (meters_per_degree * np.cos(np.radians(source.latitude)))
    
    grid_lat = np.linspace(
        source.latitude - lat_range/2, 
        source.latitude + lat_range/2, 
        grid_points
    )
    grid_lon = np.linspace(
        source.longitude - lon_range/2, 
        source.longitude + lon_range/2, 
        grid_points
    )
    
    concentration = model.calculate_concentration_field(
        source_lat=source.latitude,
        source_lon=source.longitude,
        source_height=source.height,
        emission_rate=total_emission_rate,
        grid_lat=grid_lat,
        grid_lon=grid_lon,
        temperature=source.temperature,
        velocity=source.velocity,
        diameter=source.diameter
    )
    
    return {
        "concentrations": concentration.tolist(),
        "grid_lat": grid_lat.tolist(),
        "grid_lon": grid_lon.tolist(),
        "source": {
            "id": source.id,
            "name": source.name,
            "latitude": source.latitude,
            "longitude": source.longitude
        },
        "meteorology": {
            "wind_speed": meteorology.wind_speed,
            "wind_direction": meteorology.wind_direction,
            "stability_class": meteorology.stability_class
        }
    }
