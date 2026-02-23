"""
Dependencies para el router de facturas
Usa Dependency Injection de FastAPI para inyectar servicios
"""
from fastapi import Depends, Query, HTTPException
from .service import WSFEv1Service


def _get_env(env: str = Query("homo", description="Ambiente: 'homo' (homologación) o 'prod' (producción)")) -> str:
    """Valida y retorna el ambiente"""
    if env not in ("homo", "prod"):
        raise HTTPException(status_code=400, detail="env debe ser 'homo' o 'prod'")
    return env


def get_wsfev1_service(env: str = Depends(_get_env)) -> WSFEv1Service:
    """
    Dependency para obtener una instancia de WSFEv1Service
    
    FastAPI inyecta automáticamente el servicio en los endpoints que lo requieran.
    Esto permite:
    - Reutilización de la conexión
    - Testing más fácil (puedes mockear la dependencia)
    - Separación de responsabilidades
    """
    return WSFEv1Service(env=env)
