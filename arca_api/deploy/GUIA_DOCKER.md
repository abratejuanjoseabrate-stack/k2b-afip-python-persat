# Despliegue Docker - Java + Python

## Resumen de Arquitectura Docker

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Host (Ubuntu)                  │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐      ┌──────────────┐                 │
│  │   TomEE 9    │◄────►│ arca_api     │                 │
│  │   :8080      │ HTTP │   :8000      │                 │
│  │   (Java)     │      │  (Python)    │                 │
│  └──────┬───────┘      └──────────────┘                 │
│         │                                               │
│    [Expuesto]                                          │
│         │                                               │
│         ▼                                               │
│   Clientes / Internet                                   │
└─────────────────────────────────────────────────────────┘
```

## Ventajas de Docker vs Instalación Nativa

| Aspecto | Docker | Instalación Nativa |
|---------|--------|-------------------|
| **Despliegue** | `docker-compose up -d` | Múltiples pasos manuales |
| **Actualización** | Rebuild imagen | Reinstalar manualmente |
| **Rollback** | `docker-compose down && up` | Restaurar backups |
| **Entornos** | Igual en dev/prod | Puede variar |
| **Aislamiento** | Contenedores separados | Servicios en mismo OS |
| **Backup** | Volúmenes montados | Copiar archivos manual |

## Pre-requisitos en Servidor Ubuntu

```bash
# Instalar Docker
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Agregar usuario al grupo docker (para no usar sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verificar instalación
docker --version
docker compose version
```

## Estructura de Archivos en Servidor

```
/opt/k2b/
├── docker-compose.yml          # Orquestación de servicios
├── .env                        # Variables de entorno
├── dist/
│   └── K2BHurlinghamAppWeb.war # WAR compilado
├── conf/
│   ├── afip.properties         # Config AFIP Java
│   └── certs/                  # Certificados Java
│       ├── afip-homo.p12
│       └── afip-prod.p12
├── servicioAfip/
│   └── arca_api/
│       ├── Dockerfile
│       ├── certs/              # Certificados Python
│       │   ├── homo/
│       │   │   ├── 20250224-2130356-20323144008-0e5dc4f0.crt
│       │   │   └── 20250224-2130356-20323144008-0e5dc4f0.key
│       │   └── prod/
│       └── cache/              # Cache persistente
├── logs/
│   ├── tomee/                  # Logs TomEE
│   └── arca_api/               # Logs Python
└── nginx/                      # Opcional: reverse proxy
    └── nginx.conf
```

## Paso 1: Preparar el Servidor

```bash
# Crear estructura de directorios
sudo mkdir -p /opt/k2b/{dist,conf/certs,servicioAfip/arca_api/certs/{homo,prod},logs/{tomee,arca_api},nginx}
sudo chown -R $USER:$USER /opt/k2b

# Clonar o copiar el proyecto
cd /opt
# Opción A: Clonar desde git
git clone https://github.com/tu-usuario/K2BHurlinghamAppWeb.git

# Opción B: Copiar desde tu máquina
scp -r K2BHurlinghamAppWeb/* usuario@servidor:/opt/k2b/
```

## Paso 2: Configurar Variables de Entorno

```bash
cd /opt/k2b
cat > .env << 'EOF'
# Entorno
APP_ENV=production
LOG_LEVEL=INFO

# AFIP Homologación
CUIT_HOMO=20449965493
CERT_PATH_HOMO=certs/homo/20250224-2130356-20323144008-0e5dc4f0.crt
KEY_PATH_HOMO=certs/homo/20250224-2130356-20323144008-0e5dc4f0.key

# AFIP Producción
CUIT_PROD=20449965493
CERT_PATH_PROD=certs/prod/certificado.crt
KEY_PATH_PROD=certs/prod/private.key

# Configuración Java
JAVA_OPTS=-Xms512m -Xmx2048m -XX:+UseG1GC -Dpython.backend.url=http://arca_api:8000
EOF
```

## Paso 3: Copiar Certificados

```bash
# Copiar certificados Python al servidor
scp /ruta/local/certs/homo/* usuario@servidor:/opt/k2b/servicioAfip/arca_api/certs/homo/
scp /ruta/local/certs/prod/* usuario@servidor:/opt/k2b/servicioAfip/arca_api/certs/prod/

# Copiar certificados Java
scp /ruta/local/afip-homo.p12 usuario@servidor:/opt/k2b/conf/certs/
scp /ruta/local/afip-prod.p12 usuario@servidor:/opt/k2b/conf/certs/
```

## Paso 4: Desplegar con Docker Compose

```bash
cd /opt/k2b

# Iniciar servicios
docker compose up -d

# Verificar estado
docker compose ps
docker compose logs -f

# Ver logs específicos
docker compose logs -f arca_api
docker compose logs -f tomee
```

## Paso 5: Verificar Funcionamiento

```bash
# Probar Python backend internamente
docker compose exec tomee curl http://arca_api:8000/api/v1/health

# Probar desde fuera (Java expuesto en :8080)
curl http://servidor:8080/K2BHurlinghamAppWeb/api/comprobantes/padron/a5?cuit=23258973879
```

## Comandos de Administración

```bash
# Detener servicios
docker compose down

# Reiniciar servicio específico
docker compose restart arca_api
docker compose restart tomee

# Rebuild imagen (después de cambios en código Python)
docker compose build arca_api
docker compose up -d arca_api

# Ver recursos utilizados
docker stats

# Backup de volúmenes
docker run --rm -v k2b_arca_api_cache:/source -v $(pwd):/backup alpine tar czf /backup/arca_api_cache_$(date +%Y%m%d).tar.gz -C /source .
docker run --rm -v k2b_tomee_logs:/source -v $(pwd):/backup alpine tar czf /backup/tomee_logs_$(date +%Y%m%d).tar.gz -C /source .

# Acceder a shell del contenedor
docker compose exec arca_api sh
docker compose exec tomee bash
```

## Actualización de Servicios

### Actualizar Código Python:
```bash
# 1. Actualizar código en servidor
cd /opt/k2b
# git pull o copiar nuevos archivos

# 2. Rebuild imagen
docker compose build arca_api

# 3. Reiniciar servicio
docker compose up -d arca_api
```

### Actualizar WAR Java:
```bash
# 1. Copiar nuevo WAR
cp /ruta/nuevo/K2BHurlinghamAppWeb.war /opt/k2b/dist/

# 2. Reiniciar TomEE (detecta cambios automáticamente)
docker compose restart tomee
```

## Solución de Problemas

### Contenedor Python no inicia:
```bash
# Verificar logs
docker compose logs arca_api

# Común: permisos de certificados
docker compose exec arca_api ls -la /app/certs/
docker compose exec arca_api cat /app/.env
```

### Java no puede conectar a Python:
```bash
# Verificar red Docker
docker network ls
docker network inspect k2b_k2b_network

# Probar conectividad desde TomEE
docker compose exec tomee ping arca_api
docker compose exec tomee curl http://arca_api:8000/api/v1/health
```

### Puerto 8080 ocupado:
```bash
# Verificar qué usa el puerto
sudo netstat -tlnp | grep 8080
sudo ss -tlnp | grep 8080

# Cambiar puerto en docker-compose.yml
# ports:
#   - "8081:8080"  # Cambiar 8080 externo a 8081
```

## Configuración Nginx Reverse Proxy (Opcional)

Para exponcer en puerto 80/443 con SSL:

```bash
# Crear nginx.conf
cat > /opt/k2b/nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream tomee {
        server tomee:8080;
    }

    server {
        listen 80;
        server_name tu-dominio.com;
        
        location / {
            proxy_pass http://tomee;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# Habilitar en docker-compose.yml (descomentar sección nginx)
docker compose up -d nginx
```

## Monitoreo Básico

```bash
# Script de health check
cat > /opt/k2b/health_check.sh << 'EOF'
#!/bin/bash
# Health check para K2B

if ! docker compose ps | grep -q "Up"; then
    echo "ERROR: Contenedores no están corriendo"
    docker compose up -d
fi

if ! curl -sf http://localhost:8080/K2BHurlinghamAppWeb/ > /dev/null; then
    echo "ERROR: TomEE no responde"
    docker compose restart tomee
fi

if ! docker compose exec -T tomee curl -sf http://arca_api:8000/api/v1/health > /dev/null; then
    echo "ERROR: Python backend no responde"
    docker compose restart arca_api
fi

echo "$(date): Health check OK"
EOF
chmod +x /opt/k2b/health_check.sh

# Agregar a crontab (cada 5 minutos)
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/k2b/health_check.sh >> /opt/k2b/logs/health_check.log 2>&1") | crontab -
```

## Seguridad en Producción

1. **Firewall**: Solo exponer puertos necesarios (80, 443, 8080)
2. **Docker**: Usar imágenes oficiales, mantener actualizadas
3. **Certificados**: Montar como read-only (`:ro`)
4. **Logs**: No incluir datos sensibles, rotar logs
5. **Backup**: Automatizar backup de volúmenes y certificados
6. **SSL**: Configurar Let's Encrypt para HTTPS

## Comparación: Docker vs Nativo

| Característica | Docker | Nativo |
|---------------|--------|--------|
| **Setup inicial** | ⭐⭐⭐ Fácil | ⭐⭐ Complejo |
| **Mantenimiento** | ⭐⭐⭐ Simple | ⭐⭐ Manual |
| **Performance** | ⭐⭐ Buena | ⭐⭐⭐ Óptima |
| **Recursos** | ⭐⭐ Moderado | ⭐⭐⭐ Bajo overhead |
| **Portabilidad** | ⭐⭐⭐ Excelente | ⭐⭐ Limitada |
| **Debug** | ⭐⭐ Requiere conocimiento | ⭐⭐⭐ Directo |

**Recomendación**: Usar Docker para producción. Es más fácil de mantener, actualizar y escalar.

## URLs de Acceso Final

| Servicio | URL Local (Dev) | URL Docker (Prod) |
|----------|-----------------|-------------------|
| Java App | `http://localhost:8080` | `http://servidor:8080` |
| Python | `http://localhost:8000` | Solo interno (Docker network) |
| Nginx | - | `http://servidor` (si se configura) |

---

**¿Necesitás que ajuste algo de la configuración Docker?**
