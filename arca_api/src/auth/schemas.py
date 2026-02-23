"""
Schemas Pydantic para autenticación
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime


class UserCreate(BaseModel):
    """Schema para crear un nuevo usuario"""
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="Password mínimo 8 caracteres"
    )


class UserUpdate(BaseModel):
    """Schema para actualizar usuario (opcional)"""
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Schema de respuesta con información del usuario (sin password)"""
    id: int
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema de respuesta con JWT token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")


class TokenData(BaseModel):
    """Datos extraídos del token JWT (para uso interno)"""
    user_id: int | None = None
    email: str | None = None
