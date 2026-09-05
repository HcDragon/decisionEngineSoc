"""
FastAPI Router for Smart SOC Decision Engine.
Re-exports the production-grade application from decision_engine.api.routes.
"""
from decision_engine.api.routes import app, decision_manager, db, event_bus, INCIDENTS_DB

__all__ = ["app", "decision_manager", "db", "event_bus", "INCIDENTS_DB"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
