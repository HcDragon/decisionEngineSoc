"""
FastAPI Main Application Factory for AI-Based Smart SOC Manager.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from typing import Literal

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from soc.backend.app.config import settings
from soc.backend.app.db.session import check_db_health, init_db
from soc.backend.app.monitor.streamer import traffic_monitor
from soc.backend.app.api.traffic import router as traffic_router
from soc.backend.app.api.engine import router as engine_router

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("soc.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for application startup and shutdown."""
    logger.info("Initializing AI-Based Smart SOC Manager...")
    logger.info(f"Loaded config from: {settings.config_path}")
    logger.info(f"Model path: {settings.model_path}")
    logger.info(f"Current Automation Mode: {settings.AUTOMATION_MODE}")
    logger.info(f"Configured Executor: {settings.SOC_EXECUTOR} (Lab Mode: {settings.SOC_LAB_MODE})")

    # Initialize / verify database tables
    try:
        init_db()
        if not check_db_health():
            logger.warning("Database connectivity check failed on startup.")
    except Exception as e:
        logger.error(f"Error during DB initialization: {e}")

    # Start network traffic flow monitor on the configured API port
    try:
        traffic_monitor.start(port=settings.API_PORT)
        logger.info(f"NFStream traffic monitor active on port {settings.API_PORT}")
    except Exception as e:
        logger.error(f"Error starting traffic monitor: {e}")

    # Start the virtual-firewall TTL reaper (expires blocks, removes nft rules).
    try:
        from soc.backend.app.response import reaper
        reaper.start()
    except Exception as e:
        logger.error(f"Error starting firewall reaper: {e}")

    yield

    logger.info("Shutting down AI-Based Smart SOC Manager...")
    try:
        traffic_monitor.stop()
    except Exception as e:
        logger.error(f"Error stopping traffic monitor: {e}")
    try:
        from soc.backend.app.response import reaper
        reaper.stop()
    except Exception as e:
        logger.error(f"Error stopping firewall reaper: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="AI-Based Smart SOC Manager API",
        description="Autonomous Decision Engine, Playbook Orchestrator, and Explainable Response System.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(traffic_router)
    app.include_router(engine_router)


    class HealthResponse(BaseModel):
        status: Literal["healthy", "degraded"]
        database: Literal["connected", "disconnected"]
        version: str
        timestamp: datetime
        automation_mode: str

    class SystemStatusResponse(BaseModel):
        environment: str
        automation_mode: str
        executor: str
        lab_mode: bool
        database_connected: bool
        model_dir_exists: bool
        config_dir_exists: bool
        timestamp: datetime

    class AutomationModeRequest(BaseModel):
        automation: Literal["off", "recommend_only", "auto"]

    class AutomationModeResponse(BaseModel):
        automation: str
        message: str
        updated_at: datetime

    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def get_health():
        """Health check endpoint."""
        db_ok = check_db_health()
        return HealthResponse(
            status="healthy" if db_ok else "degraded",
            database="connected" if db_ok else "disconnected",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc),
            automation_mode=settings.AUTOMATION_MODE,
        )

    @app.get("/system/status", response_model=SystemStatusResponse, tags=["System"])
    async def get_system_status():
        """Detailed system operational status."""
        return SystemStatusResponse(
            environment=settings.ENVIRONMENT,
            automation_mode=settings.AUTOMATION_MODE,
            executor=settings.SOC_EXECUTOR,
            lab_mode=settings.SOC_LAB_MODE,
            database_connected=check_db_health(),
            model_dir_exists=settings.model_path.exists(),
            config_dir_exists=settings.config_path.exists(),
            timestamp=datetime.now(timezone.utc),
        )

    @app.post("/system/mode", response_model=AutomationModeResponse, tags=["System"])
    async def set_system_mode(payload: AutomationModeRequest):
        """Update system automation mode (kill switch / guardrail control)."""
        old_mode = settings.AUTOMATION_MODE
        settings.AUTOMATION_MODE = payload.automation
        logger.warning(f"Global automation mode changed from {old_mode} to {payload.automation}")
        return AutomationModeResponse(
            automation=settings.AUTOMATION_MODE,
            message=f"Automation mode updated to {settings.AUTOMATION_MODE}",
            updated_at=datetime.now(timezone.utc),
        )

    @app.post("/system/shutdown", tags=["System"])
    async def shutdown_system():
        """Cleanly terminate the SOC server and background workers."""
        import os
        import signal
        import threading
        import time

        logger.info("Shutdown requested via /system/shutdown endpoint.")

        def _do_exit():
            time.sleep(0.3)
            os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=_do_exit, daemon=True).start()
        return {"status": "shutting_down", "message": "SOC Backend is shutting down cleanly..."}


    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("soc.backend.app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)
