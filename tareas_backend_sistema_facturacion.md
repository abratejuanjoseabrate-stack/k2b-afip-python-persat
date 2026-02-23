# Listado de Tareas Backend - Sistema de Facturación

## Análisis basado en: https://interfazpruebafacturador.netlify.app/dashboard

---

## 1. AUTENTICACIÓN Y AUTORIZACIÓN

### 1.1 Autenticación
- [ ] **POST /api/auth/login** - Iniciar sesión
  - Validar credenciales (email/username y password)
  - Generar token JWT
  - Retornar información del usuario y permisos

- [ ] **POST /api/auth/logout** - Cerrar sesión
  - Invalidar token JWT
  - Limpiar sesión del servidor

- [ ] **POST /api/auth/refresh** - Renovar token
  - Validar refresh token
  - Generar nuevo access token

- [ ] **GET /api/auth/me** - Obtener usuario actual
  - Retornar información del usuario autenticado
  - Incluir roles y permisos

### 1.2 Autorización
- [ ] Middleware de autenticación JWT
- [ ] Middleware de autorización por roles (Administrador, Gerente, Vendedor)
- [ ] Validación de permisos por endpoint

---

## 2. DASHBOARD

### 2.1 Métricas del Dashboard
- [ ] **GET /api/dashboard/metrics** - Obtener métricas principales
  - Monto estimado a facturar (total de OTs cerradas pendientes)
  - Cantidad de órdenes listas para facturar
  - Cantidad de OTs cerradas pendientes de facturar
  - Cantidad de órdenes con antigüedad > 30 días
  - Calcular montos y contadores en tiempo real

### 2.2 Órdenes de Trabajo (OTs)
- [ ] **GET /api/orders** - Listar órdenes cerradas pendientes de facturar
  - Parámetros: `page`, `limit`, `search` (cliente o ID OT), `sort`, `order`
  - Filtrar solo OTs con estado "Cerrada" y sin factura asociada
  - Incluir información del cliente
  - Calcular "tiempo desde cierre" (Hace X días/horas)
  - Retornar paginación (total, página actual, límite)

- [ ] **GET /api/orders/{order_id}** - Obtener detalle de una orden
  - Información completa de la OT
  - Items/servicios incluidos
  - Cliente asociado
  - Historial de estados

- [ ] **GET /api/orders/{order_id}/invoice-data** - Obtener datos para generar factura
  - Datos de la OT formateados para facturación
  - Validar que la OT esté cerrada y sin factura

---

## 3. FACTURAS

### 3.1 Gestión de Facturas
- [ ] **POST /api/invoices** - Generar nueva factura desde una OT
  - Recibir `order_id`
  - Validar que la OT esté cerrada y sin factura previa
  - Generar número de factura único (formato: F-YYYY-NNN)
  - Calcular montos, impuestos, totales
  - Establecer fecha de emisión y vencimiento
  - Crear registro de factura con estado "Pendiente"
  - Actualizar estado de la OT (marcar como facturada)
  - Integración con AFIP (si aplica)

- [ ] **GET /api/invoices** - Listar facturas emitidas
  - Parámetros: `page`, `limit`, `search` (N° Factura, Cliente, OT), `status`, `sort`, `order`
  - Incluir información del cliente y OT asociada
  - Calcular estado (Pagada, Pendiente, Vencida) basado en fecha de vencimiento
  - Retornar paginación

- [ ] **GET /api/invoices/{invoice_id}** - Obtener detalle de factura
  - Información completa de la factura
  - Items/servicios facturados
  - Cliente y OT asociada
  - Historial de pagos (si aplica)
  - PDF de la factura (si existe)

- [ ] **PUT /api/invoices/{invoice_id}/status** - Actualizar estado de factura
  - Cambiar estado (Pendiente → Pagada)
  - Registrar fecha de pago
  - Actualizar saldos del cliente

- [ ] **GET /api/invoices/{invoice_id}/pdf** - Generar/descargar PDF de factura
  - Generar PDF con formato de factura
  - Incluir QR code (si aplica)
  - Retornar archivo PDF

### 3.2 Exportación
- [ ] **GET /api/invoices/export** - Exportar reporte de facturas
  - Parámetros: `format` (CSV, Excel, PDF), `filters` (fechas, estados, clientes)
  - Generar archivo con datos filtrados
  - Retornar URL de descarga o archivo directo

---

## 4. CLIENTES

### 4.1 Gestión de Clientes
- [ ] **GET /api/clients** - Listar clientes
  - Parámetros: `page`, `limit`, `search` (nombre, email, teléfono), `status`, `sort`, `order`
  - Incluir información de contacto completa
  - Retornar paginación

- [ ] **GET /api/clients/{client_id}** - Obtener detalle de cliente
  - Información completa del cliente
  - Historial de facturas
  - Órdenes de trabajo asociadas
  - Saldos pendientes

- [ ] **POST /api/clients** - Crear nuevo cliente
  - Validar datos requeridos (nombre, email, teléfono, dirección)
  - Validar email único
  - Crear registro con estado "Pendiente" o "Activo"
  - Retornar cliente creado

- [ ] **PUT /api/clients/{client_id}** - Actualizar cliente
  - Validar permisos
  - Actualizar información del cliente
  - Validar email único (si cambió)

- [ ] **DELETE /api/clients/{client_id}** - Eliminar/desactivar cliente
  - Validar que no tenga facturas pendientes
  - Marcar como inactivo (soft delete) o eliminar

- [ ] **PUT /api/clients/{client_id}/status** - Cambiar estado del cliente
  - Activar/Desactivar cliente
  - Validar reglas de negocio

### 4.2 Métricas de Clientes
- [ ] **GET /api/clients/metrics** - Obtener métricas de clientes
  - Total de clientes
  - Clientes activos
  - Nuevos clientes del mes actual
  - Comparación con mes anterior

---

## 5. REPORTES

### 5.1 Reportes Operativos
- [ ] **GET /api/reports/operational** - Obtener reporte operativo
  - Parámetros: `period` (Este Mes, Mes Anterior, Personalizado), `start_date`, `end_date`
  - OTs Finalizadas (total y comparación con período anterior)
  - Facturación Estimada (en OTs cerradas)
  - Tiempo Promedio por servicio
  - Cumplimiento SLA (porcentaje y comparación)
  - Calcular porcentajes de cambio

- [ ] **GET /api/reports/weekly-activity** - Actividad semanal
  - Volumen de OTs por día de la semana
  - Separar Finalizadas vs Pendientes
  - Últimas 4 semanas o período personalizado

- [ ] **GET /api/reports/service-types** - Distribución por tipo de servicio
  - Agrupar OTs por categoría (Mantenimiento Prev., Reparaciones, Instalaciones, Visitas Técnicas)
  - Contar cantidad de OTs por tipo
  - Calcular porcentajes

- [ ] **GET /api/reports/technician-performance** - Rendimiento de técnicos
  - OTs completadas por técnico en el período
  - Tiempo promedio por técnico
  - Calcular eficiencia (porcentaje)
  - Estado actual de cada técnico (En Ruta, Trabajando, Disponible, Finalizado)
  - Parámetros: `period`, `technician_id` (opcional)

### 5.2 Exportación de Reportes
- [ ] **GET /api/reports/export** - Exportar reporte en PDF
  - Parámetros: `report_type`, `format` (PDF), `period`, `filters`
  - Generar PDF con gráficos y tablas
  - Retornar archivo PDF

---

## 6. CONFIGURACIÓN

### 6.1 Gestión de Usuarios
- [ ] **GET /api/users** - Listar usuarios
  - Parámetros: `page`, `limit`, `search` (nombre, email), `role`, `status`, `sort`, `order`
  - Incluir información de rol y estado
  - Retornar paginación

- [ ] **GET /api/users/{user_id}** - Obtener detalle de usuario
  - Información completa del usuario
  - Roles y permisos asignados
  - Historial de actividad (opcional)

- [ ] **POST /api/users** - Crear nuevo usuario
  - Validar datos requeridos (nombre, email, password, rol)
  - Validar email único
  - Encriptar password
  - Asignar rol y permisos
  - Crear con estado "Activo" o "Inactivo"
  - Enviar email de bienvenida con credenciales (opcional)

- [ ] **PUT /api/users/{user_id}** - Actualizar usuario
  - Validar permisos (solo admin puede cambiar roles)
  - Actualizar información del usuario
  - Si cambia password, encriptar nuevo
  - Validar email único (si cambió)

- [ ] **DELETE /api/users/{user_id}** - Eliminar/desactivar usuario
  - Validar que no sea el último administrador
  - Marcar como inactivo (soft delete) o eliminar

- [ ] **PUT /api/users/{user_id}/status** - Cambiar estado del usuario
  - Activar/Desactivar usuario
  - Validar reglas de negocio

- [ ] **PUT /api/users/{user_id}/role** - Cambiar rol del usuario
  - Validar permisos (solo admin)
  - Actualizar rol y permisos asociados

### 6.2 Configuración General
- [ ] **GET /api/settings/general** - Obtener configuración general
  - Datos de la empresa
  - Configuración del sistema
  - Preferencias de facturación

- [ ] **PUT /api/settings/general** - Actualizar configuración general
  - Validar permisos (solo admin)
  - Actualizar datos de configuración

### 6.3 Configuración de Facturación
- [ ] **GET /api/settings/billing** - Obtener configuración de facturación
  - Datos fiscales
  - Configuración de AFIP
  - Formatos de numeración
  - Plazos de vencimiento

- [ ] **PUT /api/settings/billing** - Actualizar configuración de facturación
  - Validar permisos
  - Actualizar configuración fiscal

### 6.4 Seguridad
- [ ] **GET /api/settings/security** - Obtener configuración de seguridad
  - Políticas de contraseñas
  - Configuración de sesiones
  - Logs de seguridad

- [ ] **PUT /api/settings/security** - Actualizar configuración de seguridad
  - Validar permisos (solo admin)
  - Actualizar políticas de seguridad

---

## 7. INTEGRACIÓN CON AFIP (Argentina)

### 7.1 Servicios AFIP
- [ ] **POST /api/afip/authorize** - Autorizar factura en AFIP
  - Integración con Web Service de Facturación Electrónica (WSFE)
  - Obtener CAE (Código de Autorización Electrónico)
  - Registrar factura en AFIP
  - Manejar errores y reintentos

- [ ] **GET /api/afip/status** - Verificar estado de conexión con AFIP
  - Validar certificados
  - Verificar disponibilidad del servicio

- [ ] **POST /api/afip/validate-tax-id** - Validar CUIT/CUIL
  - Consultar padrón de AFIP
  - Validar datos del contribuyente

---

## 8. UTILIDADES Y SERVICIOS AUXILIARES

### 8.1 Búsqueda y Filtros
- [ ] Implementar búsqueda full-text en múltiples campos
- [ ] Implementar filtros avanzados con múltiples criterios
- [ ] Ordenamiento por múltiples columnas

### 8.2 Paginación
- [ ] Middleware de paginación estándar
- [ ] Retornar metadatos de paginación (total, página, límite, total_páginas)

### 8.3 Validación y Errores
- [ ] Validación de datos de entrada (schemas)
- [ ] Manejo centralizado de errores
- [ ] Mensajes de error descriptivos
- [ ] Códigos de estado HTTP apropiados

### 8.4 Logging y Auditoría
- [ ] Logging de operaciones críticas
- [ ] Auditoría de cambios (facturas, clientes, usuarios)
- [ ] Historial de acciones por usuario

### 8.5 Notificaciones
- [ ] Sistema de notificaciones (email, in-app)
- [ ] Notificar facturas vencidas
- [ ] Notificar nuevas facturas generadas
- [ ] Recordatorios de pagos

---

## 9. BASE DE DATOS

### 9.1 Modelos de Datos
- [ ] **users** - Usuarios del sistema
  - id, email, password_hash, nombre, rol, estado, created_at, updated_at

- [ ] **clients** - Clientes
  - id, nombre, email, telefono, direccion, ciudad, estado, created_at, updated_at

- [ ] **orders** - Órdenes de Trabajo
  - id, numero_ot, client_id, fecha_apertura, fecha_cierre, estado_operativo, monto_total, created_at, updated_at

- [ ] **invoices** - Facturas
  - id, numero_factura, order_id, client_id, fecha_emision, fecha_vencimiento, monto_subtotal, impuestos, monto_total, estado, cae (si AFIP), created_at, updated_at

- [ ] **invoice_items** - Items de Factura
  - id, invoice_id, descripcion, cantidad, precio_unitario, subtotal

- [ ] **technicians** - Técnicos
  - id, nombre, especialidad, estado_actual, created_at, updated_at

- [ ] **order_technicians** - Relación OT-Técnico
  - order_id, technician_id, tiempo_real, fecha_asignacion

- [ ] **settings** - Configuración del sistema
  - key, value, type, updated_at

### 9.2 Índices y Optimización
- [ ] Índices en campos de búsqueda frecuente
- [ ] Índices en foreign keys
- [ ] Índices en campos de filtrado (estado, fechas)

---

## 10. TESTING

### 10.1 Tests Unitarios
- [ ] Tests para cada endpoint
- [ ] Tests de validación de datos
- [ ] Tests de lógica de negocio

### 10.2 Tests de Integración
- [ ] Tests de flujos completos (crear OT → generar factura → pagar)
- [ ] Tests de integración con AFIP (mock)
- [ ] Tests de autenticación y autorización

### 10.3 Tests de Carga
- [ ] Tests de rendimiento con múltiples usuarios
- [ ] Optimización de consultas lentas

---

## 11. DOCUMENTACIÓN

### 11.1 API Documentation
- [ ] Documentar todos los endpoints (OpenAPI/Swagger)
- [ ] Ejemplos de requests y responses
- [ ] Códigos de error y sus significados

### 11.2 Documentación Técnica
- [ ] Arquitectura del sistema
- [ ] Diagrama de base de datos
- [ ] Flujos de procesos principales

---

## PRIORIZACIÓN SUGERIDA

### Fase 1 - MVP (Funcionalidad Básica)
1. Autenticación y autorización
2. CRUD de Clientes
3. CRUD de Órdenes de Trabajo
4. Generar factura desde OT
5. Listar facturas
6. Dashboard básico con métricas

### Fase 2 - Funcionalidades Completas
1. Reportes operativos
2. Gestión de usuarios
3. Exportación de reportes
4. Búsqueda y filtros avanzados

### Fase 3 - Integraciones y Optimización
1. Integración con AFIP
2. Notificaciones
3. Auditoría y logging
4. Optimización y testing

---

## NOTAS TÉCNICAS

- **Framework sugerido**: FastAPI (Python) o Express.js (Node.js)
- **Base de datos**: PostgreSQL o MySQL
- **Autenticación**: JWT tokens
- **Validación**: Pydantic (FastAPI) o Joi (Express)
- **ORM**: SQLAlchemy (Python) o Sequelize/TypeORM (Node.js)
- **Testing**: pytest (Python) o Jest (Node.js)
- **Documentación**: OpenAPI/Swagger

---

**Fecha de creación**: 2026-01-XX
**Última actualización**: 2026-01-XX
