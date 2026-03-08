"""
Dependencies para el router de padrón.
Singleton por ambiente: una sola instancia de PadronA5Service por env para no reconectar en cada request.
"""
import threading
from fastapi import Depends, Query, HTTPException
from .service import PadronA4Service, PadronA5Service

_padron_a5_instances: dict[str, PadronA5Service] = {}
_padron_a5_lock = threading.Lock()

_padron_a4_instances: dict[str, PadronA4Service] = {}
_padron_a4_lock = threading.Lock()


def _get_env(env: str = Query("homo", description="Ambiente: 'homo' (homologación) o 'prod' (producción)")) -> str:
    """Valida y retorna el ambiente"""
    if env not in ("homo", "prod"):
        raise HTTPException(status_code=400, detail="env debe ser 'homo' o 'prod'")
    return env


def get_padron_service(env: str = Depends(_get_env)) -> PadronA5Service:
    """
    Una instancia de PadronA5Service por ambiente (singleton). Evita descargar WSDL y reconectar en cada request.
    """
    with _padron_a5_lock:
        if env not in _padron_a5_instances:
            _padron_a5_instances[env] = PadronA5Service(env=env)
        return _padron_a5_instances[env]


def clear_padron_a5_service(env: str) -> None:
    """
    Elimina el singleton de PadronA5Service para el ambiente dado.
    Útil cuando el token AFIP expira: tras invalidar caché TA, al limpiar aquí
    la próxima llamada a get_padron_service(env) creará una instancia nueva con TA fresco.
    """
    with _padron_a5_lock:
        _padron_a5_instances.pop(env, None)


def get_padron_a4_service(env: str = Depends(_get_env)) -> PadronA4Service:
    """
    Una instancia de PadronA4Service por ambiente (singleton).
    """
    with _padron_a4_lock:
        if env not in _padron_a4_instances:
            _padron_a4_instances[env] = PadronA4Service(env=env)
        return _padron_a4_instances[env]
