"""
Modelos Pydantic para padrón
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from datetime import date


class ImpuestoDetalle(BaseModel):
    """Detalle de impuesto del contribuyente"""
    id_impuesto: int = Field(..., description="ID del impuesto")
    descripcion: Optional[str] = Field(None, description="Descripción del impuesto")
    estado: Optional[str] = Field(None, description="Estado del impuesto (AC/BD)")
    periodo: Optional[str] = Field(None, description="Período de inscripción (AAAAMM)")


class ActividadDetalle(BaseModel):
    """Detalle de actividad del contribuyente"""
    id_actividad: int = Field(..., description="ID de la actividad")
    descripcion: Optional[str] = Field(None, description="Descripción de la actividad")
    periodo: Optional[str] = Field(None, description="Período de alta (AAAAMM)")
    orden: Optional[int] = Field(None, description="Orden de prioridad")


class PadronA5Response(BaseModel):
    """Response de consulta Padrón A5"""

    # Datos básicos
    id_persona: str = Field(..., description="CUIT/DNI consultado")
    tipo_persona: Optional[str] = Field(None, description="FISICA o JURIDICA")
    denominacion: Optional[str] = Field(None, description="Nombre/Razón social")
    estado: Optional[str] = Field(None, description="Estado de la clave (ACTIVO, etc.)")
    
    # Datos de persona física
    nombre: Optional[str] = Field(None, description="Nombre (si es persona física)")
    apellido: Optional[str] = Field(None, description="Apellido (si es persona física)")
    
    # Documento
    tipo_documento: Optional[str] = Field(None, description="Tipo de documento (DNI, CUIT, etc.)")
    numero_documento: Optional[str] = Field(None, description="Número de documento")
    
    # Fechas
    fecha_inscripcion: Optional[str] = Field(None, description="Fecha de inscripción (YYYY-MM-DD)")
    fecha_contrato_social: Optional[str] = Field(None, description="Fecha de contrato social (si aplica)")
    
    # Ubicación fiscal
    direccion: Optional[str] = Field(None, description="Dirección fiscal")
    localidad: Optional[str] = Field(None, description="Localidad")
    provincia: Optional[str] = Field(None, description="Provincia")
    cod_postal: Optional[str] = Field(None, description="Código postal")
    
    # Contacto
    telefono: Optional[str] = Field(None, description="Teléfono de contacto")
    email: Optional[str] = Field(None, description="Email de contacto")
    
    # Impuestos y actividades
    impuestos: List[int] = Field(default_factory=list, description="IDs de impuestos")
    impuestos_detallados: List[ImpuestoDetalle] = Field(default_factory=list, description="Detalle de impuestos")
    actividades: List[int] = Field(default_factory=list, description="IDs de actividades")
    actividades_detalladas: List[ActividadDetalle] = Field(default_factory=list, description="Detalle de actividades")
    
    # Indicadores de IVA
    imp_iva: Optional[str] = Field(None, description="Indicador situación IVA (AC, EX, etc.)")
    monotributo: Optional[str] = Field(None, description="Indicador monotributo (AC, EX, etc.)")
    cat_iva: Optional[int] = Field(None, description="Categoría IVA estimada")
    
    # Respuesta completa
    raw: Dict[str, Any] = Field(default_factory=dict, description="Respuesta completa (JSON)")
