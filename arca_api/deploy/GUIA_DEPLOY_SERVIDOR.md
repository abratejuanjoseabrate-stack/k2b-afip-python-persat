# Guía de Deploy en Servidor - K2B AFIP Python

Guía completa para desplegar el backend Python FastAPI (AFIP) en servidor Ubuntu usando Docker y Git.

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    SERVIDOR UBUNTU                          │
│  ┌─────────────────┐      ┌──────────────────────────┐     │
│  │   TomEE (Java)  │──────▶│  Python Backend (Docker) │     │
│  │   Puerto 8080   │      │  Puerto 127.0.0.1:8000   │     │
│  │   WAR con       │      │  (solo localhost)        │     │
│  │   config.properties│   └──────────────────────────┘     │
│  └─────────────────┘                                       │
│                    │                                        │
│  Configuración: config.properties (dentro del WAR)         │
│  URL Python: http://127.0.0.1:8000                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Repositorios Git

### 1. k2b-afip-python (Backend Python)
- **URL:** `https://gbk.kaizen2b.net/git/ddelias/k2b-afip-python.git`
- **Contenido:** Backend FastAPI + pyafipws + Docker
- **Deploy:** Automático vía `git pull`

### 2. k2b-app-java (Aplicación Java)
- **URL:** Repositorio separado del proyecto Java
- **Contenido:** Aplicación Java + config.properties
- **Deploy:** Manual (WAR)

---

## Configuración Java-Python

### Archivo config.properties (dentro del WAR)

El archivo `src/java/resources/config.properties` se empaqueta dentro del WAR:

```properties
# Configuracion Backend Python AFIP
# Este archivo se empaqueta dentro del WAR

# URL del backend Python (Docker en servidor)
python.backend.url=http://127.0.0.1:8000
```

### Cómo funciona

1. El WAR se despliega en TomEE
2. Al iniciar, `ComprobanteResource` carga `config.properties` desde el classpath
3. Java se conecta a `http://127.0.0.1:8000` (Python en Docker)

**Jerarquía de configuración (Java):**
1. Archivo `config.properties` (dentro del WAR) ← **USADO EN PRODUCCIÓN**
2. System property (`-Dpython.backend.url=...`)
3. Variable de entorno (`PYTHON_BACKEND_URL`)
4. Default: `http://127.0.0.1:8000`

---

## Paso 1: Preparar Servidor Ubuntu

### 1.1 Instalar Docker

```bash
# Conectar por SSH
ssh tu-usuario@SERVIDOR_IP

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Instalar Docker Compose
sudo apt install -y docker-compose-plugin

# Verificar
docker --version
docker compose version
```

### 1.2 Crear directorios

```bash
sudo mkdir -p /opt/afip
sudo chown $USER:$USER /opt/afip
```

---

## Paso 2: Deploy Backend Python (Automático con Git)

### 2.1 Clonar repositorio (primera vez)

```bash
cd /opt
git clone https://gbk.kaizen2b.net/git/ddelias/k2b-afip-python.git afip
cd afip

# Verificar estructura
ls -la
# Debería mostrar: arca_api/, *.py, docker-compose.yml, etc.
```

### 2.2 Subir certificados AFIP (una sola vez)

**Desde tu máquina Windows:**

```powershell
$ServerIP = "XXX.XXX.XXX.XXX"
$Username = "tu-usuario"

# Crear directorios de certificados
ssh ${Username}@${ServerIP} "mkdir -p /opt/afip/arca_api/certs/{homo,prod}"

# Subir certificados de homologación
scp -r servicioAfip\arca_api\certs\homo\* ${Username}@${ServerIP}:/opt/afip/arca_api/certs/homo/

# Subir certificados de producción  
scp -r servicioAfip\arca_api\certs\prod\* ${Username}@${ServerIP}:/opt/afip/arca_api/certs/prod/
```

### 2.3 Iniciar Docker

```bash
cd /opt/afip

# Primera vez (construye imagen)
docker compose up -d --build

# Ver logs
watch docker compose logs -f arca_api
```

### 2.4 Verificar funcionamiento

```bash
# Health check
curl http://localhost:8000/health

# Crear usuario inicial
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@tuempresa.com","password":"TuPassword123"}'
```

---

## Paso 3: Deploy Aplicación Java (Manual)

### 3.1 Generar WAR desde NetBeans

1. En NetBeans: **Clean and Build Project** (F11)
2. El WAR se genera en: `dist/K2BHurlinghamAppWeb.war`

### 3.2 Subir WAR al servidor

**Desde tu máquina Windows:**

```powershell
$ServerIP = "XXX.XXX.XXX.XXX"
$Username = "tu-usuario"

scp dist\K2BHurlinghamAppWeb.war ${Username}@${ServerIP}:/opt/tomee/webapps/
```

### 3.3 Reiniciar TomEE (en servidor)

```bash
ssh tu-usuario@SERVIDOR_IP
sudo systemctl restart tomee
# o
sudo /opt/tomee/bin/shutdown.sh
sudo /opt/tomee/bin/startup.sh
```

### 3.4 Verificar conectividad

```bash
# Ver logs de TomEE
sudo tail -f /opt/tomee/logs/catalina.out | grep -i "python\|config"

# Debería mostrar:
# "Configuracion cargada desde config.properties: http://127.0.0.1:8000"
```

---

## Actualizaciones (Post-Deploy)

### Actualizar Backend Python

```bash
ssh tu-usuario@SERVIDOR_IP
cd /opt/afip

# Bajar cambios del repo Git
git pull

# Reiniciar contenedor
sudo docker compose restart arca_api

# Verificar
sudo docker compose logs --tail 20 arca_api
```

### Actualizar Aplicación Java

```powershell
# En tu máquina Windows - generar nuevo WAR
# NetBeans: Clean and Build

# Subir nuevo WAR
$ServerIP = "XXX.XXX.XXX.XXX"
scp dist\K2BHurlinghamAppWeb.war tu-usuario@${ServerIP}:/opt/tomee/webapps/
```

```bash
# En servidor
sudo systemctl restart tomee
```

---

## Comandos de Administración

### Docker Python

```bash
cd /opt/afip

# Ver estado
docker compose ps
docker compose logs --tail 50 arca_api

# Reiniciar
docker compose restart arca_api

# Detener (conserva datos)
docker compose stop

# Iniciar
docker compose start

# Destruir todo (⚠️ pierde BD SQLite)
docker compose down
```

### Verificación de Conectividad

```bash
# Desde el servidor - probar Python
curl http://localhost:8000/health

# Desde el servidor - probar Java
curl http://localhost:8080/K2BHurlinghamAppWeb/api/comprobantes/padron/a5?cuit=30712330984
```

---

## Troubleshooting

### Error: "No se pudo autenticar con el backend Python"

**Causa:** Java no puede conectar a Python

**Solución:**
```bash
# 1. Verificar Python está corriendo
curl http://localhost:8000/health

# 2. Verificar logs de TomEE
sudo grep -i "python\|config" /opt/tomee/logs/catalina.out

# 3. Verificar config.properties está en el WAR
jar -tf /opt/tomee/webapps/K2BHurlinghamAppWeb.war | grep config.properties
```

### Error de certificados

```bash
# Verificar certificados existen
ls -la /opt/afip/arca_api/certs/homo/
ls -la /opt/afip/arca_api/certs/prod/

# Limpiar cache AFIP
sudo rm -rf /opt/afip/arca_api/cache/*
docker compose restart arca_api
```

### Puerto 8000 ocupado

```bash
# Ver qué usa el puerto
sudo netstat -tlnp | grep 8000

# Cambiar puerto en docker-compose.yml (si es necesario)
# ports:
#   - "127.0.0.1:8001:8000"
```

---

## Estructura Final en Servidor

```
/opt/
├── afip/                              ← Repo k2b-afip-python
│   ├── .git/                          ← Git
│   ├── docker-compose.yml             ← Docker
│   ├── arca_api/
│   │   ├── src/                       ← Código FastAPI
│   │   ├── Dockerfile
│   │   ├── certs/                     ← Certificados AFIP (NO Git)
│   │   │   ├── homo/
│   │   │   └── prod/
│   │   ├── cache/                     ← Tokens AFIP (auto)
│   │   └── database.db                ← SQLite usuarios (auto)
│   └── *.py                           ← pyafipws
│
└── tomee/                             ← TomEE Java
    ├── webapps/
    │   └── K2BHurlinghamAppWeb.war    ← WAR con config.properties
    └── logs/
        └── catalina.out
```

---

## URLs de Acceso

| Servicio | URL Interna (Servidor) | Acceso Externo |
|----------|------------------------|----------------|
| Python API | `http://127.0.0.1:8000` | ❌ No (solo localhost) |
| Python Swagger | `http://127.0.0.1:8000/docs` | ❌ No |
| TomEE | `http://SERVIDOR:8080` | ✅ Sí (si se expone) |
| App Java | `http://SERVIDOR:8080/K2BHurlinghamAppWeb` | ✅ Sí |

---

## Resumen de Comandos

| Acción | Comando |
|--------|---------|
| **Deploy Python** | `cd /opt/afip && git pull && docker compose restart` |
| **Deploy Java** | Subir WAR + `sudo systemctl restart tomee` |
| **Logs Python** | `docker compose logs -f arca_api` |
| **Logs Java** | `sudo tail -f /opt/tomee/logs/catalina.out` |
| **Health Python** | `curl http://localhost:8000/health` |

---

**¿Listo para hacer el primer deploy?** Sigue los pasos 1-3 de esta guía.
