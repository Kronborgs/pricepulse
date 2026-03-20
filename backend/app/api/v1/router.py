from fastapi import APIRouter

from app.api.v1 import watches, products, shops, history, dashboard

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(watches.router, prefix="/watches", tags=["watches"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(shops.router, prefix="/shops", tags=["shops"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
