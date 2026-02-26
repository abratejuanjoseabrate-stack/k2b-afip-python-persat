"""
Router de padrón - Endpoints REST para WS-SR-PADRON (A5)
Router unificado que acepta ambiente (homo/prod) como parámetro
"""
from fastapi import APIRouter, HTTPException, Query, Depends

from .schemas import PadronA5Response, ImpuestoDetalle, ActividadDetalle
from .service import PadronA4Service, PadronA5Service
from .dependencies import get_padron_service, get_padron_a4_service
from ..auth.dependencies import get_current_user
from ..auth.models import User
from ..shared.exceptions import AFIPError
from ..shared.logging_config import get_logger

logger = get_logger(__name__)


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


@router.get("/a5", response_model=PadronA5Response)
def consultar_padron_a5(
    id_persona: str = Query(..., description="CUIT/DNI a consultar (sin guiones)"),
    debug: str = Query("false", description="Devuelve request/response SOAP completos (solo debugging): true/1"),
    current_user: User = Depends(get_current_user),
    service: PadronA5Service = Depends(get_padron_service)
):
    """
    Consulta padrón A5 (constancia) por CUIT/DNI.
    
    **Requiere autenticación JWT** - Incluye header: `Authorization: Bearer <token>`
    """
    logger.info(f"Usuario {current_user.email} (id={current_user.id}) consultando padrón para: {id_persona}")
    debug_enabled = debug.lower() in ("true", "1")
    try:
        id_persona = (id_persona or "").strip()
        padron = service.consultar(id_persona)

        raw = {}
        try:
            raw = getattr(padron, "data", {}) or {}
        except Exception:
            raw = {}

        # Extraer datos desde raw (donde están los datos reales de AFIP)
        datos = raw if isinstance(raw, dict) else {}
        domicilio = datos.get("domicilioFiscal", {}) if isinstance(datos.get("domicilioFiscal"), dict) else {}

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
            raw=raw,
        )

    except HTTPException:
        raise
    except AFIPError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/a4", response_model=PadronA5Response)
def consultar_padron_a4(
    id_persona: str = Query(..., description="CUIT/DNI a consultar (sin guiones)"),
    debug: str = Query("false", description="Devuelve request/response SOAP completos (solo debugging): true/1"),
    current_user: User = Depends(get_current_user),
    service: PadronA4Service = Depends(get_padron_a4_service)
):
    """
    Consulta padrón A4 (Padrón Alcance 4) por CUIT/DNI.

    **Requiere autenticación JWT** - Incluye header: `Authorization: Bearer <token>`

    Use query **env** para elegir ambiente: `homo` (homologación) o `prod` (producción).
    Ejemplo: `/api/v1/padron/a4?id_persona=20123456789&env=prod`
    """
    logger.info(f"Usuario {current_user.email} (id={current_user.id}) consultando padrón A4 para: {id_persona}")
    try:
        id_persona = (id_persona or "").strip()
        padron = service.consultar(id_persona)

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
