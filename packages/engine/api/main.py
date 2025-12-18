"""
Gold Trader's Edge - FastAPI Backend
Main application entry point for the trading signals API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from api.routers import signals, market, analytics
from api.core.config import settings

# Create FastAPI app
app = FastAPI(
    title="Gold Trader's Edge API",
    description="Real-time gold trading signals based on 6 proven rules",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(signals.router, prefix="/v1/signals", tags=["Signals"])
app.include_router(market.router, prefix="/v1/market", tags=["Market Data"])
app.include_router(analytics.router, prefix="/v1/analytics", tags=["Analytics"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Gold Trader's Edge API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs",
        "endpoints": {
            "signals": "/v1/signals/latest",
            "market": "/v1/market/ohlcv",
            "analytics": "/v1/analytics/summary"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
