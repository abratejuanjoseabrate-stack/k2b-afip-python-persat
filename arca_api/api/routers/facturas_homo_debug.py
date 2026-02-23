"""
Router de testing/debug para facturas - HOMOLOGACIÓN
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

router = APIRouter(prefix="/api/v1/facturas", tags=["testing y debug - homologacion"])


@router.get("/auth/verify", response_model=AuthVerifyResponse)
def verificar_autenticacion():
    """
    Verifica la autenticación con AFIP y retorna token y sign
    
    Este endpoint es útil para:
    - Verificar que los certificados funcionan correctamente
    - Obtener token y sign para debugging
    - Validar configuración de credenciales
    
    Retorna el token y sign del ticket de acceso actual (usando caché si está vigente).
    """
    try:
        token, sign = get_token_sign("wsfe")
        
        return AuthVerifyResponse(
            success=True,
            token=token,
            sign=sign,
            service="wsfe"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/params/condiciones-iva-receptor/xml")
def obtener_condiciones_iva_receptor_xml(clase_cmp: str = Query("A", description="Clase de comprobante para filtrar el XML (A, B o M)")):
    """
    Obtiene el XML de respuesta SOAP del webservice WSFEv1
    
    Este endpoint es útil para depuración. Retorna el XML SOAP completo 
    de la consulta de condiciones IVA filtrada por la clase seleccionada.
    """
    try:
        service = WSFEv1Service()
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


@router.get("/dummy", response_model=EstadoServidoresResponse)
def obtener_estado_servidores():
    """
    Verifica el estado de los servidores de AFIP (homologación)
    
    Retorna el estado de:
    - AppServer: Servidor de aplicación
    - DbServer: Servidor de base de datos
    - AuthServer: Servidor de autenticación
    """
    try:
        service = WSFEv1Service()
        estado = service.obtener_estado_servidores()
        return EstadoServidoresResponse(**estado)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
