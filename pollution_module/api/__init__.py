"""
API适配器模块
============

提供多种框架的API适配器，支持快速集成到现有系统

支持的框架:
- FastAPI
- Flask  
- Django
- 通用REST接口

使用示例:
    # FastAPI集成
    from pollution_module.api import create_fastapi_router
    app.include_router(create_fastapi_router(), prefix='/pollution')
    
    # Flask集成
    from pollution_module.api import create_flask_blueprint
    app.register_blueprint(create_flask_blueprint(), url_prefix='/pollution')
    
    # Django集成 (在urls.py中)
    from pollution_module.api import django_urls
    urlpatterns += django_urls
"""

from .fastapi_adapter import create_router as create_fastapi_router
from .flask_adapter import create_blueprint as create_flask_blueprint
from .common import run_simulation_api, get_contribution_api

__all__ = [
    'create_fastapi_router',
    'create_flask_blueprint',
    'run_simulation_api',
    'get_contribution_api'
]
