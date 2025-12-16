"""
Gold Signal API - Main Entry Point

This is a placeholder file. Full implementation coming in Phase 2.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Gold Signal API",
    description="Backend API for The Gold Trader's Edge platform",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Gold Signal API",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Placeholder routes - to be implemented
@app.get("/signals")
async def get_signals():
    return {
        "message": "Coming soon",
        "signals": []
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
