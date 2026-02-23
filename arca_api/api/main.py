"""
Aplicación FastAPI principal
Wrapper REST sobre pyafipws

NOTA: Este archivo mantiene la estructura antigua para compatibilidad.
Los nuevos routers unificados están en src/ y se incluyen también.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .routers import facturas_homo, facturas_prod
from .routers import facturas_homo_debug, facturas_prod_debug
from .routers import padron_homo, padron_prod
from .config import settings

# Intentar importar routers unificados de nueva estructura (opcional)
try:
    from src.facturas.router import router as facturas_router_unified
    from src.padron.router import router as padron_router_unified
    NEW_STRUCTURE_AVAILABLE = True
except ImportError:
    NEW_STRUCTURE_AVAILABLE = False

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=settings.API_DOCS_URL,
    redoc_url=settings.API_REDOC_URL
)

# CORS middleware - configurar para tu frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Vue dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers unificados (nueva estructura) - aceptan env como parámetro
if NEW_STRUCTURE_AVAILABLE:
    app.include_router(facturas_router_unified)
    app.include_router(padron_router_unified)

# Routers por ambiente (estructura antigua - mantenida para compatibilidad)
# Homologación
app.include_router(facturas_homo.router, prefix="/homo")
app.include_router(facturas_homo_debug.router, prefix="/homo")
app.include_router(padron_homo.router, prefix="/homo")

# Producción
app.include_router(facturas_prod.router, prefix="/prod")
app.include_router(facturas_prod_debug.router, prefix="/prod")
app.include_router(padron_prod.router, prefix="/prod")


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return JSONResponse(content={
        "status": "ok",
        "version": settings.API_VERSION,
        "cuit": settings.CUIT,
        "punto_venta": settings.PTO_VTA
    })


@app.get("/homo/health")
def health_check_homo():
    """Health check homologación"""
    return JSONResponse(content={
        "status": "ok",
        "env": "homo",
        "version": settings.API_VERSION,
        "cuit": settings.CUIT,
        "punto_venta": settings.PTO_VTA
    })


@app.get("/prod/health")
def health_check_prod():
    """Health check producción"""
    return JSONResponse(content={
        "status": "ok",
        "env": "prod",
        "version": settings.API_VERSION
    })


@app.get("/")
def root():
    """Endpoint raíz"""
    return {
        "message": "PyAfipWs API",
        "version": settings.API_VERSION,
        "docs": settings.API_DOCS_URL,
        "redoc": settings.API_REDOC_URL,
        "homo_base": "/homo",
        "prod_base": "/prod"
    }
