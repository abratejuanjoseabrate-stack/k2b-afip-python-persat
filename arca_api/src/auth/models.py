"""
Modelo de usuario para autenticación (SQLAlchemy)
"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class User(Base):
    """
    Modelo de usuario para autenticación
    
    Campos:
    - id: Identificador único
    - email: Email del usuario (único, indexado)
    - hashed_password: Contraseña hasheada con bcrypt
    - is_active: Si el usuario está activo
    - is_superuser: Si es superusuario/admin (opcional)
    - created_at: Fecha de creación
    - updated_at: Fecha de última actualización
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow
    )
