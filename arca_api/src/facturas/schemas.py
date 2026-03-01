"""
Modelos Pydantic para facturas
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ComprobanteAsociado(BaseModel):
    """Modelo para comprobante asociado (usado en Notas de Crédito/Débito)"""
    tipo: int = Field(..., description="Tipo de comprobante asociado (ej: 1=Factura A, 6=Factura B, 11=Factura C)")
    pto_vta: int = Field(..., description="Punto de venta del comprobante asociado")
    nro: int = Field(..., description="Número del comprobante asociado")
    cuit: Optional[str] = Field(None, description="CUIT del emisor del comprobante asociado (opcional)")
    fecha: Optional[str] = Field(None, description="Fecha del comprobante asociado en formato YYYYMMDD (opcional)")

    class Config:
        json_schema_extra = {
            "example": {
                "tipo": 11,
                "pto_vta": 1,
                "nro": 123,
                "cuit": None,
                "fecha": "20260118"
            }
        }


class AlicuotaIVA(BaseModel):
    iva_id: int = Field(..., description="Id de alícuota IVA según AFIP (ej: 5=21%)")
    base_imp: float = Field(..., description="Base imponible de la alícuota")
    importe: float = Field(..., description="Importe de IVA para la alícuota")


class FacturaCreate(BaseModel):
    """
    Request para crear cualquier tipo de comprobante electrónico
    
    Soporta:
    - Facturas A, B, C (tipo_cbte: 1, 6, 11)
    - Notas de Crédito A, B, C (tipo_cbte: 3, 8, 13)
    - Notas de Débito A, B, C (tipo_cbte: 2, 7, 12)
    - Y otros tipos de comprobante según AFIP
    
    Para Notas de Crédito/Débito, usar el campo `cbtes_asoc` para asociar la factura original.
    """
    tipo_cbte: int = Field(
        ..., 
        description="Tipo de comprobante. Ejemplos: 1=Factura A, 6=Factura B, 11=Factura C, 3=NC A, 8=NC B, 13=NC C, 2=ND A, 7=ND B, 12=ND C"
    )
    punto_vta: int = Field(..., description="Punto de venta")
    concepto: int = Field(..., description="Tipo de concepto (1=Productos, 2=Servicios, 3=Productos y Servicios)")
    tipo_doc: int = Field(..., description="Tipo de documento (80=CUIT, 96=DNI, 99=Consumidor Final)")
    nro_doc: str = Field(..., description="Número de documento")
    imp_total: float = Field(..., description="Importe total")
    imp_neto: float = Field(..., description="Importe neto gravado")
    imp_iva: float = Field(default=0.0, description="Importe de IVA")
    imp_tot_conc: float = Field(default=0.0, description="Importe total de conceptos no gravados")
    imp_trib: float = Field(default=0.0, description="Importe de tributos")
    imp_op_ex: float = Field(default=0.0, description="Importe de operaciones exentas")
    fecha_cbte: str = Field(..., description="Fecha del comprobante (YYYYMMDD)")
    fecha_serv_desde: Optional[str] = Field(
        None,
        description="Fecha de inicio del servicio (YYYYMMDD). Obligatorio cuando concepto es 2 o 3."
    )
    fecha_serv_hasta: Optional[str] = Field(
        None,
        description="Fecha de fin del servicio (YYYYMMDD). Obligatorio cuando concepto es 2 o 3."
    )
    fecha_venc_pago: Optional[str] = Field(
        None,
        description="Fecha de vencimiento de pago (YYYYMMDD). Obligatorio cuando concepto es 2 o 3."
    )
    moneda_id: str = Field(default="PES", description="Código de moneda (PES=Pesos, DOL=Dólar, EUR=Euro)")
    moneda_ctz: str = Field(default="1.0000", description="Cotización de moneda")
    condicion_iva_receptor_id: Optional[int] = Field(
        None, 
        description="Condición IVA del receptor (Obligatorio según RG 5616). Ej: 5=Consumidor Final"
    )
    iva: Optional[List[AlicuotaIVA]] = Field(
        None,
        description="Detalle de IVA (alícuotas). Requerido por AFIP cuando ImpNeto > 0.",
    )
    cbtes_asoc: Optional[List[ComprobanteAsociado]] = Field(
        None,
        description="Lista de comprobantes asociados (OBLIGATORIO para Notas de Crédito/Débito). Debe referenciar la factura original."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tipo_cbte": 11,
                "punto_vta": 1,
                "concepto": 1,
                "tipo_doc": 99,
                "nro_doc": "0",
                "imp_total": 121.0,
                "imp_neto": 100.0,
                "imp_iva": 21.0,
                "fecha_cbte": "20250122",
                "condicion_iva_receptor_id": 5
            }
        }


class CompConsultarResponse(BaseModel):
    """
    Response de consulta de un comprobante existente en AFIP.
    
    Incluye todos los datos necesarios para crear una Nota de Crédito/Débito
    basada en este comprobante.
    """
    tipo_cbte: int = Field(..., description="Tipo de comprobante consultado (ej: 11=Factura C)")
    punto_vta: int = Field(..., description="Punto de venta consultado")
    cbte_nro: int = Field(..., description="Número de comprobante consultado")
    resultado: Optional[str] = Field(None, description="Resultado según AFIP (A=Aprobado, R=Rechazado, o vacío si no disponible)")
    cae: Optional[str] = Field(None, description="CAE informado por AFIP para este comprobante (si aplica)")
    vencimiento: Optional[str] = Field(None, description="Vencimiento del CAE (YYYYMMDD) si aplica")
    fecha_cbte: Optional[str] = Field(None, description="Fecha del comprobante (YYYYMMDD) si AFIP la informa")
    reproceso: Optional[str] = Field(None, description="Indicador de reproceso (S/N) si AFIP lo informa")
    obs: List[str] = Field(default_factory=list, description="Observaciones informadas por AFIP")
    err_msg: Optional[str] = Field(None, description="Mensaje de error si AFIP informa error")
    err_code: Optional[str] = Field(None, description="Código de error si AFIP informa error")
    
    # Campos adicionales necesarios para crear Nota de Crédito/Débito
    concepto: Optional[int] = Field(None, description="Tipo de concepto (1=Productos, 2=Servicios, 3=Productos y Servicios)")
    tipo_doc: Optional[int] = Field(None, description="Tipo de documento del receptor (80=CUIT, 96=DNI, 99=Consumidor Final)")
    nro_doc: Optional[str] = Field(None, description="Número de documento del receptor")
    imp_total: Optional[float] = Field(None, description="Importe total del comprobante")
    imp_neto: Optional[float] = Field(None, description="Importe neto gravado")
    imp_iva: Optional[float] = Field(None, description="Importe de IVA")
    imp_tot_conc: Optional[float] = Field(None, description="Importe total de conceptos no gravados")
    imp_trib: Optional[float] = Field(None, description="Importe de tributos")
    imp_op_ex: Optional[float] = Field(None, description="Importe de operaciones exentas")
    moneda_id: Optional[str] = Field(None, description="Código de moneda (PES=Pesos, DOL=Dólar, EUR=Euro)")
    moneda_ctz: Optional[str] = Field(None, description="Cotización de moneda")
    cbtes_asoc: Optional[List[ComprobanteAsociado]] = Field(
        default_factory=list,
        description="Lista de comprobantes asociados (si este comprobante es una NC/ND, referencia la factura original)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tipo_cbte": 11,
                "punto_vta": 1,
                "cbte_nro": 123,
                "resultado": "A",
                "cae": "70417000000000",
                "vencimiento": "20260201",
                "fecha_cbte": "20260122",
                "reproceso": "N",
                "obs": [],
                "err_msg": None,
                "err_code": None,
                "concepto": 1,
                "tipo_doc": 99,
                "nro_doc": "0",
                "imp_total": 10.00,
                "imp_neto": 8.26,
                "imp_iva": 0.0,
                "imp_tot_conc": 0.0,
                "imp_trib": 0.0,
                "imp_op_ex": 0.0,
                "moneda_id": "PES",
                "moneda_ctz": "1.0000",
                "cbtes_asoc": []
            }
        }


class FacturaCCreate(BaseModel):
    """Request para crear una factura C"""
    punto_vta: int = Field(..., description="Punto de venta")
    concepto: int = Field(..., description="Tipo de concepto (1=Productos, 2=Servicios, 3=Productos y Servicios)")
    tipo_doc: int = Field(..., description="Tipo de documento (99=Consumidor Final)")
    nro_doc: str = Field(..., description="Número de documento")
    imp_total: float = Field(..., description="Importe total")
    imp_neto: float = Field(..., description="Importe neto gravado")
    imp_tot_conc: float = Field(default=0.0, description="Importe total de conceptos no gravados")
    imp_trib: float = Field(default=0.0, description="Importe de tributos")
    imp_op_ex: float = Field(default=0.0, description="Importe de operaciones exentas")
    fecha_cbte: str = Field(..., description="Fecha del comprobante (YYYYMMDD)")
    moneda_id: str = Field(default="PES", description="Código de moneda (PES=Pesos)")
    moneda_ctz: str = Field(default="1.0000", description="Cotización de moneda")
    condicion_iva_receptor_id: Optional[int] = Field(
        None,
        description="Condición IVA del receptor (Obligatorio según RG 5616). Ej: 5=Consumidor Final"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "punto_vta": 1,
                "concepto": 1,
                "tipo_doc": 99,
                "nro_doc": "0",
                "imp_total": 121.0,
                "imp_neto": 100.0,
                "fecha_cbte": "20250122",
                "condicion_iva_receptor_id": 5
            }
        }


class FacturaResponse(BaseModel):
    """Response de creación de factura con toda la información disponible"""
    resultado: str = Field(..., description="Resultado (A=Aprobado, R=Rechazado)")
    cae: Optional[str] = Field(None, description="CAE (Código de Autorización Electrónico)")
    vencimiento: Optional[str] = Field(None, description="Fecha de vencimiento del CAE (YYYYMMDD)")
    cbte_nro: Optional[int] = Field(None, description="Número de comprobante")
    fecha_cbte: Optional[str] = Field(None, description="Fecha del comprobante (YYYYMMDD)")
    emision_tipo: Optional[str] = Field(None, description="Tipo de emisión (normalmente 'CAE')")
    punto_venta: Optional[int] = Field(None, description="Punto de venta")
    cbt_desde: Optional[int] = Field(None, description="Número de comprobante desde")
    cbt_hasta: Optional[int] = Field(None, description="Número de comprobante hasta")
    tipo_cbte: Optional[int] = Field(None, description="Tipo de comprobante")
    reproceso: Optional[str] = Field(None, description="Indicador de reproceso (S/N)")
    obs: List[str] = Field(default_factory=list, description="Observaciones")
    err_msg: Optional[str] = Field(None, description="Mensaje de error si fue rechazado")
    err_code: Optional[str] = Field(None, description="Código de error si fue rechazado")

    class Config:
        json_schema_extra = {
            "example": {
                "resultado": "A",
                "cae": "60423794871430",
                "vencimiento": "20260128",
                "cbte_nro": 2,
                "fecha_cbte": "20260118",
                "emision_tipo": "CAE",
                "punto_venta": 1,
                "cbt_desde": 2,
                "cbt_hasta": 2,
                "tipo_cbte": 11,
                "reproceso": "N",
                "obs": []
            }
        }


class UltimoAutorizadoResponse(BaseModel):
    """Response de último comprobante autorizado"""
    tipo_cbte: int = Field(..., description="Tipo de comprobante")
    punto_vta: int = Field(..., description="Punto de venta")
    ultimo_nro: int = Field(..., description="Último número autorizado")

    class Config:
        json_schema_extra = {
            "example": {
                "tipo_cbte": 11,
                "punto_vta": 1,
                "ultimo_nro": 5
            }
        }


class PuntoVenta(BaseModel):
    """Modelo de punto de venta"""
    nro: int = Field(..., description="Número de punto de venta")
    emision_tipo: Optional[str] = Field(None, description="Tipo de emisión")
    bloqueado: Optional[str] = Field(None, description="Estado de bloqueo")
    fch_baja: Optional[str] = Field(None, description="Fecha de baja (si está dado de baja)")

    class Config:
        json_schema_extra = {
            "example": {
                "nro": 1,
                "emision_tipo": "CAE",
                "bloqueado": "No",
                "fch_baja": None
            }
        }


class PuntosVentaResponse(BaseModel):
    """Response de lista de puntos de venta"""
    puntos_venta: List[PuntoVenta] = Field(..., description="Lista de puntos de venta")

    class Config:
        json_schema_extra = {
            "example": {
                "puntos_venta": [
                    {
                        "nro": 1,
                        "emision_tipo": "CAE",
                        "bloqueado": "No",
                        "fch_baja": None
                    }
                ]
            }
        }


class IVACondition(BaseModel):
    """Modelo para condición de IVA del receptor"""
    id: int = Field(..., description="ID de la condición de IVA")
    desc: str = Field(..., description="Descripción de la condición de IVA")
    fch_desde: Optional[str] = Field(None, description="Fecha desde")
    fch_hasta: Optional[str] = Field(None, description="Fecha hasta")


class IVACondicionesResponse(BaseModel):
    """Response de lista de condiciones de IVA"""
    condiciones: List[IVACondition] = Field(..., description="Lista de condiciones de IVA")
    
    class Config:
        json_schema_extra = {
            "example": {
                "condiciones": [
                    {"id": 1, "desc": "IVA Responsable Inscripto"},
                    {"id": 5, "desc": "Consumidor Final"}
                ]
            }
        }


class AuthVerifyResponse(BaseModel):
    """Response de verificación de autenticación"""
    success: bool = Field(..., description="Si la autenticación fue exitosa")
    token: str = Field(..., description="Token de autenticación")
    sign: str = Field(..., description="Sign de autenticación")
    service: str = Field(..., description="Servicio para el que se autenticó")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "token": "PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9InllcyI/Pg...",
                "sign": "BilPbujwA5bRI+pIxcQxTKXAjIQPB/EIEaddI94S7IELTKQLAu6HZPInUudaTE2fcMIZ...",
                "service": "wsfe"
            }
        }


class TipoParametro(BaseModel):
    """Modelo genérico para tipos de parámetros (comprobante, documento, IVA, concepto)"""
    id: int = Field(..., description="ID del tipo")
    desc: str = Field(..., description="Descripción del tipo")
    fch_desde: Optional[str] = Field(None, description="Fecha desde (YYYYMMDD)")
    fch_hasta: Optional[str] = Field(None, description="Fecha hasta (YYYYMMDD)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 11,
                "desc": "Factura C",
                "fch_desde": "20100101",
                "fch_hasta": None
            }
        }


class TiposComprobanteResponse(BaseModel):
    """Response de lista de tipos de comprobante"""
    tipos: List[TipoParametro] = Field(..., description="Lista de tipos de comprobante")

    class Config:
        json_schema_extra = {
            "example": {
                "tipos": [
                    {"id": 1, "desc": "Factura A", "fch_desde": "20100101", "fch_hasta": None},
                    {"id": 6, "desc": "Factura B", "fch_desde": "20100101", "fch_hasta": None},
                    {"id": 11, "desc": "Factura C", "fch_desde": "20100101", "fch_hasta": None}
                ]
            }
        }


class TiposDocumentoResponse(BaseModel):
    """Response de lista de tipos de documento"""
    tipos: List[TipoParametro] = Field(..., description="Lista de tipos de documento")

    class Config:
        json_schema_extra = {
            "example": {
                "tipos": [
                    {"id": 80, "desc": "CUIT", "fch_desde": "20100101", "fch_hasta": None},
                    {"id": 96, "desc": "DNI", "fch_desde": "20100101", "fch_hasta": None},
                    {"id": 99, "desc": "Consumidor Final", "fch_desde": "20100101", "fch_hasta": None}
                ]
            }
        }


class TiposIVAResponse(BaseModel):
    """Response de lista de tipos de IVA (alícuotas)"""
    tipos: List[TipoParametro] = Field(..., description="Lista de tipos de IVA")

    class Config:
        json_schema_extra = {
            "example": {
                "tipos": [
                    {"id": 3, "desc": "0%", "fch_desde": "20100101", "fch_hasta": None},
                    {"id": 4, "desc": "10.5%", "fch_desde": "20100101", "fch_hasta": None},
                    {"id": 5, "desc": "21%", "fch_desde": "20100101", "fch_hasta": None}
                ]
            }
        }


class TiposConceptoResponse(BaseModel):
    """Response de lista de tipos de concepto"""
    tipos: List[TipoParametro] = Field(..., description="Lista de tipos de concepto")

    class Config:
        json_schema_extra = {
            "example": {
                "tipos": [
                    {"id": 1, "desc": "Productos", "fch_desde": "20100101", "fch_hasta": None},
                    {"id": 2, "desc": "Servicios", "fch_desde": "20100101", "fch_hasta": None},
                    {"id": 3, "desc": "Productos y Servicios", "fch_desde": "20100101", "fch_hasta": None}
                ]
            }
        }


class EstadoServidoresResponse(BaseModel):
    """Response de estado de servidores AFIP"""
    app_server: str = Field(..., description="Estado del servidor de aplicación")
    db_server: str = Field(..., description="Estado del servidor de base de datos")
    auth_server: str = Field(..., description="Estado del servidor de autenticación")

    class Config:
        json_schema_extra = {
            "example": {
                "app_server": "OK",
                "db_server": "OK",
                "auth_server": "OK"
            }
        }
