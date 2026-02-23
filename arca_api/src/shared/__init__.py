"""
Módulo compartido con utilidades y excepciones comunes
"""
from .exceptions import (
    AFIPError,
    AFIPConnectionError,
    AFIPAuthenticationError,
    AFIPValidationError,
    AFIPNotFoundError,
    AFIPServiceError,
)

__all__ = [
    "AFIPError",
    "AFIPConnectionError",
    "AFIPAuthenticationError",
    "AFIPValidationError",
    "AFIPNotFoundError",
    "AFIPServiceError",
]
