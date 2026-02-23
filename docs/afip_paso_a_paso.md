# Implementación con `pyafipws` (AFIP) — Paso a paso detallado (foco: certificados)

## Objetivo
Este documento describe, de forma operativa y detallada, qué necesitás para integrar servicios de AFIP usando la librería `pyafipws`, con énfasis en la parte de **certificados**, **WSAA** (autenticación) y el flujo típico hacia un servicio como **WSFEv1**.

---

## 1) Conceptos clave (qué hace `pyafipws`)
`pyafipws` es un conjunto de clientes/utilidades para consumir Web Services de AFIP. En la mayoría de los casos, el flujo es:

1) **WSAA (LoginCMS)**: obtenés un **Ticket de Acceso (TA)** que trae `token` y `sign`.
2) **WS objetivo** (por ejemplo WSFEv1): consumís el servicio presentando `token`, `sign` y tu `cuit`.

**Idea importante**: sin WSAA (o sin credenciales/certificados válidos para WSAA), no hay `token/sign`, y por lo tanto no podés consumir los servicios finales.

---

## 2) Qué certificados necesitás (y por qué)
### 2.1 Qué se firma y con qué
Para autenticarte en WSAA no usás usuario/clave. Usás un mecanismo de firma digital:

- **Clave privada**: firmás el pedido de login.
- **Certificado público X.509**: AFIP lo usa para verificar que la firma corresponde a tu identidad.

El pedido firmado se envía como **CMS** a `LoginCMS`.

### 2.2 Archivos típicos que vas a manejar
En integraciones con `pyafipws` lo más práctico es tener:

- `cert.crt` (certificado público)
- `private.key` (clave privada)

También podés encontrarte con:

- `*.pem`: archivo en formato PEM (texto base64). Puede contener certificado, clave, o ambos.
- `*.p12` / `*.pfx`: contenedor PKCS#12 (suele traer certificado + clave privada + cadena).

### 2.3 Caso más común: te dan un `.p12/.pfx`
En muchos entornos te entregan un único archivo `.p12`/`.pfx`.

- Ese contenedor normalmente incluye la **clave privada**.
- Suele venir **protegido con contraseña**.

**¿A qué “certificado” corresponde?**

Un archivo `.p12/.pfx` (formato PKCS#12) normalmente es el **paquete completo de tu certificado digital**, y suele incluir:

- **Tu certificado público X.509** (lo que después extraés como `cert.crt`).
- **Tu clave privada asociada** (lo que después extraés como `private.key`).
- **(Opcional) La cadena de certificados** (intermedios/CA), según cómo te lo entregue AFIP o tu proceso interno.

En la práctica, este es el material que usás para autenticarte contra **WSAA**: con la clave privada se firma el `TRA` y con el certificado AFIP verifica la firma para devolverte el `TA` (`token`/`sign`).

Para trabajar cómodo con herramientas y librerías, frecuentemente se convierte a:

- `cert.crt`
- `private.key`

> Si solo tenés un `.crt` sin `.key`, normalmente te falta la clave privada: sin clave privada no podés firmar, por ende no podés loguearte en WSAA.

---

## 2.4) GENERACIÓN DE CERTIFICADOS (PASO A PASO COMPLETO)

Esta es la sección más crítica. Aquí se explica **cómo generar desde cero** el par certificado/clave que necesitás para AFIP.

### 2.4.1) Escenarios posibles

**Escenario A**: Ya tenés un `.p12/.pfx` (te lo dio AFIP, contador, o sistema interno)
- Saltá a la sección **2.4.5 (Conversión de .p12 a .crt + .key)**

**Escenario B**: Tenés que generar todo desde cero
- Seguí desde **2.4.2** en adelante

**Escenario C**: Tenés `.crt` y `.key` ya listos
- Validá con la sección **2.4.7 (Validación del par certificado/clave)**

---

### 2.4.2) Requisitos previos para generar certificados

#### Herramientas necesarias
- **OpenSSL** instalado en tu sistema
  - Windows: descargar desde https://slproweb.com/products/Win32OpenSSL.html o usar Git Bash que trae OpenSSL
  - Linux/Mac: generalmente ya viene instalado
  - Verificar instalación: `openssl version`

#### Información que vas a necesitar
- **CUIT** del contribuyente (11 dígitos sin guiones)
- **Razón social** o nombre
- **Entorno**: homologación o producción
- **Servicio(s)** que vas a consumir (ej: `wsfe`, `wsfex`)

---

### 2.4.3) Paso 1: Generar clave privada

La clave privada es el secreto criptográfico. **Guardala en lugar seguro y nunca la compartas.**

#### Comando OpenSSL (clave RSA 2048 bits)

```bash
openssl genrsa -out private.key 2048
```

**Explicación**:
- `genrsa`: genera una clave RSA
- `-out private.key`: nombre del archivo de salida
- `2048`: tamaño en bits (AFIP acepta 2048 o superior)

#### Variante: clave con contraseña (más segura pero requiere gestión)

```bash
openssl genrsa -aes256 -out private.key 2048
```

Te va a pedir una contraseña. **Recordala**: la vas a necesitar cada vez que uses la clave.

**Resultado**: archivo `private.key` creado.

---

### 2.4.4) Paso 2: Generar CSR (Certificate Signing Request)

El CSR es la solicitud de certificado. Contiene tu información (CUIT, razón social) y la clave pública (derivada de `private.key`).

#### Comando OpenSSL

```bash
openssl req -new -key private.key -out certificado.csr
```

**Te va a pedir información**:

```
Country Name (2 letter code) [AU]: AR
State or Province Name (full name) [Some-State]: Buenos Aires
Locality Name (eg, city) []: CABA
Organization Name (eg, company) [Internet Widgits Pty Ltd]: RAZON SOCIAL DE TU EMPRESA
Organizational Unit Name (eg, section) []: 
Common Name (e.g. server FQDN or YOUR name) []: CUIT 20123456789
Email Address []: tumail@ejemplo.com

Please enter the following 'extra' attributes
to be sent with your certificate request
A challenge password []: [DEJAR EN BLANCO - presionar Enter]
An optional company name []: [DEJAR EN BLANCO - presionar Enter]
```

**Campos críticos**:
- **Country Name**: `AR` (Argentina)
- **Common Name**: `CUIT 20123456789` (reemplazar con tu CUIT real)
- **Organization Name**: razón social registrada en AFIP

**Resultado**: archivo `certificado.csr` creado.

---

### 2.4.5) Paso 3: Obtener el certificado firmado desde AFIP

Ahora tenés que presentar el CSR a AFIP para que te emitan el certificado.

**¿Qué te entrega AFIP en este paso?**

- **Un certificado X.509 emitido/firmado** (típicamente `.crt` / `.cer`), que vas a guardar como `cert.crt`.
- **(Opcional)** la cadena (intermedios/CA), dependiendo de cómo lo descargues.

**Importante**:
- AFIP **NO** te devuelve la clave privada (`private.key`). Esa clave la generaste vos en el paso 1 y debe ser la misma que se usó para crear el `certificado.csr`.
- En `pyafipws`, para WSAA vas a usar el par `cert.crt` + `private.key`.
- Si en tu circuito te entregan un `.p12/.pfx` (contenedor con cert+key), ver sección **2.4.6** para extraer `cert.crt` y `private.key`.

#### 2.4.5.1) Para HOMOLOGACIÓN

**Opción A: Certificado autofirmado (testing rápido)**

Si solo querés probar en homologación, podés generar un certificado autofirmado:

```bash
openssl x509 -req -days 365 -in certificado.csr -signkey private.key -out cert.crt
```

**Explicación**:
- `-days 365`: validez de 1 año
- `-signkey private.key`: autofirmar con tu propia clave
- `-out cert.crt`: archivo de salida

**Limitación**: este certificado NO sirve para producción, solo para pruebas locales o si AFIP homologación lo acepta (depende del servicio).

**Opción B: Solicitar certificado de homologación a AFIP**

Algunos servicios requieren que solicites el certificado a través del portal de AFIP:

1) Entrar a AFIP con clave fiscal
2) Ir a **"Administrador de Certificados Digitales"** o la sección correspondiente al servicio
3) Subir el archivo `certificado.csr`
4) AFIP procesa y te permite descargar el certificado (`.crt`)
5) Guardar como `cert.crt`

#### 2.4.5.2) Para PRODUCCIÓN

**Proceso oficial AFIP** (puede variar según el servicio):

1) Entrar a AFIP con clave fiscal del CUIT administrador
2) Buscar **"Administrador de Certificados Digitales"** o el módulo específico del servicio
3) Generar nueva solicitud de certificado:
   - Subir el CSR (`certificado.csr`)
   - Completar datos solicitados
4) AFIP valida y emite el certificado
5) Descargar el certificado emitido (puede venir como `.crt`, `.cer`, o dentro de un `.p12`)
6) Si viene en `.p12`, seguir a la sección **2.4.6**

**Importante**: el proceso exacto puede cambiar según:
- El servicio (WSFE, WSFEX, etc.)
- Si es monotributista, responsable inscripto, etc.
- Políticas internas de AFIP

**Recomendación**: consultar la documentación oficial de AFIP para el servicio específico o con tu contador/asesor.

---

### 2.4.6) Conversión de .p12/.pfx a .crt + .key (caso muy común)

Si AFIP (o tu proceso interno) te entregó un archivo `.p12` o `.pfx`, necesitás extraer:
- El certificado (`.crt`)
- La clave privada (`.key`)

#### Paso 1: Extraer el certificado

```bash
openssl pkcs12 -in archivo.p12 -clcerts -nokeys -out cert.crt
```

**Explicación**:
- `-in archivo.p12`: archivo de entrada
- `-clcerts`: extraer solo certificados de cliente
- `-nokeys`: no extraer claves privadas (solo certificado)
- `-out cert.crt`: archivo de salida

Te va a pedir la **contraseña del .p12** (si tiene).

#### Paso 2: Extraer la clave privada

```bash
openssl pkcs12 -in archivo.p12 -nocerts -nodes -out private.key
```

**Explicación**:
- `-nocerts`: no extraer certificados (solo clave)
- `-nodes`: no encriptar la clave privada en el archivo de salida (sin passphrase)
- `-out private.key`: archivo de salida

**Variante con contraseña en la clave** (más seguro):

```bash
openssl pkcs12 -in archivo.p12 -nocerts -out private_encrypted.key
```

Esto te va a pedir:
1) Contraseña del `.p12` (para leerlo)
2) Nueva contraseña para proteger `private_encrypted.key`

#### Paso 3: Verificar archivos generados

Deberías tener:
- `cert.crt` (certificado)
- `private.key` (clave privada)

---

### 2.4.7) Validación del par certificado/clave (CRÍTICO)

Antes de usar los certificados en producción, **validá que el par sea correcto**.

#### Validación 1: Verificar que certificado y clave coinciden

```bash
# Obtener hash del certificado
openssl x509 -noout -modulus -in cert.crt | openssl md5

# Obtener hash de la clave
openssl rsa -noout -modulus -in private.key | openssl md5
```

**Los dos hashes deben ser idénticos**. Si son diferentes, el certificado y la clave no corresponden al mismo par.

#### Validación 2: Ver contenido del certificado

```bash
openssl x509 -in cert.crt -text -noout
```

Verificar:
- **Subject**: debe contener tu CUIT y razón social
- **Validity**: fechas de inicio y vencimiento
- **Issuer**: quién firmó el certificado (AFIP o autofirmado)

#### Validación 3: Ver contenido de la clave privada

```bash
openssl rsa -in private.key -check
```

Debe decir `RSA key ok`.

#### Validación 4: Probar firma (simulación)

Crear un archivo de prueba y firmarlo:

```bash
echo "test" > test.txt
openssl dgst -sha256 -sign private.key -out test.sig test.txt
```

Si no da error, la clave está operativa.

---

### 2.4.8) Conversión de formatos (casos especiales)

#### De .crt a .pem

```bash
openssl x509 -in cert.crt -out cert.pem -outform PEM
```

#### De .key a .pem

```bash
cp private.key private.pem
```

(`.key` y `.pem` son generalmente el mismo formato, solo cambia la extensión)

#### Crear .p12 desde .crt + .key (inversa)

```bash
openssl pkcs12 -export -out certificado.p12 -inkey private.key -in cert.crt
```

Te va a pedir una contraseña para proteger el `.p12`.

---

### 2.4.9) Estructura de carpetas recomendada

```
C:\afip\certs\
├── miempresa\
│   ├── homo\
│   │   ├── cert.crt
│   │   ├── private.key
│   │   └── certificado.csr (backup)
│   └── prod\
│       ├── cert.crt
│       ├── private.key
│       └── certificado.csr (backup)
└── README.txt (con fechas de vencimiento y notas)
```

**Permisos recomendados** (Linux/Mac):
```bash
chmod 600 private.key  # solo lectura para el dueño
chmod 644 cert.crt     # lectura para todos
```

**Windows**: usar permisos NTFS para que solo la cuenta de servicio/usuario pueda leer `private.key`.

---

### 2.4.10) Errores comunes y soluciones

#### Error: "unable to load Private Key"
- **Causa**: archivo corrupto o formato incorrecto
- **Solución**: verificar que el archivo sea texto PEM (debe empezar con `-----BEGIN RSA PRIVATE KEY-----`)

#### Error: "bad decrypt" al extraer de .p12
- **Causa**: contraseña incorrecta
- **Solución**: verificar la contraseña del `.p12`

#### Error: certificado y clave no coinciden (hashes diferentes)
- **Causa**: usaste una clave diferente a la que generó el CSR
- **Solución**: regenerar CSR con la clave correcta, o solicitar nuevo certificado

#### Error: AFIP rechaza el certificado
- **Causa**: CUIT en el certificado no coincide con el CUIT operativo
- **Solución**: regenerar certificado con el CUIT correcto en el campo Common Name

#### Error: "certificate has expired"
- **Causa**: certificado vencido
- **Solución**: renovar certificado (generar nuevo CSR y solicitar nuevo certificado a AFIP)

---

### 2.4.11) Renovación de certificados (antes del vencimiento)

Los certificados tienen fecha de expiración (típicamente 1-2 años).

**Proceso de renovación**:

1) Generar nueva clave privada (o reutilizar la anterior, según política de seguridad)
2) Generar nuevo CSR
3) Solicitar nuevo certificado a AFIP
4) Reemplazar archivos en el servidor
5) Probar en homologación antes de pasar a producción

**Recomendación**: renovar **al menos 30 días antes** del vencimiento para evitar interrupciones.

---

### 2.4.12) Checklist final antes de usar los certificados

- [ ] Tengo `cert.crt` y `private.key`
- [ ] Los hashes coinciden (validación con `openssl md5`)
- [ ] El certificado contiene el CUIT correcto
- [ ] El certificado no está vencido
- [ ] La clave privada está protegida (permisos restrictivos)
- [ ] Tengo backup de los archivos en lugar seguro
- [ ] Sé la contraseña (si la clave está encriptada)
- [ ] Tengo certificados separados para homo y prod
- [ ] Probé en homologación antes de ir a producción

---

## 3) Homologación vs Producción (separación obligatoria)
AFIP tiene dos entornos:

- **Homologación**: pruebas.
- **Producción**: operaciones reales.

Recomendación operativa:

- Mantener **certificados y configuración separados**.
- Usar carpetas diferentes, por ejemplo:

```
C:\afip\certs\miempresa\homo\cert.crt
C:\afip\certs\miempresa\homo\private.key

C:\afip\certs\miempresa\prod\cert.crt
C:\afip\certs\miempresa\prod\private.key
```

**Por qué**:
- Evitás confundir endpoints.
- Evitás emitir comprobantes reales por error.
- Simplificás debugging: si falla en homo, no tocás prod.

---

## 4) Habilitaciones en AFIP (Administrador de Relaciones)
Aunque tengas certificados correctos, AFIP puede rechazar el acceso si el CUIT no tiene relación/habilitación para el servicio.

### 4.1 Qué hacer
1) Entrar a AFIP con el CUIT administrador.
2) Ir a **Administrador de Relaciones**.
3) Adherir/habilitar el servicio que querés consumir (por ejemplo **WSFEv1**).
4) Confirmar que la relación quedó activa para el CUIT que va a operar.

### 4.2 Errores típicos si esto está mal
- Token válido, pero el WS final devuelve error de autorización.
- El service pedido al WSAA no coincide con el habilitado.

---

## 5) WSAA paso a paso (detallado)
### 5.1 Qué es el `TRA`
El `TRA` es un XML que representa tu solicitud de acceso. Contiene:

- `uniqueId`: identificador único de la solicitud.
- `generationTime`: fecha/hora de generación.
- `expirationTime`: fecha/hora de expiración.
- `service`: nombre del servicio para el cual pedís acceso (ej: `wsfe`, `wsfex`, etc.).

**Detalle crítico**:
- AFIP valida las fechas; si el reloj del servidor/PC está corrido, WSAA puede rechazar la solicitud.

### 5.2 Qué es el CMS
El `TRA` se firma con tu **clave privada** y se empaqueta con tu **certificado** en un CMS. Ese CMS es lo que se envía a:

- `WSAA.LoginCMS`

### 5.3 Qué devuelve WSAA
Un `TA` (Ticket de Acceso) que contiene:

- `token`
- `sign`
- vencimiento

El `token/sign` dura un tiempo limitado. Lo típico es:

- Guardarlo en cache/archivo.
- Renovarlo cuando vence.

---

## 6) Consumir el Web Service final (ejemplo conceptual con WSFEv1)
Una vez que tenés `token/sign`:

1) Inicializás el cliente del WS (por ejemplo WSFEv1).
2) Informás:
   - `token`
   - `sign`
   - `cuit`
3) Consultás parámetros mínimos (según el WS):
   - puntos de venta
   - tipos de comprobante
   - tipos de documento
   - alícuotas IVA
4) Ejecutás la operación de negocio (por ejemplo solicitar CAE).
5) Persistís respuesta (CAE, vencimiento, número, observaciones).

---

## 7) Checklist específico de certificados (para evitar trabas)
### 7.1 Integridad del par
- Tenés **certificado** (`.crt/.pem`).
- Tenés **clave privada** (`.key/.pem`).
- El certificado y la clave corresponden al mismo par (si no, la firma falla).

### 7.2 Permisos
- La cuenta que ejecuta Python debe poder leer ambos archivos.
- No guardarlos en el repo.

### 7.3 Clave con contraseña
Si tu `private.key` está encriptada con passphrase:
- Necesitás contemplar cómo se va a suministrar esa passphrase (depende de la implementación concreta y de cómo firme `pyafipws`).
- En servidores, muchas integraciones usan clave sin passphrase y protegen el acceso por permisos del sistema.

### 7.4 Hora del sistema
- Confirmar que el reloj está correcto (NTP si es un servidor).

---

## 8) Servicios AFIP que “en teoría” podrías implementar con `pyafipws`
La disponibilidad exacta depende de la versión del repo, pero `pyafipws` se usa típicamente para:

### 8.1 Autenticación
- **WSAA** (Web Services de Autenticación y Autorización): base para obtener `token/sign`.

### 8.2 Facturación / comprobantes
- **WSFEv1**: Factura Electrónica (mercado interno).
- **WSFEX**: Factura Electrónica de Exportación.
- **WSMTXCA**: Esquema alternativo de comprobantes (según caso de uso).

### 8.3 Consultas
- **WS_SR_PADRON**: consultas de padrón/datos del contribuyente.

> Para listar con certeza “todos los módulos” disponibles en tu copia exacta, hay que enumerar los módulos/archivos del repo (varía por versión).

---

## 9) Datos que conviene definir antes de escribir código
- Servicio objetivo: `wsfe` / `wsfex` / `wsmtxca` / padrón / otro.
- Entorno: homologación o producción.
- CUIT operativo.
- Rutas a `cert.crt` y `private.key`.
- Estrategia de cache del `TA`.

