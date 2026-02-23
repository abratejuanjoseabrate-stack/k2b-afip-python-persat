"""
Modelos Pydantic para padrón
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class PadronA5Response(BaseModel):
    """Response de consulta Padrón A5"""

    id_persona: str = Field(..., description="CUIT/DNI consultado")
    denominacion: Optional[str] = Field(None, description="Nombre/Razón social")
    estado: Optional[str] = Field(None, description="Estado de la clave")
    direccion: Optional[str] = Field(None, description="Dirección fiscal")
    localidad: Optional[str] = Field(None, description="Localidad")
    provincia: Optional[str] = Field(None, description="Provincia")
    cod_postal: Optional[str] = Field(None, description="Código postal")
    impuestos: List[int] = Field(default_factory=list, description="IDs de impuestos")
    actividades: List[int] = Field(default_factory=list, description="IDs de actividades")
    imp_iva: Optional[str] = Field(None, description="Indicador IVA")
    monotributo: Optional[str] = Field(None, description="Indicador monotributo")
    cat_iva: Optional[int] = Field(None, description="Categoría IVA (estimada)")
    raw: Dict[str, Any] = Field(default_factory=dict, description="Respuesta completa (JSON)")
