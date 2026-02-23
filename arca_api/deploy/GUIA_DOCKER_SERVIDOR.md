# Guía de Deploy Docker en Servidor Remoto Ubuntu

Guía completa para desplegar el backend Python FastAPI (AFIP) en un servidor remoto Ubuntu usando Docker.

## Requisitos del Servidor

- Ubuntu 20.04 o superior
- Docker 24.0+ y Docker Compose 2.20+
- SSH acceso con clave pública
- 4GB RAM mínimo, 8GB recomendado

---

## Paso 1: Preparar Archivos en tu Máquina Local (Windows)

### 1.1 Crear estructura de archivos para subir

En tu máquina Windows, prepará los siguientes archivos en una carpeta (ej: `C:\deploy-afip`):

```
C:\deploy-afip\
├── docker-compose.yml          # El archivo docker-compose.prod.yml renombrado
├── servicioAfip/
│   ├── arca_api/
│   │   ├── certs/
│   │   │   ├── homo/
│   │   │   │   ├── LIROpriv20260219homo2_crt.crt
│   │   │   │   └── LIROpriv20260219homo2.key
│   │   │   └── prod/
│   │   │       ├── LIROPRUEBASFACT20260919PROD2_4d6fbf9ef97dc5b6.crt
│   │   │       └── LIROpriv20260219prod2.key
│   │   ├── logs/               # (vacío, se creará en servidor)
│   │   └── cache/              # (vacío, se creará en servidor)
│   ├── requirements.txt        # Copiar de servicioAfip/requirements.txt
│   ├── setup.py                # Copiar de servicioAfip/setup.py
│   ├── setup.cfg               # Copiar de servicioAfip/setup.cfg
│   ├── licencia.txt            # Copiar de servicioAfip/licencia.txt
│   ├── README.md               # Copiar de servicioAfip/README.md
│   ├── *.py                    # Todos los archivos .py de servicioAfip/
│   ├── formatos/               # Copiar directorio servicioAfip/formatos/
│   ├── plantillas/             # Copiar directorio servicioAfip/plantillas/
│   ├── typelib/                # Copiar directorio servicioAfip/typelib/
│   └── arca_api/
│       ├── Dockerfile
│       ├── requirements-fastapi.txt
│       ├── run.py
│       ├── src/                # Todo el código fuente
│       └── api/                # API alternativa si existe
```

### 1.2 Obtener docker-compose.yml

Copiá `docker-compose.prod.yml` del proyecto y renombralo a `docker-compose.yml`.

Modificá el `CUIT` según tu certificado:

```yaml
# En docker-compose.yml, línea 17-18:
- CUIT=30712330984  # <-- Cambiar por tu CUIT real
```

### 1.3 Preparar script de subida

Creá un archivo `deploy.ps1` en `C:\deploy-afip\`:

```powershell
# deploy.ps1 - Script para subir archivos al servidor
param(
    [Parameter(Mandatory=$true)]
    [string]$ServerIP,
    
    [Parameter(Mandatory=$true)]
    [string]$Username
)

Write-Host "Subiendo archivos a $ServerIP..." -ForegroundColor Green

# Crear directorios en servidor remoto (si no existen)
ssh $Username@$ServerIP "mkdir -p /opt/afip/servicioAfip/arca_api/{certs/{homo,prod},logs,cache}"

# Subir docker-compose.yml
scp docker-compose.yml $Username@$ServerIP:/opt/afip/

# Subir certificados
scp -r servicioAfip/arca_api/certs/homo/* $Username@$ServerIP:/opt/afip/servicioAfip/arca_api/certs/homo/
scp -r servicioAfip/arca_api/certs/prod/* $Username@$ServerIP:/opt/afip/servicioAfip/arca_api/certs/prod/

# Subir código fuente Python (solo estructura necesaria para build)
scp -r servicioAfip/arca_api/src $Username@$ServerIP:/opt/afip/servicioAfip/arca_api/
scp -r servicioAfip/arca_api/api $Username@$ServerIP:/opt/afip/servicioAfip/arca_api/
scp servicioAfip/arca_api/Dockerfile $Username@$ServerIP:/opt/afip/servicioAfip/arca_api/
scp servicioAfip/arca_api/requirements-fastapi.txt $Username@$ServerIP:/opt/afip/servicioAfip/arca_api/
scp servicioAfip/arca_api/run.py $Username@$ServerIP:/opt/afip/servicioAfip/arca_api/

# Subir archivos pyafipws necesarios para el build
scp servicioAfip/requirements.txt $Username@$ServerIP:/opt/afip/servicioAfip/
scp servicioAfip/setup.py $Username@$ServerIP:/opt/afip/servicioAfip/
scp servicioAfip/setup.cfg $Username@$ServerIP:/opt/afip/servicioAfip/
scp servicioAfip/licencia.txt $Username@$ServerIP:/opt/afip/servicioAfip/
scp servicioAfip/README.md $Username@$ServerIP:/opt/afip/servicioAfip/

# Subir todos los .py de pyafipws
Get-ChildItem servicioAfip/*.py | ForEach-Object {
    scp $_.FullName $Username@$ServerIP:/opt/afip/servicioAfip/
}

# Subir directorios de pyafipws
scp -r servicioAfip/formatos $Username@$ServerIP:/opt/afip/servicioAfip/
scp -r servicioAfip/plantillas $Username@$ServerIP:/opt/afip/servicioAfip/
scp -r servicioAfip/typelib $Username@$ServerIP:/opt/afip/servicioAfip/

Write-Host "Archivos subidos exitosamente!" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el servicio en el servidor, ejecutá:" -ForegroundColor Yellow
Write-Host "ssh $Username@$ServerIP" -ForegroundColor Cyan
Write-Host "cd /opt/afip && docker compose up -d" -ForegroundColor Cyan
```

---

## Paso 2: Configurar Servidor Ubuntu

### 2.1 Instalar Docker en el servidor (SSH)

Conectate al servidor y ejecutá:

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose
sudo apt install -y docker-compose-plugin

# Verificar instalación
docker --version
docker compose version
```

### 2.2 Crear estructura de directorios

```bash
sudo mkdir -p /opt/afip/servicioAfip/arca_api/{certs/{homo,prod},logs,cache,src,api}
sudo chown -R $USER:$USER /opt/afip
```

---

## Paso 3: Subir Archivos desde Windows

### 3.1 Ejecutar script de deploy

En PowerShell (como Administrador):

```powershell
cd C:\deploy-afip
.\deploy.ps1 -ServerIP "XXX.XXX.XXX.XXX" -Username "tu-usuario"
```

**Manualmente (si el script falla):**

```powershell
# En PowerShell, ejecutá uno por uno:
$ServerIP = "XXX.XXX.XXX.XXX"  # IP del servidor
$Username = "tu-usuario"       # Usuario SSH

# Subir docker-compose.yml
scp docker-compose.yml $Username@${ServerIP}:/opt/afip/

# Subir certificados
scp -r servicioAfip/arca_api/certs/homo/* $Username@${ServerIP}:/opt/afip/servicioAfip/arca_api/certs/homo/
scp -r servicioAfip/arca_api/certs/prod/* $Username@${ServerIP}:/opt/afip/servicioAfip/arca_api/certs/prod/

# Subir Dockerfile y código
scp servicioAfip/arca_api/Dockerfile $Username@${ServerIP}:/opt/afip/servicioAfip/arca_api/
scp servicioAfip/arca_api/requirements-fastapi.txt $Username@${ServerIP}:/opt/afip/servicioAfip/arca_api/
scp servicioAfip/arca_api/run.py $Username@${ServerIP}:/opt/afip/servicioAfip/arca_api/
scp -r servicioAfip/arca_api/src $Username@${ServerIP}:/opt/afip/servicioAfip/arca_api/

# Subir archivos pyafipws
scp servicioAfip/requirements.txt $Username@${ServerIP}:/opt/afip/servicioAfip/
scp servicioAfip/setup.py $Username@${ServerIP}:/opt/afip/servicioAfip/
scp servicioAfip/*.py $Username@${ServerIP}:/opt/afip/servicioAfip/
```

---

## Paso 4: Iniciar Servicios en el Servidor

### 4.1 Conectar por SSH

```bash
ssh tu-usuario@XXX.XXX.XXX.XXX
cd /opt/afip
```

### 4.2 Verificar archivos subidos

```bash
ls -la
ls -la servicioAfip/arca_api/certs/homo/
ls -la servicioAfip/arca_api/certs/prod/
```

### 4.3 Iniciar Docker Compose

```bash
# Primera vez (construye la imagen)
docker compose up -d --build

# Ver logs
docker compose logs -f arca_api
```

### 4.4 Verificar que funciona

```bash
# Health check interno
curl http://localhost:8000/health

# Probar login (crear usuario primero si no existe)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@tuempresa.com","password":"TuPassword123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin@tuempresa.com&password=TuPassword123"
```

---

## Paso 5: Configurar Java (TomEE) para conectar a Python

### 5.1 En el servidor, configurar TomEE

Editar `bin/setenv.sh` o `conf/catalina.properties` en TomEE:

```bash
# Agregar al final de setenv.sh
export JAVA_OPTS="$JAVA_OPTS -Dpython.backend.url=http://127.0.0.1:8000"
```

### 5.2 Verificar conectividad desde Java

```bash
# Probar desde el servidor
sudo su - tomee  # o el usuario que corre TomEE
curl http://localhost:8000/health
```

---

## Comandos Útiles de Administración

### Ver estado del servicio
```bash
cd /opt/afip
docker compose ps
docker compose logs --tail 100 arca_api
docker stats
```

### Reiniciar servicio
```bash
cd /opt/afip
docker compose restart arca_api
```

### Actualizar código Python (nueva versión)
```bash
# 1. Subir nuevos archivos desde Windows
# 2. En el servidor:
cd /opt/afip
docker compose down
docker compose build --no-cache arca_api
docker compose up -d
```

### Backup
```bash
# Backup de base de datos y cache
cd /opt/afip
tar czf backup-$(date +%Y%m%d).tar.gz servicioAfip/arca_api/database.db servicioAfip/arca_api/cache/
```

### Acceder al contenedor
```bash
docker compose exec arca_api sh
# Dentro del contenedor:
ls -la /app/certs/
cat /app/.env  # variables de entorno
```

---

## Solución de Problemas

### Puerto 8000 ocupado
```bash
# Ver qué usa el puerto
sudo netstat -tlnp | grep 8000
# Cambiar puerto en docker-compose.yml
# ports:
#   - "127.0.0.1:8001:8000"  # Usar 8001 en lugar de 8000
```

### Error de certificados
```bash
# Verificar que los certificados existen en el contenedor
docker compose exec arca_api ls -la /app/certs/homo/
docker compose exec arca_api ls -la /app/certs/prod/

# Verificar permisos (deben ser legibles)
docker compose exec arca_api cat /app/certs/homo/LIROpriv20260219homo2_crt.crt | head -1
```

### Limpiar cache
```bash
cd /opt/afip
sudo rm -rf servicioAfip/arca_api/cache/*
docker compose restart arca_api
```

---

## Firewall (UFW)

```bash
# Solo exponer puertos necesarios
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (si usás Nginx)
sudo ufw allow 443/tcp   # HTTPS (si usás SSL)
sudo ufw allow 8080/tcp  # TomEE (solo si es necesario desde fuera)
sudo ufw enable

# Puerto 8000 NO debe estar expuesto (solo localhost)
```

---

## Resumen de URLs

| Servicio | URL en Servidor | Acceso |
|----------|-----------------|--------|
| Python API | `http://127.0.0.1:8000` | Solo localhost (Java) |
| Health Check | `http://127.0.0.1:8000/health` | Local only |
| TomEE | `http://servidor:8080` | Público (si se expone) |

---

**¿Necesitás ayuda con algún paso específico?**
