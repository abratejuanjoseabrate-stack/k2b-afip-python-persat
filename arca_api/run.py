"""
Script para iniciar el servidor FastAPI
"""
import uvicorn
import sys
from pathlib import Path
import socket

# Agregar el directorio padre al path para importar pyafipws
base_dir = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(base_dir))

# Agregar arca_api al path para imports relativos
arca_api_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(arca_api_dir))

# Intentar importar desde nueva estructura primero, luego antigua
try:
    from src.config import settings
    app_module = "src.main:app"
    print("Usando nueva estructura (src/)")
except ImportError:
    from api.config import settings
    app_module = "api.main:app"
    print("Usando estructura antigua (api/)")

if __name__ == "__main__":
    host = settings.API_HOST
    port = settings.API_PORT

    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = None

    print("Servidor FastAPI iniciado. Accesos:")
    print(f"- Root:   http://127.0.0.1:{port}/")
    print(f"- Docs:   http://127.0.0.1:{port}/docs")
    print(f"- ReDoc:  http://127.0.0.1:{port}/redoc")
    if local_ip and local_ip != "127.0.0.1":
        print(f"- LAN:    http://{local_ip}:{port}/ (y /docs)")

    # Actualizar reload_dirs para incluir src/ si existe
    reload_dirs = settings.API_RELOAD_DIRS
    if "src" not in reload_dirs:
        reload_dirs = list(reload_dirs) + ["src"]

    uvicorn.run(
        app_module,
        host=host,
        port=port,
        reload=settings.API_RELOAD,
        reload_dirs=reload_dirs
    )
