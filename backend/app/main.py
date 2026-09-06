
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routers import mps, projects, analytics, live_prediction

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MPLADS AI Risk Intelligence API",
    version="0.1.0",
    description="Development API for the SIH26102 MPLADS risk/anomaly platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mps.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(live_prediction.router, prefix="/api")

@app.get("/")
def root():
    return {
        "name": "MPLADS AI Risk Intelligence API",
        "status": "running",
        "docs": "/docs",
    }

@app.get("/health")
def health():
    return {"status": "ok"}
