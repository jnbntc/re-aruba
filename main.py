import os
from dotenv import load_dotenv
from core.api import ArubaRapidControlAPI
from core.backup import ArubaBackupManager

def main():
    load_dotenv()
    
    # Credenciales vía variables de entorno (Zero Trust)
    HOST = os.getenv("SWITCH_HOST", "192.168.1.10")
    USER = os.getenv("SWITCH_USER", "admin")
    PASS = os.getenv("SWITCH_PASS", "admin")

    print(f"[*] Conectando a {HOST}...")
    switch = ArubaRapidControlAPI(HOST, USER, PASS)

    if switch.authenticate():
        print("[+] Autenticación exitosa (Bypass RSA -> OK).")
        
        # 1. Mutación de Estado (Bypass de SNMP Read-Only)
        print("[*] Inyectando telemetría de ubicación...")
        switch.set_system_state("FNSW-CORE", "Datacenter Rack 42", "IT Ops")
        
        # 2. Extracción de Configuración
        print("[*] Extrayendo running-config...")
        manager = ArubaBackupManager(switch)
        manager.backup_cli_config(f"{HOST}_backup.cfg")
        
        print("[✔] Ejecución finalizada.")
    else:
        print("[-] Error de autenticación.")

if __name__ == "__main__":
    main()