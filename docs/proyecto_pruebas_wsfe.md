# Proyecto de pruebas con `pyafipws` + `WSFEv1` (homologación)

Este documento describe un **paso a paso mínimo** para armar un proyecto separado y ejecutar pruebas contra **WSAA + WSFEv1** en **homologación**.

---

## 1) Requisitos

- Python 3.x
- Certificados para homologación:
  - `cert.crt` (certificado X.509)
  - `private.key` (clave privada)

---

## 2) Crear carpeta del proyecto

Ejemplo:

```text
afip_pruebas_wsfe/
  certs/
    homo/
      cert.crt
      private.key
  src/
    test_wsaa_wsfe.py
  requirements.txt
  README.md
```

---

## 3) Crear entorno virtual e instalar dependencias

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pyafipws cryptography pysimplesoap
pip freeze > requirements.txt
```

---

## 4) URLs de homologación

`pyafipws` usa estos endpoints (los mismos que están en `ejemplos/factura_electronica.py`):

- WSAA (LoginCms WSDL):

```text
https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl
```

- WSFEv1 (WSDL):

```text
https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL
```

---

## 5) Script mínimo (WSAA -> WSFEv1)

Crear `src/test_wsaa_wsfe.py` con este contenido:

```python
from pyafipws.wsaa import WSAA
from pyafipws.wsfev1 import WSFEv1

import os

# Homologación
URL_WSAA = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
URL_WSFEV1 = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"

# IMPORTANTE: reemplazar por tu CUIT
CUIT = 20123456789

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CERT = os.path.join(BASE_DIR, "certs", "homo", "cert.crt")
PRIVATEKEY = os.path.join(BASE_DIR, "certs", "homo", "private.key")
CACHE = os.path.join(BASE_DIR, "cache")

os.makedirs(CACHE, exist_ok=True)


def main():
    wsaa = WSAA()
    wsfev1 = WSFEv1()

    # 1) Autenticación WSAA: obtiene TA (token/sign)
    ta = wsaa.Autenticar(
        "wsfe",
        CERT,
        PRIVATEKEY,
        wsdl=URL_WSAA,
        cache=CACHE,
        debug=True,
    )

    # 2) Configurar WSFEv1 con el ticket
    wsfev1.Cuit = CUIT
    wsfev1.SetTicketAcceso(ta)

    # 3) Conectar al WSFEv1
    wsfev1.Conectar(CACHE, URL_WSFEV1)

    # 4) Llamada simple de salud (no factura nada)
    wsfev1.Dummy()

    print("AppServerStatus:", wsfev1.AppServerStatus)
    print("DbServerStatus:", wsfev1.DbServerStatus)
    print("AuthServerStatus:", wsfev1.AuthServerStatus)


if __name__ == "__main__":
    main()
```

---

## 6) Ejecutar la prueba

```powershell
python .\src\test_wsaa_wsfe.py
```

Si todo está OK, deberías ver:

- `AppServerStatus: OK`
- `DbServerStatus: OK`
- `AuthServerStatus: OK`

---

## 7) Problemas comunes

- **No tenés `private.key`**
  - No vas a poder firmar el `TRA` (WSAA). Necesitás `cert.crt` + `private.key`.

- **Tenés `.p12/.pfx` en vez de `.crt/.key`**
  - Convertí/extráe a `cert.crt` y `private.key` (ver `docs/afip_paso_a_paso.md` sección 2.4.6).

- **Certificado y clave no coinciden**
  - Validá que correspondan (ver `docs/afip_paso_a_paso.md` sección 2.4.7).

- **Errores SSL / certificados de CA**
  - En algunos entornos puede ser necesario configurar `cacert` (ver `conf/afip_ca_info.crt`).

---

## Estado

Con este proyecto ya podés:

1) Obtener `token/sign` vía WSAA para el servicio `wsfe`.
2) Conectarte a WSFEv1 y probar `Dummy()`.
