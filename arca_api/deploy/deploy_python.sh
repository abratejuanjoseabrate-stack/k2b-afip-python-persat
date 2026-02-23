#!/bin/bash
# deploy_python_backend.sh - Script de despliegue para servidor Ubuntu

set -e

echo "=== Despliegue AFIP Python Backend ==="

# 1. Crear usuario dedicado (opcional pero recomendado)
sudo useradd -r -s /bin/false -d /opt/arca_api arca_api 2>/dev/null || echo "Usuario arca_api ya existe"

# 2. Crear directorios
sudo mkdir -p /opt/arca_api
sudo mkdir -p /opt/arca_api/logs
sudo mkdir -p /opt/arca_api/certs/homo
sudo mkdir -p /opt/arca_api/certs/prod

# 3. Copiar código (asumiendo que estás en el directorio del proyecto)
echo "Copiando archivos..."
sudo cp -r src /opt/arca_api/
sudo cp -r api /opt/arca_api/ 2>/dev/null || true
sudo cp run.py /opt/arca_api/ 2>/dev/null || true
sudo cp requirements.txt /opt/arca_api/

# 4. Crear virtual environment
echo "Creando entorno virtual..."
cd /opt/arca_api
sudo python3.11 -m venv venv
sudo venv/bin/pip install --upgrade pip
sudo venv/bin/pip install -r requirements.txt

# 5. Configurar permisos
sudo chown -R arca_api:arca_api /opt/arca_api
sudo chmod 750 /opt/arca_api/certs
sudo chmod 640 /opt/arca_api/certs/*/* 2>/dev/null || true

# 6. Crear archivo .env (si no existe)
if [ ! -f /opt/arca_api/.env ]; then
    sudo tee /opt/arca_api/.env > /dev/null <<EOF
# Configuración AFIP Python Backend
APP_ENV=production
LOG_LEVEL=INFO

# AFIP Homologación
CUIT_HOMO=20449965493
CERT_PATH_HOMO=certs/homo/20250224-2130356-20323144008-0e5dc4f0.crt
KEY_PATH_HOMO=certs/homo/20250224-2130356-20323144008-0e5dc4f0.key

# AFIP Producción (completar con datos reales)
CUIT_PROD=20449965493
CERT_PATH_PROD=certs/prod/certificado.crt
KEY_PATH_PROD=certs/prod/private.key
EOF
    echo "Archivo .env creado - EDITAR con datos reales"
fi

# 7. Instalar servicio systemd
sudo cp deploy/arca_api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable arca_api

echo ""
echo "=== Instalación completada ==="
echo "Pasos manuales restantes:"
echo "1. Copiar certificados a /opt/arca_api/certs/"
echo "2. Editar /opt/arca_api/.env con configuración real"
echo "3. Iniciar servicio: sudo systemctl start arca_api"
echo "4. Verificar: sudo systemctl status arca_api"
echo "5. Logs: sudo journalctl -u arca_api -f"
