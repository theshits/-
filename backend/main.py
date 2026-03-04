from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from contextlib import asynccontextmanager
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db
from backend.api import sources, receptors, meteorology, simulation, config, map

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="空气污染扩散模拟平台 API",
    description="基于高斯扩散模型的空气污染扩散模拟系统",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router, prefix="/api/sources", tags=["排放源管理"])
app.include_router(receptors.router, prefix="/api/receptors", tags=["受体点管理"])
app.include_router(meteorology.router, prefix="/api/meteorology", tags=["气象场管理"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["扩散模拟"])
app.include_router(config.router, prefix="/api/config", tags=["系统配置"])
app.include_router(map.router, prefix="/api/map", tags=["地图数据"])

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request):
    return templates.TemplateResponse("sources.html", {"request": request})

@app.get("/receptors", response_class=HTMLResponse)
async def receptors_page(request: Request):
    return templates.TemplateResponse("receptors.html", {"request": request})

@app.get("/meteorology", response_class=HTMLResponse)
async def meteorology_page(request: Request):
    return templates.TemplateResponse("meteorology.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
