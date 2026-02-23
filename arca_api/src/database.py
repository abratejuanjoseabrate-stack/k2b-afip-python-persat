"""
Configuración de base de datos con SQLAlchemy 2.0 async
Usa SQLite para desarrollo (fácil migración a MySQL después)
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings
from .shared.logging_config import get_logger

logger = get_logger(__name__)

# Crear engine async
# SQLite requiere connect_args={"check_same_thread": False} para async
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG if hasattr(settings, "DEBUG") else False,
    connect_args=connect_args,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class para todos los modelos SQLAlchemy"""
    pass


async def get_db():
    """
    Dependency que provee una sesión de base de datos
    
    Uso en routers:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
