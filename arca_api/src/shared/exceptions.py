"""
Excepciones personalizadas para errores de AFIP
"""
from typing import Optional, Dict, Any


class AFIPError(Exception):
    """Excepción base para errores relacionados con AFIP"""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        error_code: Optional[str] = None,
        soap_request: Optional[str] = None,
        soap_response: Optional[str] = None,
        wsdl: Optional[str] = None,
    ):
        self.message = message
        self.service = service  # "wsfe", "ws_sr_padron_a5", etc.
        self.error_code = error_code
        self.soap_request = soap_request
        self.soap_response = soap_response
        self.wsdl = wsdl
        super().__init__(self.message)
    
    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        """Convierte la excepción a diccionario para respuesta JSON"""
        result = {
            "error": self.message,
            "service": self.service,
        }
        
        if self.error_code:
            result["error_code"] = self.error_code
        
        if include_debug:
            if self.wsdl:
                result["wsdl"] = self.wsdl
            if self.soap_request:
                result["soap_request"] = self.soap_request
            if self.soap_response:
                result["soap_response"] = self.soap_response
        
        return result


class AFIPConnectionError(AFIPError):
    """Error de conexión con AFIP (timeout, red, etc.)"""
    pass


class AFIPAuthenticationError(AFIPError):
    """Error de autenticación con AFIP (certificados, ticket de acceso, etc.)"""
    pass


class AFIPValidationError(AFIPError):
    """Error de validación de datos (comprobante rechazado, datos inválidos, etc.)"""
    
    def __init__(
        self,
        message: str,
        resultado: Optional[str] = None,
        observaciones: Optional[list] = None,
        **kwargs
    ):
        self.resultado = resultado  # "R" = Rechazado
        self.observaciones = observaciones or []
        super().__init__(message, **kwargs)
    
    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        result = super().to_dict(include_debug)
        if self.resultado:
            result["resultado"] = self.resultado
        if self.observaciones:
            result["observaciones"] = self.observaciones
        return result


class AFIPNotFoundError(AFIPError):
    """Recurso no encontrado en AFIP (comprobante, persona, etc.)"""
    pass


class AFIPServiceError(AFIPError):
    """Error del servicio AFIP (servidor no disponible, error interno, etc.)"""
    pass
