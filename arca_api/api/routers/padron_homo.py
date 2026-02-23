"""
Router de padrón - Endpoints REST para WS-SR-PADRON (A5) - HOMOLOGACIÓN
"""
from fastapi import APIRouter, HTTPException, Query

from ..models.padron import PadronA5Response
from ..services.padron_a5 import PadronA5Service


def _safe_text(value):
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    return str(value)


router = APIRouter(prefix="/api/v1/padron", tags=["padron homologacion"])


@router.get("/a5", response_model=PadronA5Response)
def consultar_padron_a5(
    id_persona: str = Query(..., description="CUIT/DNI a consultar (sin guiones)"),
    debug: str = Query("false", description="Devuelve request/response SOAP completos (solo debugging): true/1")
):
    """Consulta padrón A5 (constancia) por CUIT/DNI."""
    debug_enabled = debug.lower() in ("true", "1")
    service = None
    try:
        id_persona = (id_persona or "").strip()
        service = PadronA5Service()
        padron = service.consultar(id_persona)

        raw = {}
        try:
            raw = getattr(padron, "data", {}) or {}
        except Exception:
            raw = {}

        return PadronA5Response(
            id_persona=id_persona,
            denominacion=getattr(padron, "denominacion", None),
            estado=getattr(padron, "estado", None),
            direccion=getattr(padron, "direccion", None),
            localidad=getattr(padron, "localidad", None),
            provincia=getattr(padron, "provincia", None),
            cod_postal=str(getattr(padron, "cod_postal", "") or "") or None,
            impuestos=list(getattr(padron, "impuestos", []) or []),
            actividades=list(getattr(padron, "actividades", []) or []),
            imp_iva=getattr(padron, "imp_iva", None),
            monotributo=getattr(padron, "monotributo", None),
            cat_iva=getattr(padron, "cat_iva", None),
            raw=raw,
        )

    except Exception as e:
        msg = str(e)
        if debug_enabled:
            soap_request = None
            soap_response = None
            try:
                soap_request = getattr(getattr(service, "padron", None), "XmlRequest", None)
                soap_response = getattr(getattr(service, "padron", None), "XmlResponse", None)
            except Exception:
                soap_request = None
                soap_response = None
            raise HTTPException(
                status_code=502,
                detail={
                    "error": msg,
                    "wsdl": getattr(service, "wsdl", None),
                    "soap_request": _safe_text(soap_request),
                    "soap_response": _safe_text(soap_response),
                },
            )
        if "No existe persona con ese Id" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=500, detail=msg)
