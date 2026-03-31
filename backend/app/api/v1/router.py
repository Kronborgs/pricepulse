from fastapi import APIRouter

from app.api.v1 import watches, products, shops, history, dashboard, sources, ollama, reports
from app.api.auth.router import router as auth_router
from app.api.v2.ai import router as ai_router
from app.api.v2.admin_data import router as admin_data_router
from app.api.v2.events import router as events_router
from app.api.v2.mail import router as mail_router
from app.api.v2.backup import router as backup_router

api_router = APIRouter()

# ── Auth ──────────────────────────────────────────────────────────────────────
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# ── Dashboard ─────────────────────────────────────────────────────────────────
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# ── v1 (legacy + aktiv) ───────────────────────────────────────────────────────
api_router.include_router(watches.router, prefix="/watches", tags=["watches"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(shops.router, prefix="/shops", tags=["shops"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

# ── v2 ────────────────────────────────────────────────────────────────────────
api_router.include_router(sources.router, prefix="", tags=["v2-sources"])
api_router.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai-jobs"])
api_router.include_router(events_router, prefix="", tags=["sse"])
api_router.include_router(mail_router, prefix="", tags=["mail"])
api_router.include_router(admin_data_router, prefix="", tags=["admin-data"])
api_router.include_router(backup_router, prefix="", tags=["backup"])

