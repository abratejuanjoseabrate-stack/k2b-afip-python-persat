# Backend Python AFIP - Dockerfile (estructura actual)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd -m -u 1000 arca_api

# Instalar dependencias Python base
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt

# Instalar dependencias FastAPI
COPY arca_api/requirements-fastapi.txt /tmp/requirements-fastapi.txt
RUN pip install -r /tmp/requirements-fastapi.txt

# Instalar pyafipws desde directorio padre
COPY setup.py setup.cfg README.md licencia.txt /tmp/pyafipws/
COPY *.py /tmp/pyafipws/
COPY formatos/ /tmp/pyafipws/formatos/
COPY plantillas/ /tmp/pyafipws/plantillas/
COPY typelib/ /tmp/pyafipws/typelib/
RUN cd /tmp/pyafipws && pip install -e .

# Copiar código
COPY arca_api/src/ ./src/
COPY arca_api/api/ ./api/
COPY arca_api/run.py .

# Crear directorios para certificados y logs
RUN mkdir -p certs/homo certs/prod cache/homo cache/prod logs && \
    chown -R arca_api:arca_api /app

# Cambiar a usuario no-root
USER arca_api

# Puerto expuesto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicio
CMD ["python", "run.py"]
