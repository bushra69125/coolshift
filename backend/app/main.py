from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging
import time
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("coolshift")

from .routers import scenarios, optimize, export, weather

app = FastAPI(
    title="CoolShift API",
    description="Intelligent energy-efficient cooling optimization platform — SDG 7 & 13",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.time()
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    elapsed = (time.time() - t0) * 1000
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    logger.log(level, f"← {response.status_code} {request.url.path} ({elapsed:.0f}ms)")
    return response

app.include_router(scenarios.router)
app.include_router(optimize.router)
app.include_router(export.router)
app.include_router(weather.router)

logger.info("✅ CoolShift API started — SDG 7 & 13")
logger.info(f"   Groq AI: {'enabled' if os.getenv('GROQ_API_KEY') else 'disabled (no key)'}")
logger.info(f"   Supabase: {'configured' if os.getenv('SUPABASE_URL') else 'not configured'}")


@app.get("/", tags=["health"])
async def root():
    return JSONResponse({
        "service": "CoolShift Optimization API",
        "version": "1.0.0",
        "status": "running",
        "sdgs": ["SDG 7 — Affordable and Clean Energy", "SDG 13 — Climate Action"],
        "endpoints": {
            "docs": "/docs",
            "scenarios": "/scenarios/upload",
            "optimize": "/optimize/run",
            "export": "/export/excel-all",
            "weather": "/weather/custom-scenario",
        },
    })


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy"}
