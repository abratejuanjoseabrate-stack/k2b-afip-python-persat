"""
Dependencies para el router de padrón
Usa Dependency Injection de FastAPI para inyectar servicios
"""
from fastapi import Depends, Query, HTTPException
from .service import PadronA4Service, PadronA5Service


def _get_env(env: str = Query("homo", description="Ambiente: 'homo' (homologación) o 'prod' (producción)")) -> str:
    """Valida y retorna el ambiente"""
    if env not in ("homo", "prod"):
        raise HTTPException(status_code=400, detail="env debe ser 'homo' o 'prod'")
    return env


def get_padron_service(env: str = Depends(_get_env)) -> PadronA5Service:
    """
    Dependency para obtener una instancia de PadronA5Service

    FastAPI inyecta automáticamente el servicio en los endpoints que lo requieran.
    """
    return PadronA5Service(env=env)


def get_padron_a4_service(env: str = Depends(_get_env)) -> PadronA4Service:
    """
    Dependency para obtener una instancia de PadronA4Service (Padrón Alcance 4).
    """
    return PadronA4Service(env=env)
