# src/main.py
import logging
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

from .config import get_settings
from .database import create_db_and_tables, SessionLocal
from .core.embeddings import load_embedding_model
from .services.matching_service import MatchingService
from .routers import auth_router, profile_router, mentorship_router, frontend_router, matching_router, feedback_router

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Career-Focused Mentorship Matching API",
    description="A lightweight neural-matching pipeline for mentor-mentee recommendations.",
    version="1.0.0",
)

# Static files and templates
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Include routers
app.include_router(auth_router.router)
app.include_router(profile_router.router)
app.include_router(mentorship_router.router)
app.include_router(matching_router.router)  
app.include_router(frontend_router.router)
app.include_router(feedback_router.router)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Application startup event triggered.")
    try:
        create_db_and_tables()
        load_embedding_model()
        
        with SessionLocal() as db:
            matching_service = MatchingService(db)
            matching_service.initialize_faiss_with_mentors()
        
        logger.info("Startup sequence completed successfully.")
    except Exception as e:
        logger.critical(f"Critical error during startup: {e}", exc_info=True)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check FAISS index status
        from .core.vector_store import faiss_index_manager
        faiss_stats = faiss_index_manager.get_stats()
        
        return {
            "status": "healthy",
            "faiss": faiss_stats,
            "embedding_model": settings.EMBEDDING_MODEL_NAME
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}