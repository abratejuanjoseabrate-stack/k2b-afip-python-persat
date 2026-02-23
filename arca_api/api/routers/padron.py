"""
Router de padrón - DEPRECADO
Este archivo se ha dividido en:
- padron_homo.py: Endpoints de homologación
- padron_prod.py: Endpoints de producción

Se mantiene este archivo solo para compatibilidad hacia atrás.
Las importaciones deben actualizarse a usar padron_homo y padron_prod directamente.
"""
from . import padron_homo, padron_prod

# Re-exportar routers para compatibilidad hacia atrás
router = padron_homo.router
prod_router = padron_prod.router

__all__ = ['router', 'prod_router']
