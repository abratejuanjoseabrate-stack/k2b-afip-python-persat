"""
Dependencies para autenticación
Protege rutas requiriendo usuario autenticado
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from . import models, service
from ..shared.logging_config import get_logger

logger = get_logger(__name__)

# OAuth2 scheme para extraer token del header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    Dependency para obtener el usuario actual desde JWT token
    
    Uso en routers:
        @router.get("/protected")
        async def protected_route(
            current_user: User = Depends(get_current_user)
        ):
            return {"user_id": current_user.id}
    
    Args:
        token: JWT token extraído del header Authorization
        db: Sesión de base de datos
    
    Returns:
        Usuario autenticado
    
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe/está inactivo
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decodificar token
    payload = service.decode_token(token)
    if payload is None:
        logger.warning("Token inválido o expirado")
        raise credentials_exception
    
    # Obtener user_id del token
    user_id = payload.get("sub")
    if user_id is None:
        logger.warning("Token sin user_id (sub)")
        raise credentials_exception
    
    # Buscar usuario en base de datos
    result = await db.execute(
        select(models.User).where(models.User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"Usuario no encontrado: user_id={user_id}")
        raise credentials_exception
    
    if not user.is_active:
        logger.warning(f"Usuario inactivo intentando acceder: user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    logger.debug(f"Usuario autenticado: {user.email} (id={user.id})")
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Dependency adicional que garantiza que el usuario esté activo
    
    Es redundante con get_current_user (que ya verifica is_active),
    pero puede ser útil para claridad en algunos endpoints.
    """
    return current_user
