"""
Lógica global de reintento cuando AFIP devuelve "token expirado" (WSAA).
Centraliza la detección para que servicios y routers no dupliquen código.
"""
from .afip_auth import invalidar_cache_ta
from .logging_config import get_logger

logger = get_logger(__name__)


def is_token_expirado_error(e: Exception) -> bool:
    """
    Detecta si el error es por token AFIP expirado (soap:Server).
    Usado por WSFEv1Service, PadronA5Service y opcionalmente routers.
    """
    msg = (str(e) or "").lower()
    return "expirado" in msg or "token ha expirado" in msg or "soap:server" in msg


def invalidar_y_reconectar(env: str) -> None:
    """
    Invalida el caché de tickets de acceso para el ambiente y registra el evento.
    Los servicios deben llamar después a su _conectar() para obtener un TA nuevo.
    """
    n = invalidar_cache_ta(env)
    if n:
        logger.info("Caché TA invalidado para env=%s (%d archivo(s) eliminado(s))", env, n)
