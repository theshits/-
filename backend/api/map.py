from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

SHP_PATH = r"C:\Users\46589\Desktop\gnn\shp\县（等积投影）.shp"
LOAD_SHP_BY_DEFAULT = False

@router.get("/geojson")
async def get_map_geojson():
    if not LOAD_SHP_BY_DEFAULT:
        return JSONResponse(content={"type": "FeatureCollection", "features": []})
    
    try:
        import geopandas as gpd
        from pathlib import Path
        
        shp_path = Path(SHP_PATH)
        if not shp_path.exists():
            logger.warning(f"SHP文件不存在: {SHP_PATH}")
            return JSONResponse(content={"type": "FeatureCollection", "features": []})
        
        gdf = gpd.read_file(shp_path)
        
        if gdf.crs and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        geojson = gdf.__geo_interface__
        
        return JSONResponse(content=geojson)
    except ImportError as e:
        logger.error(f"缺少依赖库: {e}")
        return JSONResponse(content={"type": "FeatureCollection", "features": []})
    except Exception as e:
        logger.error(f"读取SHP文件失败: {e}")
        return JSONResponse(content={"type": "FeatureCollection", "features": []})

@router.get("/bounds")
async def get_map_bounds():
    try:
        import geopandas as gpd
        from pathlib import Path
        
        shp_path = Path(SHP_PATH)
        if not shp_path.exists():
            return {
                "min_lat": 30.0,
                "min_lon": 100.0,
                "max_lat": 40.0,
                "max_lon": 120.0
            }
        
        gdf = gpd.read_file(shp_path)
        
        if gdf.crs and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        bounds = gdf.total_bounds
        
        return {
            "min_lat": float(bounds[1]),
            "min_lon": float(bounds[0]),
            "max_lat": float(bounds[3]),
            "max_lon": float(bounds[2])
        }
    except Exception as e:
        logger.error(f"获取地图边界失败: {e}")
        return {
            "min_lat": 30.0,
            "min_lon": 100.0,
            "max_lat": 40.0,
            "max_lon": 120.0
        }

@router.get("/info")
async def get_map_info():
    try:
        import geopandas as gpd
        from pathlib import Path
        
        shp_path = Path(SHP_PATH)
        if not shp_path.exists():
            return {
                "crs": "EPSG:4326",
                "feature_count": 0,
                "columns": [],
                "bounds": {
                    "min_lat": 30.0,
                    "min_lon": 100.0,
                    "max_lat": 40.0,
                    "max_lon": 120.0
                },
                "error": "SHP文件不存在"
            }
        
        gdf = gpd.read_file(shp_path)
        
        return {
            "crs": str(gdf.crs),
            "feature_count": len(gdf),
            "columns": list(gdf.columns),
            "bounds": {
                "min_lat": float(gdf.total_bounds[1]),
                "min_lon": float(gdf.total_bounds[0]),
                "max_lat": float(gdf.total_bounds[3]),
                "max_lon": float(gdf.total_bounds[2])
            }
        }
    except Exception as e:
        logger.error(f"获取地图信息失败: {e}")
        return {
            "crs": "EPSG:4326",
            "feature_count": 0,
            "columns": [],
            "bounds": {
                "min_lat": 30.0,
                "min_lon": 100.0,
                "max_lat": 40.0,
                "max_lon": 120.0
            },
            "error": str(e)
        }
