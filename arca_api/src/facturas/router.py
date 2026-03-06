"""
Router de facturas - Endpoints REST para WSFEv1
Router unificado que acepta ambiente (homo/prod) como parámetro

Nota: Este microservicio es interno, los endpoints no requieren autenticación JWT.
"""
from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import Response
from .service import WSFEv1Service
from .dependencies import get_wsfev1_service
from ..config import settings
from ..shared.exceptions import AFIPValidationError
from ..shared.logging_config import get_logger

logger = get_logger(__name__)
from .schemas import (
    FacturaCreate,
    FacturaCCreate,
    FacturaResponse,
    UltimoAutorizadoResponse,
    CompConsultarResponse,
    PuntosVentaResponse,
    IVACondicionesResponse,
    TiposComprobanteResponse,
    TiposDocumentoResponse,
    TiposIVAResponse,
    TiposConceptoResponse,
    AuthVerifyResponse,
)
from ..shared.afip_auth import get_token_sign

router = APIRouter(prefix="/api/v1/facturas", tags=["facturas"])


@router.post("", response_model=FacturaResponse, status_code=status.HTTP_201_CREATED)
def crear_factura(
    factura: FacturaCreate,
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Crea cualquier tipo de comprobante electrónico y obtiene el CAE
    
    **Ambiente:**
    - `env=homo` (default): Usa servidores de homologación
    - `env=prod`: Usa servidores de producción
    
    **Tipos de comprobante soportados:**
    
    **Facturas:**
    - `1` = Factura A
    - `6` = Factura B  
    - `11` = Factura C
    
    **Notas de Crédito:**
    - `3` = Nota de Crédito A
    - `8` = Nota de Crédito B
    - `13` = Nota de Crédito C
    
    **Notas de Débito:**
    - `2` = Nota de Débito A
    - `7` = Nota de Débito B
    - `12` = Nota de Débito C
    
    **Importante para Notas de Crédito/Débito:**
    - El campo `cbtes_asoc` es **OBLIGATORIO** y debe referenciar la factura original
    - Debe incluir: tipo, pto_vta, nro de la factura original
    
    **Ejemplo de Nota de Crédito:**
    ```json
    {
      "tipo_cbte": 13,
      "punto_vta": 1,
      "concepto": 1,
      "tipo_doc": 99,
      "nro_doc": "0",
      "imp_total": 50.00,
      "imp_neto": 50.00,
      "imp_iva": 0.00,
      "fecha_cbte": "20260120",
      "condicion_iva_receptor_id": 5,
      "cbtes_asoc": [
        {
          "tipo": 11,
          "pto_vta": 1,
          "nro": 123,
          "fecha": "20260118"
        }
      ]
    }
    ```
    """
    logger.info(f"Creando factura tipo {factura.tipo_cbte} (endpoint interno)")
    try:
        response = service.emitir_factura(factura)
        
        # Si fue rechazado, lanzar excepción de validación
        if response.resultado == "R":
            raise AFIPValidationError(
                message=response.err_msg or "Comprobante rechazado por AFIP",
                service="wsfe",
                resultado=response.resultado,
                observaciones=response.obs,
                error_code=response.err_code,
            )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        # Re-lanzar excepciones de AFIP (serán manejadas por el handler global)
        if isinstance(e, (AFIPValidationError,)):
            raise
        # Para otras excepciones, lanzar HTTPException genérico
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/c", response_model=FacturaResponse, status_code=status.HTTP_201_CREATED)
def crear_factura_c(
    factura: FacturaCCreate,
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """Crea una Factura C (tipo_cbte=11) y obtiene el CAE.

    **Ambiente:**
    - `env=homo` (default): Usa servidores de homologación
    - `env=prod`: Usa servidores de producción

    **Campos que se pueden enviar (request):**

    **Obligatorios**
    - `punto_vta`: Punto de venta.
    - `concepto`: 1=Productos, 2=Servicios, 3=Productos y Servicios.
    - `tipo_doc`: Tipo de documento del receptor (ej. 99=Consumidor Final).
    - `nro_doc`: Número de documento del receptor (para Consumidor Final suele ser "0").
    - `imp_total`: Importe total.
    - `imp_neto`: Importe neto gravado.
    - `fecha_cbte`: Fecha del comprobante en formato `YYYYMMDD`.

    **Opcionales (con default si no se envían)**
    - `imp_tot_conc`: Total conceptos no gravados (default 0.0).
    - `imp_trib`: Total tributos (default 0.0).
    - `imp_op_ex`: Total operaciones exentas (default 0.0).
    - `moneda_id`: Código de moneda (default `PES`).
    - `moneda_ctz`: Cotización (default `1.0000`).
    - `condicion_iva_receptor_id`: Condición IVA del receptor.

    **Reglas / defaults aplicados por el servicio:**
    - Si `condicion_iva_receptor_id` no se envía y `tipo_doc=99`, se usa `5` (Consumidor Final).
    - El número de comprobante se calcula como `CompUltimoAutorizado + 1`.
    - Para Factura C, el servicio envía `imp_iva=0.0`.

    **Respuesta (response):**
    - Si AFIP aprueba, se retorna `cae`, `vencimiento` y datos del comprobante.
    - Si AFIP rechaza, se retorna HTTP 422 con `obs`/`err_msg`.
    """
    logger.info(f"Creando factura C (endpoint interno)")
    try:
        response = service.emitir_factura_c(factura)

        if response.resultado == "R":
            raise AFIPValidationError(
                message=response.err_msg or "Factura C rechazada por AFIP",
                service="wsfe",
                resultado=response.resultado,
                observaciones=response.obs,
                error_code=response.err_code,
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        # Re-lanzar excepciones de AFIP (serán manejadas por el handler global)
        if isinstance(e, (AFIPValidationError,)):
            raise
        # Para otras excepciones, lanzar HTTPException genérico
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consultar", response_model=CompConsultarResponse)
def consultar_comprobante(
    tipo_cbte: int = Query(..., description="Tipo de comprobante (ej: 11=Factura C)."),
    punto_vta: int = Query(..., description="Punto de venta (ej: 1, 2, 3...)."),
    cbte_nro: int = Query(..., description="Número del comprobante (ej: 123)."),
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Consulta un comprobante que **ya existe** en AFIP.

    **Ambiente:**
    - `env=homo` (default): Usa servidores de homologación
    - `env=prod`: Usa servidores de producción

    **¿Para qué sirve?**
    
    Usalo cuando querés **confirmar** si un comprobante está registrado/validado en AFIP,
    o recuperar el **CAE** y su vencimiento si lo perdiste.
    
    **IMPORTANTE:** Este endpoint devuelve **todos los datos del comprobante**, incluyendo
    los necesarios para crear una Nota de Crédito/Débito basada en este comprobante.

    **Cuándo usarlo (ejemplos):**
    - Emitiste una factura y querés verificar que quedó **Aprobada**.
    - Tenés tipo/punto/número y querés traer el CAE desde AFIP.
    - Necesitás auditar datos del comprobante que AFIP tiene guardados.
    - **Querés obtener los datos de una factura para crear una Nota de Crédito/Débito.**

    **Parámetros:**
    - `tipo_cbte`: tipo de comprobante (ej: 11=Factura C)
    - `punto_vta`: punto de venta
    - `cbte_nro`: número de comprobante

    **Qué devuelve:**
    - `resultado`: "A" (aprobado) o "R" (rechazado)
    - `cae` y `vencimiento` si aplica
    - `obs` y/o `err_msg` si AFIP informa observaciones/errores
    - **Datos completos del comprobante:** concepto, tipo_doc, nro_doc, importes, moneda, etc.
    - **`cbtes_asoc`:** comprobantes asociados (si este comprobante es una NC/ND)
    """
    try:
        data = service.consultar_comprobante(tipo_cbte=tipo_cbte, punto_vta=punto_vta, cbte_nro=cbte_nro)
        return CompConsultarResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ultimo-autorizado", response_model=UltimoAutorizadoResponse)
def obtener_ultimo_autorizado(
    tipo_cbte: int = Query(..., description="Tipo de comprobante"),
    punto_vta: int = Query(..., description="Punto de venta"),
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Obtiene el último número de comprobante autorizado
    
    **Ambiente:**
    - `env=homo` (default): Usa servidores de homologación
    - `env=prod`: Usa servidores de producción
    
    - **tipo_cbte**: Tipo de comprobante (ej: 11=Factura C)
    - **punto_vta**: Punto de venta
    """
    try:
        ultimo_nro = service.obtener_ultimo_autorizado(tipo_cbte, punto_vta)
        
        return UltimoAutorizadoResponse(
            tipo_cbte=tipo_cbte,
            punto_vta=punto_vta,
            ultimo_nro=ultimo_nro
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/puntos-venta", response_model=PuntosVentaResponse)
def obtener_puntos_venta(
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Obtiene la lista de puntos de venta registrados
    
    **Ambiente:**
    - `env=homo` (default): Usa servidores de homologación
    - `env=prod`: Usa servidores de producción
    
    Retorna todos los puntos de venta habilitados para el CUIT configurado,
    incluyendo información sobre estado de bloqueo y fecha de baja.
    """
    try:
        puntos_venta = service.obtener_puntos_venta()
        
        return PuntosVentaResponse(puntos_venta=puntos_venta)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/params/condiciones-iva-receptor", response_model=IVACondicionesResponse)
def obtener_condiciones_iva_receptor(
    clase_cmp: str = Query("A", description="Clase de comprobante para filtrar las condiciones (A, B o M)"),
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Obtiene la lista de condiciones de IVA de receptores válidas.
    
    **Nota sobre el filtrado:**
    AFIP devuelve diferentes condiciones según la clase de comprobante:
    - **Clase 'A'**: Solo Responsables Inscriptos, Monotributistas, etc. (No incluye Consumidor Final).
    - **Clase 'B' o 'C'**: Incluye Consumidor Final (ID 5).
    
    Este endpoint usa el método `FEParamGetCondicionIvaReceptor` de WSFEv1.
    """
    try:
        condiciones = service.obtener_condiciones_iva_receptor(clase_cmp=clase_cmp)
        return IVACondicionesResponse(condiciones=condiciones)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/params/tipos-comprobante", response_model=TiposComprobanteResponse)
def obtener_tipos_comprobante(
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Obtiene la lista de tipos de comprobante disponibles
    
    Retorna todos los tipos de comprobante que se pueden emitir:
    - Factura A, B, C
    - Notas de Crédito/Débito
    - Etc.
    """
    try:
        tipos = service.obtener_tipos_comprobante()
        return TiposComprobanteResponse(tipos=tipos)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/params/tipos-documento", response_model=TiposDocumentoResponse)
def obtener_tipos_documento(
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Obtiene la lista de tipos de documento disponibles
    
    Retorna todos los tipos de documento válidos para el receptor:
    - CUIT, DNI, Consumidor Final, etc.
    """
    try:
        tipos = service.obtener_tipos_documento()
        return TiposDocumentoResponse(tipos=tipos)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/params/tipos-iva", response_model=TiposIVAResponse)
def obtener_tipos_iva(
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Obtiene la lista de tipos de IVA (alícuotas) disponibles
    
    Retorna todas las alícuotas de IVA válidas:
    - 0%, 10.5%, 21%, etc.
    """
    try:
        tipos = service.obtener_tipos_iva()
        return TiposIVAResponse(tipos=tipos)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/params/tipos-concepto", response_model=TiposConceptoResponse)
def obtener_tipos_concepto(
    service: WSFEv1Service = Depends(get_wsfev1_service)
):
    """
    Obtiene la lista de tipos de concepto disponibles
    
    Retorna los tipos de concepto válidos:
    - Productos, Servicios, Productos y Servicios
    """
    try:
        tipos = service.obtener_tipos_concepto()
        return TiposConceptoResponse(tipos=tipos)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/c/schema")
def factura_c_schema():
    """Retorna el JSON Schema del request de Factura C (campos requeridos/opcionales)."""
    return FacturaCCreate.model_json_schema()


@router.get("/auth/verify", response_model=AuthVerifyResponse)
def verificar_certificados_afip(
    env: str = Query("homo", description="Ambiente: homo o prod"),
):
    """
    **Valida certificado y clave privada contra AFIP (WSAA).**

    No requiere autenticación JWT. Útil para comprobar que:
    - Los archivos CERT_PATH y KEY_PATH existen y son los que usa la API.
    - La pareja certificado + clave es válida y AFIP la acepta.
    - El CUIT del certificado coincide con el configurado.

    Si responde 200 con `success: true`, los certificados son correctos para ese ambiente.
    Si responde 500 (ej. "Firma inválida"), revisar cert/key/CUIT según la guía en docs.
    """
    try:
        env_lower = (env or "homo").strip().lower()
        if env_lower not in ("homo", "prod"):
            env_lower = "homo"
        token, sign = get_token_sign("wsfe", env=env_lower)
        return AuthVerifyResponse(
            success=True,
            token=token or "",
            sign=sign or "",
            service="wsfe",
        )
    except Exception as e:
        logger.exception("auth/verify falló")
        raise HTTPException(status_code=500, detail=str(e))
