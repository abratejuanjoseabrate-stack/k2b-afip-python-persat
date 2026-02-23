# Deploy del Servicio AFIP en Docker

## Requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 512MB RAM mínimo
- 2GB espacio en disco

## Estructura de Archivos

```
servicioAfip/
├── Dockerfile.deploy      # Dockerfile del servicio
├── docker-compose.yml     # Orquestación
├── .env.example          # Variables de entorno ejemplo
├── deploy.sh             # Script de deploy
├── backup.sh             # Script de backup
├── certs/                # Certificados AFIP
│   ├── homo/
│   │   ├── CERT.crt
│   │   └── keyArca2
│   └── prod/
│       ├── cert.crt
│       └── key.key
└── arca_api/             # Código del servicio
    ├── src/
    ├── requirements-fastapi.txt
    └── run.py
```

## Instalación Rápida

### 1. Preparar Certificados

Copiar tus certificados AFIP en la carpeta `certs/`:

```bash
mkdir -p certs/homo certs/prod

# Certificados de homologación (testing)
cp /ruta/a/tu/certificado.crt certs/homo/CERT.crt
cp /ruta/a/tu/clave.key certs/homo/keyArca2

# Certificados de producción (opcional)
cp /ruta/a/tu/certificado_prod.crt certs/prod/cert.crt
cp /ruta/a/tu/clave_prod.key certs/prod/key.key
```

### 2. Configurar Variables

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus datos
nano .env
```

**Variables obligatorias:**
- `AFIP_CUIT`: Tu CUIT sin guiones
- `AFIP_PTO_VTA`: Punto de venta (ej: 1)
- `JWT_SECRET_KEY`: Generar con `openssl rand -hex 32`

### 3. Deploy

```bash
# Hacer ejecutables los scripts
chmod +x deploy.sh backup.sh

# Ejecutar deploy
./deploy.sh
```

O manualmente:

```bash
# Construir e iniciar
docker-compose build
docker-compose up -d

# Verificar
curl http://localhost:8000/health
```

## Comandos Útiles

```bash
# Ver logs
docker-compose logs -f

# Reiniciar servicio
docker-compose restart

# Detener servicio
docker-compose down

# Actualizar código
git pull
docker-compose up -d --build

# Ver estado
docker-compose ps

# Acceder al contenedor
docker-compose exec afip-api bash

# Ver logs de app
ls logs/
```

## Configuración de Producción

### Firewall

```bash
# Solo exponer el puerto 8000
ufw allow 8000/tcp
ufw enable
```

### SSL con Nginx (Opcional)

Si necesitas HTTPS, agregar Nginx como reverse proxy:

```yaml
# Agregar a docker-compose.yml
nginx:
  image: nginx:alpine
  ports:
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - ./ssl:/etc/nginx/ssl:ro
```

### Backup Automático

```bash
# Agregar a crontab
crontab -e

# Backup diario a las 2 AM
0 2 * * * /ruta/a/backup.sh >> /var/log/afip-backup.log 2>&1
```

## Troubleshooting

### Error: "No existe el certificado"

Verificar que los certificados existan:
```bash
ls -la certs/homo/
```

### Error: "PUERTO 8000 en uso"

Cambiar puerto en `.env`:
```bash
API_PORT=8001
```

### Error: "Permission denied" en certificados

```bash
chmod 600 certs/homo/*
chmod 600 certs/prod/*
```

### Servicio no inicia

Ver logs:
```bash
docker-compose logs -f afip-api
```

## Endpoints Disponibles

Una vez iniciado:

- **API**: http://localhost:8000
- **Documentación**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Actualización

```bash
# 1. Backup
./backup.sh

# 2. Descargar actualización
git pull

# 3. Reconstruir
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 4. Verificar
curl http://localhost:8000/health
```

## Soporte

Para problemas con el servicio:
1. Revisar logs: `docker-compose logs`
2. Verificar configuración: `cat .env`
3. Comprobar certificados: `ls -la certs/`
