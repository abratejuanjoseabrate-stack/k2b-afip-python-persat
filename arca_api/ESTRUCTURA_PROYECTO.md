# Estructura del Proyecto - PyAfipWs FastAPI Arca

## Diagrama de Estructura de Carpetas

```
arca_api/
│
├── 📁 src/                          # ⭐ Estructura principal del proyecto
│   ├── __init__.py
│   ├── main.py                      # 🚀 Punto de entrada principal (FastAPI app)
│   ├── config.py                    # ⚙️ Configuración (Pydantic Settings)
│   ├── database.py                  # 🗄️ Configuración de base de datos (SQLAlchemy)
│   ├── test_wsaa_wsfe.py            # 🧪 Tests de servicios AFIP
│   │
│   ├── 📁 auth/                      # 🔐 Módulo de autenticación
│   │   ├── __init__.py
│   │   ├── models.py                # Modelo User (SQLAlchemy ORM)
│   │   ├── schemas.py               # Schemas Pydantic (UserCreate, UserResponse, Token)
│   │   ├── router.py                # Endpoints: /api/v1/auth/register, /login, /me
│   │   ├── service.py               # Lógica de negocio (hash, verify, JWT)
│   │   └── dependencies.py          # Dependencias (get_current_user)
│   │
│   ├── 📁 facturas/                  # 📄 Módulo de facturación electrónica
│   │   ├── __init__.py
│   │   ├── schemas.py               # Schemas: FacturaCreate, FacturaResponse, etc.
│   │   ├── router.py                # Endpoints de facturación
│   │   ├── service.py               # WSFEv1Service (wrapper de pyafipws.wsfev1)
│   │   └── dependencies.py          # Dependencias del módulo
│   │
│   ├── 📁 padron/                    # 👥 Módulo de padrón AFIP
│   │   ├── __init__.py
│   │   ├── schemas.py               # Schemas de padrón
│   │   ├── router.py                # Endpoints de consulta padrón A5
│   │   ├── service.py               # Servicio de padrón AFIP
│   │   └── dependencies.py          # Dependencias del módulo
│   │
│   └── 📁 shared/                    # 🔧 Utilidades compartidas
│       ├── __init__.py
│       ├── afip_auth.py             # Autenticación AFIP (WSAA) - Tickets de acceso
│       ├── exceptions.py            # Excepciones personalizadas (AFIPError, etc.)
│       ├── exception_handlers.py    # Handlers de excepciones para FastAPI
│       └── logging_config.py        # Configuración de logging
│
├── 📁 certs/                         # 🔒 Certificados AFIP (NO versionar)
│   ├── correr_opensll_windows.txt
│   ├── 📁 homo/                      # Certificados homologación
│   │   ├── *.crt
│   │   ├── *.key
│   │   └── *.pem
│   └── 📁 prod/                      # Certificados producción
│       ├── *.crt
│       └── *.key
│
├── 📁 cache/                         # 💾 Caché de tickets AFIP (NO versionar)
│   ├── 📁 homo/                      # Caché homologación
│   │   ├── TA-*.xml                 # Tickets de acceso
│   │   └── *.pkl                     # Archivos pickle
│   └── 📁 prod/                      # Caché producción
│       ├── TA-*.xml
│       └── *.pkl
│
├── 📄 .gitignore                     # Configuración de gitignore
├── 📄 run.py                         # 🚀 Script de inicio del servidor (uvicorn)
├── 📄 requirements-fastapi.txt      # Dependencias FastAPI y Python
├── 📄 database.db                    # 🗄️ Base de datos SQLite (NO versionar)
└── 📄 ESTRUCTURA_PROYECTO.md         # Este archivo
```

## Descripción de Módulos

### 🚀 Punto de Entrada
- **`run.py`**: Script principal para iniciar el servidor FastAPI con uvicorn
- **`src/main.py`**: Aplicación FastAPI principal, configura routers, middleware y handlers de excepciones

### ⚙️ Configuración
- **`src/config.py`**: Configuración usando Pydantic Settings, lee variables de entorno desde `.env`
- **`src/database.py`**: Configuración de SQLAlchemy y conexión a base de datos

### 🔐 Autenticación (`src/auth/`)
- **`models.py`**: Modelo User (SQLAlchemy ORM) - tabla `users`
- **`schemas.py`**: Schemas Pydantic para validación:
  - `UserCreate` - Crear usuario
  - `UserResponse` - Respuesta de usuario
  - `Token` - Token JWT
- **`router.py`**: Endpoints REST:
  - `POST /api/v1/auth/register` - Registrar nuevo usuario
  - `POST /api/v1/auth/login` - Login (OAuth2 Password Flow)
  - `GET /api/v1/auth/me` - Obtener usuario actual autenticado
- **`service.py`**: Lógica de negocio:
  - Hash de contraseñas (bcrypt)
  - Verificación de contraseñas
  - Creación de tokens JWT
- **`dependencies.py`**: Dependencias FastAPI (get_current_user)

### 📄 Facturación (`src/facturas/`)
- **`schemas.py`**: Schemas para facturas:
  - `FacturaCreate` - Crear factura
  - `FacturaResponse` - Respuesta de factura emitida
  - `PuntoVenta`, `IVACondition`, etc.
- **`router.py`**: Endpoints de facturación electrónica:
  - Emisión de facturas (A, B, C)
  - Consulta de comprobantes
  - Obtener puntos de venta
  - Obtener tipos de comprobante, documento, IVA, etc.
- **`service.py`**: `WSFEv1Service` - Wrapper de `pyafipws.wsfev1`:
  - Conexión a WSFEv1
  - Emisión de facturas
  - Consultas a AFIP
- **`dependencies.py`**: Dependencias del módulo

### 👥 Padrón AFIP (`src/padron/`)
- **`schemas.py`**: Schemas para consultas de padrón
- **`router.py`**: Endpoints de consulta padrón A5:
  - Consultar contribuyente por CUIT
  - Obtener datos del padrón
- **`service.py`**: Servicio de padrón AFIP (PadrónA5Service)
- **`dependencies.py`**: Dependencias del módulo

### 🔧 Utilidades Compartidas (`src/shared/`)
- **`afip_auth.py`**: Autenticación con WSAA (obtener tickets de acceso)
- **`exceptions.py`**: Excepciones personalizadas:
  - `AFIPError` - Error base de AFIP
  - `AFIPConnectionError` - Error de conexión
  - `AFIPServiceError` - Error del servicio
  - `AFIPValidationError` - Error de validación
- **`exception_handlers.py`**: Handlers de excepciones para FastAPI
- **`logging_config.py`**: Configuración de logging (formato, niveles, archivos)

## Archivos Importantes

### ✅ Versionar en Git
- `src/` - Todo el código fuente
- `run.py` - Script de inicio
- `requirements-fastapi.txt` - Dependencias
- `.gitignore` - Configuración git
- `ESTRUCTURA_PROYECTO.md` - Documentación

### ❌ NO Versionar (en .gitignore)
- `certs/` - Certificados y claves privadas (sensible)
- `cache/` - Caché de tickets AFIP
- `database.db` - Base de datos SQLite
- `__pycache__/` - Archivos compilados Python
- `.env` - Variables de entorno (sensible)
- `*.log` - Archivos de log

## Flujo de la Aplicación

```
run.py
  └──> src/main.py (FastAPI app)
       ├──> src/config.py (Settings desde .env)
       ├──> src/database.py (DB connection pool)
       ├──> src/auth/router.py (/api/v1/auth/*)
       │    └──> src/auth/service.py (JWT, bcrypt)
       ├──> src/facturas/router.py (/api/v1/facturas/*)
       │    └──> src/facturas/service.py (WSFEv1Service)
       │         └──> src/shared/afip_auth.py (WSAA tickets)
       └──> src/padron/router.py (/api/v1/padron/*)
            └──> src/padron/service.py (PadrónA5Service)
                 └──> src/shared/afip_auth.py (WSAA tickets)
```

## Dependencias Externas

- **FastAPI**: Framework web asíncrono
- **Uvicorn**: Servidor ASGI
- **SQLAlchemy**: ORM para base de datos
- **aiosqlite**: Driver asíncrono para SQLite
- **Pydantic**: Validación de datos y settings
- **python-jose**: JWT tokens
- **bcrypt**: Hash de contraseñas
- **pyafipws**: Librería para servicios AFIP (WSAA, WSFEv1, Padrón)
- **python-multipart**: Para formularios (OAuth2)

## Estructura de Módulos

Cada módulo (`auth`, `facturas`, `padron`) sigue el mismo patrón:
- **`schemas.py`**: Definición de datos (Pydantic)
- **`router.py`**: Endpoints HTTP (FastAPI)
- **`service.py`**: Lógica de negocio
- **`dependencies.py`**: Dependencias e inyección

Este patrón facilita el mantenimiento y la escalabilidad del código.