# re-aruba — reverse-engineered management client for Aruba Instant On switches

<p>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Target-Aruba_Instant_On_1830-333333?style=flat-square" alt="Aruba Instant On 1830" />
  <img src="https://img.shields.io/badge/Status-Experimental-orange?style=flat-square" alt="Experimental" />
</p>

> Cliente experimental en Python para interactuar con endpoints de gestión no documentados observados en switches **HPE/Aruba Instant On 1830**.

[🇬🇧 English version](#english-version)

## Resumen rápido

| | |
| --- | --- |
| **Objetivo probado** | Aruba Instant On 1830 |
| **Enfoque** | Ingeniería inversa black-box del flujo de gestión web |
| **Autenticación** | Requiere credenciales válidas |
| **Interfaz observada** | HTTP/XML y endpoints internos no documentados |
| **Estado** | Proof of concept funcional |
| **Posicionamiento** | Primitiva de automatización; no es un motor IaC completo |


`re-aruba` nació de una limitación muy concreta: en la serie 1830 probada, SNMP está disponible para lectura pero no ofrece una vía estándar de escritura para automatizar cambios de estado.

En lugar de intentar convertir SNMP en algo que no es, el proyecto reproduce parte del flujo que utiliza la propia interfaz web del switch: descubre el identificador de sesión embebido en la URI, autentica con credenciales válidas y habla directamente con endpoints internos de gestión para consultar tablas y enviar cambios mediante XML.

Este repositorio documenta ese trabajo de ingeniería inversa y contiene un **proof of concept funcional**, no una API oficial de Aruba/HPE.

## Qué problema resuelve

En el hardware probado, SNMP v1/v2c permite obtener telemetría, pero no realizar operaciones de escritura equivalentes a `SNMP SET`. Eso limita la automatización cuando se necesita, por ejemplo:

- actualizar metadatos del sistema;
- consultar estructuras internas que no aparecen cómodamente por SNMP;
- obtener una copia de la configuración para versionado;
- integrar equipos de gama de entrada en workflows de automatización existentes.

`re-aruba` utiliza los mismos mecanismos HTTP/XML observados en la administración web para cubrir parte de ese espacio.

## Qué encontramos durante el reverse engineering

### 1. Session tracking embebido en la URI

El servidor web del switch puede redirigir a una ruta dinámica similar a:

```text
/csbecf22fa/
```

El cliente captura ese prefijo desde la cabecera `Location` y lo reutiliza en las llamadas posteriores.

Esto no impide utilizar un cliente HTTP convencional: simplemente requiere reproducir el mecanismo de seguimiento que espera el firmware.

### 2. El RSA pertenece al frontend, no a la autorización

La SPA utiliza JavaScript/RSA para proteger el envío de credenciales desde el navegador. Durante la investigación encontramos que el controlador de login también acepta una ruta alternativa que puede invocarse directamente desde un cliente HTTP.

`re-aruba` usa esa ruta con **credenciales válidas**.

Por lo tanto, el proyecto **no evade la autenticación ni obtiene acceso sin credenciales**. Lo que evita es la capa RSA implementada por el frontend para poder automatizar el mismo login desde Python.

### 3. Endpoints internos y tablas virtuales

Una vez autenticado, el firmware expone estructuras internas mediante el endpoint `/wcd`. El cliente puede consultar tablas y convertir las respuestas XML a estructuras Python/JSON.

También se comprobó que determinados cambios pueden enviarse como XML con `action="set"`, evitando depender de una vía SNMP de escritura inexistente en el equipo probado.

El código valida la respuesta del firmware, pero no pretende demostrar por sí solo cómo cada versión concreta persiste internamente esos cambios. Por ese motivo hablamos de **cambios de estado mediante el backend de gestión**, no de escritura directa al kernel o a NVRAM como propiedad garantizada.

## Estado real de la implementación

| Capacidad | Estado | Implementación |
| --- | --- | --- |
| Descubrimiento del prefijo de sesión `/cs...` | ✅ Implementado | `_capture_session_token()` |
| Login sin reproducir el RSA del navegador | ✅ Implementado | `authenticate()` |
| Autenticación sin credenciales | ❌ No | Se requieren usuario y contraseña válidos |
| Consulta de tablas internas | ✅ Implementado | `query_virtual_tables()` |
| Cambio de nombre/ubicación/contacto | ✅ Implementado | `set_system_state()` |
| Exportación de tablas a JSON | ✅ Implementado | `backup_virtual_tables_json()` |
| Descarga de configuración vía endpoint interno | ✅ Implementado | `backup_cli_config()` |
| Motor declarativo/idempotente de IaC | ❌ No | El cliente puede integrarse en pipelines IaC, pero no los reemplaza |
| Soporte Aruba Instant On 1830 | ✅ Objetivo probado | Base del desarrollo |
| Soporte Aruba Instant On 1930 | ⚠️ No verificado | Puede compartir componentes de firmware, pero requiere validación específica |

## Arquitectura

```text
main.py
  │
  ├── core/api.py
  │     ├── sesión HTTP
  │     ├── descubrimiento /cs...
  │     ├── autenticación
  │     ├── consultas /wcd
  │     └── cambios XML
  │
  └── core/backup.py
        ├── exportación de tablas a JSON
        └── descarga de configuración
```

## Instalación

```bash
git clone https://github.com/jnbntc/re-aruba.git
cd re-aruba

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Crear un archivo `.env`:

```dotenv
SWITCH_HOST=192.168.1.10
SWITCH_USER=admin
SWITCH_PASS=change-me
```

Luego:

```bash
python3 main.py
```

> **Importante:** el flujo observado en el firmware utiliza HTTP y el cliente reproduce endpoints internos no documentados. Utilizalo únicamente en una red de gestión confiable y sobre equipos que administrás.

## Uso como librería

```python
from core.api import ArubaRapidControlAPI

switch = ArubaRapidControlAPI(
    host="192.168.1.10",
    username="admin",
    password="change-me",
)

if not switch.authenticate():
    raise RuntimeError("Authentication failed")

state = switch.query_virtual_tables([
    "SystemGlobalSetting",
])

switch.set_system_state(
    sys_name="FNSW-CORE",
    sys_location="Datacenter Rack 42",
    sys_contact="IT Ops",
)
```

## ¿Es Infrastructure as Code?

No por sí solo.

`re-aruba` es una **primitiva de automatización**: ofrece acceso programático a operaciones que el dispositivo no expone mediante una API pública ni mediante SNMP de escritura.

Eso permite utilizarlo desde pipelines, Ansible modules propios, inventarios versionados, jobs de backup o sistemas de reconciliación de estado. Para llamarlo IaC en sentido estricto todavía harían falta, entre otras cosas:

- modelo declarativo de estado deseado;
- idempotencia;
- diff/plan antes de aplicar;
- validación y rollback;
- tests contra múltiples versiones de firmware.

El objetivo del proyecto es proporcionar la capa de acceso necesaria para construir esas integraciones.

## Alcance y compatibilidad

El comportamiento de endpoints internos puede variar entre modelos y versiones de firmware. El código está basado en observaciones realizadas sobre hardware propio de la familia **Aruba Instant On 1830**.

No se debe asumir compatibilidad automática con 1930 u otras familias sin probar:

- autenticación;
- formato y nombre de las tablas;
- semántica de `action="set"`;
- endpoint de descarga de configuración;
- comportamiento tras reboot.

Si probás otro modelo o firmware, un issue con los resultados —sin credenciales, configuraciones privadas ni datos sensibles— ayuda a documentar la matriz de compatibilidad.

## Seguridad y disclaimer

Este proyecto fue desarrollado mediante análisis black-box de hardware administrado por el autor y se publica con fines educativos, de interoperabilidad y automatización de infraestructura.

No es software oficial de HPE/Aruba. Los endpoints utilizados no están documentados públicamente y pueden cambiar sin aviso.

Usalo únicamente sobre dispositivos propios o para los que tengas autorización explícita.

---

<a name="english-version"></a>

# re-aruba — reverse-engineered management client for Aruba Instant On switches

> Experimental Python client for interacting with undocumented management endpoints observed on **HPE/Aruba Instant On 1830** switches.

`re-aruba` started from a concrete limitation: on the tested 1830 hardware, SNMP provides read access but no standard write path for automating state changes.

Instead of trying to turn SNMP into something it is not, the project reproduces part of the workflow used by the switch web UI: it discovers the session identifier embedded in the URI, authenticates with valid credentials, and talks directly to internal management endpoints to query tables and submit XML changes.

This repository documents that reverse-engineering work and provides a **functional proof of concept**. It is not an official Aruba/HPE API.

## What the project actually does

| Capability | Status |
| --- | --- |
| Discover the dynamic `/cs...` session prefix | ✅ Implemented |
| Log in without reproducing the browser-side RSA layer | ✅ Implemented |
| Authenticate without valid credentials | ❌ No |
| Query internal virtual tables | ✅ Implemented |
| Change system name/location/contact | ✅ Implemented |
| Export selected tables as JSON | ✅ Implemented |
| Download configuration through an internal endpoint | ✅ Implemented |
| Provide a declarative/idempotent IaC engine | ❌ No — it is a building block for IaC workflows |
| Aruba Instant On 1830 support | ✅ Primary tested target |
| Aruba Instant On 1930 support | ⚠️ Unverified |

## Reverse-engineered behavior

### URI-based session tracking

The embedded web server can redirect the client to a dynamic path such as `/csbecf22fa/`. The client captures that value from the `Location` header and reuses it for subsequent requests.

### Browser-side RSA versus authentication

The web SPA uses JavaScript/RSA around credential submission. The tested firmware also exposes a login path that can be called directly by an HTTP client.

`re-aruba` invokes that path using **valid credentials**. It bypasses the browser-side RSA mechanism; it does **not** bypass authorization or provide unauthenticated access.

### Internal XML management endpoints

After authentication, the firmware exposes internal state through `/wcd`. The client can query selected tables and parse the returned XML into Python/JSON structures.

For supported settings, the client can also submit XML using `action="set"`, providing a programmatic write path where SNMP write access is unavailable.

The implementation checks the firmware response, but does not claim that every firmware version persists those writes through the same internal storage mechanism.

## Installation

```bash
git clone https://github.com/jnbntc/re-aruba.git
cd re-aruba

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```dotenv
SWITCH_HOST=192.168.1.10
SWITCH_USER=admin
SWITCH_PASS=change-me
```

Run:

```bash
python3 main.py
```

> **Security note:** the observed management flow uses HTTP and undocumented internal endpoints. Use this client only on a trusted management network and only against devices you are authorized to administer.

## IaC positioning

`re-aruba` is an **automation primitive**, not a complete Infrastructure as Code engine.

It can serve as the device-access layer for pipelines, custom Ansible modules, Git-backed backups, or desired-state reconciliation systems. A strict IaC implementation would additionally need declarative state, idempotency, plan/diff, validation, rollback, and broader firmware testing.

## Compatibility

Development is based on black-box observations of hardware from the **Aruba Instant On 1830** family.

Compatibility with 1930 or other families must be validated explicitly. Internal endpoints, table names and persistence semantics may change between models or firmware releases.

## Disclaimer

This project was developed through black-box analysis of hardware administered by the author and is published for educational, interoperability and infrastructure-automation purposes.

It is not official HPE/Aruba software. Use it only on devices you own or are explicitly authorized to manage.
