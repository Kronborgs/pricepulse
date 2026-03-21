from fastapi import APIRouter

from app.api.v1 import watches, products, shops, history, dashboard, sources, ollama

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(watches.router, prefix="/watches", tags=["watches"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(shops.router, prefix="/shops", tags=["shops"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
# v2 endpoints
api_router.include_router(sources.router, prefix="", tags=["v2"])
api_router.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
