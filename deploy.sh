#!/bin/bash
# Script de deploy del Servicio AFIP en VPS
# Uso: ./deploy.sh [production|homologacion]

set -e

ENV=${1:-homologacion}
echo "🚀 Deployando Servicio AFIP en modo: $ENV"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar que existe .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: No existe archivo .env${NC}"
    echo "Copia .env.example a .env y configura tus variables"
    exit 1
fi

# Verificar CUIT configurado
if grep -q "^AFIP_CUIT=$" .env || grep -q "^AFIP_CUIT=$" .env; then
    echo -e "${RED}❌ Error: AFIP_CUIT no configurado en .env${NC}"
    exit 1
fi

# Verificar certificados
if [ ! -d "certs/homo" ] || [ ! -f "certs/homo/CERT.crt" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: No se encontraron certificados de homologación${NC}"
    echo "Copia tus certificados a certs/homo/"
fi

# Pull de imágenes base
echo -e "${YELLOW}📦 Descargando imágenes Docker...${NC}"
docker-compose pull

# Construir imagen
echo -e "${YELLOW}🔨 Construyendo imagen...${NC}"
docker-compose build --no-cache

# Detener servicio existente si hay
echo -e "${YELLOW}🛑 Deteniendo servicio existente...${NC}"
docker-compose down || true

# Iniciar servicio
echo -e "${YELLOW}▶️  Iniciando servicio...${NC}"
docker-compose up -d

# Esperar a que inicie
echo -e "${YELLOW}⏳ Esperando inicio...${NC}"
sleep 5

# Verificar health check
echo -e "${YELLOW}🏥 Verificando salud del servicio...${NC}"
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Servicio funcionando correctamente${NC}"
    echo ""
    echo -e "${GREEN}🌐 URLs disponibles:${NC}"
    echo "  - API: http://localhost:8000"
    echo "  - Docs: http://localhost:8000/docs"
    echo "  - Health: http://localhost:8000/health"
    echo ""
    echo -e "${GREEN}📊 Comandos útiles:${NC}"
    echo "  Ver logs: docker-compose logs -f"
    echo "  Reiniciar: docker-compose restart"
    echo "  Detener: docker-compose down"
else
    echo -e "${RED}❌ Error: El servicio no respondió correctamente${NC}"
    echo "Revisa los logs: docker-compose logs"
    exit 1
fi
