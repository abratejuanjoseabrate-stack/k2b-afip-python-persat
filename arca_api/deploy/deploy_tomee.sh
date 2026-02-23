#!/bin/bash
# deploy_tomee.sh - Despliegue de TomEE 9 en Ubuntu

set -e

TOMEE_VERSION="9.0.82"
TOMEE_DIR="/opt/tomee"
JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"

echo "=== Despliegue TomEE ${TOMEE_VERSION} ==="

# 1. Descargar TomEE Plume (incluye todas las dependencias Java EE 8)
if [ ! -d "$TOMEE_DIR" ]; then
    echo "Descargando TomEE..."
    cd /tmp
    wget -q "https://archive.apache.org/dist/tomee/tomee-${TOMEE_VERSION}/apache-tomee-${TOMEE_VERSION}-plume.tar.gz"
    
    echo "Extrayendo..."
    sudo tar -xzf "apache-tomee-${TOMEE_VERSION}-plume.tar.gz" -C /opt
    sudo mv "/opt/apache-tomee-plume-${TOMEE_VERSION}" "$TOMEE_DIR"
    rm "apache-tomee-${TOMEE_VERSION}-plume.tar.gz"
fi

# 2. Crear usuario tomee
sudo useradd -r -s /bin/false -d "$TOMEE_DIR" tomee 2>/dev/null || true

# 3. Configurar permisos
sudo chown -R tomee:tomee "$TOMEE_DIR"
sudo chmod +x "$TOMEE_DIR/bin/*.sh"

# 4. Configurar setenv.sh para Java 11
sudo tee "$TOMEE_DIR/bin/setenv.sh" > /dev/null <<EOF
#!/bin/bash
export JAVA_HOME=$JAVA_HOME
export JAVA_OPTS="-Xms512m -Xmx2048m -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
export CATALINA_OPTS="-Djava.awt.headless=true -Dfile.encoding=UTF-8"
EOF
sudo chmod +x "$TOMEE_DIR/bin/setenv.sh"

# 5. Configurar puerto 8080 (por defecto ya está)
# Verificar que server.xml tenga el conector correcto

# 6. Crear directorio para despliegues
sudo mkdir -p "$TOMEE_DIR/webapps"
sudo chown -R tomee:tomee "$TOMEE_DIR/webapps"

echo "TomEE instalado en $TOMEE_DIR"
echo "Para iniciar: sudo $TOMEE_DIR/bin/startup.sh"
echo "Para detener: sudo $TOMEE_DIR/bin/shutdown.sh"
echo "Logs: $TOMEE_DIR/logs/catalina.out"
