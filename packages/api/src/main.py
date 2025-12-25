"""
Gold Signal API - Real-Time Signal Integration

Connects to the engine's signal database and provides REST API for web dashboard.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path

from src.database import init_db
from src.routes import signals_router, analytics_router, market_router
from src.routes.settings import router as settings_router

app = FastAPI(
    title="Gold Trader's Edge API",
    description="Real-time gold trading signals and analytics",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include routers
app.include_router(signals_router)
app.include_router(analytics_router)
app.include_router(market_router)
app.include_router(settings_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    init_db()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard HTML"""
    dashboard_path = Path(__file__).parent.parent / "static" / "index.html"

    if dashboard_path.exists():
        return dashboard_path.read_text()
    else:
        return """
        <html>
            <head><title>Gold Trader's Edge</title></head>
            <body>
                <h1>Gold Trader's Edge API</h1>
                <p>API is running. Visit <a href="/docs">/docs</a> for API documentation.</p>
                <p>Dashboard coming soon at <code>/static/index.html</code></p>
            </body>
        </html>
        """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Gold Trader's Edge API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
