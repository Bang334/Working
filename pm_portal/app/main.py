"""FastAPI Application Entry Point."""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routes.api_routes import router as api_router
from app.routes.view_routes import router as view_router
from app.controllers.eco_prime_controller import router as eco_prime_router
from app.controllers.procurement_controller import router as procurement_router
from app.controllers.receivables_controller import router as receivables_router
from app.controllers.email_controller import router as email_router
from app.controllers.workflow_controller import router as workflow_router
from app.controllers.shipping_documents_controller import router as shipping_documents_router
from app.database import init_db

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

app = FastAPI(
    title="Hong Ming Global PM Portal",
    description="Hệ thống tạo Hợp đồng và Biên bản Nghiệm thu song ngữ Việt - Trung",
    version="2.0.0"
)

# Enable CORS for flexible development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Include routers
app.include_router(view_router)
app.include_router(api_router)
app.include_router(eco_prime_router)
app.include_router(procurement_router)
app.include_router(receivables_router)
app.include_router(email_router)
app.include_router(workflow_router)
app.include_router(shipping_documents_router)




@app.on_event("startup")
def initialize_database_schema():
    """Create tables and apply safe additive schema migrations on startup."""
    init_db()
    from app.services.workflow_service import init_schema
    init_schema()
    from app.services.project_sync_service import init_schema as init_project_schema
    init_project_schema()
    from app.services.workspace_path_service import repair_workspace_paths
    repair_workspace_paths()


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global catch-all exception handler to return clean JSON or error message."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": f"Máy chủ gặp lỗi nội bộ: {str(exc)}",
            "path": str(request.url)
        }
    )
