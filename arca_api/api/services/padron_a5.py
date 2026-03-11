"""
Servicio para consultas de padrón (Alcance 5) en homologación.
Reintento automático una vez si AFIP devuelve "token expirado".
"""
from pathlib import Path

from pyafipws.ws_sr_padron import WSSrPadronA5

from ..config import settings
from ..services.afip_auth import get_ticket_acceso, invalidar_cache_ta, _is_token_expirado_message


class PadronA5Service:
    """Servicio para operaciones de WS-SR-PADRON A5"""

    def __init__(self, service_name: str = "ws_sr_padron_a5", env: str = "homo"):
        self.service_name = service_name
        self.env = env
        self.padron = WSSrPadronA5()
        self.wsdl = None
        self._conectar()

    def _conectar(self) -> None:
        try:
            ta = get_ticket_acceso(self.service_name, env=self.env)
        except Exception:
            # En algunos perfiles/altas, ARCA/AFIP expone el A5 como "ws_sr_constancia_inscripcion"
            if self.service_name == "ws_sr_padron_a5":
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

    def consultar(self, id_persona: str) -> WSSrPadronA5:
        """Consulta padrón A5. Si AFIP responde token expirado, invalida caché TA, reconecta y reintenta una vez."""
        id_persona = (id_persona or "").strip()
        id_persona_param = int(id_persona) if id_persona.isdigit() else id_persona
        last_error = None
        for attempt in range(2):
            try:
                ok = self.padron.Consultar(id_persona_param)
                if ok:
                    return self.padron
                exc = getattr(self.padron, "Excepcion", "") or "Error en consulta padrón"
                last_error = exc
            except Exception as e:
                last_error = str(e)
                if attempt == 0 and _is_token_expirado_message(last_error):
                    invalidar_cache_ta(self.env)
                    self._conectar()
                    continue
                raise
            # ok is False
            if attempt == 0 and _is_token_expirado_message(last_error or ""):
                invalidar_cache_ta(self.env)
                self._conectar()
                continue
            raise Exception(last_error or "Error en consulta padrón")
        raise Exception(last_error or "Error en consulta padrón")
