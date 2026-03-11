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
    Revisa str(e), faultstring, detail y message por si la excepción SOAP no incluye el mensaje en __str__.
    Mensaje típico: "soap:Server: El token ha expirado, tiempo de generacion [...], tiempo actual [...], tiempo de expiracion [...]"
    """
    def _match(s: str) -> bool:
        if not s:
            return False
        s = s.lower()
        return (
            "expirado" in s
            or "token ha expirado" in s
            or "soap:server" in s
            or ("token" in s and "expiracion" in s)
            or "tiempo de expiracion" in s  # texto exacto del mensaje AFIP
        )

    msg = str(e)
    if _match(msg):
        return True
    for attr in ("faultstring", "fault_string", "detail", "message"):
        val = getattr(e, attr, None)
        if val is not None and _match(str(val)):
            return True
    return False


def invalidar_y_reconectar(env: str) -> None:
    """
    Invalida el caché de tickets de acceso para el ambiente y registra el evento.
    Los servicios deben llamar después a su _conectar() para obtener un TA nuevo.
    """
    n = invalidar_cache_ta(env)
    if n:
        logger.info("Caché TA invalidado para env=%s (%d archivo(s) eliminado(s))", env, n)
