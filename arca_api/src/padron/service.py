"""
Servicio para consultas de padrón (Alcance 4 y 5) en homologación y producción.
Optimizado: WSDL en cache por env, singleton por proceso (vía dependencies).
"""
import ssl
import threading
import urllib.request
from pathlib import Path

from pyafipws.ws_sr_padron import WSSrPadronA4, WSSrPadronA5

from ..config import settings
from ..shared.afip_auth import get_ticket_acceso
from ..shared.exceptions import (
    AFIPConnectionError,
    AFIPNotFoundError,
    AFIPServiceError,
)
from ..shared.logging_config import get_logger

logger = get_logger(__name__)

# Cache de ruta WSDL por env: evita descargar en cada request
_wsdl_path_cache: dict[str, str] = {}
_wsdl_cache_lock = threading.Lock()


def _get_wsdl_path_padron_a5(env: str) -> str:
    """Obtiene ruta del WSDL de Padrón A5: descarga una vez por env y reutiliza."""
    with _wsdl_cache_lock:
        if env in _wsdl_path_cache:
            path = _wsdl_path_cache[env]
            if Path(path).exists():
                return path
            del _wsdl_path_cache[env]
        url_ws = settings.get_padron_a5_wsdl(env)
        cache_dir = settings.get_cache_path(env)
        cache_dir.mkdir(parents=True, exist_ok=True)
        local_path = cache_dir / f"padron_a5_{env}.wsdl"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url_ws, context=ctx, timeout=15) as response:
            local_path.write_bytes(response.read())
        _wsdl_path_cache[env] = str(local_path)
        logger.info(f"WSDL Padrón A5 ({env}) cacheado en {local_path}")
        return str(local_path)


def _get_wsdl_path_padron_a4(env: str) -> str:
    """Obtiene ruta del WSDL de Padrón A4: descarga una vez por env y reutiliza."""
    key = f"a4_{env}"
    with _wsdl_cache_lock:
        if key in _wsdl_path_cache and Path(_wsdl_path_cache[key]).exists():
            return _wsdl_path_cache[key]
        url_ws = settings.get_padron_a4_wsdl(env)
        cache_dir = settings.get_cache_path(env)
        cache_dir.mkdir(parents=True, exist_ok=True)
        local_path = cache_dir / f"padron_a4_{env}.wsdl"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url_ws, context=ctx, timeout=15) as response:
            local_path.write_bytes(response.read())
        key = f"a4_{env}"
        _wsdl_path_cache[key] = str(local_path)
        return str(local_path)


class PadronA5Service:
    """Servicio para operaciones de WS-SR-PADRON A5. Thread-safe si se reutiliza (singleton por env)."""

    def __init__(self, service_name: str = "ws_sr_padron_a5", env: str = "homo"):
        self.service_name = service_name
        self.env = env
        self.padron = WSSrPadronA5()
        self.wsdl = None
        self._lock = threading.Lock()
        self._conectar()

    def _conectar(self) -> None:
        logger.info(f"Conectando PadronA5Service en ambiente: {self.env}")
        try:
            ta = get_ticket_acceso(self.service_name, env=self.env)
        except Exception:
            if self.service_name == "ws_sr_padron_a5":
                logger.debug("Intentando con servicio alternativo: ws_sr_constancia_inscripcion")
                ta = get_ticket_acceso("ws_sr_constancia_inscripcion", env=self.env)
                self.service_name = "ws_sr_constancia_inscripcion"
            else:
                raise

        self.padron.Cuit = settings.CUIT
        self.padron.SetTicketAcceso(ta)

        wsdl_path = _get_wsdl_path_padron_a5(self.env)
        self.wsdl = settings.get_padron_a5_wsdl(self.env)
        self.padron.Conectar(cache=None, wsdl=wsdl_path, cacert=None)
        logger.info("Conexión PadronA5Service establecida correctamente")

    def consultar(self, id_persona: str) -> WSSrPadronA5:
        id_persona = (id_persona or "").strip()
        id_persona_param = int(id_persona) if id_persona.isdigit() else id_persona
        with self._lock:
            logger.info(f"Consultando padrón A5 para id_persona: {id_persona}")
            ok = self.padron.Consultar(id_persona_param)
        if not ok:
            logger.warning(f"Consulta padrón fallida para id_persona: {id_persona}")
            exc = getattr(self.padron, "Excepcion", "") or "Error en consulta padrón"
            error_msg = str(exc)
            
            # Detectar si es un error de "no encontrado"
            if "No existe persona con ese Id" in error_msg or "no existe" in error_msg.lower():
                raise AFIPNotFoundError(
                    message=error_msg,
                    service=self.service_name,
                    wsdl=self.wsdl,
                    soap_request=getattr(self.padron, "XmlRequest", None),
                    soap_response=getattr(self.padron, "XmlResponse", None),
                )
            
            # Otros errores de servicio
            raise AFIPServiceError(
                message=error_msg,
                service=self.service_name,
                wsdl=self.wsdl,
                soap_request=getattr(self.padron, "XmlRequest", None),
                soap_response=getattr(self.padron, "XmlResponse", None),
            )
        return self.padron


class PadronA4Service:
    """Servicio para operaciones de WS-SR-PADRON A4 (Padrón Alcance 4)."""

    def __init__(self, service_name: str = "ws_sr_padron_a4", env: str = "homo"):
        self.service_name = service_name
        self.env = env
        self.padron = WSSrPadronA4()
        self.wsdl = None
        self._conectar()

    def _conectar(self) -> None:
        logger.info(f"Conectando PadronA4Service en ambiente: {self.env}")
        ta = get_ticket_acceso(self.service_name, env=self.env)
        self.padron.Cuit = settings.CUIT
        self.padron.SetTicketAcceso(ta)

        wsdl_path = _get_wsdl_path_padron_a4(self.env)
        self.wsdl = settings.get_padron_a4_wsdl(self.env)
        logger.info(f"WSDL A4 desde cache: {wsdl_path}")

        self.padron.Conectar(
            cache=None,
            wsdl=wsdl_path,
            cacert=None,
        )
        logger.info("Conexión PadronA4Service establecida correctamente")

    def consultar(self, id_persona: str) -> WSSrPadronA4:
        id_persona = (id_persona or "").strip()
        logger.info(f"Consultando padrón A4 para id_persona: {id_persona}")
        id_persona_param = int(id_persona) if id_persona.isdigit() else id_persona
        ok = self.padron.Consultar(id_persona_param)
        if not ok:
            logger.warning(f"Consulta padrón A4 fallida para id_persona: {id_persona}")
            exc = getattr(self.padron, "Excepcion", "") or "Error en consulta padrón"
            error_msg = str(exc)

            if "No existe" in error_msg or "no existe" in error_msg.lower():
                raise AFIPNotFoundError(
                    message=error_msg,
                    service=self.service_name,
                    wsdl=self.wsdl,
                    soap_request=getattr(self.padron, "XmlRequest", None),
                    soap_response=getattr(self.padron, "XmlResponse", None),
                )
            raise AFIPServiceError(
                message=error_msg,
                service=self.service_name,
                wsdl=self.wsdl,
                soap_request=getattr(self.padron, "XmlRequest", None),
                soap_response=getattr(self.padron, "XmlResponse", None),
            )
        return self.padron
