import json
from core.api import ArubaRapidControlAPI

class ArubaBackupManager:
    def __init__(self, api_client: ArubaRapidControlAPI):
        self.api = api_client

    def backup_virtual_tables_json(self, output_filename: str) -> bool:
        """Exporta la DB en JSON para consumo de Agentes de IA / Telemetría."""
        tablas = ["MulticastGlobalSetting", "IGMPMLDSnoopVLANList", "ForwardingStaticTable"]
        try:
            config_data = self.api.query_virtual_tables(tablas)
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def backup_cli_config(self, output_filename: str) -> bool:
        """Descarga el startup-config compilado para repositorios Git/NSoT."""
        target_url = f"{self.api.base_url}{self.api.session_prefix}/hpe/http_download"
        params = {"action": "3", "ssd": "4"}

        try:
            response = self.api.session.get(target_url, params=params, allow_redirects=True)
            response.raise_for_status()
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            return True
        except Exception:
            return False