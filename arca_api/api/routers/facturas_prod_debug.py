"""
Router de testing/debug para facturas - PRODUCCIÓN
Endpoints de testing y debugging separados de los operacionales
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from ..services.wsfev1 import WSFEv1Service
from ..services.afip_auth import get_token_sign
from ..models.factura import (
    AuthVerifyResponse,
    EstadoServidoresResponse
)

router = APIRouter(prefix="/api/v1/facturas", tags=["testing y debug - produccion"])


@router.get("/puntos-venta/xml")
def obtener_puntos_venta_prod_xml():
    """Retorna el XML SOAP de la consulta de puntos de venta (producción)."""
    try:
        service = WSFEv1Service(env="prod")
        service.obtener_puntos_venta()
        xml_response = service.obtener_xml_response()

        if not xml_response:
            raise HTTPException(status_code=404, detail="XML de respuesta no disponible")

        return Response(content=xml_response, media_type="application/xml")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/puntos-venta/debug")
def obtener_puntos_venta_prod_debug():
    """Debug de puntos de venta en producción: incluye WSDL efectiva."""
    try:
        service = WSFEv1Service(env="prod")
        puntos_venta = service.obtener_puntos_venta()
        
        # Obtener información de debug
        wsdl = getattr(service.wsfev1, 'wsdl', 'No disponible')
        cuit = getattr(service.wsfev1, 'Cuit', 'No disponible')
        
        return {
            "puntos_venta": [{"nro": pv.nro, "emision_tipo": pv.emision_tipo, "bloqueado": pv.bloqueado, "fch_baja": pv.fch_baja} for pv in puntos_venta],
            "debug_info": {
                "wsdl": wsdl,
                "cuit": cuit,
                "env": "prod"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/params/condiciones-iva-receptor/xml")
def obtener_condiciones_iva_receptor_xml_prod(clase_cmp: str = Query("A", description="Clase de comprobante para filtrar el XML (A, B o M)")):
    """
    Obtiene el XML de respuesta SOAP del webservice WSFEv1 (producción)
    
    Este endpoint es útil para depuración. Retorna el XML SOAP completo 
    de la consulta de condiciones IVA filtrada por la clase seleccionada.
    """
    try:
        service = WSFEv1Service(env="prod")
        # primero ejecutar la consulta para tener el XML
        service.obtener_condiciones_iva_receptor(clase_cmp=clase_cmp)
        xml_response = service.obtener_xml_response()
        
        if not xml_response:
            raise HTTPException(status_code=404, detail="XML de respuesta no disponible")
        
        return Response(content=xml_response, media_type="application/xml")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/verify", response_model=AuthVerifyResponse)
def verificar_autenticacion_prod():
    """
    Verifica la autenticación con AFIP y retorna token y sign (producción)
    
    Este endpoint es útil para:
    - Verificar que los certificados de producción funcionan correctamente
    - Obtener token y sign para debugging
    - Validar configuración de credenciales de producción
    
    Retorna el token y sign del ticket de acceso actual (usando caché si está vigente).
    """
    try:
        token, sign = get_token_sign("wsfe", env="prod")
        
        return AuthVerifyResponse(
            success=True,
            token=token,
            sign=sign,
            service="wsfe"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dummy", response_model=EstadoServidoresResponse)
def obtener_estado_servidores_prod():
    """
    Verifica el estado de los servidores de AFIP (producción)
    
    Retorna el estado de:
    - AppServer: Servidor de aplicación
    - DbServer: Servidor de base de datos
    - AuthServer: Servidor de autenticación
    """
    try:
        service = WSFEv1Service(env="prod")
        estado = service.obtener_estado_servidores()
        return EstadoServidoresResponse(**estado)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
