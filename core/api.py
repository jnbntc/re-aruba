import requests
import xmltodict
import re

class ArubaRapidControlAPI:
    def __init__(self, host: str, username: str, password: str):
        self.base_url = f"http://{host}"
        self.session_prefix = "" 
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (re-aruba-agent/1.0)",
            "Accept": "application/xml, text/xml, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        })
        self.username = username
        self.password = password

    def _capture_session_token(self):
        """Intercepta el URI-based tracking token (/csXXXXXX) del daemon GoAhead."""
        try:
            res = self.session.get(self.base_url, allow_redirects=False)
            if res.status_code in [301, 302] and 'Location' in res.headers:
                loc = res.headers['Location']
                match = re.search(r'(/cs[a-fA-F0-9]+)', loc)
                if match:
                    self.session_prefix = match.group(1)
        except requests.exceptions.RequestException:
            pass

    def authenticate(self) -> bool:
        """Fuerza el fallback de autenticación asimétrica (bypass del RSA frontend)."""
        self._capture_session_token()
        
        login_url = f"{self.base_url}{self.session_prefix}/device/system.xml"
        params = {
            "action": "login",
            "user": self.username,
            "password": self.password,
            "ssd": "true"
        }
        
        try:
            response = self.session.get(login_url, params=params, allow_redirects=False)
            if response.status_code == 200 and "<statusCode>0</statusCode>" in response.text:
                return True
            return False
        except requests.exceptions.RequestException:
            return False

    def query_virtual_tables(self, tables: list) -> dict:
        """Extrae el estado del switch desde la DB interna (Tablas Virtuales)."""
        query_string = "".join([f"{{{table}}}" for table in tables])
        target_url = f"{self.base_url}{self.session_prefix}/wcd?{query_string}"
        
        response = self.session.get(target_url)
        response.raise_for_status()
        return xmltodict.parse(response.text)

    def set_system_state(self, sys_name: str, sys_location: str, sys_contact: str = "") -> bool:
        """
        Bypassea el bloqueo de SNMP de los switches de entrada inyectando 
        mutaciones directamente en memoria vía XML crudo.
        """
        target_url = f"{self.base_url}{self.session_prefix}/wcd?{{SystemGlobalSetting}}"
        
        xml_payload = (
            "<?xml version='1.0' encoding='utf-8'?>"
            "<DeviceConfiguration>"
            f'<SystemGlobalSetting action="set">'
            f'<systemName>{sys_name}</systemName>'
            f'<systemLocation>{sys_location}</systemLocation>'
            f'<systemContact>{sys_contact}</systemContact>'
            f'</SystemGlobalSetting>'
            "</DeviceConfiguration>"
        )

        try:
            response = self.session.post(target_url, data=xml_payload, allow_redirects=False)
            if response.status_code == 200 and "<statusCode>0</statusCode>" in response.text:
                return True
            return False
        except requests.exceptions.RequestException:
            return False