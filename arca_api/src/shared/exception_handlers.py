"""
Exception handlers globales para la aplicación FastAPI
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .exceptions import (
    AFIPError,
    AFIPConnectionError,
    AFIPAuthenticationError,
    AFIPValidationError,
    AFIPNotFoundError,
    AFIPServiceError,
)


def _safe_text(value) -> str | None:
    """Convierte bytes a string de forma segura"""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    return str(value)


def _is_debug_enabled(request: Request) -> bool:
    """Verifica si el modo debug está habilitado en el request"""
    debug_param = request.query_params.get("debug", "").lower()
    return debug_param in ("true", "1")


async def afip_error_handler(request: Request, exc: AFIPError) -> JSONResponse:
    """
    Handler global para excepciones de AFIP
    
    Mapea diferentes tipos de errores de AFIP a códigos HTTP apropiados:
    - AFIPConnectionError -> 502 Bad Gateway
    - AFIPAuthenticationError -> 401 Unauthorized
    - AFIPValidationError -> 422 Unprocessable Entity
    - AFIPNotFoundError -> 404 Not Found
    - AFIPServiceError -> 502 Bad Gateway
    - AFIPError (genérico) -> 500 Internal Server Error
    """
    include_debug = _is_debug_enabled(request)
    
    # Determinar código de estado HTTP según el tipo de error
    if isinstance(exc, AFIPConnectionError):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, AFIPAuthenticationError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, AFIPValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, AFIPNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, AFIPServiceError):
        status_code = status.HTTP_502_BAD_GATEWAY
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    # Convertir excepción a diccionario
    error_detail = exc.to_dict(include_debug=include_debug)
    
    return JSONResponse(
        status_code=status_code,
        content={"detail": error_detail}
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler para errores de validación de Pydantic
    
    Mejora el formato de los errores de validación para que sean más legibles
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error.get("loc", [])),
            "message": error.get("msg"),
            "type": error.get("type"),
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Error de validación",
            "errors": errors,
            "body": exc.body if hasattr(exc, "body") else None
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler genérico para excepciones no manejadas
    
    Último recurso para capturar cualquier excepción no esperada
    """
    include_debug = _is_debug_enabled(request)
    
    error_detail = {
        "error": str(exc),
        "type": type(exc).__name__
    }
    
    # En modo debug, incluir más información
    if include_debug:
        import traceback
        error_detail["traceback"] = traceback.format_exc()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": error_detail}
    )
