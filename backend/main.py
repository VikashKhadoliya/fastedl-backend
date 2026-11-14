import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.core.config import settings
from backend.routes.api import router as api_router
from backend.routes.admin import router as admin_router
from backend.routes.content import router as content_router
from backend.routes.creator import router as creator_router
from backend.db.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fastedl")

# Initialize database tables and seeds
try:
    init_db()
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade FastEDL (Fast Easy Download Link) media extraction, creator tools and admin CMS API. Download. Create. Grow.",
    version=settings.VERSION
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers under /api
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(content_router, prefix=settings.API_V1_PREFIX)
app.include_router(creator_router, prefix=settings.API_V1_PREFIX)

# Direct aliases for convenient frontend access
app.include_router(admin_router)
app.include_router(content_router)
app.include_router(creator_router)
# Also include at root for backward compatibility with existing GET / and POST /api/validate
app.include_router(api_router)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred while processing your request. Please try again later."
        }
    )
