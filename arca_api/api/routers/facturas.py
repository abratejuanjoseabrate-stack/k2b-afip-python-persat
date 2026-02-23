"""
Router de facturas - DEPRECADO
Este archivo se ha dividido en:
- facturas_homo.py: Endpoints de homologación
- facturas_prod.py: Endpoints de producción

Se mantiene este archivo solo para compatibilidad hacia atrás.
Las importaciones deben actualizarse a usar facturas_homo y facturas_prod directamente.
"""
from . import facturas_homo, facturas_prod

# Re-exportar routers para compatibilidad hacia atrás
router = facturas_homo.router
prod_router = facturas_prod.router

__all__ = ['router', 'prod_router']
