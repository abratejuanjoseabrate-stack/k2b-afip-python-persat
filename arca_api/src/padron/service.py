"""
Servicio para consultas de padrón (Alcance 5) en homologación
"""
from pathlib import Path

from pyafipws.ws_sr_padron import WSSrPadronA5

from ..config import settings
from ..shared.afip_auth import get_ticket_acceso
from ..shared.exceptions import (
    AFIPConnectionError,
    AFIPNotFoundError,
    AFIPServiceError,
)
from ..shared.logging_config import get_logger

logger = get_logger(__name__)


class PadronA5Service:
    """Servicio para operaciones de WS-SR-PADRON A5"""

    def __init__(self, service_name: str = "ws_sr_padron_a5", env: str = "homo"):
        self.service_name = service_name
        self.env = env
        self.padron = WSSrPadronA5()
        self.wsdl = None
        self._conectar()

    def _conectar(self) -> None:
        logger.info(f"Conectando PadronA5Service en ambiente: {self.env}")
        try:
            ta = get_ticket_acceso(self.service_name, env=self.env)
        except Exception:
            # En algunos perfiles/altas, ARCA/AFIP expone el A5 como "ws_sr_constancia_inscripcion"
            if self.service_name == "ws_sr_padron_a5":
                logger.debug("Intentando con servicio alternativo: ws_sr_constancia_inscripcion")
                ta = get_ticket_acceso("ws_sr_constancia_inscripcion", env=self.env)
                self.service_name = "ws_sr_constancia_inscripcion"
            else:
                raise

        self.padron.Cuit = settings.CUIT
        self.padron.SetTicketAcceso(ta)

        # Para homologación, deshabilitar verificación SSL (cacert=None)
        # Esto evita problemas con proxies corporativos / inspección TLS
        url_ws = settings.get_padron_a5_wsdl(self.env)
        self.wsdl = url_ws
        self.padron.Conectar(
            str(settings.get_cache_path(self.env)),
            url_ws,
            cacert=None,
        )
        logger.info("Conexión PadronA5Service establecida correctamente")

    def consultar(self, id_persona: str) -> WSSrPadronA5:
        id_persona = (id_persona or "").strip()
        logger.info(f"Consultando padrón A5 para id_persona: {id_persona}")
        id_persona_param = int(id_persona) if id_persona.isdigit() else id_persona
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
