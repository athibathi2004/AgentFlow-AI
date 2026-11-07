"""FastAPI application entrypoint for AgentFlow AI."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1.api import api_router
from app.config import settings
from app.core.exceptions import AgentFlowError
from app.core.logging import get_logger, setup_logging
from app.db.session import close_db, init_db
from app.mcp.manager import MCPConnectionManager

setup_logging(json_logs=False, level="INFO")
logger = get_logger("agentflow.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: database initialization and MCP synchronization."""
    logger.info("Initializing AgentFlow AI platform...")
    await init_db()
    logger.info("Database schemas verified.")

    # Synchronize MCP tools to registry
    mcp_manager = MCPConnectionManager.get_instance()
    synced_count = await mcp_manager.sync_tools_to_registry()
    logger.info(f"Model Context Protocol: Synchronized {synced_count} MCP tools.")

    yield

    logger.info("Shutting down AgentFlow AI platform...")
    await close_db()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Global Exception Handler
@app.exception_handler(AgentFlowError)
async def agentflow_exception_handler(request: Request, exc: AgentFlowError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_type": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


# Mount Frontend Dashboard Static Assets
frontend_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/ui", include_in_schema=False)
    async def serve_ui() -> FileResponse:
        return FileResponse(os.path.join(frontend_dir, "index.html"))

