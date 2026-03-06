"""
Aplicación FastAPI principal - Nueva estructura por dominio
Wrapper REST sobre pyafipws
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .config import settings
from .facturas.router import router as facturas_router
from .padron.router import router as padron_router
from .auth.router import router as auth_router
from .shared.exceptions import AFIPError
from .shared.exception_handlers import (
    afip_error_handler,
    validation_error_handler,
    generic_exception_handler,
)
from .shared.logging_config import setup_logging, get_logger

# Configurar logging al importar el módulo
log_file = Path(settings.LOG_FILE) if settings.LOG_FILE else None
setup_logging(level=settings.LOG_LEVEL, log_file=log_file)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events: startup y shutdown de la aplicación
    
    Startup:
    - Valida que existan los certificados necesarios
    - Crea directorios de cache si no existen
    - Crea tablas de base de datos si no existen
    
    Shutdown:
    - Cleanup si es necesario (actualmente no hay nada que limpiar)
    """
    # Startup
    logger.info(f"Iniciando {settings.API_TITLE} v{settings.API_VERSION}")
    logger.info(f"CUIT: {settings.CUIT}")
    logger.info(f"Punto de venta: {settings.PTO_VTA}")
    
    # Validar que existan los certificados para homologación
    cert_path, key_path = settings.get_cert_paths("homo")
    if not cert_path.exists():
        logger.warning(f"Certificado de homologación no encontrado: {cert_path}")
    if not key_path.exists():
        logger.warning(f"Clave de homologación no encontrada: {key_path}")
    
    # Crear directorios de cache si no existen
    cache_path = settings.get_cache_path("homo")
    cache_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Cache path: {cache_path}")
    
    # Crear tablas de base de datos si no existen
    from .database import engine, Base, async_session
    from sqlalchemy import select
    async with engine.begin() as conn:
        logger.info("Creando tablas de base de datos si no existen...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tablas de base de datos verificadas/creadas")

    # Seed: si no hay usuarios y están definidos PADRON_SERVICE_EMAIL/PASSWORD, crear usuario de servicio
    email = (settings.PADRON_SERVICE_EMAIL or "").strip()
    password = (settings.PADRON_SERVICE_PASSWORD or "").strip()
    if email and password:
        from .auth.models import User
        from .auth.service import hash_password
        async with async_session() as session:
            result = await session.execute(select(User).limit(1))
            if result.scalar_one_or_none() is None:
                user = User(
                    email=email,
                    hashed_password=hash_password(password),
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                logger.info("Usuario de servicio creado (email=%s) para proxy de padrón", email)
    
    logger.info("Aplicación lista")
    
    yield
    
    # Shutdown (cleanup si es necesario)
    logger.info("Cerrando aplicación")


app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url=settings.API_DOCS_URL,
    redoc_url=settings.API_REDOC_URL,
    lifespan=lifespan
)

# Exception handlers globales
app.add_exception_handler(AFIPError, afip_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

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

# Routers unificados por dominio (aceptan env como parámetro)
app.include_router(auth_router)
app.include_router(facturas_router)
app.include_router(padron_router)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return JSONResponse(content={
        "status": "ok",
        "version": settings.API_VERSION,
        "cuit": settings.CUIT,
        "punto_venta": settings.PTO_VTA
    })


@app.get("/")
def root():
    """Endpoint raíz"""
    return {
        "message": "PyAfipWs API",
        "version": settings.API_VERSION,
        "docs": settings.API_DOCS_URL,
        "redoc": settings.API_REDOC_URL,
        "endpoints": {
            "auth": "/api/v1/auth",
            "facturas": "/api/v1/facturas",
            "padron": "/api/v1/padron"
        },
        "note": "Los endpoints aceptan el parámetro 'env' (homo/prod) para seleccionar el ambiente"
    }
