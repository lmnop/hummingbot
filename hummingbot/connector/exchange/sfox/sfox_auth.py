from typing import Dict, Any


class SfoxAuth():
    """
    Auth class required by SFOX API
    """
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_ws_key(self) -> Dict[str, Any]:
        """
        Returns the API key for WS auth
        :return: api key as string
        """
        return self.api_key

    def get_headers(self,
                    method: str = None,
                    url: str = None,
                    params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generates authentication headers required by SFOX
        :return: a dictionary of auth headers
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        return headers
