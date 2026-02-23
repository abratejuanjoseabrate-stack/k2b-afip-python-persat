# Servicio AFIP - PyAfipWs API

API REST para interacturar con los web services de AFIP (factura electrónica argentina).

## Requisitos

- Python 3.9+
- Certificados AFIP (homologación y/o producción)

## Instalación

```bash
cd E:\20250726\K2BHurlinghamAppWeb\servicioAfip\arca_api

# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements-fastapi.txt
```

## Configuración

Editar el archivo `.env` con los datos del contribuyente:

```env
CUIT=TU_CUIT_SIN_GUIONES
PTO_VTA=1
```

Los certificados deben estar en:
- Homologación: `certs/homo/`
- Producción: `certs/prod/`

## Ejecución

```bash
python run.py
```

## Endpoints

| URL | Descripción |
|-----|-------------|
| http://localhost:8000/ | API Root |
| http://localhost:8000/docs | Documentación Swagger |
| http://localhost:8000/redoc | Documentación ReDoc |
| http://localhost:8000/health | Health Check |

## Ambientes

- **Homologación** (testing): Usa certificados en `certs/homo/`
- **Producción**: Usa certificados en `certs/prod/`

Los URLs de AFIP están configurados en el `.env`.
