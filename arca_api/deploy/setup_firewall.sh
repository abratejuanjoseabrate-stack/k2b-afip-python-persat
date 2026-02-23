#!/bin/bash
# setup_firewall.sh - Configuración de firewall para servidor Ubuntu

echo "=== Configurando Firewall (ufw) ==="

# 1. Resetear reglas existentes
sudo ufw --force reset

# 2. Políticas por defecto
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 3. Permitir SSH (¡IMPORTANTE! No bloquear el acceso)
sudo ufw allow 22/tcp comment 'SSH'

# 4. Permitir HTTP/HTTPS (si usás Nginx o TomEE directamente)
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw allow 8080/tcp comment 'TomEE'

# 5. DENEGAR acceso externo al Python (solo localhost)
# El Python backend escucha en 127.0.0.1:8000 por defecto,
# por lo que no es accesible desde fuera automáticamente

# 6. Habilitar firewall
sudo ufw --force enable

echo "Firewall configurado. Estado:"
sudo ufw status verbose

echo ""
echo "Resumen de puertos abiertos:"
echo "- 22: SSH (administración)"
echo "- 80: HTTP (si usás Nginx)"
echo "- 443: HTTPS (si usás certificado SSL)"
echo "- 8080: TomEE (Java backend)"
echo ""
echo "Puerto 8000 (Python) NO está expuesto - solo accesible desde localhost"
