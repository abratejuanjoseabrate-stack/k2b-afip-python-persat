#!/bin/bash
# Script de backup del Servicio AFIP
# Uso: ./backup.sh

set -e

BACKUP_DIR="/backups/afip-service"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="afip_backup_$DATE.tar.gz"

echo "Creando backup..."

# Crear directorio de backup
mkdir -p $BACKUP_DIR

# Backup de volúmenes Docker
docker run --rm \
  -v afip-cache:/source/cache:ro \
  -v afip-logs:/source/logs:ro \
  -v afip-db:/source/data:ro \
  -v $BACKUP_DIR:/backup \
  alpine:latest \
  tar czf /backup/$BACKUP_FILE -C /source .

# Backup de certificados
tar czf $BACKUP_DIR/certs_$DATE.tar.gz certs/

# Backup de configuración
cp .env $BACKUP_DIR/env_$DATE.backup

# Mantener solo ultimos 10 backups
cd $BACKUP_DIR
ls -t afip_backup_*.tar.gz | tail -n +11 | xargs -r rm
ls -t certs_*.tar.gz | tail -n +11 | xargs -r rm
ls -t env_*.backup | tail -n +11 | xargs -r rm

echo "Backup creado: $BACKUP_DIR/$BACKUP_FILE"
echo "Tamaño: $(du -h $BACKUP_DIR/$BACKUP_FILE | cut -f1)"
