"""
Configuración de la API FastAPI usando Pydantic Settings
Lee variables de entorno desde .env
"""
from pathlib import Path
from typing import Optional
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación usando Pydantic Settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        populate_by_name=True  # Permite usar tanto el alias como el nombre del campo
    )
    
    # Obtener directorio base (arca_api/)
    _base_dir: Optional[Path] = None
    
    @property
    def base_dir(self) -> Path:
        """Directorio base del proyecto"""
        if self._base_dir is None:
            # Obtener desde el archivo actual (src/config.py)
            self._base_dir = Path(__file__).parent.parent.resolve()
        return self._base_dir
    
    # Configuración de API (FastAPI)
    API_TITLE: str = "PyAfipWs API"
    API_DESCRIPTION: str = "API REST para servicios AFIP usando pyafipws"
    API_VERSION: str = "1.0.0"
    API_DOCS_URL: str = "/docs"
    API_REDOC_URL: str = "/redoc"

    # Configuración de servidor (run.py)
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_RELOAD_DIRS_STR: str = Field(default="src", alias="API_RELOAD_DIRS")
    
    # Configuración de logging
    LOG_LEVEL: str = Field(default="INFO", description="Nivel de logging: DEBUG, INFO, WARNING, ERROR")
    LOG_FILE: Optional[str] = Field(default=None, description="Archivo de log (opcional, ej: logs/app.log)")

    # Base de datos
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./database.db",
        description="URL de conexión a la base de datos. SQLite para desarrollo, MySQL para producción"
    )
    DEBUG: bool = Field(default=False, description="Modo debug (muestra queries SQL)")

    # JWT Authentication
    SECRET_KEY: str = Field(
        default="6da1f996e3c013f8d8c2e9da199c66c3c7ad2c983c45c4d028ce9c633a1b1b44",
        description="Clave secreta para firmar JWT. Generar con: openssl rand -hex 32"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="Algoritmo de firma JWT"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Tiempo de expiración del access token en minutos"
    )

    # Debug
    AFIP_DEBUG_WSAA: bool = False
    
    # CUIT
    CUIT: int = 0
    
    # Punto de venta
    PTO_VTA: int = 1
    
    # URLs de servicios AFIP
    URL_WSAA: str = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
    URL_WSFEV1: str = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
    URL_PADRON_A5: str = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl"

    URL_WSAA_PROD: str = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
    URL_WSFEV1_PROD: str = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
    URL_PADRON_A5_PROD: str = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl"
    
    # Paths de certificados (relativos al base_dir)
    # Almacenamos como string, las propiedades devuelven Path
    CERT_PATH_STR: str = Field(default="certs/homo/CERT.crt", alias="CERT_PATH")
    KEY_PATH_STR: str = Field(default="certs/homo/keyArca2", alias="KEY_PATH")
    CACHE_PATH_STR: str = Field(default="cache", alias="CACHE_PATH")
    
    PROD_CERT_PATH_STR: str = Field(default="", alias="PROD_CERT_PATH")
    PROD_KEY_PATH_STR: str = Field(default="", alias="PROD_KEY_PATH")
    PROD_CACHE_PATH_STR: str = Field(default="", alias="PROD_CACHE_PATH")
    
    @property
    def API_RELOAD_DIRS(self) -> list[str]:
        """Parse API_RELOAD_DIRS from string to list"""
        if not self.API_RELOAD_DIRS_STR:
            return ["src"]
        return [p.strip() for p in self.API_RELOAD_DIRS_STR.split(",") if p.strip()] or ["src"]
    
    @field_validator("CUIT", mode="after")
    @classmethod
    def validate_cuit(cls, v):
        """Validar que CUIT esté configurado"""
        if not v or v == 0:
            raise ValueError("Falta configurar CUIT en .env")
        return v
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Validar y crear paths después de la inicialización
        self._validate_paths()
    
    def _validate_paths(self):
        """Validar que existan los certificados y crear directorios de cache"""
        # Paths de certificados (resolver desde base_dir)
        cert_path = (self.base_dir / self.CERT_PATH_STR).resolve()
        key_path = (self.base_dir / self.KEY_PATH_STR).resolve()
        cache_path = (self.base_dir / self.CACHE_PATH_STR).resolve()
        
        # Validar certificados de homologación
        if not cert_path.exists():
            raise FileNotFoundError(f"No existe el certificado: {cert_path}")
        if not key_path.exists():
            raise FileNotFoundError(f"No existe la clave privada: {key_path}")
        
        # Crear directorio de cache si no existe
        cache_path.mkdir(parents=True, exist_ok=True)
        
        # Paths de producción (opcionales)
        if self.PROD_CERT_PATH_STR:
            prod_cert_path = (self.base_dir / self.PROD_CERT_PATH_STR).resolve()
            if not prod_cert_path.exists():
                raise FileNotFoundError(f"No existe el certificado de producción: {prod_cert_path}")
        
        if self.PROD_KEY_PATH_STR:
            prod_key_path = (self.base_dir / self.PROD_KEY_PATH_STR).resolve()
            if not prod_key_path.exists():
                raise FileNotFoundError(f"No existe la clave privada de producción: {prod_key_path}")
        
        if self.PROD_CACHE_PATH_STR:
            prod_cache_path = (self.base_dir / self.PROD_CACHE_PATH_STR).resolve()
            prod_cache_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def CERT_PATH_RESOLVED(self) -> Path:
        """Path resuelto del certificado de homologación"""
        return (self.base_dir / self.CERT_PATH_STR).resolve()
    
    @property
    def KEY_PATH_RESOLVED(self) -> Path:
        """Path resuelto de la clave privada de homologación"""
        return (self.base_dir / self.KEY_PATH_STR).resolve()
    
    @property
    def CACHE_PATH_RESOLVED(self) -> Path:
        """Path resuelto del cache de homologación"""
        return (self.base_dir / self.CACHE_PATH_STR).resolve()
    
    @property
    def PROD_CERT_PATH_RESOLVED(self) -> Optional[Path]:
        """Path resuelto del certificado de producción"""
        if not self.PROD_CERT_PATH_STR:
            return None
        return (self.base_dir / self.PROD_CERT_PATH_STR).resolve()
    
    @property
    def PROD_KEY_PATH_RESOLVED(self) -> Optional[Path]:
        """Path resuelto de la clave privada de producción"""
        if not self.PROD_KEY_PATH_STR:
            return None
        return (self.base_dir / self.PROD_KEY_PATH_STR).resolve()
    
    @property
    def PROD_CACHE_PATH_RESOLVED(self) -> Optional[Path]:
        """Path resuelto del cache de producción"""
        if not self.PROD_CACHE_PATH_STR:
            return None
        return (self.base_dir / self.PROD_CACHE_PATH_STR).resolve()
    
    # Propiedades de compatibilidad (para código existente que usa self.CERT_PATH directamente)
    @property
    def CERT_PATH(self) -> Path:
        """Path del certificado (compatibilidad)"""
        return self.CERT_PATH_RESOLVED
    
    @property
    def KEY_PATH(self) -> Path:
        """Path de la clave privada (compatibilidad)"""
        return self.KEY_PATH_RESOLVED
    
    @property
    def CACHE_PATH(self) -> Path:
        """Path del cache (compatibilidad)"""
        return self.CACHE_PATH_RESOLVED
    
    @property
    def PROD_CERT_PATH(self) -> Optional[Path]:
        """Path del certificado de producción (compatibilidad)"""
        return self.PROD_CERT_PATH_RESOLVED
    
    @property
    def PROD_KEY_PATH(self) -> Optional[Path]:
        """Path de la clave privada de producción (compatibilidad)"""
        return self.PROD_KEY_PATH_RESOLVED
    
    @property
    def PROD_CACHE_PATH(self) -> Optional[Path]:
        """Path del cache de producción (compatibilidad)"""
        return self.PROD_CACHE_PATH_RESOLVED

    def get_wsaa_wsdl(self, env: str) -> str:
        """Obtiene la URL del WSDL de WSAA según el ambiente"""
        return self.URL_WSAA_PROD if env == "prod" else self.URL_WSAA

    def get_wsfev1_wsdl(self, env: str) -> str:
        """Obtiene la URL del WSDL de WSFEv1 según el ambiente"""
        return self.URL_WSFEV1_PROD if env == "prod" else self.URL_WSFEV1

    def get_padron_a5_wsdl(self, env: str) -> str:
        """Obtiene la URL del WSDL de Padrón A5 según el ambiente"""
        if env == "prod":
            if not self.URL_PADRON_A5_PROD:
                raise RuntimeError("Falta configurar URL_PADRON_A5_PROD en .env")
            return self.URL_PADRON_A5_PROD
        return self.URL_PADRON_A5

    def get_cert_paths(self, env: str) -> tuple[Path, Path]:
        """Obtiene los paths de certificado y clave privada según el ambiente"""
        if env == "prod":
            if not self.PROD_CERT_PATH_STR or not self.PROD_KEY_PATH_STR:
                raise RuntimeError(
                    "Falta configurar PROD_CERT_PATH/PROD_KEY_PATH en .env. "
                    "Agrega estas variables con las rutas a tus certificados de producción."
                )
            # Validar que los archivos existan (validación adicional)
            prod_cert = self.PROD_CERT_PATH_RESOLVED
            prod_key = self.PROD_KEY_PATH_RESOLVED
            if not prod_cert or not prod_cert.exists():
                raise FileNotFoundError(
                    f"El certificado de producción no existe: {prod_cert}. "
                    "Verifica que PROD_CERT_PATH apunte a un archivo válido."
                )
            if not prod_key or not prod_key.exists():
                raise FileNotFoundError(
                    f"La clave privada de producción no existe: {prod_key}. "
                    "Verifica que PROD_KEY_PATH apunte a un archivo válido."
                )
            return prod_cert, prod_key
        return self.CERT_PATH_RESOLVED, self.KEY_PATH_RESOLVED

    def get_cache_path(self, env: str) -> Path:
        """Obtiene el path de cache según el ambiente"""
        if env == "prod":
            if not self.PROD_CACHE_PATH_STR:
                # Evita mezclar TA entre ambientes cuando el usuario no configuró PROD_CACHE_PATH
                prod_cache = (self.CACHE_PATH_RESOLVED / "prod").resolve()
                prod_cache.mkdir(parents=True, exist_ok=True)
                return prod_cache
            return self.PROD_CACHE_PATH_RESOLVED
        return self.CACHE_PATH_RESOLVED


# Instancia global de configuración
settings = Settings()
