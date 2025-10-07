import requests
from typing import Optional,Dict,Any

class APIClient:
    def __init__(self,base_url: str):
        self.base_url=base_url.rstrip('/')
        self.session=requests.Session()

        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """Базовый метод для выполнения запросов"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else None
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка запроса к {url}: {e}")
            return None
    def get_report(self):
        return self._request('GET','/reports')
    def get_reports(self):
        return self._request('GET','/reports')
    def create_users(self):
        return self._request('POST',)