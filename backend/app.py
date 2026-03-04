from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import init_db
from backend.api import sources, receptors, meteorology, simulation, config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(BASE_DIR, "templates")
static_dir = os.path.join(BASE_DIR, "static")

print(f"Templates directory: {templates_dir}")
print(f"Templates exists: {os.path.exists(templates_dir)}")

templates = Jinja2Templates(directory=templates_dir)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="空气污染扩散模拟平台",
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

app.include_router(sources.router, prefix="/api/sources", tags=["排放源管理"])
app.include_router(receptors.router, prefix="/api/receptors", tags=["受体点管理"])
app.include_router(meteorology.router, prefix="/api/meteorology", tags=["气象场管理"])
app.include_router(simulation.router, prefix="/api/simulation", tags=["扩散模拟"])
app.include_router(config.router, prefix="/api/config", tags=["系统配置"])

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
