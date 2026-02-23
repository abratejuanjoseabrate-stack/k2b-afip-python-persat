"""
Servicio de autenticación JWT
Funciones para hash de passwords, creación y decodificación de tokens
"""
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt

from ..config import settings
from ..shared.logging_config import get_logger

logger = get_logger(__name__)


def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando bcrypt
    
    Args:
        password: Contraseña en texto plano
    
    Returns:
        Contraseña hasheada como string
    """
    # Convertir password a bytes
    password_bytes = password.encode('utf-8')
    # Generar salt y hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Retornar como string
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con el hash
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Contraseña hasheada almacenada
    
    Returns:
        True si coinciden, False en caso contrario
    """
    try:
        # Convertir a bytes
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        # Verificar
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.warning(f"Error verificando password: {e}")
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Crea un JWT token de acceso
    
    Args:
        data: Datos a incluir en el token (típicamente {"sub": user_id})
        expires_delta: Tiempo de expiración personalizado (opcional)
    
    Returns:
        JWT token como string
    """
    to_encode = data.copy()
    
    # Calcular tiempo de expiración
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Crear token
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    logger.debug(f"Token creado para user_id: {data.get('sub')}, expira en: {expire}")
    
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """
    Decodifica y valida un JWT token
    
    Args:
        token: JWT token como string
    
    Returns:
        Payload del token si es válido, None si es inválido o expirado
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Error decodificando token: {e}")
        return None
