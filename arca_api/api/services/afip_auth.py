"""
Wrapper de pyafipws.wsaa para autenticación AFIP
Gestiona tickets de acceso (TA) con caché en disco (pyafipws).
"""
import os
from pyafipws.wsaa import WSAA
from ..config import settings


def _is_token_expirado_message(msg: str) -> bool:
    """Detecta si el mensaje es el error de AFIP 'token expirado'."""
    if not msg:
        return False
    s = msg.lower()
    return (
        "expirado" in s
        or "token ha expirado" in s
        or "soap:server" in s and "expiracion" in s
        or "tiempo de expiracion" in s
    )


def invalidar_cache_ta(env: str = "homo") -> int:
    """
    Borra el caché de TA en disco para el ambiente (archivos TA-*.xml).
    Útil cuando AFIP devuelve "El token ha expirado"; la próxima get_ticket_acceso pedirá un TA nuevo.
    En api/ no hay caché en memoria; solo se limpia disco.
    """
    cache_path = settings.get_cache_path(env)
    if not cache_path.exists():
        return 0
    removed = 0
    for f in cache_path.glob("TA-*.xml"):
        try:
            os.remove(f)
            removed += 1
        except OSError:
            pass
    return removed


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
    cache_path.mkdir(parents=True, exist_ok=True)
    wsdl = settings.get_wsaa_wsdl(env)
    
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
        raise Exception("No se pudo obtener ticket de acceso de AFIP")
    
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
    cache_path.mkdir(parents=True, exist_ok=True)
    wsdl = settings.get_wsaa_wsdl(env)
    
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
        raise Exception("No se pudo obtener ticket de acceso de AFIP")
    
    # Extraer token y sign del objeto wsaa
    token = getattr(wsaa, "Token", "")
    sign = getattr(wsaa, "Sign", "")
    
    if not token or not sign:
        raise Exception("Token o Sign vacíos en respuesta de AFIP")
    
    return token, sign
