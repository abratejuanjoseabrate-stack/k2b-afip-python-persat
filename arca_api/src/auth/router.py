"""
Router de autenticación
Endpoints: /register, /login, /me
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..config import settings
from . import schemas, models, service
from .dependencies import get_current_user
from ..shared.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register(
    user_in: schemas.UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Registrar un nuevo usuario
    
    Crea un usuario con email y password hasheado.
    El email debe ser único.
    """
    logger.info(f"Intento de registro: email={user_in.email}")
    
    # Verificar si el email ya existe
    result = await db.execute(
        select(models.User).where(models.User.email == user_in.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.warning(f"Intento de registro con email existente: {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Crear nuevo usuario
    user = models.User(
        email=user_in.email,
        hashed_password=service.hash_password(user_in.password)
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"Usuario registrado exitosamente: email={user.email}, id={user.id}")
    
    return user


@router.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Login y obtener JWT token
    
    Nota: OAuth2PasswordRequestForm usa 'username' como campo,
    pero en nuestro caso lo usamos para el email.
    
    Form data:
    - username: email del usuario
    - password: contraseña
    """
    logger.info(f"Intento de login: email={form_data.username}")
    
    # Buscar usuario por email
    result = await db.execute(
        select(models.User).where(models.User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    # Verificar credenciales
    if not user or not service.verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Login fallido: email={form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar si el usuario está activo
    if not user.is_active:
        logger.warning(f"Login fallido: usuario inactivo, email={user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive"
        )
    
    # Crear access token
    access_token = service.create_access_token(data={"sub": str(user.id)})
    
    logger.info(f"Login exitoso: email={user.email}, id={user.id}")
    
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Obtener información del usuario actual autenticado
    
    Requiere token JWT válido en el header Authorization.
    """
    return current_user
