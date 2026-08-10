# re-aruba: Aruba Instant On API Wrapper & Reverse Engineering

`re-aruba` es un cliente API nativo en Python diseñado para automatizar operaciones de capa 2 y extraer telemetría en switches HPE/Aruba (Series 1830/1930). Este proyecto nace como una solución de ingeniería inversa para superar los *vendor lock-ins* de la segmentación de hardware.

## 🧠 El Problema: Vendor Lock-in y SNMP Capado

Los fabricantes de hardware suelen aplicar restricciones de software en sus equipos *entry-level* para forzar actualizaciones hacia líneas *Enterprise*. En el caso de la serie Aruba 1830, el daemon SNMP está capado de fábrica a **SNMPv1/v2c en modo estrictamente Read-Only (RO)**.

Esto imposibilita utilizar herramientas estándar de *Network Automation* para realizar mutaciones de estado (ej. un `SNMP SET` para cambiar el `sysLocation`, apagar un puerto ante un loop, o modificar VLANs dinámicamente). 

## 🛠️ La Investigación (Reverse Engineering)

Analizando el tráfico de red, los volcados de memoria y la arquitectura del frontend web (una Single Page Application), descubrimos cómo opera el firmware cerrado (Broadcom/RapidControl) subyacente:

1. **Sesiones Basadas en URI:** El servidor embebido (GoAhead) no utiliza Cookies estándar, sino seguimiento dinámico inyectado en las cabeceras `Location` (ej. `/csbecf22fa/`), previniendo el uso de clientes HTTP convencionales.
2. **Autenticación Asimétrica en Frontend:** El login cifra las credenciales vía RSA interceptando el POST en JavaScript. `re-aruba` explota una vulnerabilidad lógica en el controlador de sesión (`system.xml?action=login`) para forzar un *fallback* de validación, bypasseando la necesidad de gestionar certificados.
3. **Tablas Virtuales XML (WCD):** El backend almacena la base de datos de red en Tablas Virtuales. Al carecer de acceso SNMP de escritura, interactuamos directamente con el demonio C (`wcd`) inyectando payloads XML crudos (`<SystemGlobalSetting action="set">`), logrando modificar el estado del switch directamente en la NVRAM.

## 🚀 Uso e Implementación de IaC

Este wrapper permite integrar hardware capado a pipelines de *Infrastructure as Code* (IaC) y Agentes de IA.

```bash
# 1. Crear entorno aislado e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configurar el inventario seguro
echo "SWITCH_HOST=192.168.1.10" > .env
echo "SWITCH_USER=admin" >> .env
echo "SWITCH_PASS=supersecret" >> .env

# 3. Ejecutar
python3 main_example.py

### Capacidades del API Client:
*   `authenticate()`: Inicia sesión mediante manipulación del URI y *fallback login*.
*   `set_system_state()`: Mutación de NVRAM para variables del sistema bypasseando el bloqueo SNMP RO.
*   `query_virtual_tables()`: Extracción profunda del estado del kernel de red en formato JSON para telemetría forense.
*   `backup_cli_config()`: Llamada a la subrutina interna de Broadcom para generar un *running-config* tradicional ideal para integraciones con repositorios Git (NSoT).

## 🛡️ Disclaimer
Este proyecto fue desarrollado mediante auditoría *Black-Box* sobre hardware de mi propiedad. Se comparte con fines exclusivamente educativos y para la investigación en automatización de redes (*Network Automation*).