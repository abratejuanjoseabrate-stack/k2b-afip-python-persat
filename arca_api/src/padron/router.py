"""
Router de padrón - Endpoints REST para WS-SR-PADRON (A5).
Cache de respuesta por (CUIT, env) con TTL 1h para reducir llamadas a AFIP.
Las llamadas a PyAfipWs (síncronas) se ejecutan en run_in_executor para no bloquear el event loop.
"""
import asyncio
import threading
import time
from fastapi import APIRouter, HTTPException, Query, Depends

from .schemas import PadronA5Response, ImpuestoDetalle, ActividadDetalle
from .service import PadronA4Service, PadronA5Service
from .dependencies import get_padron_service, get_padron_a4_service
from ..auth.dependencies import get_current_user
from ..auth import models as auth_models
from ..shared.exceptions import AFIPError
from ..shared.logging_config import get_logger

logger = get_logger(__name__)

# Cache de respuestas A5 por (id_persona, env) -> (dict respuesta, timestamp). TTL 1 hora.
_PADRON_A5_RESPONSE_CACHE: dict[tuple[str, str], tuple[dict, float]] = {}
_PADRON_A5_CACHE_LOCK = threading.Lock()
_PADRON_A5_CACHE_TTL_SEC = 3600


def _safe_text(value):
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    return str(value)


def _format_date(value):
    """Convertir datetime o fecha a string ISO"""
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def _parse_impuestos_detallados(raw_data: dict) -> list:
    """Parsear impuestos detallados desde la respuesta raw de AFIP"""
    impuestos = []
    try:
        # Buscar en diferentes estructuras posibles
        datos = raw_data.get("datos", {})
        if isinstance(datos, dict):
            impuestos_data = datos.get("impuestos", [])
        else:
            impuestos_data = raw_data.get("impuestos", [])
        
        if isinstance(impuestos_data, list):
            for imp in impuestos_data:
                if isinstance(imp, dict):
                    impuestos.append(ImpuestoDetalle(
                        id_impuesto=imp.get("idImpuesto") or imp.get("id_impuesto") or 0,
                        descripcion=imp.get("descripcionImpuesto") or imp.get("descripcion"),
                        estado=imp.get("estado"),
                        periodo=imp.get("periodo")
                    ))
    except Exception as e:
        logger.debug(f"Error parseando impuestos detallados: {e}")
    return impuestos


def _parse_actividades_detalladas(raw_data: dict) -> list:
    """Parsear actividades detalladas desde la respuesta raw de AFIP"""
    actividades = []
    try:
        # Buscar en diferentes estructuras posibles
        datos = raw_data.get("datos", {})
        if isinstance(datos, dict):
            actividades_data = datos.get("actividades", [])
        else:
            actividades_data = raw_data.get("actividades", [])
        
        if isinstance(actividades_data, list):
            for act in actividades_data:
                if isinstance(act, dict):
                    actividades.append(ActividadDetalle(
                        id_actividad=act.get("idActividad") or act.get("id_actividad") or 0,
                        descripcion=act.get("descripcionActividad") or act.get("descripcion"),
                        periodo=act.get("periodo"),
                        orden=act.get("orden")
                    ))
    except Exception as e:
        logger.debug(f"Error parseando actividades detalladas: {e}")
    return actividades


router = APIRouter(prefix="/api/v1/padron", tags=["padron"])


def _build_padron_a5_response(id_persona: str, padron, datos: dict, domicilio: dict) -> PadronA5Response:
    """Construye PadronA5Response desde el objeto padron y datos extraídos."""
    return PadronA5Response(
        id_persona=id_persona,
        tipo_persona=datos.get("tipoPersona") or getattr(padron, "tipo_persona", None),
        denominacion=datos.get("apellido") + ", " + datos.get("nombre") if datos.get("apellido") and datos.get("nombre") else getattr(padron, "denominacion", None),
        estado=datos.get("estadoClave") or getattr(padron, "estado", None),
        nombre=datos.get("nombre") or getattr(padron, "nombre", None),
        apellido=datos.get("apellido") or getattr(padron, "apellido", None),
        tipo_documento=datos.get("tipoClave") or getattr(padron, "tipo_documento", None),
        numero_documento=str(datos.get("idPersona")) if datos.get("idPersona") else getattr(padron, "numero_documento", None),
        fecha_inscripcion=_format_date(datos.get("fechaInscripcion")) or getattr(padron, "fecha_inscripcion", None),
        fecha_contrato_social=_format_date(datos.get("fechaContratoSocial")) or getattr(padron, "fecha_contrato_social", None),
        direccion=domicilio.get("direccion") or getattr(padron, "direccion", None),
        localidad=domicilio.get("localidad") or getattr(padron, "localidad", None),
        provincia=domicilio.get("descripcionProvincia") or getattr(padron, "provincia", None),
        cod_postal=str(domicilio.get("codPostal") or getattr(padron, "cod_postal", "") or "") or None,
        telefono=datos.get("telefono") or getattr(padron, "telefono", None),
        email=datos.get("email") or getattr(padron, "email", None),
        impuestos=list(getattr(padron, "impuestos", []) or []),
        impuestos_detallados=_parse_impuestos_detallados(datos),
        actividades=list(getattr(padron, "actividades", []) or []),
        actividades_detalladas=_parse_actividades_detalladas(datos),
        imp_iva=getattr(padron, "imp_iva", None),
        monotributo=getattr(padron, "monotributo", None),
        cat_iva=getattr(padron, "cat_iva", None),
        raw=datos if isinstance(datos, dict) else {},
    )


@router.get("/a5", response_model=PadronA5Response)
async def consultar_padron_a5(
    id_persona: str = Query(..., description="CUIT/DNI a consultar (sin guiones)"),
    debug: str = Query("false", description="Devuelve request/response SOAP completos (solo debugging): true/1"),
    service: PadronA5Service = Depends(get_padron_service),
    current_user: auth_models.User = Depends(get_current_user),
):
    """
    Consulta padrón A5 (constancia) por CUIT/DNI.
    Respuestas OK se cachean 1h por (CUIT, env) para reducir llamadas a AFIP.
    Requiere autenticación JWT. Incluir header: **Authorization: Bearer &lt;token&gt;**
    """
    id_persona = (id_persona or "").strip()
    cache_key = (id_persona, service.env)
    now = time.time()
    with _PADRON_A5_CACHE_LOCK:
        if cache_key in _PADRON_A5_RESPONSE_CACHE:
            data, ts = _PADRON_A5_RESPONSE_CACHE[cache_key]
            if (now - ts) < _PADRON_A5_CACHE_TTL_SEC:
                logger.info(f"Padrón A5 cache hit para {id_persona} env={service.env}")
                return PadronA5Response(**data)
            del _PADRON_A5_RESPONSE_CACHE[cache_key]

    # Log visible en la terminal donde corre arca (python run.py en :8000)
    logger.info("[PADRON A5] Request recibido id_persona=%s env=%s", id_persona, service.env)
    try:
        loop = asyncio.get_running_loop()
        padron = await loop.run_in_executor(None, lambda: service.consultar(id_persona))
        raw = getattr(padron, "data", {}) or {}
        datos = raw if isinstance(raw, dict) else {}
        domicilio = datos.get("domicilioFiscal", {}) if isinstance(datos.get("domicilioFiscal"), dict) else {}
        resp = _build_padron_a5_response(id_persona, padron, datos, domicilio)
        with _PADRON_A5_CACHE_LOCK:
            _PADRON_A5_RESPONSE_CACHE[cache_key] = (resp.model_dump(), time.time())
        return resp
    except HTTPException:
        raise
    except AFIPError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/a4", response_model=PadronA5Response)
async def consultar_padron_a4(
    id_persona: str = Query(..., description="CUIT/DNI a consultar (sin guiones)"),
    debug: str = Query("false", description="Devuelve request/response SOAP completos (solo debugging): true/1"),
    service: PadronA4Service = Depends(get_padron_a4_service)
):
    """
    Consulta padrón A4 (Padrón Alcance 4) por CUIT/DNI.
    Uso interno: no requiere autenticación.

    Use query **env** para elegir ambiente: `homo` (homologación) o `prod` (producción).
    Ejemplo: `/api/v1/padron/a4?id_persona=20123456789&env=prod`
    """
    logger.info(f"Padrón A4 consulta para: {id_persona}")
    try:
        id_persona = (id_persona or "").strip()
        loop = asyncio.get_running_loop()
        padron = await loop.run_in_executor(None, lambda: service.consultar(id_persona))

        raw = getattr(padron, "data", {}) or {}
        datos = raw if isinstance(raw, dict) else {}
        # A4 devuelve "impuesto" y "actividad"; normalizar para los parsers
        datos_para_parser = {**datos, "impuestos": datos.get("impuesto", []), "actividades": datos.get("actividad", [])}

        # A4 expone atributos directos: denominacion, direccion, tipo_persona, estado, etc.
        return PadronA5Response(
            id_persona=id_persona,
            tipo_persona=getattr(padron, "tipo_persona", None) or datos.get("tipoPersona"),
            denominacion=getattr(padron, "denominacion", None) or datos.get("razonSocial"),
            estado=getattr(padron, "estado", None) or datos.get("estadoClave"),
            nombre=datos.get("nombre"),
            apellido=datos.get("apellido"),
            tipo_documento=str(getattr(padron, "tipo_doc", "")) if getattr(padron, "tipo_doc", None) else datos.get("tipoClave"),
            numero_documento=str(getattr(padron, "nro_doc", "")) if getattr(padron, "nro_doc", None) else (str(datos.get("numeroDocumento", "")) if datos.get("numeroDocumento") else None),
            direccion=getattr(padron, "direccion", None),
            localidad=getattr(padron, "localidad", None),
            provincia=getattr(padron, "provincia", None),
            cod_postal=str(getattr(padron, "cod_postal", "") or "") or None,
            impuestos=list(getattr(padron, "impuestos", []) or []),
            impuestos_detallados=_parse_impuestos_detallados(datos_para_parser),
            actividades=list(getattr(padron, "actividades", []) or []),
            actividades_detalladas=_parse_actividades_detalladas(datos_para_parser),
            imp_iva=getattr(padron, "imp_iva", None),
            monotributo=getattr(padron, "monotributo", None),
            cat_iva=getattr(padron, "cat_iva", None),
            raw=raw,
        )
    except HTTPException:
        raise
    except AFIPError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
