"""
Wrapper de pyafipws.wsaa para autenticación AFIP
Gestiona tickets de acceso (TA) con caché en memoria (TTL 10 h) + archivos (pyafipws).
Al invalidar (token expirado) se limpia memoria y archivos para pedir TA nuevo.
"""
import os
import threading
import time
from pyafipws.wsaa import WSAA
from ..config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

# Cache en memoria: (service, env) -> (ta_xml_string, timestamp). TTL 10 h para renovar antes de las ~12 h de AFIP.
_TA_MEMORY_CACHE: dict[tuple[str, str], tuple[str, float]] = {}
_TA_CACHE_LOCK = threading.Lock()
_TA_CACHE_TTL_SEC = 10 * 3600  # 10 horas


def _normalize_ta(ta: str) -> str:
    """Limpia el XML del TA para evitar 'junk after document element'."""
    ta = (ta or "").strip()
    if "</loginTicketResponse>" in ta:
        end_idx = ta.find("</loginTicketResponse>") + len("</loginTicketResponse>")
        ta = ta[:end_idx]
    elif "</credentials>" in ta:
        end_idx = ta.find("</credentials>") + len("</credentials>")
        ta = ta[:end_idx]
    return ta.strip()


def get_ticket_acceso(service: str = "wsfe", env: str = "homo") -> str:
    """
    Obtiene ticket de acceso (TA) de AFIP.
    Usa caché en memoria (TTL 10 h) para no llamar a WSAA en cada request.
    Si el TA está vencido en memoria, usa caché en disco de pyafipws o pide uno nuevo a AFIP.
    
    Args:
        service: Servicio AFIP (por defecto "wsfe")
        env: Ambiente ("homo" o "prod")
    
    Returns:
        XML completo del ticket de acceso (TA)
    
    Raises:
        Exception: Si falla la autenticación con AFIP
    """
    key = (service, env)
    now = time.time()
    with _TA_CACHE_LOCK:
        entry = _TA_MEMORY_CACHE.get(key)
        if entry:
            ta_cached, ts = entry
            if (now - ts) < _TA_CACHE_TTL_SEC:
                logger.debug(f"TA desde caché en memoria para {service}/{env}")
                return ta_cached
            # Expirado en memoria; quitar para pedir uno nuevo
            _TA_MEMORY_CACHE.pop(key, None)

    wsaa = WSAA()
    cert_path, key_path = settings.get_cert_paths(env)
    cache_path = settings.get_cache_path(env)
    wsdl = settings.get_wsaa_wsdl(env)

    logger.debug(f"Obteniendo ticket de acceso para servicio: {service}, ambiente: {env}")
    ta = wsaa.Autenticar(
        service,
        str(cert_path),
        str(key_path),
        wsdl=wsdl,
        cache=str(cache_path),
        debug=settings.AFIP_DEBUG_WSAA,
    )

    if not ta:
        logger.error(f"No se pudo obtener ticket de acceso para servicio: {service}, ambiente: {env}")
        raise Exception("No se pudo obtener ticket de acceso de AFIP")

    logger.info(f"Ticket de acceso obtenido para servicio: {service}, ambiente: {env}")
    ta = _normalize_ta(ta)

    with _TA_CACHE_LOCK:
        _TA_MEMORY_CACHE[key] = (ta, now)

    return ta


def get_token_sign(service: str = "wsfe", env: str = "homo") -> tuple[str, str]:
    """
    Obtiene token y sign de autenticación AFIP.
    Útil para verificación y debugging.
    
    Args:
        service: Servicio AFIP (por defecto "wsfe")
        env: Ambiente ("homo" o "prod")
    
    Returns:
        Tuple (token, sign) del ticket de acceso
    
    Raises:
        Exception: Si falla la autenticación con AFIP
    """
    wsaa = WSAA()

    cert_path, key_path = settings.get_cert_paths(env)
    cache_path = settings.get_cache_path(env)
    wsdl = settings.get_wsaa_wsdl(env)
    
    logger.debug(f"Obteniendo token/sign para servicio: {service}, ambiente: {env}")
    
    # Autenticar con AFIP (usa caché automático de pyafipws)
    ta = wsaa.Autenticar(
        service,
        str(cert_path),
        str(key_path),
        wsdl=wsdl,
        cache=str(cache_path),
        debug=settings.AFIP_DEBUG_WSAA,
    )
    
    if not ta:
        logger.error(f"No se pudo obtener ticket de acceso para token/sign, servicio: {service}, ambiente: {env}")
        raise Exception("No se pudo obtener ticket de acceso de AFIP")
    
    # Extraer token y sign del objeto wsaa
    token = getattr(wsaa, "Token", "")
    sign = getattr(wsaa, "Sign", "")
    
    if not token or not sign:
        logger.error("Token o Sign vacíos en respuesta de AFIP")
        raise Exception("Token o Sign vacíos en respuesta de AFIP")
    
    logger.debug("Token y Sign obtenidos exitosamente")
    return token, sign


def invalidar_cache_ta(env: str = "homo") -> int:
    """
    Borra el caché de TA (memoria + archivos) para el ambiente dado.
    Útil cuando AFIP devuelve "El token ha expirado": la próxima llamada
    a get_ticket_acceso() pedirá un TA nuevo a AFIP.

    Args:
        env: Ambiente ("homo" o "prod")

    Returns:
        Número de archivos eliminados (en disco)
    """
    with _TA_CACHE_LOCK:
        to_drop = [k for k in _TA_MEMORY_CACHE if k[1] == env]
        for k in to_drop:
            del _TA_MEMORY_CACHE[k]
        if to_drop:
            logger.info(f"Caché TA en memoria invalidado para env={env} ({len(to_drop)} entrada(s))")

    cache_path = settings.get_cache_path(env)
    if not cache_path.exists():
        return 0
    removed = 0
    for f in cache_path.glob("TA-*.xml"):
        try:
            os.remove(f)
            removed += 1
            logger.info(f"Caché TA en disco invalidado: eliminado {f.name} (env={env})")
        except OSError as e:
            logger.warning(f"No se pudo eliminar {f}: {e}")
    return removed
