"""
Wrapper de pyafipws.wsaa para autenticación AFIP
Gestiona tickets de acceso (TA) con caché
"""
import os
from pyafipws.wsaa import WSAA
from ..config import settings
from .logging_config import get_logger

logger = get_logger(__name__)


def get_ticket_acceso(service: str = "wsfe", env: str = "homo") -> str:
    """
    Obtiene ticket de acceso (TA) de AFIP.
    Usa caché si el ticket está vigente.
    
    Args:
        service: Servicio AFIP (por defecto "wsfe")
        env: Ambiente ("homo" o "prod")
    
    Returns:
        XML completo del ticket de acceso (TA)
    
    Raises:
        Exception: Si falla la autenticación con AFIP
    """
    wsaa = WSAA()

    cert_path, key_path = settings.get_cert_paths(env)
    cache_path = settings.get_cache_path(env)
    wsdl = settings.get_wsaa_wsdl(env)
    
    logger.debug(f"Obteniendo ticket de acceso para servicio: {service}, ambiente: {env}")
    logger.debug(f"Cert: {cert_path}, Key: {key_path}, WSDL: {wsdl}")
    
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
        logger.error(f"No se pudo obtener ticket de acceso para servicio: {service}, ambiente: {env}")
        raise Exception("No se pudo obtener ticket de acceso de AFIP")
    
    logger.info(f"Ticket de acceso obtenido exitosamente para servicio: {service}, ambiente: {env}")
    
    # wsaa.Autenticar() retorna el XML completo del TA
    # Limpiar posibles espacios/líneas extras al final que causan "junk after document element"
    ta = ta.strip()
    
    # Si el TA tiene múltiples documentos XML o contenido extra, extraer solo el primero
    # El error "junk after document element" ocurre cuando hay contenido después del cierre del elemento raíz
    # Buscar el cierre del elemento raíz principal (loginTicketResponse o credentials)
    if "</loginTicketResponse>" in ta:
        # Extraer hasta el cierre de loginTicketResponse
        end_idx = ta.find("</loginTicketResponse>") + len("</loginTicketResponse>")
        ta = ta[:end_idx]
    elif "</credentials>" in ta:
        # Si viene solo credentials, extraer hasta su cierre
        end_idx = ta.find("</credentials>") + len("</credentials>")
        ta = ta[:end_idx]
    
    # Asegurar que termine correctamente (sin espacios extras)
    ta = ta.strip()
    
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
    Borra los archivos de caché de tickets de acceso (TA) para el ambiente dado.
    Útil cuando AFIP devuelve "El token ha expirado": al borrar el caché,
    la próxima llamada a get_ticket_acceso() solicitará un TA nuevo a AFIP.

    Args:
        env: Ambiente ("homo" o "prod")

    Returns:
        Número de archivos eliminados
    """
    cache_path = settings.get_cache_path(env)
    if not cache_path.exists():
        return 0
    removed = 0
    for f in cache_path.glob("TA-*.xml"):
        try:
            os.remove(f)
            removed += 1
            logger.info(f"Caché TA invalidado: eliminado {f.name} (env={env})")
        except OSError as e:
            logger.warning(f"No se pudo eliminar {f}: {e}")
    return removed
